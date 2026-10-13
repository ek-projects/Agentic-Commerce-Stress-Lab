#!/bin/sh
set -eu
export ACL_LOCAL_MODEL="${ACL_LOCAL_MODEL:-/mnt/seagate/Models/Agentic-Commerce-Stress-Lab/qwen2.5-0.5b-instruct-q4_0.gguf}"
export ACL_MUTATION_SEED="${ACL_MUTATION_SEED:-42}"
unset ACL_LLAMA_URL || true
VARIANTS="${ACL_QWEN_VARIANTS:-5}"
exec python3 differential_eval.py --variants "$VARIANTS" --mutator-cmd "python3 local_llm_mutator.py" --mutator-timeout 240 --json qwen_differential_report.json --html qwen_stress_report.html
