# Submission email (ready to send)

**To:** submit@builderr.ai
**Subject:** Signalpost Round 1 — Submission v1 — Dhruval Padia

---

Hi,

Signalpost Round 1 submission.

Agent name: Dhruval Padia
Repository URL: https://github.com/dhruval30/signalpost-challenge
Exact commit hash: 46e46c41d5d78cb57c8b64f65ebd7f7488f33904
100-company smoke-test result or report URL: https://github.com/dhruval30/signalpost-challenge/blob/46e46c41d5d78cb57c8b64f65ebd7f7488f33904/signalpost-starter-kit/smoke/smoke-report.json
One-command run instruction: `cd signalpost-starter-kit && uv sync && curl -L 'https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv' -o brreg-enheter.csv && uv run python scripts/run_competition_batch.py --organisations <builderr-batch.jsonl> --bulk brreg-enheter.csv --profiles-output out/profiles.jsonl --output out/envelopes.jsonl --report out/run-report.json --run-id <builderr-run-id> --expected-count <batch-size>`
Models / APIs / licences: BRREG Enhetsregisteret bulk CSV + REST (Norwegian open government data, NLOD-compatible); registry-listed company websites fetched in compliance with robots and rate limits; permitted public RSS/HTTP feeds via included connectors (Google News RSS, YouTube search, Fagfolkguiden reviews, LinkedIn guest surfaces, Google Maps result normalization, annual-report workforce extractor). No proprietary LLM API on the evaluator path. No server-side secrets required; any optional connector reads credentials from environment variables only and returns `blocked` / `not_available` when unset.
Expected cost per official run: USD 0.00 per 100-company run and USD 0.00 projected for a 1,000-company official batch at current configuration (BRREG + public websites + RSS only; `third_party_cost_usd` reported per run).
Contact for results: padiadhruval@gmail.com
Builderr source: source=mlcontests.com

Thanks,
Dhruval Padia
padiadhruval@gmail.com
