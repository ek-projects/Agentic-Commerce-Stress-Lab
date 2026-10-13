#!/bin/sh
set -eu

export ACL_LOCAL_MODEL="${ACL_LOCAL_MODEL:-/mnt/seagate/Models/Agentic-Commerce-Stress-Lab/qwen2.5-0.5b-instruct-q4_0.gguf}"
export ACL_MUTATION_SEED="${ACL_MUTATION_SEED:-42}"
unset ACL_LLAMA_URL || true
VARIANTS="${ACL_QWEN_VARIANTS:-5}"
GPU_PY="${ACL_GPU_PYTHON:-.runtime/llama-py-cu124/bin/python}"

if [ -z "${ACL_LLM_BACKEND:-}" ] && [ -x "$GPU_PY" ]; then
  export ACL_LLM_BACKEND=llama_cpp_python
  export ACL_LLM_GPU_LAYERS="${ACL_LLM_GPU_LAYERS:--1}"
  MUTATOR_PY="$GPU_PY"
else
  export ACL_LLM_BACKEND="${ACL_LLM_BACKEND:-cli}"
  MUTATOR_PY="${ACL_MUTATOR_PYTHON:-python3}"
fi

exec python3 differential_eval.py \
  --variants "$VARIANTS" \
  --mutator-cmd "$MUTATOR_PY local_llm_mutator.py" \
  --mutator-timeout 240 \
  --json qwen_differential_report.json \
  --html qwen_stress_report.html
