"""PayPal Sandbox boundary for the Agentic Commerce Stress Lab.

The module is intentionally server-side and standard-library only. It can build a
PayPal Orders v2 create-order request offline, and can send it to the sandbox when
PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET are explicitly available in the process
environment. It never targets PayPal live endpoints.
"""
from __future__ import annotations

from dataclasses import dataclass
import base64
import json
import os
from typing import Any, Optional
from urllib import error, parse, request

from trace_lab import ALLOW, Decision, Event, PaymentIntent, ProvenanceGuard, Trace, intent_digest

SANDBOX_BASE_URL = "https://api-m.sandbox.paypal.com"


class PayPalSandboxError(RuntimeError):
    pass


@dataclass(frozen=True)
class BoundaryPlan:
    decision: Decision
    paypal_request_id: Optional[str]
    payload: Optional[dict[str, Any]]
    payment_intent: Optional[PaymentIntent]
    network_call_allowed: bool


class PayPalSandboxClient:
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: str = SANDBOX_BASE_URL,
        timeout: float = 20.0,
    ):
        if base_url.rstrip("/") != SANDBOX_BASE_URL:
            raise ValueError("This lab client is sandbox-only; live PayPal endpoints are refused.")
        self.client_id = client_id or os.getenv("PAYPAL_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("PAYPAL_CLIENT_SECRET")
        self.base_url = SANDBOX_BASE_URL
        self.timeout = timeout
        self._access_token: Optional[str] = None

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _json_request(self, method: str, path: str, *, headers: dict[str, str], body: Optional[bytes] = None) -> dict[str, Any]:
        req = request.Request(self.base_url + path, data=body, method=method, headers=headers)
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise PayPalSandboxError(f"PayPal Sandbox HTTP {exc.code}: {raw[:1000]}") from exc
        except error.URLError as exc:
            raise PayPalSandboxError(f"PayPal Sandbox network error: {exc.reason}") from exc

    def get_access_token(self) -> str:
        if self._access_token:
            return self._access_token
        if not self.configured:
            raise PayPalSandboxError("Sandbox credentials are not configured.")
        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        body = parse.urlencode({"grant_type": "client_credentials"}).encode()
        data = self._json_request(
            "POST",
            "/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {basic}",
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            body=body,
        )
        token = data.get("access_token")
        if not token:
            raise PayPalSandboxError("Sandbox token response did not contain access_token.")
        self._access_token = str(token)
        return self._access_token

    def create_order(self, payload: dict[str, Any], request_id: str) -> dict[str, Any]:
        token = self.get_access_token()
        body = json.dumps(payload, separators=(",", ":")).encode()
        return self._json_request(
            "POST",
            "/v2/checkout/orders",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "PayPal-Request-Id": request_id,
            },
            body=body,
        )


def _money(cents: int) -> str:
    if cents <= 0:
        raise ValueError("amount_cents must be positive")
    return f"{cents / 100:.2f}"


def create_order_payload(intent: PaymentIntent) -> dict[str, Any]:
    """Map a guarded internal intent to a PayPal Orders v2 request.

    The PayPal merchant is the sandbox business account represented by the API
    credentials. The lab's logical merchant field is therefore preserved as
    trace metadata (`custom_id`) rather than pretending it changes the PayPal
    credential-bound payee.
    """
    digest = intent_digest(intent)
    return {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": intent.order_id[:256],
                "custom_id": f"acl:{digest[:48]}",
                "description": f"StressLab {intent.item} via {intent.merchant}"[:127],
                "amount": {
                    "currency_code": intent.currency,
                    "value": _money(intent.amount_cents),
                },
            }
        ],
    }


def _last_payment_attempt(trace: Trace) -> Optional[Event]:
    attempts = [event for event in trace.events if event.kind == "payment_attempt"]
    return attempts[-1] if attempts else None


def plan_paypal_boundary(trace: Trace, guard: Optional[ProvenanceGuard] = None) -> BoundaryPlan:
    guard = guard or ProvenanceGuard()
    decision = guard.evaluate(trace.events)
    attempt = _last_payment_attempt(trace)

    if decision.verdict != ALLOW or attempt is None or attempt.intent is None:
        return BoundaryPlan(decision, None, None, attempt.intent if attempt else None, False)

    if not attempt.nonce:
        return BoundaryPlan(Decision("BLOCK", "allowed_trace_missing_payment_nonce"), None, None, attempt.intent, False)

    # PayPal-Request-Id is the provider idempotency key. Bind it deterministically
    # to the single-use consent nonce without exposing the nonce verbatim.
    request_id = f"acl-{intent_digest(attempt.intent)[:20]}-{attempt.nonce[:32]}"
    return BoundaryPlan(
        decision=decision,
        paypal_request_id=request_id,
        payload=create_order_payload(attempt.intent),
        payment_intent=attempt.intent,
        network_call_allowed=True,
    )


def execute_paypal_boundary(
    trace: Trace,
    *,
    client: Optional[PayPalSandboxClient] = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    plan = plan_paypal_boundary(trace)
    result: dict[str, Any] = {
        "trace": trace.name,
        "verdict": plan.decision.verdict,
        "reason": plan.decision.reason,
        "network_call_allowed": plan.network_call_allowed,
        "dry_run": dry_run,
        "paypal_request_id": plan.paypal_request_id,
        "payload": plan.payload,
    }
    if not plan.network_call_allowed:
        result["paypal_called"] = False
        return result
    if dry_run:
        result["paypal_called"] = False
        return result

    client = client or PayPalSandboxClient()
    response = client.create_order(plan.payload or {}, plan.paypal_request_id or "")
    result["paypal_called"] = True
    result["paypal_response"] = {
        "id": response.get("id"),
        "status": response.get("status"),
        "links": response.get("links", []),
    }
    return result
