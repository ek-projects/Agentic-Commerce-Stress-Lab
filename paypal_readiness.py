#!/usr/bin/env python3
"""Operational readiness check for the PayPal Sandbox boundary.

This script never targets PayPal live endpoints and never prints credentials or access
tokens. By default it checks configuration and Sandbox reachability only. Passing
``--create-order`` additionally creates one Sandbox order, but only from a trace that
passes the independent payment boundary. A known-blocked trace is evaluated with
``dry_run=False`` as a negative control and must still make no provider call.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Optional
from urllib import error, parse, request

from paypal_boundary import (
    SANDBOX_BASE_URL,
    PayPalSandboxClient,
    PayPalSandboxError,
    execute_paypal_boundary,
)
from trace_lab import build_dataset


def probe_oauth_endpoint(timeout: float = 10.0) -> dict[str, Any]:
    """Probe Sandbox OAuth reachability without supplying credentials.

    HTTP 400/401 is sufficient evidence that the PayPal Sandbox endpoint answered;
    it is deliberately *not* treated as authenticated readiness.
    """
    body = parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = request.Request(
        SANDBOX_BASE_URL + "/v1/oauth2/token",
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            response.read(1)
            return {
                "reachable": True,
                "http_status": int(response.status),
                "authenticated": False,
                "note": "Endpoint answered without configured client credentials; this is not an auth success.",
            }
    except error.HTTPError as exc:
        exc.read(1024)
        return {
            "reachable": True,
            "http_status": int(exc.code),
            "authenticated": False,
            "note": "Sandbox endpoint answered the unauthenticated probe.",
        }
    except error.URLError as exc:
        return {
            "reachable": False,
            "http_status": None,
            "authenticated": False,
            "note": f"Network error: {exc.reason}",
        }


def _reference_traces():
    traces = build_dataset(variants=1)
    allowed = next(trace for trace in traces if trace.category == "benign_stable")
    blocked = next(trace for trace in traces if trace.category == "attack_detached_confirmation")
    return allowed, blocked


def readiness_report(
    *,
    client: Optional[PayPalSandboxClient] = None,
    create_order: bool = False,
    network_probe: Optional[Callable[[], dict[str, Any]]] = probe_oauth_endpoint,
) -> dict[str, Any]:
    client = client or PayPalSandboxClient()
    report: dict[str, Any] = {
        "sandbox_base_url": SANDBOX_BASE_URL,
        "credentials_present": bool(client.configured),
        "network_probe": None,
        "oauth": {"attempted": False, "ok": False},
        "create_order": {"requested": bool(create_order), "attempted": False, "ok": False},
        "blocked_negative_control": {"attempted": False, "provider_called": False, "ok": False},
        "authenticated_sandbox_ready": False,
        "end_to_end_create_order_verified": False,
        "status": "unknown",
    }

    if network_probe is not None:
        report["network_probe"] = network_probe()

    if not client.configured:
        report["status"] = "credentials_missing"
        return report

    report["oauth"]["attempted"] = True
    try:
        token = client.get_access_token()
        report["oauth"]["ok"] = bool(token)
    except PayPalSandboxError as exc:
        report["oauth"]["error"] = str(exc)[:1000]
        report["status"] = "oauth_failed"
        return report

    report["authenticated_sandbox_ready"] = True
    report["status"] = "oauth_ready"
    if not create_order:
        return report

    allowed, blocked = _reference_traces()

    # Negative control first: even with dry_run=False and a configured real client,
    # the boundary must return before any provider method is invoked.
    blocked_result = execute_paypal_boundary(blocked, client=client, dry_run=False)
    report["blocked_negative_control"] = {
        "attempted": True,
        "trace": blocked.name,
        "verdict": blocked_result["verdict"],
        "reason": blocked_result["reason"],
        "provider_called": bool(blocked_result["paypal_called"]),
        "ok": not blocked_result["paypal_called"],
    }
    if blocked_result["paypal_called"]:
        report["status"] = "boundary_negative_control_failed"
        return report

    report["create_order"]["attempted"] = True
    try:
        safe_result = execute_paypal_boundary(allowed, client=client, dry_run=False)
    except PayPalSandboxError as exc:
        report["create_order"]["error"] = str(exc)[:1000]
        report["status"] = "create_order_failed"
        return report

    response = safe_result.get("paypal_response") or {}
    report["create_order"] = {
        "requested": True,
        "attempted": True,
        "ok": bool(safe_result.get("paypal_called") and response.get("id")),
        "trace": allowed.name,
        "boundary_verdict": safe_result["verdict"],
        "request_id": safe_result.get("paypal_request_id"),
        "paypal_order_id": response.get("id"),
        "paypal_status": response.get("status"),
    }
    report["end_to_end_create_order_verified"] = bool(report["create_order"]["ok"])
    report["status"] = "create_order_verified" if report["end_to_end_create_order_verified"] else "create_order_failed"
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--create-order",
        action="store_true",
        help="after OAuth succeeds, create one real PayPal Sandbox order from the known-safe trace",
    )
    parser.add_argument("--no-network-probe", action="store_true")
    parser.add_argument("--json", default="paypal_readiness_report.json")
    args = parser.parse_args()

    report = readiness_report(
        create_order=args.create_order,
        network_probe=None if args.no_network_probe else probe_oauth_endpoint,
    )
    Path(args.json).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
