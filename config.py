from pathlib import Path

_REPO_DIR = Path(__file__).resolve().parent
_PIPEDEV_DIR = _REPO_DIR.parent

proc_root = str(_PIPEDEV_DIR / "runtime_dir" / "realtime")
caltable_root = str(_PIPEDEV_DIR / "caltables_latest")
dest_dir = str(_PIPEDEV_DIR / "runtime_dir" / "realtime_collect")
