"""Deterministic authorization facts exposed to agents and audit reports.

These facts summarize structured event evidence. They do not choose PAY/CLARIFY/STOP
and are deliberately kept separate from the final payment boundary decision.
"""
from __future__ import annotations

from typing import Any

from trace_lab import PaymentIntent, intent_digest


def authorization_facts(stimulus: dict[str, Any]) -> dict[str, Any]:
    events = stimulus.get("events", [])
    latest_proposal_idx = None
    latest_proposal = None
    latest_confirm_idx = None
    latest_confirm = None
    latest_cancel_idx = None

    for idx, event in enumerate(events):
        if event.get("kind") == "proposal" and isinstance(event.get("intent"), dict):
            latest_proposal_idx = idx
            latest_proposal = event.get("intent")
        elif event.get("kind") == "user_confirm" and event.get("actor") == "user":
            latest_confirm_idx = idx
            latest_confirm = event
        elif event.get("kind") == "cancel" and event.get("actor") == "user":
            latest_cancel_idx = idx

    authentic_confirmation = bool(
        latest_confirm
        and latest_confirm.get("authentic", True)
        and latest_confirm.get("nonce")
        and latest_confirm.get("digest")
    )

    expected_digest = None
    if isinstance(latest_proposal, dict):
        try:
            expected_digest = intent_digest(PaymentIntent(**latest_proposal))
        except (TypeError, ValueError):
            expected_digest = None

    confirmation_matches_current = bool(
        authentic_confirmation
        and expected_digest
        and latest_confirm.get("digest") == expected_digest
        and latest_confirm_idx is not None
        and latest_proposal_idx is not None
        and latest_confirm_idx > latest_proposal_idx
    )

    confirmation_consumed = False
    if authentic_confirmation and latest_confirm_idx is not None:
        for idx, event in enumerate(events):
            if idx <= latest_confirm_idx or event.get("kind") != "payment_complete":
                continue
            if (
                event.get("nonce") == latest_confirm.get("nonce")
                and event.get("digest") == latest_confirm.get("digest")
            ):
                confirmation_consumed = True
                break

    return {
        "authentic_confirmation_present": authentic_confirmation,
        "confirmation_matches_current_proposal": confirmation_matches_current,
        "confirmation_consumed": confirmation_consumed,
        "proposal_after_latest_confirmation": bool(
            latest_proposal_idx is not None
            and latest_confirm_idx is not None
            and latest_proposal_idx > latest_confirm_idx
        ),
        "cancelled_after_confirmation": bool(
            latest_cancel_idx is not None
            and latest_confirm_idx is not None
            and latest_cancel_idx > latest_confirm_idx
        ),
    }
