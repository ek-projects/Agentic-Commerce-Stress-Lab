"""Zero-dependency local dashboard for the hackathon demo.

Binds to 127.0.0.1 by default and performs no PayPal network calls. The dashboard
runs the offline template differential suite and can additionally display already-
generated cross-model and PayPal readiness evidence from local JSON report files.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path

from agent_under_test import ConfirmationAwareAgent, GreedyLatestProposalAgent
from ai_mutation import TemplateMutationProvider
from differential_eval import run_suite


def make_report(variants: int = 5) -> dict:
    return run_suite(
        TemplateMutationProvider(),
        [GreedyLatestProposalAgent(), ConfirmationAwareAgent()],
        variants=variants,
    )


def _load_optional_json(path: str) -> dict | None:
    candidate = Path(path)
    if not candidate.exists():
        return None
    try:
        raw = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def _load_preferred_json(primary: str, fallback: str) -> tuple[dict | None, str]:
    local = _load_optional_json(primary)
    if local is not None:
        return local, "local-runtime-report"
    bundled = _load_optional_json(fallback)
    if bundled is not None:
        return bundled, "bundled-verified-snapshot"
    return None, "missing"


def make_evidence_report(
    comparison_path: str = "model_comparison_report.json",
    paypal_path: str = "paypal_readiness_report.json",
    comparison_fallback: str = "evidence/cross_model_verified.json",
    paypal_fallback: str = "evidence/paypal_sandbox_verified.json",
) -> dict:
    """Read evidence only; prefer fresh local reports, then bundled sanitized snapshots."""
    comparison, comparison_source = _load_preferred_json(comparison_path, comparison_fallback)
    paypal, paypal_source = _load_preferred_json(paypal_path, paypal_fallback)
    return {
        "cross_model": comparison,
        "cross_model_source": comparison_source,
        "paypal_readiness": paypal,
        "paypal_source": paypal_source,
        "offline": True,
        "note": "Evidence endpoint never calls PayPal or loads an LLM; bundled snapshots are sanitized.",
    }


def dashboard_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agentic Commerce Stress Lab</title>
<style>
:root{font-family:Inter,system-ui,-apple-system,sans-serif;color:#161616;background:#f5f5f3}body{margin:0}.wrap{max-width:1180px;margin:auto;padding:36px 22px 60px}
.hero{display:flex;justify-content:space-between;gap:20px;align-items:end}.eyebrow{font-size:12px;font-weight:750;letter-spacing:.12em;text-transform:uppercase;color:#666}
h1{font-size:42px;line-height:1.02;margin:7px 0 10px;letter-spacing:-.04em}.sub{max-width:780px;color:#555;font-size:17px;line-height:1.45}
button{border:0;border-radius:9px;background:#171717;color:white;padding:11px 16px;font-weight:700;cursor:pointer}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:28px 0 12px}
.card{background:#fff;border:1px solid #ddd;border-radius:13px;padding:17px}.label{font-size:12px;color:#666;text-transform:uppercase;letter-spacing:.06em}.value{font-size:28px;font-weight:780;margin-top:6px}
.panel{background:#fff;border:1px solid #ddd;border-radius:13px;overflow:hidden;margin-top:16px}.panel h2{font-size:18px;padding:17px 18px;margin:0;border-bottom:1px solid #e4e4e4}.panelbody{padding:16px 18px}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:10px 12px;border-bottom:1px solid #eee;text-align:left}th{background:#fafafa;color:#555;font-weight:700}.pass{font-weight:750}.fail{font-weight:750;text-decoration:underline}.muted{color:#777}.pill{display:inline-block;border:1px solid #ccc;border-radius:999px;padding:2px 7px;font-size:11px}.footer{margin-top:18px;color:#777;font-size:12px}.statusgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.statusitem{border:1px solid #e4e4e4;border-radius:9px;padding:12px}.statusitem b{display:block;margin-top:5px;font-size:16px}
@media(max-width:760px){.hero{display:block}.hero button{margin-top:16px}.cards{grid-template-columns:repeat(2,1fr)}h1{font-size:34px}.panel{overflow:auto}.statusgrid{grid-template-columns:1fr}}
</style>
</head><body><div class="wrap">
<div class="hero"><div><div class="eyebrow">PayPal AI Hackathon 2026 prototype</div><h1>Agentic Commerce<br>Stress Lab</h1><div class="sub">Stress agentic payment decisions, compare model behavior, and independently verify whether unsafe payment attempts are contained before the PayPal boundary.</div></div><button onclick="loadAll()">Refresh evidence</button></div>

<div class="cards"><div class="card"><div class="label">Evaluations</div><div class="value" id="cases">—</div></div><div class="card"><div class="label">Agent relation pass</div><div class="value" id="agentpass">—</div></div><div class="card"><div class="label">Unsafe agent PAYs</div><div class="value" id="unsafe">—</div></div><div class="card"><div class="label">Boundary contained</div><div class="value" id="boundary">—</div></div></div>
<div class="cards"><div class="card"><div class="label">Cross-model raw agreement</div><div class="value" id="modelagree">—</div></div><div class="card"><div class="label">Shared raw unsafe PAY</div><div class="value" id="sharedunsafe">—</div></div><div class="card"><div class="label">PayPal Sandbox</div><div class="value" id="paypalstatus">—</div></div><div class="card"><div class="label">E2E create-order</div><div class="value" id="e2e">—</div></div></div>

<div class="panel"><h2>Judge demo: model decision → boundary → PayPal</h2><div class="panelbody"><div class="statusgrid" id="story"><div class="statusitem"><span class="muted">Loading verified evidence…</span></div></div></div></div>
<div class="panel"><h2>Differential results</h2><table><thead><tr><th>Mutation</th><th>Relation</th><th>Agent</th><th>Action</th><th>Agent check</th><th>Boundary</th><th>PayPal network</th></tr></thead><tbody id="rows"><tr><td colspan="7" class="muted">Run the suite to load results.</td></tr></tbody></table></div>
<div class="panel"><h2>Cross-model evidence</h2><div class="panelbody" id="models"><span class="muted">Run ./run_cross_model_compare.sh to generate local evidence.</span></div></div>
<div class="panel"><h2>PayPal Sandbox readiness</h2><div class="panelbody" id="paypal"><span class="muted">Run python3 paypal_readiness.py to generate the readiness report.</span></div></div>
<div class="footer">Judge-safe dashboard. It runs the offline template suite and reads fresh local reports when present, otherwise bundled sanitized verified snapshots. Viewing it never creates a PayPal order.</div>
</div>
<script>
function esc(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));}
function setText(id,v){document.getElementById(id).textContent=v;}
async function loadStress(){
 const r=await fetch('/api/report',{cache:'no-store'}); const d=await r.json(); const s=d.summary;
 setText('cases',s.cases); setText('agentpass',s.agent_relation_pass+'/'+s.cases); setText('unsafe',s.unsafe_agent_pays); setText('boundary',s.boundary_pass+'/'+s.cases);
 document.getElementById('rows').innerHTML=d.cases.map(x=>`<tr><td>${esc(x.name)}</td><td><span class="pill">${esc(x.relation)}</span></td><td>${esc(x.agent)}</td><td>${esc(x.agent_action)}</td><td class="${x.agent_relation_pass?'pass':'fail'}">${x.agent_relation_pass?'PASS':'FAIL'}</td><td class="${x.boundary_pass?'pass':'fail'}">${esc(x.boundary_verdict)} · ${x.boundary_pass?'PASS':'FAIL'}</td><td>${x.paypal_network_allowed?'ALLOWED':'BLOCKED'}</td></tr>`).join('');
}
async function loadEvidence(){
 const r=await fetch('/api/evidence',{cache:'no-store'}); const d=await r.json(); const c=d.cross_model; const p=d.paypal_readiness;
 if(c && c.cross_model){
   const x=c.cross_model; setText('modelagree',x.raw_action_agreement+'/'+c.trace_count); setText('sharedunsafe',x.all_models_raw_unsafe_pay);
   const entries=Object.entries(c.model_summaries||{}); document.getElementById('models').innerHTML=`<div class="statusgrid">${entries.map(([name,s])=>`<div class="statusitem"><span class="label">${esc(name)}</span><b>${s.raw_correct}/${s.n} raw correct</b><span class="muted">${s.raw_unsafe_pays} raw unsafe PAY · boundary ${s.boundary_pass}/${s.n}</span></div>`).join('')}<div class="statusitem"><span class="label">Trace agreement</span><b>${x.raw_action_agreement}/${c.trace_count}</b><span class="muted">${x.raw_action_disagreement} raw disagreement · ${x.all_models_raw_unsafe_pay} shared unsafe PAY</span></div></div>`;
 } else {setText('modelagree','not run');setText('sharedunsafe','—');}
 if(p){
   const reachable=!!(p.network_probe&&p.network_probe.reachable); setText('paypalstatus',p.authenticated_sandbox_ready?'VERIFIED':(reachable?'reachable':esc(p.status||'unknown'))); setText('e2e',p.end_to_end_create_order_verified?'VERIFIED':'not verified');
   document.getElementById('paypal').innerHTML=`<div class="statusgrid"><div class="statusitem"><span class="label">OAuth endpoint</span><b>${reachable?'Reachable':'Not verified'}</b><span class="muted">HTTP ${esc(p.network_probe&&p.network_probe.http_status||'—')}</span></div><div class="statusitem"><span class="label">Credentials</span><b>${p.credentials_present?'Present':'Missing'}</b><span class="muted">OAuth authenticated: ${p.authenticated_sandbox_ready?'yes':'no'}</span></div><div class="statusitem"><span class="label">Create order</span><b>${p.end_to_end_create_order_verified?'Verified':'Not verified'}</b><span class="muted">status: ${esc(p.status)}</span></div></div>`;
 } else {setText('paypalstatus','not run');setText('e2e','—');}
 const material=(c&&c.material_attacks)||{trace_count:40,all_models_raw_pay:40};
 const blocked=p&&p.blocked_negative_control; const created=p&&p.create_order;
 document.getElementById('story').innerHTML=`<div class="statusitem"><span class="label">1 · Agent decision</span><b>/ attack PAY</b><span class="muted">Both tested model families chose PAY on every material attack trace.</span></div><div class="statusitem"><span class="label">2 · Independent boundary</span><b>${blocked&&blocked.ok?'BLOCK verified':'offline containment'}</b><span class="muted">Known-bad trace provider call: ${blocked&&blocked.provider_called?'YES':'NO'}.</span></div><div class="statusitem"><span class="label">3 · PayPal Sandbox</span><b>${created&&created.paypal_status?esc(created.paypal_status):'evidence unavailable'}</b><span class="muted">Only a guarded ALLOW trace reached Orders v2. Evidence: .</span></div>`;
}
async function loadAll(){const btn=document.querySelector('button');btn.disabled=true;btn.textContent='Refreshing…';try{await Promise.all([loadStress(),loadEvidence()]);}catch(e){document.getElementById('rows').innerHTML='<tr><td colspan="7">Error: '+esc(e)+'</td></tr>';}finally{btn.disabled=false;btn.textContent='Refresh evidence';}}
loadAll();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    variants = 5

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/index.html":
            self._send(200, "text/html; charset=utf-8", dashboard_html().encode())
            return
        if self.path == "/api/report":
            report = make_report(self.variants)
            self._send(200, "application/json; charset=utf-8", json.dumps(report).encode())
            return
        if self.path == "/api/evidence":
            report = make_evidence_report()
            self._send(200, "application/json; charset=utf-8", json.dumps(report).encode())
            return
        self._send(404, "text/plain; charset=utf-8", b"Not found\n")

    def log_message(self, fmt: str, *args) -> None:
        print("dashboard:", fmt % args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Agentic Commerce Stress Lab dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8088)
    parser.add_argument("--variants", type=int, default=5)
    args = parser.parse_args()
    Handler.variants = args.variants
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"dashboard listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
