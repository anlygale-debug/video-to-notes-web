#!/usr/bin/env python3
import argparse
import os
from pathlib import Path

from vtn.access import AccessManager
from vtn.storage.sqlite import SQLiteRepository
from vtn.domain.models import utc_now


def manager_from_environment():
    database_path = Path(os.environ.get("VTN_DATABASE_PATH", "data/vtn.sqlite3"))
    secret = (os.environ.get("VTN_SESSION_SECRET") or "").strip()
    if not secret:
        raise SystemExit("VTN_SESSION_SECRET 未配置")
    repository = SQLiteRepository(database_path)
    repository.migrate()
    return repository, AccessManager(repository, secret)


def main():
    parser = argparse.ArgumentParser(description="管理 Video to Notes 内测码")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create", help="创建一个内测码")
    create.add_argument("--label", required=True)
    create.add_argument("--minutes", type=int, default=30)
    create.add_argument("--notes", type=int, default=5)
    create.add_argument("--max-video-minutes", type=int, default=20)
    subparsers.add_parser("list", help="列出内测资格与剩余额度")
    revoke = subparsers.add_parser("revoke", help="撤销一个内测资格")
    revoke.add_argument("access_id")
    args = parser.parse_args()

    repository, manager = manager_from_environment()
    try:
        if args.command == "create":
            grant = manager.create_grant(
                args.label,
                transcription_seconds_limit=args.minutes * 60,
                note_generation_limit=args.notes,
                max_video_seconds=args.max_video_minutes * 60,
            )
            print(f"ACCESS_ID={grant['id']}")
            print(f"INVITE_CODE={grant['code']}")
        elif args.command == "list":
            rows = repository._fetchall(
                "SELECT id,label,enabled FROM access_grants ORDER BY created_at"
            )
            for row in rows:
                snapshot = manager.snapshot(row["id"])
                print(
                    f"{row['id']}\t{row['label']}\t"
                    f"{'enabled' if row['enabled'] else 'revoked'}\t"
                    f"transcription={snapshot['remaining_transcription_seconds']}s\t"
                    f"notes={snapshot['remaining_note_generations']}"
                )
        elif args.command == "revoke":
            if not manager.revoke(args.access_id):
                raise SystemExit("未找到该 ACCESS_ID")
            print("已撤销")
    finally:
        repository.close()


if __name__ == "__main__":
    main()
