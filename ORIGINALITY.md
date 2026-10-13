# Originality / competitor check — 2026-10-13

This note exists to prevent the project from making novelty claims that are no longer defensible.

## Closest public work found

### AIP-Bench / PCAT
Paper: `Protocol-Level Attacks on Agentic Commerce Platforms: A Cross-Platform Taxonomy, AIP-Bench, and Unified Defense` (2026)

Public artifact: https://github.com/yedidel/aip-bench-public

Overlap with us:
- deterministic agentic-commerce security benchmark;
- protocol-level attacks rather than model-only failures;
- replay / authorization / structural trust concerns;
- platform-agnostic defense layer.

Conclusion: **we must not claim to be the first deterministic agentic-commerce security benchmark.**

### Agentic Commerce Bench / gordonguard
Paper: `Agentic Commerce Bench: Measuring Fraud Detection for Agents That Spend Money` (2026)

Public artifact: https://github.com/BuildWithGordonAI/agentcommercebench

Overlap with us:
- offline stress harness;
- intent/action mismatch, replay, payee substitution and hostile counterparties;
- explicit benchmark-validity methodology and equal-input comparisons.

Conclusion: a broad fraud benchmark would be crowded and difficult to differentiate.

### alex-hahn/agentic-commerce
Repository: https://github.com/alex-hahn/agentic-commerce

Overlap with us:
- trust layer between an LLM agent and commerce execution;
- single-use, cart-bound human approval;
- prompt-injection containment;
- deterministic policy engine and replay/idempotency controls.

Conclusion: **cart-bound approval + policy guard is not enough as a hackathon novelty claim.**

### AP2 and related work
AP2 already treats mandate binding, checkout association and replay protection as core protocol concerns. Recent security analyses also focus on manipulated pre-authorization context and cross-agent/tool trust boundaries.

Conclusion: cryptographically binding a final checkout to prior approval is important, but not novel by itself.

## Revised position

Do **not** pitch Agentic Commerce Stress Lab as another payment firewall, mandate protocol or generic benchmark.

Pitch it as a **metamorphic / differential testing lab for AI commerce agents**:

> Given one user mandate, generate many semantically equivalent, ambiguous and adversarial conversation/handoff variants, run them through an agent stack, and compare the resulting structured payment attempt at the PayPal boundary.

The product question becomes:

**"Does the agent still produce the same safe PayPal order when the conversation, tool outputs and agent handoffs are perturbed — and does it stop or ask again when a material term changes?"**

This is a testing product rather than a competing payment protocol.

## Differentiation to protect

1. **Conversation-to-payment metamorphic tests**
   - paraphrases that should not alter the payment;
   - ambiguous revisions that should force clarification;
   - material revisions that should require fresh consent;
   - malicious tool / merchant / sub-agent text that tries to alter the payment.

2. **Differential execution**
   Run the same mandate and mutation set against multiple agent configurations/models and compare the final PayPal request, not just the model text.

3. **Intent lineage graph**
   Show where each payment field came from and at which event it changed: user, shopping agent, merchant, tool, or payment agent.

4. **PayPal as the observable execution boundary**
   A passing trace may create a PayPal Sandbox order. BLOCK/CLARIFY traces must never call PayPal. The lab records the exact request body and provider idempotency key.

5. **AI is the adversarial generator, not the security oracle**
   Use AI to create realistic conversational mutations and multi-agent handoffs. Keep the final money-movement invariants deterministic and auditable.

## Claims we can make only after evidence exists

- We can say we provide an equal-input, reproducible stress harness.
- We can say the current synthetic reference guard passes the hand-authored invariants.
- We cannot yet say AI-generated attacks find failures in real agents.
- We cannot yet say PayPal Sandbox integration works: credentials are not currently configured on the server.
- We cannot claim independent benchmark validity until the generator/oracle coupling is reduced and stronger baselines are added.

## Hackathon fit

The PayPal AI Hackathon requires meaningful PayPal + AI integration, a working prototype, public source and a functional demo. Judging equally weights technological implementation, design, potential impact, innovation and presentation.

The most credible path is therefore:

**AI red-team generator -> agent under test -> intent-lineage/diff engine -> deterministic payment-boundary gate -> PayPal Sandbox -> visual report.**

That is materially more differentiated than the current HMAC/state-machine prototype and produces a clear sub-three-minute demo story.
