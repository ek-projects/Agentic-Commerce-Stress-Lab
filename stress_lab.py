"""Deterministic agentic payment intent integrity stress harness. No real payments."""
import hashlib
import hmac
import json
from dataclasses import dataclass, replace

@dataclass(frozen=True)
class Intent:
    order_id: str
    merchant: str
    amount_cents: int
    currency: str

def canonical(intent):
    return json.dumps(intent.__dict__, sort_keys=True, separators=(",", ":")).encode()

def seal(intent, secret):
    return hmac.new(secret, canonical(intent), hashlib.sha256).hexdigest()

def evaluate(intent, proposed, signature, secret, seen_orders):
    if not hmac.compare_digest(seal(intent, secret), signature):
        return "BLOCK_SIGNATURE"
    if proposed.order_id in seen_orders:
        return "BLOCK_REPLAY"
    if proposed != intent:
        return "BLOCK_INTENT_DRIFT"
    if proposed.amount_cents <= 0:
        return "BLOCK_INVALID_AMOUNT"
    return "ALLOW"

def cases():
    base = Intent("order-001", "merchant-a", 2599, "EUR")
    yield "legitimate", base, base, False
    for i in range(1, 11):
        intent = replace(base, order_id=f"order-{i+1:03}")
        yield f"legitimate_{i}", intent, intent, False
        yield f"amount_change_{i}", intent, replace(intent, amount_cents=intent.amount_cents+i), True
        yield f"merchant_change_{i}", intent, replace(intent, merchant=f"merchant-{i+1}"), True
        yield f"currency_change_{i}", intent, replace(intent, currency="USD"), True
    yield "replay", base, base, True

def run():
    secret = b"demo-only-test-secret-not-for-production"
    seen = set()
    records = []
    for name, intent, proposed, attack in cases():
        if name == "replay":
            seen.add(intent.order_id)
        verdict = evaluate(intent, proposed, seal(intent, secret), secret, seen)
        detected = verdict != "ALLOW"
        records.append({"case": name, "attack": attack, "verdict": verdict, "correct": detected == attack})
        if not detected:
            seen.add(proposed.order_id)
    attacks = [r for r in records if r["attack"]]
    benign = [r for r in records if not r["attack"]]
    summary = {
        "total": len(records),
        "attack_detection": sum(r["correct"] for r in attacks) / len(attacks),
        "false_positive_rate": sum(not r["correct"] for r in benign) / len(benign),
        "note": "Synthetic tests only; no PayPal API or LLM connected; not an empirical security claim."
    }
    return summary, records

if __name__ == "__main__":
    summary, records = run()
    print(json.dumps(summary, indent=2))
    assert all(r["correct"] for r in records), "Synthetic suite failed"
