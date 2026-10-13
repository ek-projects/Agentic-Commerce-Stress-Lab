# PayPal AI Hackathon 2026 — Submission Draft

## Project title

**Agentic Commerce Stress Lab**

## One-line pitch

A metamorphic and differential stress-testing lab that finds when AI commerce agents lose the user's payment intent across conversations and handoffs, then verifies that unsafe attempts stop before the PayPal payment boundary.

## Devpost description

AI commerce agents can turn a natural-language mandate into tool calls, handoffs, revised proposals, and finally a payment. The hard part is not only whether an agent can pay — it is whether the payment still represents what the user actually confirmed.

Agentic Commerce Stress Lab generates semantically equivalent, ambiguous, and adversarial variants of the same commerce trace, runs them through agents under test, compares their payment decisions, reconstructs intent lineage, and applies an independent deterministic authorization boundary before PayPal. Irrelevant conversational changes should preserve the same payment. Material changes such as amount drift, merchant drift, cancellation, replay, or detached confirmation must stop or require clarification.

The lab includes local AI mutation generation plus two independent local decision-model families (Qwen2.5 and SmolLM2). On the controlled 60-trace cross-model corpus, both models chose `PAY` on all 40 material attack traces. The deterministic boundary contained every tested unsafe attempt. We then verified the provider boundary end to end with PayPal Sandbox: a known-blocked trace made zero provider calls, while a guarded `ALLOW` trace authenticated through PayPal OAuth and created an Orders v2 Sandbox order with status `CREATED`.

The goal is not to make an LLM the final payment authority. AI creates realistic stress cases and exposes behavioral failures; deterministic, auditable authorization evidence decides whether money may move.

## Why PayPal is central

- Uses PayPal OAuth 2.0 in Sandbox.
- Uses PayPal Orders v2 `POST /v2/checkout/orders`.
- Derives `PayPal-Request-Id` from guarded intent/consent context for idempotency.
- Exercises the payment boundary with both an explicit negative control and a verified safe order.
- The client is sandbox-only and rejects the live PayPal endpoint.

## How AI is used

- Qwen2.5-0.5B-Instruct generates adversarial/semantic mutation plans.
- Qwen2.5-1.5B-Instruct acts as a commerce decision model under test.
- SmolLM2-1.7B-Instruct provides an independent model-family comparison.
- The benchmark compares raw model actions separately from deterministic adapter/boundary behavior.
- AI never mints authorization evidence and is not the final authority for payment execution.

## Judge quick start

Requires Python 3.10+; the core judge demo has no third-party Python dependency.

```bash
python3 -m unittest -v
python3 web_demo.py
```

Open `http://127.0.0.1:8088`. The dashboard runs the offline differential suite and displays bundled sanitized snapshots of the verified cross-model and PayPal Sandbox evidence. It does not perform any PayPal network call while being viewed.

Optional reproducibility paths for local models and authenticated Sandbox execution are documented in `README.md`, `LOCAL_AI.md`, and `RESULTS.md`.

## Verified evidence

- Template differential suite: boundary 40/40; zero MUST_BLOCK network allowances.
- Metamorphic template suite: 80/80 relations pass.
- Qwen2.5 expanded run: 44/60 raw unsafe `PAY`; boundary 60/60.
- SmolLM2 expanded run: 45/60 raw unsafe `PAY`; boundary 60/60.
- Cross-model raw action agreement: 59/60.
- Material attack traces: both models output `PAY` on 40/40.
- PayPal Sandbox OAuth: authenticated successfully.
- Negative control: `attack-detached-confirmation-0` → `BLOCK`, provider called: false.
- Safe control: `benign-stable-0` → `ALLOW`, PayPal Orders v2 status: `CREATED`.

See `evidence/` for the sanitized snapshots included in the repository. Generated runtime reports contain additional detail and are ignored by Git.

## What is original here

The project does not claim that deterministic payment guards, replay protection, or agent-commerce benchmarks are new. Its focus is the combination of:

1. conversation-to-payment metamorphic relations;
2. AI-generated semantic and multi-agent handoff perturbations;
3. differential execution across agent/model configurations;
4. intent-lineage reconstruction for payment fields;
5. PayPal Sandbox as the observable execution boundary.

See `ORIGINALITY.md` for prior-art positioning.

## Limitations

- The benchmark corpus is controlled and synthetic; results are not estimates of real-world attack prevalence.
- The cross-model study uses two small local model families and different quantizations; it is not a general model ranking.
- Boundary containment does not make an incorrect model decision correct; the UI reports both separately.
- No production PayPal endpoint or real-money payment is used.

## Demo video script — target 2:35

**0:00–0:18 — Hook**

“An AI shopping agent can remember what you asked for and still lose what you actually authorized. Agentic Commerce Stress Lab tests the gap between conversation and payment.”

Show the dashboard title and the three-stage Judge Demo panel.

**0:18–0:48 — The failure**

Show cross-model evidence. Explain that the same 60 controlled traces were run through Qwen2.5 and SmolLM2. Highlight: 59/60 raw-action agreement, and both models chose `PAY` on 40/40 material attack traces.

**0:48–1:20 — Metamorphic testing**

Show a differential row: an irrelevant change is `SAME_PAYMENT`; an amount/currency/merchant/cancellation/replay mutation is `MUST_BLOCK`. Show intent lineage or the row table and emphasize that agent correctness and payment-boundary containment are scored separately.

**1:20–1:55 — Independent boundary**

Show the negative-control result. “The model wants to pay, but authorization evidence no longer matches the current proposal. The deterministic boundary blocks it before the provider call.” Highlight provider called: NO.

**1:55–2:20 — PayPal integration**

Show PayPal Sandbox readiness: authenticated OAuth and E2E create-order VERIFIED. “For a known-safe ALLOW trace, the same boundary permits the PayPal Orders v2 call; Sandbox returns CREATED.”

**2:20–2:35 — Close**

“AI generates and exposes the failure. An auditable boundary decides whether money moves. That gives agent builders a reproducible way to test payment intent before deployment.”

## Video recording checklist

- Keep the video under 3 minutes.
- Record the actual local dashboard running, not static slides.
- Do not show Sandbox credentials, OAuth tokens, order IDs, or account details.
- Avoid copyrighted music and unnecessary third-party logos.
- Upload publicly to YouTube and place the link in Devpost.

## Submission checklist

- [x] Working prototype
- [x] Meaningful AI functionality
- [x] Meaningful PayPal integration
- [x] PayPal Sandbox authenticated end-to-end verification
- [x] Open-source license in repository
- [x] Reproducible judge quick start
- [x] Sanitized verified evidence bundled in repository
- [ ] Public GitHub/GitLab/Bitbucket repository URL
- [ ] Public YouTube demo video under 3 minutes
- [ ] Final Devpost form submitted
