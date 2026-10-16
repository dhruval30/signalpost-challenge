"""In-process wiring for permitted external connectors.

Each helper returns a list of observations with exact-entity proof per the
Signalpost external-footprint contract and a status row for reporting.
Failures are isolated per-connector per-company so a single blocked source
never collapses an envelope — they return `[]` and an error status.
"""
from __future__ import annotations

import importlib.util
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def _load(module_name: str, filename: str):
    """Load a stand-alone script as a module without polluting sys.path."""
    full = f"_signalpost_connectors.{module_name}"
    if full in sys.modules:
        return sys.modules[full]
    spec = importlib.util.spec_from_file_location(full, _SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[full] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _safe_call(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> tuple[list[dict], dict]:
    try:
        result = fn(*args, **kwargs)
    except Exception as exc:
        return [], {"status": "error", "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
    if isinstance(result, tuple) and len(result) == 2:
        rows, status = result
    else:
        rows, status = (result or []), {}
    if isinstance(rows, dict):
        rows = [rows] if rows else []
    return list(rows or []), (status or {})


def google_news_rss(profile: dict, *, per_company: int = 10, years: int = 2) -> tuple[list[dict], dict]:
    """Exact-title Google News RSS hits for the registered legal name."""
    module = _load("gnews", "run_google_news_rss_connector.py")
    return _safe_call(module.fetch, profile, per_company, years)


def fagfolkguiden_reviews(profile: dict, cache_dir: Path) -> tuple[list[dict], dict]:
    """Embedded Google aggregate rating lifted from the exact Fagfolkguiden page."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    module = _load("fagfolk", "run_fagfolkguiden_reviews_connector.py")
    return _safe_call(module.fetch, profile, cache_dir)


def annual_report_workforce(
    profile: dict,
    cache_dir: Path,
    *,
    ocr_pages: int = 0,
    ocr_dpi: int = 130,
) -> tuple[list[dict], dict]:
    """Company-scope workforce count parsed from the latest official annual report PDF.

    OCR is disabled by default (ocr_pages=0) to avoid requiring poppler/tesseract
    on evaluator hosts. Set ocr_pages>0 locally to recover image-only reports.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    module = _load("workforce", "run_annual_report_workforce_connector.py")
    observation, status = module.collect(profile, cache_dir, ocr_pages=ocr_pages, ocr_dpi=ocr_dpi)
    rows = [observation] if observation else []
    return rows, (status or {})


_CONNECTORS: tuple[tuple[str, str], ...] = (
    ("google_news_rss", "news"),
    ("fagfolkguiden_reviews", "reviews"),
    ("annual_report_workforce", "workforce"),
)


def collect_external(profile: dict, *, cache_root: Path, enable_ocr: bool = False) -> dict[str, Any]:
    """Run every permitted connector against one profile concurrently."""
    tasks: dict[str, Callable[[], tuple[list[dict], dict]]] = {
        "google_news_rss": lambda: google_news_rss(profile),
        "fagfolkguiden_reviews": lambda: fagfolkguiden_reviews(profile, cache_root / "fagfolkguiden"),
        "annual_report_workforce": lambda: annual_report_workforce(
            profile,
            cache_root / "annual-reports",
            ocr_pages=10 if enable_ocr else 0,
        ),
    }
    observations: list[dict] = []
    per_connector: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        futures = {pool.submit(fn): name for name, fn in tasks.items()}
        for future in futures:
            name = futures[future]
            try:
                rows, status = future.result(timeout=60)
            except Exception as exc:
                rows, status = [], {"status": "error", "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
            observations.extend(rows)
            per_connector[name] = {"accepted": len(rows), **status}

    status = "available" if observations else ("not_available" if not any("error" in v for v in per_connector.values()) else "failed")
    return {
        "status": status,
        "observations": observations,
        "connectors": per_connector,
    }
