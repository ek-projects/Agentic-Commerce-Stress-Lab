# External integration protocols

Agentic Commerce Stress Lab keeps model/provider credentials outside the benchmark core. Real AI systems plug in through small JSON stdin/stdout adapters.

## Agent-under-test protocol

Run:

```bash
python3 differential_eval.py --agent-cmd "python3 /path/to/my_agent_adapter.py"
```

The adapter receives one JSON object on stdin containing the trace name, category, conversation and multi-agent event history, plus the expected output schema.

It must emit exactly one JSON object with `action` set to `PAY`, `CLARIFY`, or `STOP`. A `PAY` action must include a structured payment intent plus any confirmation nonce/digest the agent is relying on.

The lab independently appends that action to the trace, runs the deterministic boundary guard, builds the PayPal request plan and records field lineage. Agent prose is never treated as payment authorization.

For heavyweight local or remote adapters, `agent_decision_benchmark.py` also supports `--persistent-agent-cmd`. The persistent contract is newline-delimited JSON: one complete stimulus object per input line and exactly one complete action object per output line. The process remains alive across traces, allowing model weights and provider sessions to stay loaded; benchmark traces remain separate requests and the boundary/oracle logic is unchanged.

A persistent adapter is responsible for request isolation. The bundled local Qwen adapter explicitly resets the llama.cpp context before each request while retaining loaded weights. A persistent provider integration should provide an equivalent fresh-conversation guarantee rather than carrying conversational state from one benchmark trace into the next.

## AI mutation-provider protocol

Run:

```bash
python3 differential_eval.py --mutator-cmd "python3 /path/to/my_ai_mutator.py"
```

The external command receives a structured mutation request describing the source trace, the metamorphic relations and the output schema.

It returns a JSON object with a `mutations` array. Each mutation contains a name, a relation (`SAME_PAYMENT` or `MUST_BLOCK`), an event array and a short rationale. Providers may also attach a `metadata` object; the differential report preserves it so model identity, seed, normalizations and fallback use remain auditable.

`SAME_PAYMENT` means the mutation is semantically irrelevant to payment terms; a correct agent should preserve the same payment. `MUST_BLOCK` means the mutation materially changes or revokes authority; the system must not send the changed payment without fresh valid confirmation.

The mutation provider may be backed by any AI model. The lab deliberately avoids coupling the benchmark to one vendor SDK. The bundled local Qwen adapter constrains AI-labelled `SAME_PAYMENT` cases to non-authoritative merchant/tool text rather than free-form user paraphrases; this prevents the same model from silently defining both the perturbation and its semantic-equivalence oracle.

## Differential output

`differential_eval.py` produces:

- `differential_report.json` — machine-readable results;
- `stress_report.html` — self-contained visual report;
- separate scores for agent behavior and payment-boundary containment;
- an intent-lineage view showing which actor changed each payment field.

This separation matters: an unsafe agent attempt is a valid stress-test finding even when the deterministic payment boundary successfully contains it.

## Raw model vs adapter output

An external agent adapter may include audit metadata such as `model_raw`, `model`, `seed`, `mode`, `adapter_fallback`, and `authorization_facts`. The decision benchmark keeps the raw model action separate from the adapter's final action.

This distinction matters when an adapter applies a fail-safe. For example, if a model returns `PAY` but no structured confirmation exists, an adapter may safely emit `CLARIFY`; the report still records the model's raw `PAY` as an unsafe model decision rather than crediting the correction to the model.

The deterministic payment boundary independently evaluates any final `PAY`. Adapter safety and boundary safety are therefore visible as separate layers rather than merged into one score.
## Cross-model report comparison

`compare_model_reports.py` compares reports only after verifying that their raw-model rows cover the same trace identifiers. It reports raw-action agreement separately from adapter-action agreement, because deterministic adapter fail-safes can make final actions agree even when the underlying models disagree. `run_cross_model_compare.sh` is the bundled sequential runner for Qwen2.5 and SmolLM2.
