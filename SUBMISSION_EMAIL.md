# Submission email (ready to send)

**To:** submit@builderr.ai
**Subject:** Signalpost Round 1 — Submission v1 — `<AGENT NAME>`

---

Hi Signalpost team,

Please find our Round 1 submission below.

**Agent name:** `<FILL — e.g. Numerize Signalpost Agent>`
**Contact:** developer@numerize.ai
**Submission version:** 1 (baseline)

**Repository:** https://github.com/dhruval30/signalpost-challenge
**Exact commit SHA:** `8dc9ca72894546162af5b9bcffee430cf6e05788`
**Branch:** `main`

**Setup (Python 3.12+ with [`uv`](https://docs.astral.sh/uv/)):**

```
git clone https://github.com/dhruval30/signalpost-challenge.git
cd signalpost-challenge/signalpost-starter-kit
uv sync
curl -L 'https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv' -o brreg-enheter.csv
```

**Evaluator command (one documented command, accepts a JSONL batch of organisation numbers):**

```
uv run python scripts/run_competition_batch.py \
  --organisations <builderr-batch.jsonl> \
  --bulk brreg-enheter.csv \
  --profiles-output out/profiles.jsonl \
  --output out/envelopes.jsonl \
  --report out/run-report.json \
  --run-id <builderr-run-id> \
  --expected-count <batch-size>
```

Produces exactly one terminal envelope per input in `out/envelopes.jsonl` and a machine-readable run report (`out/run-report.json`) with runtime, request count and third-party cost.

**100-company smoke-test report:** `signalpost-starter-kit/smoke/smoke-report.json` in the repository (reproducible with `smoke-companies.jsonl` → `run_competition_batch.py --run-id smoke-001 --expected-count 100`). See `SUBMISSION.md` for the exact reproduce commands.

**Models and APIs:** BRREG Enhetsregisteret (public bulk CSV + REST) for identity, roles, workplaces and financials; registry-listed company websites for identity verification and site activity; permitted public RSS/HTTP feeds via the included connectors (Google News RSS, YouTube search, Fagfolkguiden reviews, LinkedIn guest surfaces, Google Maps result normalization, annual-report workforce extractor). No proprietary LLM is on the evaluator path. No server-side secrets are required; any optional connector reads credentials from environment variables only and is skipped (returning `blocked` / `not_available`) when unset.

**Source rights and licences:** BRREG data under NLOD-compatible terms; company websites fetched in compliance with robots and rate limits with content hash + retrieval timestamp recorded per claim; LinkedIn/Meta/Indeed via permitted surfaces only.

**Estimated external API cost per official batch:** USD 0.00 at current configuration. Projected cost for a 1,000-company official batch: USD 0.00. The run report's `third_party_cost_usd` field is populated per batch.

**Compliance checklist:**

- One terminal envelope per input (enforced by `terminal_envelope` / `validate_envelopes`)
- Claim-level `source_url`, `retrieved_at`, `content_sha256`
- Availability states: `available` / `not_available` / `blocked` / `not_applicable` / `ambiguous` / `failed`; missing values never silently converted to zero
- Idempotent refresh with prior snapshots preserved (verified by `scripts/run_refresh_replay.py`)
- Pinned Python 3.12+ dependencies (`pyproject.toml` + `uv.lock`)
- 104 tests + 5 subtests pass (`uv run --with pytest pytest -q`)
- 100-company smoke-test report included
- No fabricated financial values; wrong-company matches return `ambiguous` or `not_available`

Thanks — happy to answer anything.

`<FILL — signature>`
