from __future__ import annotations

import argparse
import copy
import json
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .source_list import get_sun_ra_dec, get_time_mjd, mask_far_sun_sources
from .utils import (
    copy_input_path,
    create_job_dir,
    ensure_path,
    run_command,
    serialize_paths,
    setup_job_logger,
    write_json,
)
from .visualization import plot_solar_image


DEFAULT_MAIN_WORKER_CONFIG: dict[str, dict[str, Any]] = {
    "global": {
        "container_image": "peijin/lwa-solar-pipehost:v202510",
        "output_prefix": None,
        "keep_ms_tmp": False,
        "fch_img": False,
        "mfs_img": False,
        "debug": False,
        "plot_mid_steps": False,
        "cleanup_on_success": False,
        "strategy_file": None,
    },
    "flagavg_dp3": {"avg_freqstep": 4},
    "selfcal_fullsky_wsclean": {
        "niter": 800,
        "mgain": 0.9,
        "horizon_mask": 5,
        "save_source_list": False,
        "auto_mask": False,
        "auto_threshold": False,
    },
    "selfcal_gaincal": {
        "solint": 0,
        "caltype": "diagonalphase",
        "uvlambdamin": 30,
        "maxiter": 500,
        "tolerance": 1e-5,
        "usemodelcolumn": True,
        "modelcolumn": "MODEL_DATA",
    },
    "selfcal_applycal": {"cal_entry_lst": ["phase"]},
    "subtract_sources_wsclean": {
        "niter": 1500,
        "mgain": 0.9,
        "horizon_mask": 0.1,
        "save_source_list": True,
    },
    "mask_far_sun_sources": {"distance_deg": 6.0},
    "final_avg_dp3": {"freq_step": 4},
    "final_wsclean": {
        "j": 8,
        "mem": 6,
        "quiet": True,
        "no_dirty": True,
        "no_update_model_required": True,
        "horizon_mask": "5deg",
        "size": "384 384",
        "scale": "2arcmin",
        "weight": "briggs -0.5",
        "minuv_l": 10,
        "auto_threshold": 3,
        "niter": 6000,
        "mgain": 0.9,
        "beam_fitting_size": 2,
        "pol": "I",
        "channels_out": 12,
    },
    "debug_subtracted_wsclean": {"niter": 5000, "mgain": 0.9, "horizon_mask": 0.1},
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


@dataclass
class Params:
    gaintable_file: str
    container_image: str = "peijin/lwa-solar-pipehost:v202510"
    output_prefix: str | None = None
    keep_ms_tmp: bool = False
    fch_img: bool = False
    mfs_img: bool = False
    debug: bool = False
    plot_mid_steps: bool = False
    cleanup_on_success: bool = False
    strategy_file: str | None = None
    main_worker: dict[str, dict[str, Any]] = field(default_factory=lambda: copy.deepcopy(DEFAULT_MAIN_WORKER_CONFIG))

    def step(self, step_name: str) -> dict[str, Any]:
        return self.main_worker.get(step_name, {})


@dataclass
class JobResult:
    job_id: str
    job_dir: Path
    copied_data_file: Path
    artifacts: dict[str, Path] = field(default_factory=dict)
    metrics: dict[str, float | int | str] = field(default_factory=dict)
    success: bool = False
    errors: list[str] = field(default_factory=list)
    flist_fch: list[Path] = field(default_factory=list)
    fname_mfs: Path | None = None


def load_params(path: str | Path = "params_input.json") -> Params:
    params_path = ensure_path(path)
    with params_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    # New format: {"main_worker": {"global": {...}, "<step>": {...}}}
    if "main_worker" in raw:
        merged = _deep_merge(DEFAULT_MAIN_WORKER_CONFIG, raw["main_worker"])
        global_cfg = merged.get("global", {})
        gaintable = global_cfg.get("gaintable_file")
        if not gaintable or not str(gaintable).strip():
            raise ValueError("params_input.json must include main_worker.global.gaintable_file")
        return Params(
            gaintable_file=str(gaintable),
            container_image=str(global_cfg.get("container_image", DEFAULT_MAIN_WORKER_CONFIG["global"]["container_image"])),
            output_prefix=global_cfg.get("output_prefix"),
            keep_ms_tmp=bool(global_cfg.get("keep_ms_tmp", False)),
            fch_img=bool(global_cfg.get("fch_img", False)),
            mfs_img=bool(global_cfg.get("mfs_img", False)),
            debug=bool(global_cfg.get("debug", False)),
            plot_mid_steps=bool(global_cfg.get("plot_mid_steps", False)),
            cleanup_on_success=bool(global_cfg.get("cleanup_on_success", False)),
            strategy_file=global_cfg.get("strategy_file"),
            main_worker=merged,
        )

    # Backward compatibility for old flat format.
    if "gaintable_file" not in raw or not str(raw["gaintable_file"]).strip():
        raise ValueError("params_input.json must include non-empty 'gaintable_file'")

    legacy_main_worker = _deep_merge(DEFAULT_MAIN_WORKER_CONFIG, {"global": raw})
    return Params(**raw, main_worker=legacy_main_worker)


def _coerce_params(params: dict[str, Any] | Params) -> Params:
    if isinstance(params, Params):
        return params
    if "main_worker" in params and "gaintable_file" not in params:
        merged = _deep_merge(DEFAULT_MAIN_WORKER_CONFIG, params["main_worker"])
        global_cfg = merged.get("global", {})
        gaintable = global_cfg.get("gaintable_file")
        if not gaintable:
            raise ValueError("params.main_worker.global.gaintable_file is required")
        return Params(
            gaintable_file=str(gaintable),
            container_image=str(global_cfg.get("container_image", DEFAULT_MAIN_WORKER_CONFIG["global"]["container_image"])),
            output_prefix=global_cfg.get("output_prefix"),
            keep_ms_tmp=bool(global_cfg.get("keep_ms_tmp", False)),
            fch_img=bool(global_cfg.get("fch_img", False)),
            mfs_img=bool(global_cfg.get("mfs_img", False)),
            debug=bool(global_cfg.get("debug", False)),
            plot_mid_steps=bool(global_cfg.get("plot_mid_steps", False)),
            cleanup_on_success=bool(global_cfg.get("cleanup_on_success", False)),
            strategy_file=global_cfg.get("strategy_file"),
            main_worker=merged,
        )
    return Params(**params)


def _make_wsclean_cmd(msfile: Path, imagename: str, **kwargs: Any) -> list[str]:
    defaults: dict[str, str] = {
        "j": "16",
        "mem": "6",
        "weight": "uniform",
        "no-dirty": "",
        "no-update-model-required": "",
        "no-negative": "",
        "niter": "10000",
        "mgain": "0.8",
        "auto-threshold": "3",
        "auto-mask": "8",
        "pol": "I",
        "minuv-l": "10",
        "intervals-out": "1",
        "no-reorder": "",
        "beam-fitting-size": "2",
        "horizon-mask": "2deg",
        "quiet": "",
        "size": "4096 4096",
        "scale": "2arcmin",
    }

    for key, value in kwargs.items():
        cli_key = key.replace("_", "-")
        if value is False:
            defaults.pop(cli_key, None)
        elif value is True:
            defaults[cli_key] = ""
        else:
            defaults[cli_key] = str(value)

    cmd = ["wsclean"]
    for key, value in defaults.items():
        cmd.append(f"-{key}")
        if value:
            cmd.extend(value.split())
    cmd.extend(["-name", imagename, str(msfile)])
    return cmd


def _in_container(path: Path) -> str:
    return f"/data/{path.name}"


def _run_in_container(cmd: list[str], job_dir: Path, image: str, logger: Any) -> None:
    run_command(
        [
            "podman",
            "run",
            "--rm",
            "-v",
            f"{job_dir}:/data:rw",
            "-w",
            "/data",
            image,
            *cmd,
        ],
        logger,
    )


def _run_casa_applycal(
    raw_ms: Path,
    output_ms: Path,
    gaintable: Path,
    repo_root: Path,
    logger: Any,
    job_dir: Path,
    image: str,
) -> None:
    run_command(
        [
            "podman",
            "run",
            "--rm",
            "-v",
            f"{job_dir}:/data:rw",
            "-v",
            f"{repo_root}:/lwasoft:ro",
            "-w",
            "/data",
            image,
            "python3",
            "/lwasoft/exe/flagant_applybp.py",
            _in_container(raw_ms),
            _in_container(output_ms),
            _in_container(gaintable),
        ],
        logger,
    )


def _run_dp3_flag_avg(
    input_ms: Path,
    output_ms: Path,
    strategy_file: Path | None,
    logger: Any,
    job_dir: Path,
    image: str,
    avg_freqstep: int = 4,
) -> None:
    if strategy_file is None:
        strategy_file_str = "/usr/local/share/linc/rfistrategies/lofar-default.lua"
    else:
        strategy_file_str = _in_container(strategy_file)

    parset = (
        f"msin={_in_container(input_ms)} "
        f"msout={_in_container(output_ms)} "
        "msin.datacolumn=CORRECTED_DATA "
        "steps=[flag,avg] "
        "flag.type=aoflagger "
        f"flag.strategy={strategy_file_str} "
        "avg.type=averager "
        f"avg.freqstep={avg_freqstep}"
    )
    _run_in_container(["DP3", *parset.split()], job_dir=job_dir, image=image, logger=logger)


def _run_wsclean(
    input_ms: Path,
    output_prefix: str,
    logger: Any,
    job_dir: Path,
    image: str,
    **kwargs: Any,
) -> None:
    cmd = _make_wsclean_cmd(Path(input_ms.name), Path(output_prefix).name, **kwargs)
    _run_in_container(cmd, job_dir=job_dir, image=image, logger=logger)


def _run_gaincal(
    input_ms: Path,
    solution_fname: Path,
    logger: Any,
    job_dir: Path,
    image: str,
    solint: int,
    caltype: str,
    uvlambdamin: int,
    maxiter: int,
    tolerance: float,
    usemodelcolumn: bool,
    modelcolumn: str,
) -> None:
    parset = (
        f"msin={_in_container(input_ms)} showprogress=False verbosity=quiet "
        "steps=[gaincal] msout=. "
        f"gaincal.solint={solint} gaincal.caltype={caltype} gaincal.uvlambdamin={uvlambdamin} "
        f"gaincal.maxiter={maxiter} gaincal.tolerance={tolerance} "
        f"gaincal.usemodelcolumn={'true' if usemodelcolumn else 'false'} gaincal.modelcolumn={modelcolumn} "
        f"gaincal.parmdb={_in_container(solution_fname)}"
    )
    _run_in_container(["DP3", *parset.split()], job_dir=job_dir, image=image, logger=logger)


def _run_applycal_dp3(
    input_ms: Path,
    output_ms: Path,
    solution_fname: Path,
    cal_entry_lst: list[str],
    logger: Any,
    job_dir: Path,
    image: str,
) -> None:
    parset = (
        f"msin={_in_container(input_ms)} msout={_in_container(output_ms)} steps=[applycal] "
        "showprogress=False verbosity=quiet "
        f"applycal.parmdb={_in_container(solution_fname)} "
        f"applycal.steps=[{','.join(cal_entry_lst)}] "
    )
    for entry in cal_entry_lst:
        parset += f"applycal.{entry}.correction={entry}000 "
    _run_in_container(["DP3", *parset.split()], job_dir=job_dir, image=image, logger=logger)


def _run_dp3_subtract(
    input_ms: Path,
    output_ms: Path,
    source_list: Path,
    logger: Any,
    job_dir: Path,
    image: str,
) -> None:
    parset = (
        f"msin={_in_container(input_ms)} showprogress=False verbosity=quiet msout={_in_container(output_ms)} "
        "steps=[predict] predict.type=predict "
        f"predict.sourcedb={_in_container(source_list)} predict.operation=subtract"
    )
    _run_in_container(["DP3", *parset.split()], job_dir=job_dir, image=image, logger=logger)


def _phaseshift_to_sun(ms_file: Path, output_ms: Path, logger: Any, job_dir: Path, image: str) -> None:
    time_mjd = get_time_mjd(ms_file)
    sun_ra, sun_dec = get_sun_ra_dec(time_mjd)
    parset = (
        f"msin={_in_container(ms_file)} msout={_in_container(output_ms)} showprogress=False verbosity=quiet "
        "steps=[phaseshift] phaseshift.type=phaseshift "
        f"phaseshift.phasecenter=[{sun_ra}deg,{sun_dec}deg]"
    )
    _run_in_container(["DP3", *parset.split()], job_dir=job_dir, image=image, logger=logger)


def _run_dp3_avg(
    input_ms: Path,
    output_ms: Path,
    logger: Any,
    job_dir: Path,
    image: str,
    freq_step: int = 4,
) -> None:
    parset = (
        f"msin={_in_container(input_ms)} msout={_in_container(output_ms)} steps=[avg] showprogress=False verbosity=quiet "
        f"avg.type=averager avg.freqstep={freq_step}"
    )
    _run_in_container(["DP3", *parset.split()], job_dir=job_dir, image=image, logger=logger)


def _collect_artifacts(job_dir: Path) -> dict[str, Path]:
    artifacts: dict[str, Path] = {}
    patterns = ["*.fits", "*.png", "*.h5", "*.txt", "*.ms"]
    idx = 0
    for pattern in patterns:
        for file in sorted(job_dir.glob(pattern)):
            artifacts[f"artifact_{idx:03d}_{file.name}"] = file
            idx += 1
    return artifacts


def _run_pipeline(
    copied_ms: Path,
    copied_gaintable: Path,
    output_prefix: str,
    params: Params,
    logger: Any,
    repo_root: Path,
) -> tuple[dict[str, Path], list[Path], Path | None]:
    data_dir = copied_ms.parent
    applied_bp_ms = data_dir / f"{copied_ms.stem}_applied_bp.ms"
    flagged_avg_ms = data_dir / f"{copied_ms.stem}_flagged_avg.ms"
    solution_file = data_dir / f"{output_prefix}_solution.h5"
    final_ms = data_dir / f"{copied_ms.stem}_{output_prefix}_final.ms"
    flagavg_cfg = params.step("flagavg_dp3")
    selfcal_wsclean_cfg = params.step("selfcal_fullsky_wsclean")
    selfcal_gaincal_cfg = params.step("selfcal_gaincal")
    selfcal_applycal_cfg = params.step("selfcal_applycal")
    subtract_sources_wsclean_cfg = params.step("subtract_sources_wsclean")
    mask_far_sun_cfg = params.step("mask_far_sun_sources")
    final_avg_cfg = params.step("final_avg_dp3")
    final_wsclean_cfg = params.step("final_wsclean")
    debug_subtracted_wsclean_cfg = params.step("debug_subtracted_wsclean")

    strategy_src = (
        Path(params.strategy_file)
        if params.strategy_file
        else repo_root / "solarpipeworker" / "lua" / "LWA_sun_PZ.lua"
    )
    strategy_file = copy_input_path(strategy_src, data_dir) if strategy_src.exists() else None


    # step 1: applycal
    _run_casa_applycal(
        copied_ms,
        applied_bp_ms,
        copied_gaintable,
        repo_root,
        logger,
        job_dir=data_dir,
        image=params.container_image,
    )

    # step 2: flagavg
    _run_dp3_flag_avg(
        applied_bp_ms,
        flagged_avg_ms,
        strategy_file,
        logger,
        job_dir=data_dir,
        image=params.container_image,
        avg_freqstep=int(flagavg_cfg.get("avg_freqstep", 4)),
    )

    # step 3: selfcal_fullsky_wsclean
    current_ms = flagged_avg_ms
    _run_wsclean(
        current_ms,
        str(data_dir / f"{output_prefix}_image"),
        logger,
        job_dir=data_dir,
        image=params.container_image,
        **selfcal_wsclean_cfg,
    )
    
    # step 4: selfcal_gaincal
    _run_gaincal(
        current_ms,
        solution_file,
        logger,
        job_dir=data_dir,
        image=params.container_image,
        solint=int(selfcal_gaincal_cfg.get("solint", 0)),
        caltype=str(selfcal_gaincal_cfg.get("caltype", "diagonalphase")),
        uvlambdamin=int(selfcal_gaincal_cfg.get("uvlambdamin", 30)),
        maxiter=int(selfcal_gaincal_cfg.get("maxiter", 500)),
        tolerance=float(selfcal_gaincal_cfg.get("tolerance", 1e-5)),
        usemodelcolumn=bool(selfcal_gaincal_cfg.get("usemodelcolumn", True)),
        modelcolumn=str(selfcal_gaincal_cfg.get("modelcolumn", "MODEL_DATA")),
    )
    # step 5: selfcal_applycal
    _run_applycal_dp3(
        current_ms,
        final_ms,
        solution_file,
        list(selfcal_applycal_cfg.get("cal_entry_lst", ["phase"])),
        logger,
        job_dir=data_dir,
        image=params.container_image,
    )

    # step 6: subtract_sources
    if params.keep_ms_tmp is False:
        if current_ms.exists():
            shutil.rmtree(current_ms)

    # step 7: subtract_sources_wsclean
    _run_wsclean(
        final_ms,
        str(data_dir / f"{output_prefix}_image_source"),
        logger,
        job_dir=data_dir,
        image=params.container_image,
        **subtract_sources_wsclean_cfg,
    )

    time_mjd = get_time_mjd(final_ms)
    sun_ra, sun_dec = get_sun_ra_dec(time_mjd)
    source_list_file = data_dir / f"{output_prefix}_image_source-sources.txt"
    masked_sources_file = data_dir / f"{output_prefix}_image_source_masked-sources.txt"
    mask_far_sun_sources(
        source_list_file,
        masked_sources_file,
        sun_ra,
        sun_dec,
        distance_deg=float(mask_far_sun_cfg.get("distance_deg", 6.0)),
    )

    subtracted_ms = data_dir / f"{output_prefix}_image_source_masked_subtracted.ms"
    # step 8: subtract_sources_dp3
    _run_dp3_subtract(
        final_ms,
        subtracted_ms,
        masked_sources_file,
        logger,
        job_dir=data_dir,
        image=params.container_image,
    )

    # step 9: phaseshift_to_sun
    shifted_ms = data_dir / f"{output_prefix}_image_source_sun_shifted.ms"
    _phaseshift_to_sun(
        subtracted_ms,
        shifted_ms,
        logger,
        job_dir=data_dir,
        image=params.container_image,
    )

    # step 10: final_avg
    shifted_ms_avg = data_dir / f"{output_prefix}_image_source_sun_shifted_avg.ms"
    _run_dp3_avg(
        shifted_ms,
        shifted_ms_avg,
        logger,
        job_dir=data_dir,
        image=params.container_image,
        freq_step=int(final_avg_cfg.get("freq_step", 4)),
    )

    # step 11: fch_img
    final_wsclean_kwargs = dict(final_wsclean_cfg)
    channels_out = int(final_wsclean_kwargs.pop("channels_out", 12))

    flist_fch: list[Path] = []
    fname_mfs: Path | None = None

    if params.fch_img:
        cmd = _make_wsclean_cmd(
            Path(shifted_ms_avg.name),
            f"{output_prefix}_fch",
            join_channels=True,
            channels_out=channels_out,
            **final_wsclean_kwargs,
        )
        _run_in_container(cmd, job_dir=data_dir, image=params.container_image, logger=logger)
        flist_fch = sorted(data_dir.glob(f"{output_prefix}_fch-0*image*.fits"))
        auto_mfs = data_dir / f"{output_prefix}_fch-MFS-image.fits"
        if auto_mfs.exists():
            fname_mfs = auto_mfs

    # step 12: mfs_img
    if params.mfs_img and not params.fch_img:
        cmd = _make_wsclean_cmd(
            Path(shifted_ms_avg.name),
            f"{output_prefix}_mfs",
            **final_wsclean_kwargs,
        )
        _run_in_container(cmd, job_dir=data_dir, image=params.container_image, logger=logger)
        mfs_images = sorted(data_dir.glob(f"{output_prefix}_mfs*image.fits"))
        if mfs_images:
            fname_mfs = mfs_images[0]
            plot_solar_image(fname_mfs)
    elif params.mfs_img and params.fch_img:
        logger.info(
            "Skipping separate MFS clean because fch_img is enabled; using *_fch-MFS-image.fits."
        )

    if params.debug:
        _run_wsclean(
            subtracted_ms,
            str(data_dir / f"{output_prefix}_image_source_masked_subtracted"),
            logger,
            job_dir=data_dir,
            image=params.container_image,
            **debug_subtracted_wsclean_cfg,
        )

    return (
        {
            "applied_bp_ms": applied_bp_ms,
            "flagged_avg_ms": flagged_avg_ms,
            "solution_file": solution_file,
            "final_ms": final_ms,
            "shifted_ms_avg": shifted_ms_avg,
        },
        flist_fch,
        fname_mfs,
    )


def run_job(data_file: str | Path, runtime_dir: str | Path, params: dict[str, Any] | Params) -> JobResult:
    params_obj = _coerce_params(params)
    data_path = ensure_path(data_file).resolve()
    runtime_path = ensure_path(runtime_dir).resolve()
    gaintable_path = ensure_path(params_obj.gaintable_file).resolve()

    if not data_path.exists():
        raise FileNotFoundError(f"data_file not found: {data_path}")
    if not gaintable_path.exists():
        raise FileNotFoundError(f"gaintable_file not found: {gaintable_path}")
    if shutil.which("podman") is None:
        raise RuntimeError("podman is required but was not found in PATH")

    repo_root = Path(__file__).resolve().parent.parent
    job_id, job_dir = create_job_dir(runtime_path)
    logger = setup_job_logger(job_dir)

    copied_data = copy_input_path(data_path, job_dir)
    copied_gaintable = copy_input_path(gaintable_path, job_dir)

    result = JobResult(job_id=job_id, job_dir=job_dir, copied_data_file=copied_data)
    output_prefix = params_obj.output_prefix or data_path.stem.split(".")[0]
    start = time.time()

    try:
        pipeline_artifacts, flist_fch, fname_mfs = _run_pipeline(
            copied_ms=copied_data,
            copied_gaintable=copied_gaintable,
            output_prefix=output_prefix,
            params=params_obj,
            logger=logger,
            repo_root=repo_root,
        )
        result.success = True
        result.artifacts.update(pipeline_artifacts)
        result.flist_fch = flist_fch
        result.fname_mfs = fname_mfs
    except Exception as exc:  # noqa: BLE001
        logger.exception("Job failed")
        result.success = False
        result.errors.append(str(exc))
    finally:
        result.metrics["elapsed_seconds"] = round(time.time() - start, 3)
        result.artifacts.update(_collect_artifacts(job_dir))

        summary = {
            "job_id": result.job_id,
            "job_dir": str(result.job_dir),
            "copied_data_file": str(result.copied_data_file),
            "artifacts": {k: str(v) for k, v in result.artifacts.items()},
            "metrics": result.metrics,
            "success": result.success,
            "errors": result.errors,
            "flist_fch": [str(p) for p in result.flist_fch],
            "fname_mfs": str(result.fname_mfs) if result.fname_mfs else None,
            "params": asdict(params_obj),
        }
        write_json(job_dir / "summary.json", summary)

        if result.success and params_obj.cleanup_on_success:
            shutil.rmtree(job_dir)

    return result


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Run solarpipeworker job")
    parser.add_argument("--data-file", required=True)
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--params", default="params_input.json")
    args = parser.parse_args()

    params = load_params(args.params)
    result = run_job(args.data_file, args.runtime_dir, params)

    payload = {
        "job_id": result.job_id,
        "job_dir": str(result.job_dir),
        "success": result.success,
        "errors": result.errors,
    }
    print(json.dumps(serialize_paths(payload), indent=2))
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
