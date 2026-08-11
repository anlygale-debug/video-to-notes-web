import json
import re
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from vtn.access import AccessManager, install_access_middleware
from vtn.adapters.media import FakePlatformMedia
from vtn.adapters.llm import FakeLLM
from vtn.adapters.transcription import FakeTranscriber
from vtn.invite_admin import create_invite_admin_app
from vtn.llm_provider import LLMModelCatalog, LLMProviderStore
from vtn.storage.sqlite import SQLiteRepository
from vtn.transcription_provider import TranscriptionProviderStore
from vtn.web.api import create_v3_router
from vtn.workflows.parser import ParserWorkflow
from vtn.workflows.notes import NoteWorkflow


class InviteAdminHttpTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repository = SQLiteRepository(Path(self.tempdir.name) / "admin.sqlite3")
        self.repository.migrate()
        self.access = AccessManager(
            self.repository, "test-session-secret", secure_cookie=False
        )
        self.admin = TestClient(
            create_invite_admin_app(
                self.repository,
                self.access,
                csrf_token="known-admin-csrf",
            )
        )
        self.headers = {"X-VTN-Admin-CSRF": "known-admin-csrf"}

    def tearDown(self):
        self.repository.close()
        self.tempdir.cleanup()

    def _create_grant(self, label="张三｜第一轮测试"):
        return self.admin.post(
            "/api/grants",
            headers=self.headers,
            json={
                "label": label,
                "transcription_minutes": 60,
                "note_generations": 10,
                "max_video_minutes": 20,
            },
        )

    def test_create_returns_code_once_and_list_never_reveals_it(self):
        blocked = self.admin.post(
            "/api/grants",
            json={
                "label": "无令牌请求",
                "transcription_minutes": 30,
                "note_generations": 5,
                "max_video_minutes": 20,
            },
        )
        self.assertEqual(blocked.status_code, 403)

        created = self._create_grant()
        self.assertEqual(created.status_code, 201)
        payload = created.json()
        self.assertEqual(payload["grant"]["label"], "张三｜第一轮测试")
        self.assertEqual(payload["grant"]["remaining_transcription_minutes"], 60)
        self.assertEqual(payload["grant"]["remaining_note_generations"], 10)
        self.assertTrue(payload["invite_code"].startswith("VTN-"))
        self.assertIn("<svg", payload["qr_svg"])

        invite_code = payload["invite_code"]
        listed = self.admin.get("/api/grants", headers=self.headers)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["items"]), 1)
        self.assertNotIn(invite_code, listed.text)
        self.assertNotIn("invite_code", listed.text)
        self.assertNotIn("qr_svg", listed.text)

        page = self.admin.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertRegex(page.text, re.compile(r'name="vtn-admin-csrf"'))
        self.assertNotIn(invite_code, page.text)

    def test_revoke_invalidates_the_code_and_an_existing_user_session(self):
        created = self._create_grant("李四｜访谈测试").json()
        access_id = created["grant"]["id"]
        invite_code = created["invite_code"]

        user_app = FastAPI()
        user_app.include_router(
            create_v3_router(
                self.repository,
                parser_workflow=object(),
                access_manager=self.access,
            )
        )
        install_access_middleware(user_app, self.access)
        user = TestClient(user_app)
        self.assertEqual(
            user.post("/api/v3/access/login", json={"code": invite_code}).status_code,
            200,
        )
        self.assertTrue(user.get("/api/v3/access/status").json()["authenticated"])

        missing_token = self.admin.delete(f"/api/grants/{access_id}")
        self.assertEqual(missing_token.status_code, 403)
        revoked = self.admin.delete(
            f"/api/grants/{access_id}", headers=self.headers
        )
        self.assertEqual(revoked.status_code, 200)
        self.assertEqual(revoked.json()["grant"]["status"], "revoked")

        self.assertFalse(user.get("/api/v3/access/status").json()["authenticated"])
        self.assertEqual(
            TestClient(user_app)
            .post("/api/v3/access/login", json={"code": invite_code})
            .status_code,
            401,
        )

    def test_existing_code_can_be_verified_for_local_browser_import(self):
        first = self._create_grant("owner").json()
        second = self._create_grant("朋友 A").json()

        verified = self.admin.post(
            f"/api/grants/{first['grant']['id']}/verify-code",
            headers=self.headers,
            json={"invite_code": first["invite_code"]},
        )
        self.assertEqual(verified.status_code, 200)
        self.assertEqual(verified.json(), {"verified": True})

        wrong_grant = self.admin.post(
            f"/api/grants/{second['grant']['id']}/verify-code",
            headers=self.headers,
            json={"invite_code": first["invite_code"]},
        )
        self.assertEqual(wrong_grant.status_code, 422)

        missing_token = self.admin.post(
            f"/api/grants/{first['grant']['id']}/verify-code",
            json={"invite_code": first["invite_code"]},
        )
        self.assertEqual(missing_token.status_code, 403)

    def test_invalid_limits_are_rejected_without_creating_a_grant(self):
        response = self.admin.post(
            "/api/grants",
            headers=self.headers,
            json={
                "label": "   ",
                "transcription_minutes": 0,
                "note_generations": 0,
                "max_video_minutes": 0,
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            self.admin.get("/api/grants", headers=self.headers).json()["items"],
            [],
        )

    def test_editing_remaining_quota_preserves_usage_and_records_the_change(self):
        created = self._create_grant("owner").json()
        access_id = created["grant"]["id"]
        invite_code = created["invite_code"]

        parser = ParserWorkflow(
            self.repository,
            FakePlatformMedia(),
            FakeTranscriber("完整逐字稿。" * 120),
            run_in_background=False,
            access_manager=self.access,
        )
        user_app = FastAPI()
        user_app.include_router(
            create_v3_router(
                self.repository,
                parser_workflow=parser,
                access_manager=self.access,
            )
        )
        install_access_middleware(user_app, self.access)
        user = TestClient(user_app)
        user.post("/api/v3/access/login", json={"code": invite_code})
        first_parse = user.post(
            "/api/v3/parser/tasks",
            json={
                "source_url": "https://example.test/first-video",
                "include_transcript": False,
            },
        ).json()["task"]
        user.post(
            f"/api/v3/parser/records/{first_parse['record_id']}/transcription-tasks",
            json={"provider": "cloudflare"},
        )
        before = user.get("/api/v3/access/status").json()["access"]
        self.assertEqual(before["remaining_transcription_seconds"], 3000)

        edited = self.admin.patch(
            f"/api/grants/{access_id}",
            headers=self.headers,
            json={
                "label": "owner｜长视频",
                "remaining_transcription_minutes": 100,
                "remaining_note_generations": 12,
                "max_video_minutes": 60,
            },
        )
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.json()["grant"]["label"], "owner｜长视频")
        self.assertEqual(
            edited.json()["grant"]["remaining_transcription_minutes"], 100
        )
        self.assertEqual(edited.json()["grant"]["remaining_note_generations"], 12)
        self.assertEqual(edited.json()["grant"]["max_video_minutes"], 60)
        self.assertEqual(edited.json()["warnings"], [])

        after = user.get("/api/v3/access/status").json()["access"]
        self.assertEqual(after["label"], "owner｜长视频")
        self.assertEqual(after["remaining_transcription_seconds"], 6000)
        self.assertEqual(after["remaining_note_generations"], 12)
        self.assertEqual(after["max_video_seconds"], 3600)

        second_parse = user.post(
            "/api/v3/parser/tasks",
            json={
                "source_url": "https://example.test/second-video",
                "include_transcript": False,
            },
        ).json()["task"]
        user.post(
            f"/api/v3/parser/records/{second_parse['record_id']}/transcription-tasks",
            json={"provider": "cloudflare"},
        )
        self.assertEqual(
            user.get("/api/v3/access/status").json()["access"][
                "remaining_transcription_seconds"
            ],
            5400,
        )

        history = self.admin.get(
            f"/api/grants/{access_id}/adjustments", headers=self.headers
        )
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()["items"]), 1)
        adjustment = history.json()["items"][0]
        self.assertEqual(adjustment["previous"]["remaining_transcription_minutes"], 50)
        self.assertEqual(adjustment["next"]["remaining_transcription_minutes"], 100)
        self.assertEqual(adjustment["previous"]["max_video_minutes"], 20)
        self.assertEqual(adjustment["next"]["max_video_minutes"], 60)

    def test_edit_warns_when_one_video_can_exceed_remaining_quota(self):
        created = self._create_grant("额度提醒").json()
        response = self.admin.patch(
            f"/api/grants/{created['grant']['id']}",
            headers=self.headers,
            json={
                "label": "额度提醒",
                "remaining_transcription_minutes": 30,
                "remaining_note_generations": 5,
                "max_video_minutes": 60,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["warnings"],
            ["单视频上限高于剩余转录额度，请同时补充转录额度。"],
        )

    def test_cloudflare_credentials_are_verified_and_never_returned(self):
        class SuccessfulVerifier:
            def verify(self, account_id, api_token):
                self.account_id = account_id
                self.api_token = api_token

        verifier = SuccessfulVerifier()
        provider_store = TranscriptionProviderStore(
            Path(self.tempdir.name) / "transcription-provider.json",
            local_model_name="tiny",
        )
        admin = TestClient(
            create_invite_admin_app(
                self.repository,
                self.access,
                csrf_token="known-admin-csrf",
                provider_store=provider_store,
                cloudflare_verifier=verifier,
            )
        )
        secret = "cloudflare-test-token-that-must-never-return"

        saved = admin.put(
            "/api/transcription-provider/cloudflare",
            headers=self.headers,
            json={
                "account_id": "0123456789abcdef0123456789abcdef",
                "api_token": secret,
            },
        )
        status = admin.get(
            "/api/transcription-provider",
            headers=self.headers,
        )

        self.assertEqual(saved.status_code, 200)
        self.assertEqual(verifier.account_id, "0123456789abcdef0123456789abcdef")
        self.assertEqual(verifier.api_token, secret)
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["active_provider"], "local")
        self.assertTrue(status.json()["cloudflare"]["configured"])
        self.assertTrue(status.json()["cloudflare"]["token_saved"])
        self.assertEqual(
            status.json()["cloudflare"]["account_id"],
            "0123456789abcdef0123456789abcdef",
        )
        self.assertNotIn(secret, saved.text)
        self.assertNotIn(secret, status.text)

    def test_cloudflare_account_can_be_edited_without_reentering_saved_token(self):
        class RecordingVerifier:
            def __init__(self):
                self.calls = []

            def verify(self, account_id, api_token):
                self.calls.append((account_id, api_token))

        verifier = RecordingVerifier()
        provider_store = TranscriptionProviderStore(
            Path(self.tempdir.name) / "transcription-provider.json",
            local_model_name="tiny",
        )
        admin = TestClient(
            create_invite_admin_app(
                self.repository,
                self.access,
                csrf_token="known-admin-csrf",
                provider_store=provider_store,
                cloudflare_verifier=verifier,
            )
        )
        original_token = "cloudflare-original-secret-token"
        admin.put(
            "/api/transcription-provider/cloudflare",
            headers=self.headers,
            json={
                "account_id": "0123456789abcdef0123456789abcdef",
                "api_token": original_token,
            },
        )

        edited = admin.put(
            "/api/transcription-provider/cloudflare",
            headers=self.headers,
            json={
                "account_id": "fedcba9876543210fedcba9876543210",
                "api_token": "",
            },
        )

        self.assertEqual(edited.status_code, 200)
        self.assertEqual(
            verifier.calls[-1],
            ("fedcba9876543210fedcba9876543210", original_token),
        )
        self.assertEqual(
            edited.json()["cloudflare"]["account_id"],
            "fedcba9876543210fedcba9876543210",
        )
        self.assertNotIn(original_token, edited.text)

    def test_verified_cloudflare_provider_can_be_activated_without_restart(self):
        class SuccessfulVerifier:
            def verify(self, _account_id, _api_token):
                pass

        provider_store = TranscriptionProviderStore(
            Path(self.tempdir.name) / "transcription-provider.json",
            local_model_name="tiny",
        )
        admin = TestClient(
            create_invite_admin_app(
                self.repository,
                self.access,
                csrf_token="known-admin-csrf",
                provider_store=provider_store,
                cloudflare_verifier=SuccessfulVerifier(),
            )
        )
        admin.put(
            "/api/transcription-provider/cloudflare",
            headers=self.headers,
            json={
                "account_id": "0123456789abcdef0123456789abcdef",
                "api_token": "cloudflare-valid-secret-token",
            },
        )

        switched = admin.post(
            "/api/transcription-provider/switch",
            headers=self.headers,
            json={"provider": "cloudflare"},
        )
        status = admin.get(
            "/api/transcription-provider",
            headers=self.headers,
        )

        self.assertEqual(switched.status_code, 200)
        self.assertEqual(switched.json()["active_provider"], "cloudflare")
        self.assertEqual(status.json()["active_provider"], "cloudflare")

    def test_deleting_active_cloudflare_credentials_falls_back_to_local(self):
        class SuccessfulVerifier:
            def verify(self, _account_id, _api_token):
                pass

        provider_store = TranscriptionProviderStore(
            Path(self.tempdir.name) / "transcription-provider.json",
            local_model_name="tiny",
        )
        admin = TestClient(
            create_invite_admin_app(
                self.repository,
                self.access,
                csrf_token="known-admin-csrf",
                provider_store=provider_store,
                cloudflare_verifier=SuccessfulVerifier(),
            )
        )
        secret = "cloudflare-secret-that-will-be-deleted"
        admin.put(
            "/api/transcription-provider/cloudflare",
            headers=self.headers,
            json={
                "account_id": "0123456789abcdef0123456789abcdef",
                "api_token": secret,
            },
        )
        admin.post(
            "/api/transcription-provider/switch",
            headers=self.headers,
            json={"provider": "cloudflare"},
        )

        deleted = admin.delete(
            "/api/transcription-provider/cloudflare",
            headers=self.headers,
        )
        status = admin.get(
            "/api/transcription-provider",
            headers=self.headers,
        )

        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["active_provider"], "local")
        self.assertFalse(deleted.json()["cloudflare"]["configured"])
        self.assertFalse(status.json()["cloudflare"]["token_saved"])
        self.assertNotIn(secret, deleted.text)
        self.assertNotIn(secret, status.text)

    def test_cloudflare_usage_is_reported_as_an_app_local_estimate(self):
        provider_store = TranscriptionProviderStore(
            Path(self.tempdir.name) / "transcription-provider.json",
        )

        provider_store.record_cloudflare_usage(600)
        usage = provider_store.status()["usage"]

        self.assertEqual(usage["today_transcription_minutes"], 10)
        self.assertAlmostEqual(usage["estimated_used_neurons"], 466.3)
        self.assertAlmostEqual(
            usage["estimated_remaining_free_minutes"],
            (10_000 - 466.3) / 46.63,
            places=1,
        )
        self.assertEqual(usage["scope"], "this_app_only")

    def test_existing_llm_settings_appear_as_a_safe_disabled_profile(self):
        settings_path = Path(self.tempdir.name) / "settings.json"
        secret = "deepseek-secret-that-must-never-return"
        settings_path.write_text(
            json.dumps(
                {
                    "api_base": "https://api.deepseek.com/v1",
                    "api_key": secret,
                    "model": "deepseek-chat",
                }
            ),
            encoding="utf-8",
        )
        llm_store = LLMProviderStore(settings_path, default_enabled=False)
        admin = TestClient(
            create_invite_admin_app(
                self.repository,
                self.access,
                csrf_token="known-admin-csrf",
                llm_store=llm_store,
            )
        )

        response = admin.get("/api/llm-providers", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["notes_enabled"])
        self.assertEqual(payload["active_profile"]["label"], "DeepSeek")
        self.assertEqual(payload["active_profile"]["model"], "deepseek-chat")
        self.assertTrue(payload["active_profile"]["api_key_saved"])
        self.assertNotIn(secret, response.text)

    def test_version_two_llm_profiles_migrate_to_the_paid_channel(self):
        settings_path = Path(self.tempdir.name) / "settings-v2.json"
        settings_path.write_text(
            json.dumps(
                {
                    "version": 2,
                    "notes_enabled": True,
                    "active_profile_id": "paid-old",
                    "profiles": [
                        {
                            "id": "paid-old",
                            "label": "原有付费模型",
                            "api_base": "https://api.example.test/v1",
                            "api_key": "legacy-secret",
                            "model": "legacy-model",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        status = LLMProviderStore(settings_path).status()

        self.assertEqual(status["active_channel"], "paid")
        self.assertEqual(status["channels"]["paid"]["default_profile_id"], "paid-old")
        self.assertEqual(status["profiles"][0]["channel"], "paid")
        self.assertEqual(status["profiles"][0]["protocol"], "openai_chat")
        self.assertTrue(status["profiles"][0]["enabled"])

    def test_llm_profiles_can_be_created_edited_activated_and_deleted(self):
        store = LLMProviderStore(
            Path(self.tempdir.name) / "settings.json",
            default_enabled=False,
        )
        admin = TestClient(
            create_invite_admin_app(
                self.repository,
                self.access,
                csrf_token="known-admin-csrf",
                llm_store=store,
            )
        )
        first_secret = "deepseek-profile-secret"
        second_secret = "openrouter-profile-secret"

        first = admin.post(
            "/api/llm-providers",
            headers=self.headers,
            json={
                "label": "DeepSeek 常用",
                "api_base": "https://api.deepseek.com/v1",
                "api_key": first_secret,
                "model": "deepseek-chat",
            },
        )
        second = admin.post(
            "/api/llm-providers",
            headers=self.headers,
            json={
                "label": "OpenRouter 备用",
                "api_base": "https://openrouter.ai/api/v1",
                "api_key": second_secret,
                "model": "openai/gpt-4.1-mini",
            },
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        first_id = first.json()["profile"]["id"]
        second_id = second.json()["profile"]["id"]
        self.assertTrue(first.json()["profile"]["active"])
        self.assertNotIn(first_secret, first.text)
        self.assertNotIn(second_secret, second.text)

        edited = admin.put(
            f"/api/llm-providers/{first_id}",
            headers=self.headers,
            json={
                "label": "DeepSeek 主线路",
                "api_base": "https://api.deepseek.com/v1",
                "api_key": "",
                "model": "deepseek-reasoner",
            },
        )
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.json()["profile"]["model"], "deepseek-reasoner")
        self.assertEqual(store.credentials(first_id)["api_key"], first_secret)

        activated = admin.post(
            f"/api/llm-providers/{second_id}/activate",
            headers=self.headers,
        )
        enabled = admin.put(
            "/api/llm-providers/notes-enabled",
            headers=self.headers,
            json={"enabled": True},
        )
        self.assertEqual(activated.status_code, 200)
        self.assertEqual(activated.json()["active_profile_id"], second_id)
        self.assertTrue(enabled.json()["notes_enabled"])

        deleted = admin.delete(
            f"/api/llm-providers/{second_id}",
            headers=self.headers,
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(deleted.json()["notes_enabled"])
        self.assertEqual(deleted.json()["active_profile_id"], "")
        self.assertEqual(len(deleted.json()["profiles"]), 1)
        self.assertNotIn(second_secret, deleted.text)

    def test_llm_connection_is_only_tested_by_explicit_admin_action(self):
        class RecordingVerifier:
            def __init__(self):
                self.calls = []

            def verify(self, profile):
                self.calls.append(dict(profile))

        verifier = RecordingVerifier()
        store = LLMProviderStore(Path(self.tempdir.name) / "settings.json")
        admin = TestClient(
            create_invite_admin_app(
                self.repository,
                self.access,
                csrf_token="known-admin-csrf",
                llm_store=store,
                llm_verifier=verifier,
            )
        )
        secret = "connection-test-secret"
        created = admin.post(
            "/api/llm-providers",
            headers=self.headers,
            json={
                "label": "测试线路",
                "api_base": "https://example-llm.test/v1",
                "api_key": secret,
                "model": "test-chat",
            },
        )
        profile_id = created.json()["profile"]["id"]
        self.assertEqual(verifier.calls, [])

        tested = admin.post(
            f"/api/llm-providers/{profile_id}/test",
            headers=self.headers,
        )

        self.assertEqual(tested.status_code, 200)
        self.assertEqual(len(verifier.calls), 1)
        self.assertEqual(verifier.calls[0]["api_key"], secret)
        self.assertIsNotNone(tested.json()["profile"]["verified_at"])
        self.assertNotIn(secret, tested.text)

    def test_saved_llm_key_is_only_revealed_by_explicit_local_admin_request(self):
        store = LLMProviderStore(Path(self.tempdir.name) / "reveal-settings.json")
        secret = "local-admin-reveal-secret"
        saved = store.save_profile(
            label="FCC NVIDIA 免费",
            api_base="http://127.0.0.1:8082",
            api_key=secret,
            model="anthropic/nvidia_nim/nvidia/nemotron-3-super-120b-a12b",
            channel="free",
            protocol="anthropic_messages",
        )
        admin = TestClient(
            create_invite_admin_app(
                self.repository,
                self.access,
                csrf_token="known-admin-csrf",
                llm_store=store,
            )
        )

        blocked = admin.post(f"/api/llm-providers/{saved['id']}/reveal-key")
        status = admin.get("/api/llm-providers", headers=self.headers)
        revealed = admin.post(
            f"/api/llm-providers/{saved['id']}/reveal-key",
            headers=self.headers,
        )

        self.assertEqual(blocked.status_code, 403)
        self.assertNotIn(secret, status.text)
        self.assertEqual(revealed.status_code, 200)
        self.assertEqual(revealed.json()["api_key"], secret)

    def test_fcc_model_catalog_adds_note_optimized_ultra_and_filters_eol_models(self):
        direct = LLMModelCatalog._catalog_item(
            "anthropic/nvidia_nim/z-ai/glm-5.2",
            fcc_proxy=True,
        )
        ignored_duplicate = LLMModelCatalog._catalog_item(
            "claude-3-freecc-no-thinking/nvidia_nim/z-ai/glm-5.2",
            fcc_proxy=True,
        )
        note_optimized_ultra = LLMModelCatalog._catalog_item(
            "claude-3-freecc-no-thinking/nvidia_nim/nvidia/nemotron-3-ultra-550b-a55b",
            fcc_proxy=True,
        )
        retired_deepseek = LLMModelCatalog._catalog_item(
            "anthropic/nvidia_nim/deepseek-ai/deepseek-v4-pro",
            fcc_proxy=True,
        )
        compatibility_alias = LLMModelCatalog._catalog_item(
            "claude-sonnet-4-20250514",
            fcc_proxy=True,
        )

        self.assertEqual(direct["upstream_id"], "z-ai/glm-5.2")
        self.assertEqual(direct["publisher"], "z-ai")
        self.assertEqual(direct["reasoning_mode"], "provider_default")
        self.assertIsNone(ignored_duplicate)
        self.assertEqual(note_optimized_ultra["reasoning_mode"], "off")
        self.assertIn("关闭深度思考", note_optimized_ultra["label"])
        self.assertIsNone(retired_deepseek)
        self.assertIsNone(compatibility_alias)

    def test_free_model_list_and_verified_switch_use_saved_proxy_key(self):
        class StaticCatalog:
            def __init__(self):
                self.calls = []

            def list(self, profile):
                self.calls.append(dict(profile))
                return [
                    {
                        "id": "anthropic/nvidia_nim/nvidia/nemotron-3-super-120b-a12b",
                        "upstream_id": "nvidia/nemotron-3-super-120b-a12b",
                        "publisher": "nvidia",
                        "label": "nvidia/nemotron-3-super-120b-a12b",
                    },
                    {
                        "id": "anthropic/nvidia_nim/z-ai/glm-5.2",
                        "upstream_id": "z-ai/glm-5.2",
                        "publisher": "z-ai",
                        "label": "z-ai/glm-5.2",
                    },
                ]

        class MatchingVerifier:
            def __init__(self):
                self.calls = []

            def verify(self, profile):
                self.calls.append(dict(profile))
                return {"response_model": profile["model"]}

        store = LLMProviderStore(Path(self.tempdir.name) / "free-models.json")
        saved = store.save_profile(
            label="FCC NVIDIA 免费",
            api_base="http://127.0.0.1:8082",
            api_key="saved-local-proxy-key",
            model="anthropic/nvidia_nim/nvidia/nemotron-3-super-120b-a12b",
            channel="free",
            protocol="anthropic_messages",
        )
        catalog = StaticCatalog()
        verifier = MatchingVerifier()
        admin = TestClient(
            create_invite_admin_app(
                self.repository,
                self.access,
                csrf_token="known-admin-csrf",
                llm_store=store,
                llm_verifier=verifier,
                llm_catalog=catalog,
            )
        )

        listed = admin.get(
            f"/api/llm-providers/{saved['id']}/models",
            headers=self.headers,
        )
        switched = admin.put(
            f"/api/llm-providers/{saved['id']}/model",
            headers=self.headers,
            json={"model": "anthropic/nvidia_nim/z-ai/glm-5.2"},
        )

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["count"], 2)
        self.assertNotIn("saved-local-proxy-key", listed.text)
        self.assertEqual(switched.status_code, 200)
        self.assertEqual(
            switched.json()["profile"]["model"],
            "anthropic/nvidia_nim/z-ai/glm-5.2",
        )
        self.assertEqual(
            switched.json()["verification"]["response_model"],
            "anthropic/nvidia_nim/z-ai/glm-5.2",
        )
        self.assertEqual(verifier.calls[-1]["api_key"], "saved-local-proxy-key")
        self.assertIsNotNone(switched.json()["profile"]["verified_at"])
        self.assertNotIn("saved-local-proxy-key", switched.text)

    def test_failed_or_mismatched_free_model_switch_keeps_original_model(self):
        class StaticCatalog:
            def list(self, _profile):
                return [
                    {
                        "id": "anthropic/nvidia_nim/z-ai/glm-5.2",
                        "upstream_id": "z-ai/glm-5.2",
                        "publisher": "z-ai",
                        "label": "z-ai/glm-5.2",
                    }
                ]

        class MismatchedVerifier:
            def verify(self, _profile):
                return {"response_model": "anthropic/nvidia_nim/other/model"}

        store = LLMProviderStore(Path(self.tempdir.name) / "model-mismatch.json")
        saved = store.save_profile(
            label="FCC NVIDIA 免费",
            api_base="http://127.0.0.1:8082",
            api_key="saved-local-proxy-key",
            model="claude-sonnet-4-5",
            channel="free",
            protocol="anthropic_messages",
        )
        admin = TestClient(
            create_invite_admin_app(
                self.repository,
                self.access,
                csrf_token="known-admin-csrf",
                llm_store=store,
                llm_verifier=MismatchedVerifier(),
                llm_catalog=StaticCatalog(),
            )
        )

        response = admin.put(
            f"/api/llm-providers/{saved['id']}/model",
            headers=self.headers,
            json={"model": "anthropic/nvidia_nim/z-ai/glm-5.2"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("不一致", response.json()["detail"])
        self.assertEqual(store.profile(saved["id"])["model"], "claude-sonnet-4-5")

    def test_admin_note_switch_controls_real_note_api_without_restart(self):
        store = LLMProviderStore(Path(self.tempdir.name) / "settings.json")
        access = AccessManager(
            self.repository,
            "test-session-secret",
            secure_cookie=False,
            paid_calls_enabled=False,
            paid_calls_status=store.is_enabled,
            parser_calls_enabled=True,
        )
        admin = TestClient(
            create_invite_admin_app(
                self.repository,
                access,
                csrf_token="known-admin-csrf",
                llm_store=store,
            )
        )
        created_profile = admin.post(
            "/api/llm-providers",
            headers=self.headers,
            json={
                "label": "DeepSeek",
                "api_base": "https://api.deepseek.com/v1",
                "api_key": "safe-test-secret",
                "model": "deepseek-chat",
            },
        )
        self.assertEqual(created_profile.status_code, 201)
        grant = admin.post(
            "/api/grants",
            headers=self.headers,
            json={
                "label": "LLM 开关测试",
                "transcription_minutes": 30,
                "note_generations": 5,
                "max_video_minutes": 20,
            },
        ).json()

        user_app = FastAPI()
        notes = NoteWorkflow(
            self.repository,
            FakeLLM(),
            run_in_background=False,
            access_manager=access,
        )
        user_app.include_router(
            create_v3_router(
                self.repository,
                parser_workflow=object(),
                note_workflow=notes,
                access_manager=access,
            )
        )
        install_access_middleware(user_app, access)
        user = TestClient(user_app)
        user.post("/api/v3/access/login", json={"code": grant["invite_code"]})
        note_request = {
            "generation_route": "paid",
            "source": {"type": "paste", "transcript": "这是一段可生成笔记的测试逐字稿。"},
            "request_text": "",
        }

        blocked = user.post("/api/v3/note-tasks", json=note_request)
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.json()["error"]["code"], "PAID_CALLS_PAUSED")

        enabled = admin.put(
            "/api/llm-providers/notes-enabled",
            headers=self.headers,
            json={"enabled": True},
        )
        allowed = user.post("/api/v3/note-tasks", json=note_request)

        self.assertTrue(enabled.json()["notes_enabled"])
        self.assertEqual(allowed.status_code, 202)
        self.assertEqual(allowed.json()["task"]["state"], "recommendation_ready")

    def test_free_and_paid_llm_channels_can_be_controlled_independently(self):
        store = LLMProviderStore(Path(self.tempdir.name) / "channel-settings.json")
        admin = TestClient(
            create_invite_admin_app(
                self.repository,
                self.access,
                csrf_token="known-admin-csrf",
                llm_store=store,
            )
        )
        paid = admin.post(
            "/api/llm-providers",
            headers=self.headers,
            json={
                "label": "DeepSeek 高速",
                "api_base": "https://api.deepseek.com",
                "api_key": "paid-secret",
                "model": "deepseek-v4-pro",
                "channel": "paid",
                "protocol": "openai_chat",
                "enabled": True,
            },
        )
        free = admin.post(
            "/api/llm-providers",
            headers=self.headers,
            json={
                "label": "FCC NVIDIA 免费",
                "api_base": "http://127.0.0.1:8082",
                "api_key": "local-fcc-token",
                "model": "claude-sonnet-4-5",
                "channel": "free",
                "protocol": "anthropic_messages",
                "enabled": True,
            },
        )

        self.assertEqual(paid.status_code, 201)
        self.assertEqual(free.status_code, 201)
        free_id = free.json()["profile"]["id"]
        status = free.json()
        self.assertEqual(status["channels"]["free"]["default_profile_id"], free_id)
        self.assertEqual(status["active_channel"], "paid")

        enabled_free = admin.put(
            "/api/llm-providers/channels/free/enabled",
            headers=self.headers,
            json={"enabled": True},
        )
        switched = admin.put(
            "/api/llm-providers/active-channel",
            headers=self.headers,
            json={"channel": "free"},
        )
        disabled_profile = admin.put(
            f"/api/llm-providers/{free_id}/enabled",
            headers=self.headers,
            json={"enabled": False},
        )

        self.assertEqual(enabled_free.status_code, 200)
        self.assertEqual(switched.json()["active_channel"], "free")
        self.assertEqual(switched.json()["active_profile"]["protocol"], "anthropic_messages")
        self.assertFalse(disabled_profile.json()["route_ready"])
        self.assertTrue(disabled_profile.json()["channels"]["paid"]["enabled"])

    def test_only_local_llm_proxies_may_use_plain_http(self):
        store = LLMProviderStore(Path(self.tempdir.name) / "http-settings.json")
        local = store.save_profile(
            label="本机 FCC",
            api_base="http://localhost:8082",
            api_key="local-token",
            model="claude-sonnet-4-5",
            channel="free",
            protocol="anthropic_messages",
        )
        self.assertEqual(local["api_base"], "http://localhost:8082")

        with self.assertRaisesRegex(Exception, "只有本机代理允许"):
            store.save_profile(
                label="不安全远程服务",
                api_base="http://example.com/v1",
                api_key="unsafe-token",
                model="test-model",
                channel="free",
            )


if __name__ == "__main__":
    unittest.main()
