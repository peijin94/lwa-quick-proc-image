#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

try:
    from casatools import table
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"casatools is required for msoverview.py: {exc}")


CORR_TYPE_MAP = {
    5: "RR",
    6: "RL",
    7: "LR",
    8: "LL",
    9: "XX",
    10: "XY",
    11: "YX",
    12: "YY",
}

VALUE_TYPE_ITEMSIZE = {
    "boolean": 1,
    "char": 1,
    "uchar": 1,
    "short": 2,
    "ushort": 2,
    "int": 4,
    "uint": 4,
    "float": 4,
    "double": 8,
    "complex": 8,   # complex64 on disk
    "dcomplex": 16, # complex128 on disk
}


def _to_mhz(freq_hz: float) -> float:
    return float(freq_hz) / 1e6


def _format_bytes(num_bytes: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{num_bytes:.2f} B"


def _estimate_column_storage(tb: table, col: str, nrows: int) -> dict[str, object]:
    """
    Estimate storage for a column using one-row sample and column descriptor.
    """
    desc = tb.getcoldesc(col)
    sample_arr = np.array([])
    sample_error: str | None = None
    if nrows > 0:
        # Fast path: attempt to read first row via getcol.
        try:
            sample_arr = np.asarray(tb.getcol(col, startrow=0, nrow=1))
        except Exception as exc:  # some array columns are undefined for row 0
            sample_error = str(exc)
            # Fallback: probe a handful of rows and use first readable cell.
            probe_rows = min(nrows, 128)
            for row in range(probe_rows):
                try:
                    sample_arr = np.asarray(tb.getcell(col, row))
                    break
                except Exception:
                    continue

    # Try to infer per-row element count from the one-row sample.
    if sample_arr.size == 0:
        elems_per_row = 0
        sample_shape = ()
        dtype_str = str(desc.get("valueType", "unknown"))
        itemsize_sample = 0
    elif sample_arr.ndim == 0:
        elems_per_row = 1
        sample_shape = ()
        dtype_str = str(sample_arr.dtype)
        itemsize_sample = int(sample_arr.dtype.itemsize)
    elif sample_arr.ndim == 1:
        elems_per_row = int(sample_arr.size)
        sample_shape = (int(sample_arr.size),)
        dtype_str = str(sample_arr.dtype)
        itemsize_sample = int(sample_arr.dtype.itemsize)
    else:
        # Casacore convention: last axis is row axis for getcol.
        row_sample = sample_arr[..., 0]
        elems_per_row = int(row_sample.size)
        sample_shape = tuple(int(x) for x in row_sample.shape)
        dtype_str = str(row_sample.dtype)
        itemsize_sample = int(row_sample.dtype.itemsize)

    value_type = str(desc.get("valueType", dtype_str))
    itemsize_ondisk = VALUE_TYPE_ITEMSIZE.get(value_type.lower(), itemsize_sample)
    estimated_bytes = float(nrows * elems_per_row * itemsize_ondisk)
    return {
        "column": col,
        "value_type": value_type,
        "dtype": dtype_str,
        "sample_shape_per_row": sample_shape,
        "elements_per_row": elems_per_row,
        "itemsize_bytes_on_disk": itemsize_ondisk,
        "itemsize_bytes_sample": itemsize_sample,
        "estimated_storage_bytes": estimated_bytes,
        "estimated_storage_human": _format_bytes(estimated_bytes),
        "sample_note": sample_error,
    }


def _load_main_summary(ms_path: Path) -> dict[str, object]:
    tb = table()
    tb.open(str(ms_path))
    colnames = tb.colnames()
    nrows = tb.nrows()
    column_summaries = [_estimate_column_storage(tb, c, int(nrows)) for c in colnames]

    ant1 = tb.getcol("ANTENNA1") if "ANTENNA1" in colnames else np.array([])
    ant2 = tb.getcol("ANTENNA2") if "ANTENNA2" in colnames else np.array([])
    times = tb.getcol("TIME") if "TIME" in colnames else np.array([])

    tb.close()

    baselines = int(len(np.unique(np.stack([ant1, ant2], axis=1), axis=0))) if ant1.size else 0
    antennas_in_main = int(len(np.unique(np.concatenate([ant1, ant2])))) if ant1.size else 0

    return {
        "nrows": int(nrows),
        "column_count": len(colnames),
        "columns": list(colnames),
        "column_summaries": column_summaries,
        "baselines_in_main": baselines,
        "antennas_in_main": antennas_in_main,
        "time_min_mjd_s": float(np.min(times)) if times.size else None,
        "time_max_mjd_s": float(np.max(times)) if times.size else None,
    }


def _load_antenna_summary(ms_path: Path) -> dict[str, object]:
    tb = table()
    tb.open(str(ms_path / "ANTENNA"))
    n_ant = tb.nrows()
    names = tb.getcol("NAME").tolist() if "NAME" in tb.colnames() else []
    tb.close()
    return {"n_antennas": int(n_ant), "antenna_names_preview": names[:10]}


def _load_spw_summary(ms_path: Path) -> dict[str, object]:
    tb = table()
    tb.open(str(ms_path / "SPECTRAL_WINDOW"))
    n_spw = tb.nrows()

    num_chan = tb.getcol("NUM_CHAN") if "NUM_CHAN" in tb.colnames() else np.array([])
    ref_freq = tb.getcol("REF_FREQUENCY") if "REF_FREQUENCY" in tb.colnames() else np.array([])
    total_bw = tb.getcol("TOTAL_BANDWIDTH") if "TOTAL_BANDWIDTH" in tb.colnames() else np.array([])
    chan_freq = tb.getcol("CHAN_FREQ") if "CHAN_FREQ" in tb.colnames() else np.array([])
    tb.close()

    spw_rows: list[dict[str, object]] = []
    for spw_id in range(int(n_spw)):
        nchan = int(num_chan[spw_id]) if num_chan.size else None
        ref_mhz = _to_mhz(ref_freq[spw_id]) if ref_freq.size else None
        bw_mhz = _to_mhz(total_bw[spw_id]) if total_bw.size else None
        if chan_freq.size:
            cmin = _to_mhz(np.min(chan_freq[:, spw_id]))
            cmax = _to_mhz(np.max(chan_freq[:, spw_id]))
        else:
            cmin, cmax = None, None
        spw_rows.append(
            {
                "spw_id": spw_id,
                "num_chan": nchan,
                "ref_freq_mhz": ref_mhz,
                "total_bw_mhz": bw_mhz,
                "chan_freq_min_mhz": cmin,
                "chan_freq_max_mhz": cmax,
            }
        )

    return {
        "n_spw": int(n_spw),
        "num_chan_per_spw": num_chan.astype(int).tolist() if num_chan.size else [],
        "spw_rows": spw_rows,
    }


def _load_polarization_summary(ms_path: Path) -> dict[str, object]:
    tb = table()
    tb.open(str(ms_path / "POLARIZATION"))
    n_pol_rows = tb.nrows()
    corr_type = tb.getcol("CORR_TYPE") if "CORR_TYPE" in tb.colnames() else np.array([])
    n_corr = tb.getcol("NUM_CORR") if "NUM_CORR" in tb.colnames() else np.array([])
    tb.close()

    pol_rows: list[dict[str, object]] = []
    for row_id in range(int(n_pol_rows)):
        if corr_type.size:
            ctypes = [int(x) for x in corr_type[:, row_id]]
            clabels = [CORR_TYPE_MAP.get(x, f"TYPE{x}") for x in ctypes]
        else:
            clabels = []
        pol_rows.append(
            {
                "pol_id": row_id,
                "num_corr": int(n_corr[row_id]) if n_corr.size else None,
                "corr_labels": clabels,
            }
        )

    return {"n_pol_rows": int(n_pol_rows), "pol_rows": pol_rows}


def _load_data_description_summary(ms_path: Path) -> dict[str, object]:
    tb = table()
    tb.open(str(ms_path / "DATA_DESCRIPTION"))
    n_rows = tb.nrows()
    spw_ids = tb.getcol("SPECTRAL_WINDOW_ID") if "SPECTRAL_WINDOW_ID" in tb.colnames() else np.array([])
    pol_ids = tb.getcol("POLARIZATION_ID") if "POLARIZATION_ID" in tb.colnames() else np.array([])
    tb.close()

    dd_rows = []
    for i in range(int(n_rows)):
        dd_rows.append(
            {
                "ddid": i,
                "spw_id": int(spw_ids[i]) if spw_ids.size else None,
                "pol_id": int(pol_ids[i]) if pol_ids.size else None,
            }
        )
    return {"n_data_description_rows": int(n_rows), "dd_rows": dd_rows}


def build_overview(ms_path: Path) -> dict[str, object]:
    return {
        "ms_path": str(ms_path),
        "main": _load_main_summary(ms_path),
        "antenna": _load_antenna_summary(ms_path),
        "spectral_window": _load_spw_summary(ms_path),
        "polarization": _load_polarization_summary(ms_path),
        "data_description": _load_data_description_summary(ms_path),
    }


def print_overview(overview: dict[str, object]) -> None:
    print(f"MS: {overview['ms_path']}")
    main = overview["main"]
    antenna = overview["antenna"]
    spw = overview["spectral_window"]
    pol = overview["polarization"]
    dd = overview["data_description"]

    print("")
    print("[MAIN]")
    print(f"rows: {main['nrows']}")
    print(f"columns: {main['column_count']}")
    print(f"column names: {', '.join(main['columns'])}")
    print(f"antennas seen in main: {main['antennas_in_main']}")
    print(f"baselines in main: {main['baselines_in_main']}")
    print(f"time min (s): {main['time_min_mjd_s']}")
    print(f"time max (s): {main['time_max_mjd_s']}")
    print("column details:")
    for c in main["column_summaries"]:
        line = (
            "  {column}: valueType={value_type} dtype={dtype} shape_per_row={sample_shape_per_row} "
            "elem/row={elements_per_row} itemsize(ondisk)={itemsize_bytes_on_disk}B "
            "itemsize(sample)={itemsize_bytes_sample}B est={estimated_storage_human}".format(
                **c
            )
        )
        if c.get("sample_note"):
            line += " [sample-fallback]"
        print(line)

    print("")
    print("[ANTENNA]")
    print(f"num antennas: {antenna['n_antennas']}")
    print(f"antenna preview: {antenna['antenna_names_preview']}")

    print("")
    print("[SPECTRAL_WINDOW]")
    print(f"num spw: {spw['n_spw']}")
    print(f"channels per spw: {spw['num_chan_per_spw']}")
    for row in spw["spw_rows"]:
        print(
            "spw={spw_id} nchan={num_chan} ref={ref_freq_mhz:.3f}MHz "
            "bw={total_bw_mhz:.3f}MHz range=[{chan_freq_min_mhz:.3f}, {chan_freq_max_mhz:.3f}]MHz".format(
                **row
            )
        )

    print("")
    print("[POLARIZATION]")
    print(f"pol rows: {pol['n_pol_rows']}")
    for row in pol["pol_rows"]:
        print(f"pol={row['pol_id']} num_corr={row['num_corr']} corr={row['corr_labels']}")

    print("")
    print("[DATA_DESCRIPTION]")
    print(f"rows: {dd['n_data_description_rows']}")
    for row in dd["dd_rows"]:
        print(f"ddid={row['ddid']} spw={row['spw_id']} pol={row['pol_id']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Print an overview of a CASA Measurement Set")
    parser.add_argument("ms_file", help="Path to .ms directory")
    args = parser.parse_args()

    ms_path = Path(args.ms_file)
    if not ms_path.exists() or not ms_path.is_dir():
        raise SystemExit(f"MS path not found or not a directory: {ms_path}")

    overview = build_overview(ms_path)
    print_overview(overview)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
