#!/bin/sh
set -eu

VARIANTS="${ACL_COMPARE_VARIANTS:-5}"
SEED="${ACL_AGENT_SEED:-17}"
QWEN_MODEL="${ACL_QWEN_MODEL:-/mnt/seagate/Models/Agentic-Commerce-Stress-Lab/qwen2.5-1.5b-instruct-q4_0.gguf}"
SMOL_MODEL="${ACL_SMOL_MODEL:-/mnt/seagate/Models/Agentic-Commerce-Stress-Lab/smollm2-1.7b-instruct-q4_k_m.gguf}"
GPU_PY="${ACL_GPU_PYTHON:-.runtime/llama-py-cu124/bin/python}"

if [ -z "${ACL_LLM_BACKEND:-}" ] && [ -x "$GPU_PY" ]; then
  BACKEND=llama_cpp_python
  GPU_LAYERS="${ACL_LLM_GPU_LAYERS:--1}"
  AGENT_PY="$GPU_PY"
else
  BACKEND="${ACL_LLM_BACKEND:-cli}"
  GPU_LAYERS="${ACL_LLM_GPU_LAYERS:-0}"
  AGENT_PY="${ACL_AGENT_PYTHON:-python3}"
fi

run_model() {
  model="$1"
  json_out="$2"
  html_out="$3"
  python3 agent_decision_benchmark.py \
    --variants "$VARIANTS" \
    --persistent-agent-cmd "env ACL_LOCAL_MODEL=$model ACL_AGENT_SEED=$SEED ACL_LLM_BACKEND=$BACKEND ACL_LLM_GPU_LAYERS=$GPU_LAYERS $AGENT_PY local_llm_agent.py --mode policy --serve-jsonl" \
    --agent-timeout 240 \
    --json "$json_out" \
    --html "$html_out"
}

run_model "$QWEN_MODEL" qwen15_decision_report.json qwen15_decision_report.html
run_model "$SMOL_MODEL" smollm2_decision_report_v5.json smollm2_decision_report_v5.html

exec python3 compare_model_reports.py \
  --report Qwen2.5=qwen15_decision_report.json \
  --report SmolLM2=smollm2_decision_report_v5.json \
  --json model_comparison_report.json \
  --html model_comparison_report.html
