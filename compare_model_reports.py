#!/usr/bin/env python3
"""Compare real-model agent decision reports trace by trace."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from html import escape
import json
from pathlib import Path
from typing import Any


def model_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [row for row in report.get("rows", []) if row.get("raw_model_action") is not None]
    if not rows:
        raise ValueError("report contains no raw model decisions")
    agents = {row.get("agent") for row in rows}
    if len(agents) != 1:
        raise ValueError(f"expected one raw-model agent per report, found {sorted(agents)}")
    return rows


def load_view(label: str, path: str) -> dict[str, Any]:
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = model_rows(report)
    by_trace = {row["trace"]: row for row in rows}
    if len(by_trace) != len(rows):
        raise ValueError(f"duplicate trace in {path}")
    metadata = [row.get("agent_metadata") or {} for row in rows]
    return {
        "label": label,
        "path": path,
        "rows": rows,
        "by_trace": by_trace,
        "identity": {
            "models": sorted({m.get("model") for m in metadata if m.get("model")}),
            "backends": sorted({m.get("backend") for m in metadata if m.get("backend")}),
            "gpu_layers": sorted({m.get("gpu_layers") for m in metadata if m.get("gpu_layers") is not None}),
            "seeds": sorted({m.get("seed") for m in metadata if m.get("seed") is not None}),
        },
    }


def summarize(view: dict[str, Any]) -> dict[str, Any]:
    rows = view["rows"]
    return {
        "n": len(rows),
        "raw_correct": sum(bool(r.get("raw_model_action_correct")) for r in rows),
        "raw_unsafe_pays": sum(bool(r.get("raw_model_unsafe_pay")) for r in rows),
        "adapter_correct": sum(bool(r.get("action_correct")) for r in rows),
        "adapter_unsafe_pays": sum(bool(r.get("unsafe_agent_pay")) for r in rows),
        "adapter_fallbacks": sum(bool((r.get("agent_metadata") or {}).get("adapter_fallback")) for r in rows),
        "boundary_pass": sum(bool(r.get("boundary_pass")) for r in rows),
        "identity": view["identity"],
    }


def compare(views: list[dict[str, Any]]) -> dict[str, Any]:
    if len(views) < 2:
        raise ValueError("at least two reports are required")
    reference = set(views[0]["by_trace"])
    for view in views[1:]:
        if set(view["by_trace"]) != reference:
            raise ValueError("reports do not cover the same trace set")

    labels = [view["label"] for view in views]
    trace_rows: list[dict[str, Any]] = []
    raw_agreement = adapter_agreement = all_raw_unsafe_pay = all_raw_correct = 0

    for trace in sorted(reference):
        rows = [view["by_trace"][trace] for view in views]
        raw_actions = {view["label"]: row["raw_model_action"] for view, row in zip(views, rows)}
        adapter_actions = {view["label"]: row["agent_action"] for view, row in zip(views, rows)}
        raw_same = len(set(raw_actions.values())) == 1
        adapter_same = len(set(adapter_actions.values())) == 1
        raw_agreement += raw_same
        adapter_agreement += adapter_same
        all_raw_unsafe_pay += all(bool(row.get("raw_model_unsafe_pay")) for row in rows)
        all_raw_correct += all(bool(row.get("raw_model_action_correct")) for row in rows)
        trace_rows.append({
            "trace": trace,
            "category": rows[0]["category"],
            "expected_verdict": rows[0]["expected_verdict"],
            "raw_actions": raw_actions,
            "adapter_actions": adapter_actions,
            "raw_agreement": raw_same,
            "adapter_agreement": adapter_same,
            "raw_correct": {view["label"]: bool(row.get("raw_model_action_correct")) for view, row in zip(views, rows)},
            "raw_unsafe_pay": {view["label"]: bool(row.get("raw_model_unsafe_pay")) for view, row in zip(views, rows)},
        })

    per_category: dict[str, dict[str, Any]] = defaultdict(dict)
    for category in sorted({row["category"] for row in trace_rows}):
        subset = [row for row in trace_rows if row["category"] == category]
        for label in labels:
            per_category[category][label] = {
                "n": len(subset),
                "raw_actions": dict(Counter(row["raw_actions"][label] for row in subset)),
                "raw_correct": sum(row["raw_correct"][label] for row in subset),
                "raw_unsafe_pays": sum(row["raw_unsafe_pay"][label] for row in subset),
            }

    return {
        "title": "Agentic Commerce Stress Lab — Cross-model Differential Report",
        "labels": labels,
        "trace_count": len(reference),
        "model_summaries": {view["label"]: summarize(view) for view in views},
        "cross_model": {
            "raw_action_agreement": raw_agreement,
            "raw_action_disagreement": len(reference) - raw_agreement,
            "adapter_action_agreement": adapter_agreement,
            "all_models_raw_unsafe_pay": all_raw_unsafe_pay,
            "all_models_raw_correct": all_raw_correct,
        },
        "per_category": dict(per_category),
        "trace_rows": trace_rows,
        "limitations": [
            "Controlled synthetic benchmark; not a population estimate for real commerce traffic.",
            "Different model families and quantizations are compared behaviorally, not as a general quality ranking.",
            "Boundary containment does not make an unsafe model decision correct.",
        ],
    }


def render_html(report: dict[str, Any], path: str) -> None:
    labels = report["labels"]
    cards = []
    for label in labels:
        s = report["model_summaries"][label]
        cards.append(
            f"<section><h2>{escape(label)}</h2>"
            f"<p><b>{s['raw_correct']}/{s['n']}</b> raw correct · <b>{s['raw_unsafe_pays']}</b> raw unsafe PAY · "
            f"<b>{s['adapter_correct']}/{s['n']}</b> adapter correct · <b>{s['boundary_pass']}/{s['n']}</b> boundary pass</p>"
            f"<p><code>{escape(json.dumps(s['identity'], sort_keys=True))}</code></p></section>"
        )
    rows = []
    for row in report["trace_rows"]:
        raw = " · ".join(f"{escape(label)}={escape(row['raw_actions'][label])}" for label in labels)
        css = "ok" if row["raw_agreement"] else "warn"
        rows.append(
            f"<tr class='{css}'><td>{escape(row['trace'])}</td><td>{escape(row['category'])}</td>"
            f"<td>{escape(row['expected_verdict'])}</td><td>{raw}</td><td>{'yes' if row['raw_agreement'] else 'no'}</td></tr>"
        )
    cross = report["cross_model"]
    document = f"""<!doctype html><meta charset='utf-8'><title>{escape(report['title'])}</title>
<style>body{{font:15px system-ui;max-width:1200px;margin:32px auto;padding:0 18px}}section{{border:1px solid #ccc;border-radius:10px;padding:10px 16px;margin:10px 0}}table{{border-collapse:collapse;width:100%}}th,td{{border-bottom:1px solid #ddd;padding:8px;text-align:left}}.warn{{background:#fff3cd}}.ok{{background:#f5fff5}}code{{white-space:pre-wrap}}</style>
<h1>{escape(report['title'])}</h1><p>{report['trace_count']} aligned traces · raw agreement <b>{cross['raw_action_agreement']}/{report['trace_count']}</b> · all-model raw unsafe PAY <b>{cross['all_models_raw_unsafe_pay']}</b>.</p>
{''.join(cards)}
<table><thead><tr><th>Trace</th><th>Category</th><th>Oracle</th><th>Raw actions</th><th>Agreement</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"""
    Path(path).write_text(document, encoding="utf-8")


def parse_spec(spec: str) -> tuple[str, str]:
    if "=" not in spec:
        raise argparse.ArgumentTypeError("report must be LABEL=PATH")
    label, path = spec.split("=", 1)
    if not label or not path:
        raise argparse.ArgumentTypeError("report must be LABEL=PATH")
    return label, path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="append", required=True, help="LABEL=PATH; repeat for each model")
    ap.add_argument("--json", default="model_comparison_report.json")
    ap.add_argument("--html", default="model_comparison_report.html")
    args = ap.parse_args()
    views = [load_view(*parse_spec(spec)) for spec in args.report]
    report = compare(views)
    Path(args.json).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    render_html(report, args.html)
    print(json.dumps({"trace_count": report["trace_count"], "model_summaries": report["model_summaries"], "cross_model": report["cross_model"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
