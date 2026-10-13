#!/bin/sh
set -eu

export ACL_LOCAL_MODEL="${ACL_LOCAL_MODEL:-/mnt/seagate/Models/Agentic-Commerce-Stress-Lab/qwen2.5-1.5b-instruct-q4_0.gguf}"
export ACL_AGENT_SEED="${ACL_AGENT_SEED:-17}"
VARIANTS="${ACL_AGENT_VARIANTS:-1}"

exec python3 agent_decision_benchmark.py \
  --variants "$VARIANTS" \
  --agent-cmd "python3 local_llm_agent.py --mode policy" \
  --agent-timeout 240 \
  --json qwen15_decision_report.json \
  --html qwen15_decision_report.html
