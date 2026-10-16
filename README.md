# Signalpost Challenge Submission

Agent that researches Norwegian companies by organisation number and returns a terminal JSONL envelope per input, with claim-level evidence, availability states, and refresh metadata.

Round 1 runs 23 Aug – 21 Oct 2026. Revision cutoff: 18 Oct 2026. See [`docs/challenge/brief.md`](docs/challenge/brief.md) and [`docs/challenge/evaluation-contract.md`](docs/challenge/evaluation-contract.md).

## Repository layout

```
.
├── README.md                       # this file
├── SUBMISSION.md                   # official submission metadata (URL, commit, costs)
├── docs/
│   └── challenge/                  # organiser-provided brief, contract and guides
├── signalpost-starter-kit/         # the runnable agent (preserved layout)
│   ├── README.md                   # starter-kit docs (first-run walkthrough)
│   ├── OUTPUT_CONTRACT.md          # terminal-envelope schema
│   ├── pyproject.toml / uv.lock    # pinned Python 3.12+ dependencies
│   ├── select_entry_batch.py       # builds a local JSONL batch from the universe
│   ├── scripts/                    # run_competition_batch.py, run_refresh_replay.py, connectors
│   ├── src/norway_company_agent/   # library code (identity, evidence, refresh, batch, …)
│   ├── tests/                      # pytest suite + evaluator fixtures
│   └── docs/                       # architecture, control loop, connectors, sources
└── .gitignore                      # excludes caches, env, large registry data, local output
```

Starter-kit directory structure is preserved to avoid breaking imports, scripts, tests, and relative paths used by the control-loop/refresh code.

## Architecture (one paragraph)

The agent anchors identity in the Brønnøysund (BRREG) bulk registry, pulls official financials/roles/workplaces, then verifies the registry-listed website and emits one terminal envelope per input organisation number. Each claim carries source URL, retrieval timestamp, content SHA-256, and an availability state (`available`, `not_available`, `blocked`, `not_applicable`, `ambiguous`, `failed`). Snapshots feed a deterministic refresh replay that reports material changes idempotently. External-footprint connectors (website activity, Google News RSS, LinkedIn guest, Fagfolkguiden reviews, YouTube, Google Maps normalization, annual-report workforce extraction) widen coverage without weakening identity gates.

## Setup

Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```bash
cd signalpost-starter-kit
uv sync
```

## Verification (no network required)

Runs the full pytest suite and the deterministic refresh replay against bundled fixtures:

```bash
cd signalpost-starter-kit
uv run --with pytest pytest -q
uv run python scripts/run_refresh_replay.py \
  --manifest tests/fixtures/refresh-snapshots.json \
  --output out/refresh-demo.json
```

Expected: `104 passed, 5 subtests passed` and the replay report writes `qualification_passed: true`, `precision: 1.0`, `recall: 1.0`, `evidence_complete: true`, `idempotent_rerun: true`.

## 100-company smoke test (live network)

```bash
cd signalpost-starter-kit

curl -L 'https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv' -o brreg-enheter.csv
curl -L 'https://builderr.ai/signalpost-company-universe-2025.jsonl.gz' -o signalpost-universe.jsonl.gz

uv run python select_entry_batch.py \
  --universe signalpost-universe.jsonl.gz \
  --count 100 \
  --output smoke-companies.jsonl

uv run python scripts/run_competition_batch.py \
  --organisations smoke-companies.jsonl \
  --bulk brreg-enheter.csv \
  --profiles-output out/smoke-profiles.jsonl \
  --output out/smoke-envelopes.jsonl \
  --report out/smoke-report.json \
  --run-id smoke-001 \
  --expected-count 100
```

The report is written to `signalpost-starter-kit/out/smoke-report.json` (gitignored; regenerate locally). A frozen copy of our baseline smoke run is tracked at [`signalpost-starter-kit/smoke/smoke-report.json`](signalpost-starter-kit/smoke/smoke-report.json) when published.

## Evaluator command (official batch)

Point `--organisations` at the Builderr-supplied batch:

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

Produces exactly one terminal envelope per input company in `out/envelopes.jsonl`, with claim-level source/retrieval-time/content hash and a machine-readable run report (`out/run-report.json`) covering runtime, request count and third-party cost.

## Output contract

See [`signalpost-starter-kit/OUTPUT_CONTRACT.md`](signalpost-starter-kit/OUTPUT_CONTRACT.md).

## Data

- `financial-filer-master-2025.jsonl` (~125 MB) is kept locally for research and is **excluded from Git**. It is derived from the public frozen 2025-filer snapshot; regenerate from the published universe.
- `brreg-enheter.csv` and `signalpost-universe.jsonl.gz` are downloaded on demand and excluded from Git.

## Source rights

Follow each source's terms, robots policy, rate limits and licence. Open-source connector code does not grant platform permission. LinkedIn, Meta and Indeed are discovery targets with restrictions — use permitted APIs, licensed providers, or return `blocked` / `not_available`. See [`signalpost-starter-kit/docs/external-connectors.md`](signalpost-starter-kit/docs/external-connectors.md) and [`docs/challenge/perimitted-sources.md`](docs/challenge/perimitted-sources.md).

## Submission

See [`SUBMISSION.md`](SUBMISSION.md) for the submission metadata the organisers request.
