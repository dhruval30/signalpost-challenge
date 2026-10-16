#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from norway_company_agent.batch import profile_complete_for_modules, profiles_from_bulk, read_organisation_inputs, terminal_envelope, validate_envelopes  # noqa: E402
from norway_company_agent.evidence import utc_now  # noqa: E402
from norway_company_agent.external_connectors import collect_external  # noqa: E402
from norway_company_agent.identity import apply_website_identity_gate  # noqa: E402
from norway_company_agent.official import fetch_official_modules  # noqa: E402
from norway_company_agent.website import fetch_website  # noqa: E402


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluator-owned Signalpost batch contract")
    parser.add_argument("--organisations", required=True, help="JSON, JSONL, or text organisation-number list")
    parser.add_argument("--bulk", required=True, help="Frozen Brreg entity snapshot")
    parser.add_argument("--output", required=True, help="Terminal envelope JSONL")
    parser.add_argument("--profiles-output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--expected-count", type=int, default=100)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--checkpoint-every", type=int, default=25)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--modules", default="registry,accounting_obligation,registry_live,financials,financial_history,roles,group,locations,website")
    parser.add_argument("--external-cache", default="out/.external-cache", help="Directory for external-connector caches (PDFs, Fagfolkguiden pages).")
    parser.add_argument("--external-ocr", action=argparse.BooleanOptionalAction, default=True, help="Enable OCR fallback for image-only annual reports (requires pdftoppm + tesseract; degrades silently if missing).")
    parser.add_argument("--skip-external", action="store_true", help="Disable external-footprint connectors (useful for offline debugging).")
    args = parser.parse_args()

    started_at = utc_now()
    organisation_inputs = read_organisation_inputs(args.organisations)
    orgs = [item["organisation_number"] for item in organisation_inputs]
    if len(orgs) != args.expected_count:
        raise SystemExit(f"Expected {args.expected_count} organisations, received {len(orgs)}")
    profiles, registry_metadata = profiles_from_bulk(args.bulk, orgs)
    annotations = {item["organisation_number"]: item for item in organisation_inputs}
    for profile in profiles:
        for key in ("evaluation_split", "sample_slice"):
            if key in annotations[profile["organisation_number"]]:
                profile[key] = annotations[profile["organisation_number"]][key]
    requested_modules = [item.strip() for item in args.modules.split(",") if item.strip()]
    fetch_modules = set(requested_modules) - {"registry", "accounting_obligation", "website", "external_footprint"}
    external_cache_root = Path(args.external_cache)
    external_enabled = not args.skip_external
    operations = {"requests": 0, "bytes": 0, "latencies_ms": []}

    def enrich(profile: dict) -> tuple[dict, dict]:
        records, metrics = fetch_official_modules(profile["organisation_number"], fetch_modules)
        profile["evidence"].update(records)
        website_metrics = {"requests": 0, "bytes": 0, "latencies_ms": []}
        if "website" in requested_modules:
            website_record, website_metrics = fetch_website(profile.get("website"))
            profile["evidence"]["website"] = apply_website_identity_gate(profile, website_record)["website"]
        external_requests = 0
        if external_enabled:
            external = collect_external(profile, cache_root=external_cache_root, enable_ocr=args.external_ocr)
            profile["evidence"]["external_footprint"] = external
            external_requests = sum(1 for _ in external.get("connectors", {}))
        metric = {
            "requests": len(metrics) + website_metrics["requests"] + external_requests,
            "bytes": sum(item.bytes_received for item in metrics) + website_metrics["bytes"],
            "latencies_ms": [item.elapsed_ms for item in metrics] + website_metrics["latencies_ms"],
        }
        profile["run_metrics"] = metric
        return profile, metric

    state: dict[str, dict] = {}
    resumed_profiles = 0
    profiles_output = Path(args.profiles_output)
    if args.resume and profiles_output.exists():
        prior = [json.loads(line) for line in profiles_output.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not set(item["organisation_number"] for item in prior).issubset(set(orgs)):
            raise SystemExit("Resume profile membership is not a subset of this batch")
        state = {
            item["organisation_number"]: item
            for item in prior
            if profile_complete_for_modules(item, requested_modules)
        }
        resumed_profiles = len(state)
    pending_profiles = [profile for profile in profiles if profile["organisation_number"] not in state]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(enrich, profile): profile["organisation_number"] for profile in pending_profiles}
        for index, future in enumerate(as_completed(futures), 1):
            profile, metric = future.result()
            state[profile["organisation_number"]] = profile
            operations["requests"] += metric["requests"]
            operations["bytes"] += metric["bytes"]
            operations["latencies_ms"].extend(metric["latencies_ms"])
            if index % args.checkpoint_every == 0 or index == len(pending_profiles):
                checkpoint = [state[org] for org in orgs if org in state]
                write_jsonl(profiles_output, checkpoint)

    completed_at = utc_now()
    ordered_profiles = [state[org] for org in orgs]
    envelopes = [
        terminal_envelope(profile, run_id=args.run_id, modules=requested_modules, started_at=started_at, completed_at=completed_at)
        for profile in ordered_profiles
    ]
    validation = validate_envelopes(envelopes, args.expected_count)
    write_jsonl(profiles_output, ordered_profiles)
    write_jsonl(Path(args.output), envelopes)
    latencies = sorted(operations.pop("latencies_ms"))
    operations["p50_ms"] = latencies[len(latencies) // 2] if latencies else None
    operations["p95_ms"] = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))] if latencies else None
    external_summary: dict[str, dict] = {}
    external_observation_total = 0
    for profile in ordered_profiles:
        ext = (profile.get("evidence") or {}).get("external_footprint") or {}
        external_observation_total += len(ext.get("observations") or [])
        for name, status in (ext.get("connectors") or {}).items():
            bucket = external_summary.setdefault(name, {"accepted": 0, "companies_with_observation": 0, "statuses": {}})
            accepted = int(status.get("accepted") or 0)
            bucket["accepted"] += accepted
            if accepted:
                bucket["companies_with_observation"] += 1
            key = str(status.get("status") or ("accepted" if accepted else "none"))
            bucket["statuses"][key] = bucket["statuses"].get(key, 0) + 1
    report = {
        "run_id": args.run_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "expected_count": args.expected_count,
        "emitted_envelopes": len(envelopes),
        "resumed_profiles": resumed_profiles,
        "profiles_fetched_this_run": len(pending_profiles),
        "modules": requested_modules,
        "registry": registry_metadata,
        "operations": operations,
        "external_footprint": {
            "connectors": external_summary,
            "total_observations": external_observation_total,
            "companies_with_any_observation": sum(
                1 for profile in ordered_profiles
                if ((profile.get("evidence") or {}).get("external_footprint") or {}).get("observations")
            ),
        },
        "validation": validation,
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if validation["passed"] else 1)


if __name__ == "__main__":
    main()
