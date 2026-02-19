from __future__ import annotations

import json
from pathlib import Path

from solarpipeworker.utils import copy_input_path, create_job_dir
from solarpipeworker.main_worker import load_params


def test_create_job_dir(tmp_path: Path) -> None:
    job_id, job_dir = create_job_dir(tmp_path)
    assert job_id
    assert job_dir.exists()
    assert job_dir.parent == tmp_path


def test_copy_input_path_directory(tmp_path: Path) -> None:
    src = tmp_path / "input.ms"
    src.mkdir()
    (src / "table.dat").write_text("x", encoding="utf-8")

    dst = copy_input_path(src, tmp_path / "job")
    assert dst.exists()
    assert (dst / "table.dat").read_text(encoding="utf-8") == "x"


def test_load_params(tmp_path: Path) -> None:
    params_file = tmp_path / "params_input.json"
    params_file.write_text(
        json.dumps(
            {
                "main_worker": {
                    "global": {
                        "gaintable_file": "/tmp/fake.bcal",
                        "output_prefix": "abc",
                        "cleanup_on_success": False,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    params = load_params(params_file)
    assert params.gaintable_file == "/tmp/fake.bcal"
    assert params.output_prefix == "abc"
