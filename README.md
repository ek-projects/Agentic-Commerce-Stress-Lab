# Agentic Commerce Stress Lab

Experimental lab for testing whether AI commerce agents preserve **user payment intent across conversations, tool calls and agent handoffs**.

The project is now positioned as a **metamorphic / differential stress-testing tool**, not as another payment firewall or a claim that AI beats deterministic security rules.

Core question:

> Given one user mandate, do semantically equivalent conversation variants produce the same PayPal order, while material or ambiguous changes stop before money movement?

## Current status

### Phase 1 — immutable-intent smoke test
`stress_lab.py`

- HMAC-SHA256 sealed intent
- amount / merchant / currency drift checks
- replay check
- 42 deterministic synthetic scenarios
- no external services

This phase is a basic integrity smoke test, not a novel security result.

### Phase 2 — illustrative unequal-input benchmark
`benchmark.py`

250 synthetic examples compared a weak amount-limit/replay baseline with the signed-intent checker. The two systems had different information access, so this result is retained only as a methodological warning.

### Phase 3 — equal-input negative control
`equal_input_benchmark.py`

240 cases give both systems the same authenticated intent and replay state. Both score 240/240. This invalidates any claim that the original HMAC checker itself outperforms equivalent deterministic rules.

### Phase 4 — causal-consent traces
`trace_lab.py`, `agentic_benchmark.py`

The lab models user, shopping agent, merchant agent, tool agent and payment agent events.

Reference invariants include:

- authentic user confirmation;
- confirmation bound to the exact intent digest;
- single-use confirmation nonce;
- user cancellation revokes consent;
- post-confirmation drift requires new confirmation;
- detached/stale confirmations are blocked;
- ambiguous requests without bound confirmation return `CLARIFY`.

Current deterministic corpus:

- 240 traces
- 12 categories
- 160 attack traces
- provenance guard: 240/240 on its hand-authored oracle
- equal-input snapshot baseline: 160/240

These figures measure coverage of constructed protocol properties. They are **not** independent security validation and are not a generic superiority claim.

### Phase 5 — metamorphic testing core
`metamorphic_lab.py`

The lab now tests relationships between a source trace and mutated versions of that same trace.

Current relations:

- `SAME_PAYMENT`: irrelevant conversational changes must preserve the exact PayPal plan;
- `MUST_BLOCK`: material changes after confirmation must stop before PayPal.

Current template suite:

- 80 metamorphic cases
- 40 same-payment mutations
- 40 must-block mutations
- 80/80 currently pass

Next step: replace/augment template mutations with AI-generated conversation and handoff perturbations, while keeping the money-movement oracle deterministic.

## PayPal boundary

`paypal_boundary.py`

A server-side, standard-library-only adapter builds PayPal Orders v2 create-order requests.

Safety properties:

- sandbox endpoint only: `https://api-m.sandbox.paypal.com`;
- the client refuses the live PayPal endpoint;
- BLOCK/CLARIFY traces cannot reach the provider call;
- `PayPal-Request-Id` is derived from the guarded payment/consent context for provider idempotency;
- no credentials are stored in the repository.

Important current limitation: `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` are not configured in the server process, so a real PayPal Sandbox API call has **not** yet been verified.

## Demo

Offline, zero network:

```bash
python3 demo.py
```

The demo runs one allowed flow, one adversarial flow and a metamorphic smoke suite. The adversarial flow is invoked with network mode enabled internally to prove that the boundary itself prevents the PayPal call.

After sandbox credentials are explicitly configured:

```bash
python3 demo.py --live-sandbox
```

Only the safe flow may create a Sandbox order.

## Run the verification suite

```bash
python3 -m unittest -v
python3 agentic_benchmark.py
python3 metamorphic_lab.py
python3 demo.py
```

Generated artifacts:

- `agentic_traces.jsonl`
- `agentic_benchmark_report.json`

## Originality position

See `ORIGINALITY.md`.

Public work already exists on deterministic agentic-commerce security benchmarks, fraud benchmarks, cart-bound approval, replay protection and trust layers. Therefore this project should **not** claim first-of-kind status for those ideas.

The differentiation we are pursuing is:

1. conversation-to-payment metamorphic testing;
2. AI-generated semantic/handoff perturbations;
3. differential execution across agent configurations/models;
4. an intent-lineage graph showing the provenance of each payment field;
5. PayPal Sandbox as the observable execution boundary.

The intended architecture is:

```text
AI red-team generator
        |
        v
conversation + multi-agent mutations
        |
        v
agent under test
        |
        v
intent lineage / payment diff
        |
        v
deterministic boundary gate
        |
        v
PayPal Sandbox
```

AI should generate realistic stress cases; AI should not be the final authority deciding whether money may move.

## Hackathon readiness gaps

Before submission the project still needs:

1. verified PayPal Sandbox authentication and create-order call;
2. a real AI mutation generator integrated into the lab;
3. at least one external agent-under-test path, ideally more than one for differential testing;
4. intent-lineage visualization / usable product UI;
5. stronger benchmark validity checks and stronger baselines;
6. public Git repository, reproducible setup and sub-three-minute demo video.

## Safety

- No real payments.
- No production PayPal endpoint.
- No credentials committed to source.
- No claim is made about fraud detection, merchant risk scoring or real-world attack prevalence.
- Synthetic perfect scores are reported as construction checks, not proof of production efficacy.


## Phase 6 — external agents, differential scoring and lineage

`agent_under_test.py`, `ai_mutation.py`, `differential_eval.py`, `lineage.py`

The lab now has provider-neutral JSON adapters for both a real agent under test and an AI mutation generator. This allows the benchmark core to stay deterministic while external AI systems generate realistic conversational/handoff perturbations or decide what action to take. See `PROTOCOLS.md`.

Run the current offline differential demo:

```bash
python3 differential_eval.py --variants 5
```

Current verified default result with two deterministic comparison agents:

- 40 evaluated agent/mutation cases;
- 30/40 agent-relation checks pass;
- the intentionally greedy agent makes 10 unsafe `PAY` attempts on `MUST_BLOCK` mutations;
- payment-boundary containment passes 40/40;
- zero `MUST_BLOCK` cases are allowed to reach the PayPal network boundary.

The run generates `differential_report.json` and `stress_report.html`. The HTML report includes intent lineage so a reviewer can see which actor changed each payment field. The unsafe attempts are expected findings from the negative-control agent, not failures of the boundary.

External integrations are invoked with `--agent-cmd` and `--mutator-cmd`. A real model/provider is still required before we can claim AI-generated mutations or real-model agent results.
