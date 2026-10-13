#!/usr/bin/env python3
"""Small optional CPU/CUDA throughput probe for a local llama-cpp-python runtime."""
from __future__ import annotations

import argparse
import json
import time

from llama_cpp import Llama


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='/mnt/seagate/Models/Agentic-Commerce-Stress-Lab/qwen2.5-1.5b-instruct-q4_0.gguf')
    ap.add_argument('--gpu-layers', type=int, default=-1)
    ap.add_argument('--label', default='gpu')
    ap.add_argument('--n-ctx', type=int, default=2048)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--seed', type=int, default=17)
    ap.add_argument('--max-tokens', type=int, default=64)
    args = ap.parse_args()

    t0 = time.perf_counter()
    llm = Llama(
        model_path=args.model,
        n_ctx=args.n_ctx,
        n_gpu_layers=args.gpu_layers,
        n_threads=args.threads,
        seed=args.seed,
        verbose=False,
    )
    t1 = time.perf_counter()
    response = llm.create_chat_completion(
        messages=[
            {'role': 'system', 'content': 'Return exactly one JSON object and no markdown.'},
            {'role': 'user', 'content': 'Return a JSON object with action PAY and a short reason that the exact current proposal is confirmed.'},
        ],
        max_tokens=args.max_tokens,
        temperature=0.15,
        top_p=0.9,
        seed=args.seed,
    )
    t2 = time.perf_counter()
    usage = response.get('usage', {})
    completion_tokens = int(usage.get('completion_tokens') or 0)
    print(json.dumps({
        'backend': args.label,
        'gpu_layers': args.gpu_layers,
        'load_s': round(t1 - t0, 3),
        'generation_s': round(t2 - t1, 3),
        'completion_tokens': completion_tokens,
        'tokens_per_s': round(completion_tokens / (t2 - t1), 2) if completion_tokens else 0.0,
        'content': response['choices'][0]['message']['content'],
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
