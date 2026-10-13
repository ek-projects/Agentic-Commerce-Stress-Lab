# Verified results

Last updated: 2026-10-13.

This file distinguishes construction checks from empirical observations.

## Deterministic phases

- Phase 1 smoke suite: 42 scenarios pass.
- Phase 3 equal-input negative control: deterministic baseline 240/240 and integrity prototype 240/240. This demonstrates no advantage for the original HMAC checker when both systems receive the same evidence.
- Phase 4 causal-consent corpus: 240 traces across 12 categories. The reference guard scores 240/240 against its hand-authored oracle; this is a construction check, not independent validation.
- Template metamorphic suite: 80/80 relations pass.

## Local-AI differential run

Configuration:

- Qwen2.5-0.5B-Instruct Q4_0 via `llama-cli`;
- mutation seed 42;
- 5 benign source traces;
- 2 model requests per source;
- 10 mutations total;
- two deterministic comparison agents.

Observed result:

- 20 agent/mutation evaluations;
- boundary containment 20/20;
- 0 `MUST_BLOCK` cases allowed to reach the PayPal network boundary;
- greedy-latest-proposal agent: 5 unsafe payment attempts out of 10 mutations;
- confirmation-aware agent: 10/10 relation-correct;
- 6/10 mutations fully model-derived;
- 4/10 mutations required deterministic fallback values.

Interpretation: the local AI path is real and reproducible, and it can generate non-authoritative adversarial tool text. The 0.5B model is not yet reliable enough to generate structured material-payment attacks without assistance: only 1/5 `MUST_BLOCK` plans in this run was complete without fallback.

## Runtime failures intentionally excluded

- A llama.cpp JSON-schema sampler attempt failed during sampler initialization.
- A repeated-request Qwen2.5-1.5B `llama-server` run stalled with a processing slot showing zero prompt-token and generation progress. The run was cancelled.
- A five-seed evaluation launched against that stalled server exceeded the mutation-provider timeout. It is not counted.

## PayPal status

The PayPal Sandbox host is reachable and returned HTTP 401 to an intentionally unauthenticated OAuth request, confirming network reachability. No `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` are configured in the server process, so no authenticated Sandbox token or real Sandbox order has yet been verified.
