#!/bin/sh
set -eu

export ACL_LOCAL_MODEL="${ACL_LOCAL_MODEL:-/mnt/seagate/Models/Agentic-Commerce-Stress-Lab/qwen2.5-1.5b-instruct-q4_0.gguf}"
export ACL_AGENT_SEED="${ACL_AGENT_SEED:-17}"
VARIANTS="${ACL_AGENT_VARIANTS:-1}"
GPU_PY="${ACL_GPU_PYTHON:-.runtime/llama-py-cu124/bin/python}"

if [ -z "${ACL_LLM_BACKEND:-}" ] && [ -x "$GPU_PY" ]; then
  export ACL_LLM_BACKEND=llama_cpp_python
  export ACL_LLM_GPU_LAYERS="${ACL_LLM_GPU_LAYERS:--1}"
  AGENT_PY="$GPU_PY"
else
  export ACL_LLM_BACKEND="${ACL_LLM_BACKEND:-cli}"
  AGENT_PY="${ACL_AGENT_PYTHON:-python3}"
fi

exec python3 agent_decision_benchmark.py \
  --variants "$VARIANTS" \
  --agent-cmd "$AGENT_PY local_llm_agent.py --mode policy" \
  --agent-timeout 240 \
  --json qwen15_decision_report.json \
  --html qwen15_decision_report.html
