import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_settings_in_dotenv_reach_config(tmp_path):
    """Regression: Config reads os.environ at import time, so .env must be loaded first."""
    script = (
        "import dotenv, pathlib, sys\n"
        "orig = dotenv.load_dotenv\n"
        f"dotenv.load_dotenv = lambda *a, **k: orig(pathlib.Path({str(tmp_path / '.env')!r}))\n"
        "from portfolio.config import Config\n"
        "print(Config.SECRET_KEY, Config.SQLALCHEMY_DATABASE_URI)\n"
    )
    (tmp_path / ".env").write_text("SECRET_KEY='from-dotenv'\nMYSQL_HOST='db.example'\nMYSQL_USER='u'\n"
                                   "MYSQL_PASSWORD='p@ss'\nMYSQL_DB='u$portfolio'\n")
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("MYSQL_", "SECRET_KEY", "DATABASE_URL"))}
    out = subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=env,
                         capture_output=True, text=True, check=True).stdout
    assert "from-dotenv" in out
    assert "mysql+pymysql://u:p%40ss@db.example/u%24portfolio" in out
