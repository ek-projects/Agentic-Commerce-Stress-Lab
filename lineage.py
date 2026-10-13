"""Intent-lineage extraction and self-contained HTML reporting."""
from __future__ import annotations

from dataclasses import asdict
from html import escape
import json
from pathlib import Path
from typing import Any

from trace_lab import Event, PaymentIntent, Trace, intent_digest

FIELDS = ("order_id", "merchant", "amount_cents", "currency", "item", "quantity")


def intent_fields(intent: PaymentIntent | None) -> dict[str, Any]:
    if intent is None:
        return {}
    return {field: getattr(intent, field) for field in FIELDS}


def build_lineage(trace: Trace) -> dict[str, Any]:
    state: dict[str, Any] = {}
    origin: dict[str, dict[str, Any]] = {}
    changes: list[dict[str, Any]] = []
    confirmations: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []

    for index, event in enumerate(trace.events):
        row: dict[str, Any] = {
            "index": index,
            "kind": event.kind,
            "actor": event.actor,
            "text": event.text,
            "authentic": event.authentic,
            "nonce": event.nonce,
            "digest": event.digest,
        }
        if event.intent is not None:
            fields = intent_fields(event.intent)
            row["intent"] = fields
            row["intent_digest"] = intent_digest(event.intent)
            for field, value in fields.items():
                previous = state.get(field, None)
                if field not in state or previous != value:
                    change = {
                        "event": index,
                        "actor": event.actor,
                        "kind": event.kind,
                        "field": field,
                        "from": previous,
                        "to": value,
                    }
                    changes.append(change)
                    origin[field] = {
                        "event": index,
                        "actor": event.actor,
                        "kind": event.kind,
                        "value": value,
                    }
                    state[field] = value
        if event.kind == "user_confirm":
            confirmations.append({
                "event": index,
                "actor": event.actor,
                "authentic": event.authentic,
                "nonce": event.nonce,
                "digest": event.digest,
            })
        timeline.append({k: v for k, v in row.items() if v not in (None, "", {})})

    attempts = [event for event in trace.events if event.kind == "payment_attempt"]
    final_attempt = attempts[-1] if attempts else None
    final_fields = intent_fields(final_attempt.intent if final_attempt else None)

    return {
        "trace": trace.name,
        "category": trace.category,
        "attack": trace.attack,
        "expected": trace.expected,
        "final_payment": final_fields,
        "final_payment_digest": intent_digest(final_attempt.intent) if final_attempt and final_attempt.intent else None,
        "field_origins": origin,
        "changes": changes,
        "confirmations": confirmations,
        "timeline": timeline,
    }


def _render_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return escape(json.dumps(value, sort_keys=True))
    return escape(str(value))


def render_html_report(report: dict[str, Any], output_path: str) -> str:
    title = escape(str(report.get("title", "Agentic Commerce Stress Lab")))
    cases = report.get("cases", [])
    rows = []
    for case in cases:
        rows.append(
            "<tr>"
            f"<td>{escape(str(case.get('name','')))}</td>"
            f"<td>{escape(str(case.get('relation','')))}</td>"
            f"<td>{escape(str(case.get('agent','')))}</td>"
            f"<td>{escape(str(case.get('agent_action','')))}</td>"
            f"<td>{'PASS' if case.get('agent_relation_pass') else 'FAIL'}</td>"
            f"<td>{escape(str(case.get('boundary_verdict','')))}</td>"
            f"<td>{'PASS' if case.get('boundary_pass') else 'FAIL'}</td>"
            "</tr>"
        )

    lineage_sections = []
    for case in cases[:12]:
        lineage = case.get("lineage") or {}
        change_rows = []
        for change in lineage.get("changes", []):
            change_rows.append(
                "<tr>"
                f"<td>{change.get('event')}</td>"
                f"<td>{escape(str(change.get('actor','')))}</td>"
                f"<td>{escape(str(change.get('field','')))}</td>"
                f"<td>{_render_value(change.get('from'))}</td>"
                f"<td>{_render_value(change.get('to'))}</td>"
                "</tr>"
            )
        lineage_sections.append(
            f"<details><summary>{escape(str(case.get('name','')))}</summary>"
            "<table><thead><tr><th>Event</th><th>Actor</th><th>Field</th><th>From</th><th>To</th></tr></thead>"
            f"<tbody>{''.join(change_rows)}</tbody></table>"
            f"<pre>{escape(json.dumps(lineage.get('final_payment', {}), indent=2, sort_keys=True))}</pre>"
            "</details>"
        )

    summary = report.get("summary", {})
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
body{{font-family:system-ui,-apple-system,sans-serif;max-width:1180px;margin:40px auto;padding:0 20px;color:#171717;background:#fafafa}}
h1,h2{{letter-spacing:-.02em}} .cards{{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0 28px}}
.card{{background:white;border:1px solid #ddd;border-radius:10px;padding:14px 18px;min-width:150px}}
.card b{{display:block;font-size:1.45rem;margin-top:3px}} table{{width:100%;border-collapse:collapse;background:white;margin:12px 0 24px}}
th,td{{border:1px solid #ddd;padding:8px;text-align:left;vertical-align:top}} th{{background:#f1f1f1}}
code,pre{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}} pre{{background:#111;color:#eee;padding:12px;border-radius:8px;overflow:auto}}
details{{background:white;border:1px solid #ddd;border-radius:8px;padding:10px 12px;margin:10px 0}} summary{{cursor:pointer;font-weight:650}}
.small{{color:#555;font-size:.92rem}}
</style></head><body>
<h1>{title}</h1>
<p class="small">Metamorphic agent stress results and payment-intent lineage. Generated locally by the lab.</p>
<div class="cards">
<div class="card">Cases<b>{summary.get('cases',0)}</b></div>
<div class="card">Agent relation pass<b>{summary.get('agent_relation_pass',0)}</b></div>
<div class="card">Boundary pass<b>{summary.get('boundary_pass',0)}</b></div>
<div class="card">Unsafe agent PAYs<b>{summary.get('unsafe_agent_pays',0)}</b></div>
</div>
<h2>Differential results</h2>
<table><thead><tr><th>Case</th><th>Relation</th><th>Agent</th><th>Action</th><th>Agent</th><th>Boundary verdict</th><th>Boundary</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<h2>Intent lineage samples</h2>
{''.join(lineage_sections)}
</body></html>"""
    Path(output_path).write_text(html, encoding="utf-8")
    return output_path
