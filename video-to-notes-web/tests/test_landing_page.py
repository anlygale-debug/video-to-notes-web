import unittest

from fastapi.testclient import TestClient

from app import app


class LandingPageHttpTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_product_landing_page_is_available_at_public_route(self):
        response = self.client.get("/video-notes")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("从视频链接，到一份可以继续使用的内容。", response.text)

    def test_landing_page_links_to_app_and_serves_owned_assets(self):
        response = self.client.get("/video-notes")

        self.assertGreaterEqual(response.text.count('href="/next"'), 4)
        self.assertNotIn("../static/app.html", response.text)
        self.assertIn('href="/static/landing/styles.css?v=3"', response.text)
        self.assertIn('src="/static/landing/script.js?v=2"', response.text)

        for asset_path in (
            "/static/landing/styles.css",
            "/static/landing/script.js",
            "/static/landing/assets/parser-result.png",
            "/static/landing/assets/note-recommendations.png",
            "/static/landing/assets/note-reading.png",
        ):
            with self.subTest(asset_path=asset_path):
                self.assertEqual(self.client.get(asset_path).status_code, 200)


if __name__ == "__main__":
    unittest.main()
