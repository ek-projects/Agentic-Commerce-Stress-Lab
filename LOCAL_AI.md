# Local AI mutation runtime

Verified on 2026-10-13.

## Recommended reproducible path

The stable local benchmark path uses:

- `llama.cpp-tools` from the Kali package repository;
- `/usr/bin/llama-cli`;
- runtime observed: `0.5.0` / Debian build 11146;
- Qwen2.5-0.5B-Instruct GGUF, Q4_0;
- local path: `/mnt/seagate/Models/Agentic-Commerce-Stress-Lab/qwen2.5-0.5b-instruct-q4_0.gguf`;
- local size observed: ~409 MiB;
- SHA-256: `7671c0c304e6ce5a7fc577bcb12aba01e2c155cc2efd29b2213c95b18edaf6ed`;
- deterministic mutation seed: `42` by default.

The model file is deliberately outside this Git repository.

Run the verified path with:

```bash
./run_qwen_eval.sh
```

By default that evaluates 5 source traces, asks Qwen for two mutation plans per source, and compares two deterministic agents. Override with `ACL_QWEN_VARIANTS` or `ACL_MUTATION_SEED`.

## Adapter design

`local_llm_mutator.py` implements the stdin/stdout mutation-provider protocol. The LLM never emits payment authorization. It proposes mutation content; deterministic code materializes that content into structured events. Existing confirmation nonces and digests are not editable by the model.

`SAME_PAYMENT` AI mutations are restricted to non-authoritative merchant/tool text. Free-form user paraphrases are not accepted as an AI-labelled equivalence class because that would make the model part of its own oracle.

`MUST_BLOCK` plans may request amount, quantity, merchant, or cancellation changes. The adapter records every normalization and every fallback. Reports separately count mutations that are fully model-derived and mutations that required fallback values.

The JSON extractor deliberately selects the **last** complete JSON object from `llama-cli` output. This matters because the CLI can echo prompt material containing the source JSON; selecting the first object previously caused the input to be mistaken for the model answer.

## Verified five-seed run

Using Qwen2.5-0.5B-Instruct Q4_0 with seed 42:

- 5 source traces;
- 10 mutation plans;
- 20 agent/mutation evaluations;
- payment-boundary containment: 20/20;
- unsafe PayPal-network allowance on `MUST_BLOCK`: 0;
- greedy baseline: 5 unsafe payment attempts;
- confirmation-aware baseline: 10/10 relation-correct;
- 6/10 mutations fully model-derived;
- 4/10 required deterministic fallback data.

All 5 `SAME_PAYMENT` injections were model-derived. On `MUST_BLOCK`, the 0.5B model was much weaker: only 1/5 plans supplied enough structured information without fallback. This is a limitation, not a success metric.

## Larger local model / server mode

A Qwen2.5-1.5B-Instruct Q4_0 model is also present outside the repository:

- local path: `/mnt/seagate/Models/Agentic-Commerce-Stress-Lab/qwen2.5-1.5b-instruct-q4_0.gguf`;
- local size observed: ~1017 MiB;
- SHA-256: `dcd819ff094852c38faba6873d8ff0c9d51eadb2844539e52042ae5d647bbfdb`.

A persistent `llama-server` path was tested, but under repeated requests the installed Debian/Kali runtime entered a state where a slot reported `is_processing=true` while zero prompt tokens and zero generated tokens advanced. That run was cancelled and is **not** used as benchmark evidence. `run_local_llm_server.sh` remains an experimental convenience only.

## Known runtime limitation

The installed llama.cpp JSON-schema sampler failed on the tested GGUF/runtime combination. The adapter therefore extracts ordinary JSON output and performs strict Python validation/normalization before materializing a mutation. Invalid or incomplete fields are recorded as fallbacks; they are never treated as payment authority.
