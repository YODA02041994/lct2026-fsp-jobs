"""Свежий клон: папки для файла SQLite нет — подключение должно создать её само (раньше ./run.sh dev падал)."""
import os, subprocess, sys, tempfile


def test_sqlite_parent_dir_is_created():
    root = tempfile.mkdtemp()
    db = os.path.join(root, "нет_такой_папки", "fsp.db")
    env = {**os.environ, "FSP_DATABASE_URL": f"sqlite:///{db}", "FSP_SECRET_KEY": "x"}
    code = "from app.db import init_db; init_db()"
    r = subprocess.run([sys.executable, "-c", code], cwd=os.path.dirname(os.path.dirname(__file__)), env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-500:]
    assert os.path.exists(db)
