"""Equal-input benchmark over multi-agent commerce traces.

The benchmark measures causal consent/provenance properties on synthetic traces.
It does not measure real PayPal security, LLM robustness, or production fraud risk.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import json

from trace_lab import (
    ALLOW,
    BLOCK,
    CLARIFY,
    ProvenanceGuard,
    SnapshotBaseline,
    build_dataset,
    export_jsonl,
)


def score(system, traces):
    rows = []
    for trace in traces:
        decision = system.evaluate(trace.events)
        rows.append({
            "name": trace.name,
            "category": trace.category,
            "attack": trace.attack,
            "expected": trace.expected,
            "verdict": decision.verdict,
            "reason": decision.reason,
            "correct": decision.verdict == trace.expected,
        })
    return rows


def summarize(rows):
    total = len(rows)
    correct = sum(r["correct"] for r in rows)
    attack_rows = [r for r in rows if r["attack"]]
    benign_rows = [r for r in rows if not r["attack"]]
    unsafe_allows = sum(r["attack"] and r["verdict"] == ALLOW for r in rows)
    benign_blocks = sum((not r["attack"]) and r["expected"] == ALLOW and r["verdict"] == BLOCK for r in rows)
    categories = defaultdict(lambda: {"n": 0, "correct": 0, "verdicts": Counter()})
    for row in rows:
        entry = categories[row["category"]]
        entry["n"] += 1
        entry["correct"] += int(row["correct"])
        entry["verdicts"][row["verdict"]] += 1

    return {
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "attack_cases": len(attack_rows),
        "benign_or_ambiguous_cases": len(benign_rows),
        "unsafe_allows": unsafe_allows,
        "unsafe_allow_rate_on_attacks": unsafe_allows / len(attack_rows) if attack_rows else 0.0,
        "benign_blocks": benign_blocks,
        "verdict_counts": dict(Counter(r["verdict"] for r in rows)),
        "categories": {
            key: {
                "n": value["n"],
                "correct": value["correct"],
                "accuracy": value["correct"] / value["n"],
                "verdicts": dict(value["verdicts"]),
            }
            for key, value in sorted(categories.items())
        },
    }


def main():
    traces = build_dataset(variants=20)
    baseline_rows = score(SnapshotBaseline(), traces)
    guard_rows = score(ProvenanceGuard(), traces)

    export_count = export_jsonl("agentic_traces.jsonl", variants=20)
    report = {
        "dataset": {
            "traces": len(traces),
            "exported_jsonl": export_count,
            "categories": len(set(t.category for t in traces)),
            "expected_verdicts": dict(Counter(t.expected for t in traces)),
            "attack_traces": sum(t.attack for t in traces),
            "description": "Deterministic synthetic multi-agent traces with user, shopping-agent, merchant-agent, tool-agent and payment-agent events.",
        },
        "equal_input": True,
        "snapshot_baseline": summarize(baseline_rows),
        "provenance_guard": summarize(guard_rows),
        "interpretation": (
            "Both systems receive the exact same event trace. The snapshot baseline only binds payment to the most recent user-confirmed candidate, "
            "while the provenance guard additionally validates authentication, digest binding, cancellation and nonce lifecycle. Differences therefore "
            "measure coverage of those protocol properties on this constructed dataset, not generic AI superiority."
        ),
        "limitations": [
            "All traces are synthetic and generated from hand-authored attack templates.",
            "The reference guard is designed around the benchmark invariants, so perfect accuracy is not independent validation.",
            "No LLM-generated conversations are included yet.",
            "No PayPal Sandbox API call is included yet.",
            "No claim is made about fraud detection, merchant risk, or production security efficacy.",
        ],
    }

    with open("agentic_benchmark_report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(json.dumps(report, indent=2, sort_keys=True))

    assert len(traces) == 240
    assert report["provenance_guard"]["correct"] == len(traces)
    assert report["provenance_guard"]["unsafe_allows"] == 0
    assert report["snapshot_baseline"]["correct"] < len(traces)
    return report


if __name__ == "__main__":
    main()
