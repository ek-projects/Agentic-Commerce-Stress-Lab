"""Agent-under-test adapters for Agentic Commerce Stress Lab.

The external-command adapter is the bridge to a real AI commerce agent. The agent
receives a JSON trace stimulus on stdin and must emit one JSON object on stdout.
No provider SDK is required by the lab itself.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import shlex
import subprocess
from typing import Iterable, Optional, Protocol

from trace_lab import Event, PaymentIntent, Trace, intent_digest

PAY = "PAY"
CLARIFY = "CLARIFY"
STOP = "STOP"


@dataclass(frozen=True)
class AgentAction:
    action: str
    reason: str = ""
    intent: Optional[PaymentIntent] = None
    nonce: Optional[str] = None
    digest: Optional[str] = None
    metadata: Optional[dict] = None


class CommerceAgent(Protocol):
    name: str

    def run(self, trace: Trace) -> AgentAction: ...


def stimulus_events(trace: Trace) -> tuple[Event, ...]:
    """Remove the authored final payment attempt; preserve history such as completion/replay."""
    return tuple(event for event in trace.events if event.kind != "payment_attempt")


def trace_stimulus_dict(trace: Trace) -> dict:
    events = []
    for event in stimulus_events(trace):
        item = {
            "kind": event.kind,
            "actor": event.actor,
            "nonce": event.nonce,
            "digest": event.digest,
            "authentic": event.authentic,
            "text": event.text,
        }
        if event.intent is not None:
            item["intent"] = asdict(event.intent)
        events.append({k: v for k, v in item.items() if v not in (None, "")})
    return {
        "trace": trace.name,
        "category": trace.category,
        "events": events,
        "output_schema": {
            "action": "PAY|CLARIFY|STOP",
            "reason": "string",
            "intent": {
                "order_id": "string",
                "merchant": "string",
                "amount_cents": "integer",
                "currency": "string",
                "item": "string",
                "quantity": "integer",
            },
            "nonce": "string-or-null",
            "digest": "string-or-null",
        },
    }


def action_to_event(action: AgentAction) -> Optional[Event]:
    if action.action != PAY or action.intent is None:
        return None
    return Event(
        "payment_attempt",
        "agent_under_test",
        intent=action.intent,
        nonce=action.nonce,
        digest=action.digest,
        text=action.reason,
    )


def append_action(trace: Trace, action: AgentAction) -> Trace:
    event = action_to_event(action)
    if event is None:
        return Trace(trace.name, trace.category, trace.expected, stimulus_events(trace), trace.attack)
    return Trace(trace.name, trace.category, trace.expected, stimulus_events(trace) + (event,), trace.attack)


class GreedyLatestProposalAgent:
    """Intentionally naive built-in agent used as a stress-target negative control.

    It pays the latest proposal and reuses the latest observed confirmation token.
    It does not understand cancellation, token lifecycle or detached confirmation.
    """

    name = "greedy-latest-proposal"

    def run(self, trace: Trace) -> AgentAction:
        latest_intent: Optional[PaymentIntent] = None
        nonce: Optional[str] = None
        digest: Optional[str] = None
        for event in stimulus_events(trace):
            if event.kind == "proposal" and event.intent is not None:
                latest_intent = event.intent
            elif event.kind == "user_confirm" and event.actor == "user":
                nonce = event.nonce
                digest = event.digest

        if latest_intent is None:
            return AgentAction(CLARIFY, "No concrete payment proposal is available.")
        if nonce is None:
            return AgentAction(CLARIFY, "No user confirmation token was observed.")
        return AgentAction(PAY, "Pay the latest proposal using the latest observed confirmation.", latest_intent, nonce, digest)


class ConfirmationAwareAgent:
    """Stronger deterministic comparison agent.

    It only pays when the latest authentic user confirmation still matches the latest
    proposal and has not subsequently been cancelled. This remains a reference baseline,
    not an AI system.
    """

    name = "confirmation-aware"

    def run(self, trace: Trace) -> AgentAction:
        latest_intent: Optional[PaymentIntent] = None
        confirmed_intent: Optional[PaymentIntent] = None
        nonce: Optional[str] = None
        digest: Optional[str] = None
        cancelled = False

        for event in stimulus_events(trace):
            if event.kind == "proposal" and event.intent is not None:
                latest_intent = event.intent
            elif event.kind == "user_confirm" and event.actor == "user" and event.authentic and latest_intent is not None:
                if event.digest == intent_digest(latest_intent) and event.nonce:
                    confirmed_intent = latest_intent
                    nonce = event.nonce
                    digest = event.digest
                    cancelled = False
            elif event.kind == "cancel" and event.actor == "user":
                cancelled = True

        if cancelled:
            return AgentAction(STOP, "User cancelled after confirmation.")
        if latest_intent is None:
            return AgentAction(CLARIFY, "No concrete proposal.")
        if confirmed_intent != latest_intent or not nonce or not digest:
            return AgentAction(CLARIFY, "Latest terms are not bound to a valid user confirmation.")
        return AgentAction(PAY, "Latest proposal is still exactly confirmed.", latest_intent, nonce, digest)


class ExternalCommandAgent:
    """Run any external agent through a tiny stdin/stdout JSON contract.

    Example command shape:
        python3 my_agent_adapter.py

    The adapter receives one JSON object on stdin and must emit exactly one JSON object.
    """

    def __init__(self, command: str, *, timeout: float = 60.0, name: Optional[str] = None):
        self.command = command
        self.timeout = timeout
        self.name = name or f"external:{command}"

    def run(self, trace: Trace) -> AgentAction:
        proc = subprocess.run(
            shlex.split(self.command),
            input=json.dumps(trace_stimulus_dict(trace)),
            text=True,
            capture_output=True,
            timeout=self.timeout,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"External agent exited {proc.returncode}: {proc.stderr[:1000]}")
        try:
            raw = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"External agent did not return valid JSON: {proc.stdout[:1000]}") from exc

        action = str(raw.get("action", "")).upper()
        if action not in {PAY, CLARIFY, STOP}:
            raise ValueError(f"Invalid external action: {action!r}")

        intent = None
        if raw.get("intent") is not None:
            intent = PaymentIntent(**raw["intent"])
        if action == PAY and intent is None:
            raise ValueError("PAY requires an intent")

        metadata = {}
        if isinstance(raw.get("metadata"), dict):
            metadata.update(raw["metadata"])
        for key in ("adapter_fallback", "model_raw", "model", "seed", "mode", "backend", "gpu_layers", "authorization_facts"):
            if key in raw:
                metadata[key] = raw[key]

        return AgentAction(
            action=action,
            reason=str(raw.get("reason", "")),
            intent=intent,
            nonce=raw.get("nonce"),
            digest=raw.get("digest"),
            metadata=metadata or None,
        )
