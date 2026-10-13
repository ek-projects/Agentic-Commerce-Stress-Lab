"""Equal-input deterministic benchmark. No external services, money or AI."""
import json
from dataclasses import dataclass, replace
from stress_lab import Intent, seal, evaluate

SECRET=b"demo-only-test-secret-not-for-production"

@dataclass(frozen=True)
class Example:
    kind: str
    authorized: Intent
    proposed: Intent
    malicious: bool
    replay: bool = False
    invalid_signature: bool = False

def dataset(n=40):
    cases=[]
    for i in range(n):
        a=Intent(f"order-{i:04d}","shop-a",500+i,"EUR")
        cases.extend([
            Example("valid",a,a,False),
            Example("amount-drift",a,replace(a,amount_cents=a.amount_cents+1),True),
            Example("merchant-drift",a,replace(a,merchant="shop-b"),True),
            Example("currency-drift",a,replace(a,currency="USD"),True),
            Example("replay",a,a,True,replay=True),
            Example("invalid-signature",a,a,True,invalid_signature=True),
        ])
    return cases

def rules(e,signature,seen):
    """A fair, deterministic baseline receiving the SAME signed intent and replay state."""
    if signature != seal(e.authorized,SECRET):
        return "BLOCK_SIGNATURE"
    if e.proposed.order_id in seen:
        return "BLOCK_REPLAY"
    if e.proposed != e.authorized:
        return "BLOCK_INTENT_DRIFT"
    if e.proposed.amount_cents <= 0:
        return "BLOCK_INVALID_AMOUNT"
    return "ALLOW"

def evaluate_cases():
    records=[]
    for e in dataset():
        signature="0"*64 if e.invalid_signature else seal(e.authorized,SECRET)
        seen={e.proposed.order_id} if e.replay else set()
        baseline=rules(e,signature,seen)
        tested=evaluate(e.authorized,e.proposed,signature,SECRET,seen)
        records.append({"kind":e.kind,"expected_block":e.malicious,
                        "baseline":baseline,"integrity":tested,
                        "agreement":baseline==tested})
    return records

if __name__=="__main__":
    records=evaluate_cases()
    assert all(x["agreement"] for x in records)
    assert all((x["integrity"]!="ALLOW")==x["expected_block"] for x in records)
    print(json.dumps({
        "cases":len(records),
        "baseline_correct":sum((x["baseline"]!="ALLOW")==x["expected_block"] for x in records),
        "integrity_correct":sum((x["integrity"]!="ALLOW")==x["expected_block"] for x in records),
        "baseline_integrity_agreement":sum(x["agreement"] for x in records),
        "finding":"When given the same authenticated intent, deterministic rules match this prototype exactly.",
        "limitation":"Designed synthetic data; this is not agent or PayPal testing."
    },indent=2))
