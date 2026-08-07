from pathlib import Path

from vtn.invite_admin import create_invite_admin_app_from_environment


app = create_invite_admin_app_from_environment(Path(__file__).parent)
