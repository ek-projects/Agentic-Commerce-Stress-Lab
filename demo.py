"""Small end-to-end CLI demo for the hackathon prototype.

Default mode never makes a network call. Use --live-sandbox only after sandbox
credentials are provided in PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET.
"""
from __future__ import annotations

import argparse
import json

from metamorphic_lab import build_metamorphic_cases, evaluate_case
from paypal_boundary import PayPalSandboxClient, execute_paypal_boundary
from trace_lab import build_dataset


def compact(result):
    return {
        "trace": result["trace"],
        "verdict": result["verdict"],
        "reason": result["reason"],
        "paypal_called": result["paypal_called"],
        "paypal_request_id": result.get("paypal_request_id"),
        "paypal_response": result.get("paypal_response"),
    }


def main():
    parser = argparse.ArgumentParser(description="Agentic Commerce Stress Lab demo")
    parser.add_argument("--live-sandbox", action="store_true", help="Create one PayPal Sandbox order for the safe trace.")
    args = parser.parse_args()

    traces = build_dataset(variants=1)
    safe = next(t for t in traces if t.category == "benign_stable")
    attack = next(t for t in traces if t.category == "attack_detached_confirmation")

    client = PayPalSandboxClient()
    if args.live_sandbox and not client.configured:
        raise SystemExit("PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET are required for --live-sandbox")

    safe_result = execute_paypal_boundary(safe, client=client, dry_run=not args.live_sandbox)
    attack_result = execute_paypal_boundary(attack, client=client, dry_run=False)

    meta = build_metamorphic_cases(variants=1)
    meta_results = [evaluate_case(case) for case in meta]

    output = {
        "mode": "live PayPal Sandbox" if args.live_sandbox else "offline dry-run",
        "safe_flow": compact(safe_result),
        "attack_flow": compact(attack_result),
        "metamorphic_smoke": {
            "cases": len(meta_results),
            "passed": sum(r.passed for r in meta_results),
            "details": [
                {
                    "name": r.name,
                    "relation": r.relation,
                    "passed": r.passed,
                    "source_verdict": r.source_verdict,
                    "mutated_verdict": r.mutated_verdict,
                }
                for r in meta_results
            ],
        },
        "important": (
            "The blocked trace is executed with dry_run=False on purpose: the boundary itself must prevent the provider call. "
            "A live sandbox run, when configured, only sends the safe trace."
        ),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
