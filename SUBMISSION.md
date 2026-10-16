# Signalpost — Submission Metadata

## Repository

- GitHub: https://github.com/dhruval30/signalpost-challenge
- Commit SHA: `<FILL_AFTER_PUSH>`
- Branch: `main`

## Agent

- Agent name: `<FILL>`
- Contact: `<FILL — email the organisers should reach>`
- Version: 1 (baseline)

## Reproducible setup

Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/dhruval30/signalpost-challenge.git
cd signalpost-challenge/signalpost-starter-kit
uv sync
```

## Evaluator command

Exactly one documented command. It accepts a Builderr-supplied JSONL batch of organisation numbers and writes one terminal envelope per input to `out/envelopes.jsonl` plus a machine-readable run report.

```bash
cd signalpost-starter-kit
uv run python scripts/run_competition_batch.py \
  --organisations <builderr-batch.jsonl> \
  --bulk brreg-enheter.csv \
  --profiles-output out/profiles.jsonl \
  --output out/envelopes.jsonl \
  --report out/run-report.json \
  --run-id <builderr-run-id> \
  --expected-count <batch-size>
```

Pre-step (fetch BRREG bulk CSV once per run, pinned to the official endpoint):

```bash
curl -L 'https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv' -o brreg-enheter.csv
```

## 100-company smoke test

Location in repository:

- Report: `signalpost-starter-kit/smoke/smoke-report.json`
- Envelopes: not committed (regenerate with the command below; large and reproducible).

Reproduce:

```bash
cd signalpost-starter-kit
curl -L 'https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv' -o brreg-enheter.csv
curl -L 'https://builderr.ai/signalpost-company-universe-2025.jsonl.gz' -o signalpost-universe.jsonl.gz
uv run python select_entry_batch.py --universe signalpost-universe.jsonl.gz --count 100 --output smoke-companies.jsonl
uv run python scripts/run_competition_batch.py \
  --organisations smoke-companies.jsonl \
  --bulk brreg-enheter.csv \
  --profiles-output out/smoke-profiles.jsonl \
  --output out/smoke-envelopes.jsonl \
  --report out/smoke-report.json \
  --run-id smoke-001 \
  --expected-count 100
```

Offline verification (no network):

```bash
cd signalpost-starter-kit
uv run --with pytest pytest -q      # 104 tests + 5 subtests
uv run python scripts/run_refresh_replay.py \
  --manifest tests/fixtures/refresh-snapshots.json \
  --output out/refresh-demo.json    # qualification_passed: true
```

## Models and APIs used

- **BRREG Enhetsregisteret** (public bulk CSV + REST): identity anchor, roles, workplaces, financials, group links. Rate-limited per BRREG terms.
- **Registry-listed company websites**: HTTP fetch for identity verification and site activity/news extraction (static HTML first; headless browser escalation only when a deterministic completeness check fails).
- **Permitted public RSS/HTTP feeds** via the included connectors (Google News RSS, YouTube search, Fagfolkguiden reviews, LinkedIn guest surfaces, Google Maps result normalization, annual-report workforce extractor).
- **No proprietary LLM API** is invoked by the evaluator command path. The optional sentiment extra uses a local transformers model (`torch`/`transformers`/`accelerate`) and is not required for the baseline evaluator run.

No server-side secrets are required for the baseline evaluator command. Any connector that needs an API key reads it from an environment variable only and is skipped (returning `blocked` / `not_available`) when the variable is unset.

## Source rights and licences

- BRREG data: Norwegian government open data (NLOD-compatible), used in accordance with BRREG terms.
- Public company websites: fetched in compliance with each site's robots policy and rate limits. Content hashes and retrieval timestamps are recorded for every claim.
- Code licence: see repository (defaults to the organiser-supplied starter-kit terms where applicable).
- Platform data: LinkedIn / Meta / Indeed are not scraped directly; permitted guest or outbound-link surfaces only. Returns `blocked` where restricted.

## Estimated external API cost per official batch

- Baseline evaluator path: **USD 0.00** per 100-company run (BRREG + public websites + RSS only). Current per-run `third_party_cost_usd` in the machine-readable report is `0`.
- Projected cost for a 1,000-company official batch: **USD 0.00** at current configuration. Any future connector that incurs cost will be declared explicitly in the run report.

## Checks against the official-run contract

- [x] Pinned Python 3.12+ dependencies (`pyproject.toml` + `uv.lock`)
- [x] One documented evaluator command
- [x] Exactly one terminal envelope per input (enforced by `terminal_envelope` / `validate_envelopes`)
- [x] Claim-level source URL, retrieval time, content SHA-256
- [x] Availability states: `available` / `not_available` / `blocked` / `not_applicable` / `ambiguous` / `failed` (no silent zeros)
- [x] Idempotent refresh with prior snapshots preserved (`run_refresh_replay.py`)
- [x] 100-company smoke-test report included in the repository
- [x] Machine-readable run report with runtime, request count, third-party cost
- [x] Source rights and secrets handling documented above

## Leaderboard

No official leaderboard score is claimed yet. Score is reported by Builderr after an official batch run.
