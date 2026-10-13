#!/bin/sh
set -eu
MODEL="${ACL_LOCAL_MODEL:-/mnt/seagate/Models/Agentic-Commerce-Stress-Lab/qwen2.5-0.5b-instruct-q4_0.gguf}"
exec /usr/bin/llama-server \
  -m "$MODEL" \
  --host 127.0.0.1 \
  --port 8099 \
  -t 4 \
  --device BLAS \
  -c 4096 \
  --parallel 1 \
  --reasoning off \
  --log-disable
