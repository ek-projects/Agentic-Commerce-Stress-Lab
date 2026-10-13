"""Zero-dependency local dashboard for the hackathon demo.

Binds to 127.0.0.1 by default and performs no PayPal network calls. The dashboard
runs the offline differential suite and visualizes agent failures separately from
payment-boundary containment.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json

from agent_under_test import ConfirmationAwareAgent, GreedyLatestProposalAgent
from ai_mutation import TemplateMutationProvider
from differential_eval import run_suite


def make_report(variants: int = 5) -> dict:
    return run_suite(
        TemplateMutationProvider(),
        [GreedyLatestProposalAgent(), ConfirmationAwareAgent()],
        variants=variants,
    )


def dashboard_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agentic Commerce Stress Lab</title>
<style>
:root{font-family:Inter,system-ui,-apple-system,sans-serif;color:#161616;background:#f5f5f3}
body{margin:0}.wrap{max-width:1180px;margin:auto;padding:36px 22px 60px}
.hero{display:flex;justify-content:space-between;gap:20px;align-items:end}.eyebrow{font-size:12px;font-weight:750;letter-spacing:.12em;text-transform:uppercase;color:#666}
h1{font-size:42px;line-height:1.02;margin:7px 0 10px;letter-spacing:-.04em}.sub{max-width:760px;color:#555;font-size:17px;line-height:1.45}
button{border:0;border-radius:9px;background:#171717;color:white;padding:11px 16px;font-weight:700;cursor:pointer}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:28px 0}
.card{background:#fff;border:1px solid #ddd;border-radius:13px;padding:17px}.label{font-size:12px;color:#666;text-transform:uppercase;letter-spacing:.06em}.value{font-size:30px;font-weight:780;margin-top:6px}
.panel{background:#fff;border:1px solid #ddd;border-radius:13px;overflow:hidden;margin-top:16px}.panel h2{font-size:18px;padding:17px 18px;margin:0;border-bottom:1px solid #e4e4e4}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:10px 12px;border-bottom:1px solid #eee;text-align:left}th{background:#fafafa;color:#555;font-weight:700}.pass{font-weight:750}.fail{font-weight:750;text-decoration:underline}.muted{color:#777}.pill{display:inline-block;border:1px solid #ccc;border-radius:999px;padding:2px 7px;font-size:11px}.footer{margin-top:18px;color:#777;font-size:12px}
@media(max-width:760px){.hero{display:block}.hero button{margin-top:16px}.cards{grid-template-columns:repeat(2,1fr)}h1{font-size:34px}.panel{overflow:auto}}
</style>
</head><body><div class="wrap">
<div class="hero"><div><div class="eyebrow">PayPal AI Hackathon 2026 prototype</div><h1>Agentic Commerce<br>Stress Lab</h1><div class="sub">Metamorphic tests perturb conversations and agent handoffs, then compare the structured payment attempt at the PayPal boundary. Agent mistakes and boundary containment are scored separately.</div></div><button onclick="loadReport()">Run stress suite</button></div>
<div class="cards"><div class="card"><div class="label">Evaluations</div><div class="value" id="cases">—</div></div><div class="card"><div class="label">Agent relation pass</div><div class="value" id="agentpass">—</div></div><div class="card"><div class="label">Unsafe agent PAYs</div><div class="value" id="unsafe">—</div></div><div class="card"><div class="label">Boundary contained</div><div class="value" id="boundary">—</div></div></div>
<div class="panel"><h2>Differential results</h2><table><thead><tr><th>Mutation</th><th>Relation</th><th>Agent</th><th>Action</th><th>Agent check</th><th>Boundary</th><th>PayPal network</th></tr></thead><tbody id="rows"><tr><td colspan="7" class="muted">Run the suite to load results.</td></tr></tbody></table></div>
<div class="footer">Offline dashboard. No real payments. PayPal Sandbox calls remain disabled in this view.</div>
</div>
<script>
function esc(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));}
async function loadReport(){
 const btn=document.querySelector('button'); btn.disabled=true; btn.textContent='Running…';
 try{const r=await fetch('/api/report',{cache:'no-store'}); const d=await r.json(); const s=d.summary;
 document.getElementById('cases').textContent=s.cases;
 document.getElementById('agentpass').textContent=s.agent_relation_pass+'/'+s.cases;
 document.getElementById('unsafe').textContent=s.unsafe_agent_pays;
 document.getElementById('boundary').textContent=s.boundary_pass+'/'+s.cases;
 document.getElementById('rows').innerHTML=d.cases.map(x=>`<tr><td>${esc(x.name)}</td><td><span class="pill">${esc(x.relation)}</span></td><td>${esc(x.agent)}</td><td>${esc(x.agent_action)}</td><td class="${x.agent_relation_pass?'pass':'fail'}">${x.agent_relation_pass?'PASS':'FAIL'}</td><td class="${x.boundary_pass?'pass':'fail'}">${esc(x.boundary_verdict)} · ${x.boundary_pass?'PASS':'FAIL'}</td><td>${x.paypal_network_allowed?'ALLOWED':'BLOCKED'}</td></tr>`).join('');
 }catch(e){document.getElementById('rows').innerHTML='<tr><td colspan="7">Error: '+esc(e)+'</td></tr>';}finally{btn.disabled=false;btn.textContent='Run stress suite';}}
loadReport();
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
