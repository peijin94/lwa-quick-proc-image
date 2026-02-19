from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any


def create_job_dir(runtime_dir: Path) -> tuple[str, Path]:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    job_id = str(uuid.uuid4())
    job_dir = runtime_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    return job_id, job_dir


def copy_input_path(src: Path, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    return dst


def setup_job_logger(job_dir: Path, logger_name: str = "solarpipeworker") -> logging.Logger:
    logger = logging.getLogger(f"{logger_name}.{job_dir.name}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(job_dir / "job.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger


def run_command(
    cmd: list[str],
    logger: logging.Logger,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    logger.info("Running command: %s", " ".join(cmd))
    start = time.time()
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.time() - start
    logger.info("Command finished in %.2fs with code %s", elapsed, result.returncode)
    if result.stdout:
        logger.info("stdout:\n%s", result.stdout)
    if result.stderr:
        logger.info("stderr:\n%s", result.stderr)

    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed with code {result.returncode}: {' '.join(cmd)}\n{result.stderr.strip()}"
        )
    return result


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)


def ensure_path(path_like: str | Path) -> Path:
    return path_like if isinstance(path_like, Path) else Path(path_like)


def serialize_paths(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, Path):
            out[key] = str(value)
        elif isinstance(value, dict):
            out[key] = serialize_paths(value)
        else:
            out[key] = value
    return out
