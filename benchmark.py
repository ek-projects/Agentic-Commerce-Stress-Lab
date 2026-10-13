"""Reproducible offline benchmark; measures tampering checks, not AI security."""
from dataclasses import dataclass, replace
import json
from stress_lab import Intent, seal, evaluate

SECRET = b"demo-only-test-secret-not-for-production"

@dataclass(frozen=True)
class Scenario:
    label: str
    original: Intent
    proposed: Intent
    malicious: bool
    replay: bool = False

def scenarios():
    result = []
    for i in range(50):
        base = Intent(f"ord-{i:04}", "shop-a", 2000 + i, "EUR")
        result.append(Scenario("legitimate", base, base, False))
        result.append(Scenario("amount", base, replace(base, amount_cents=base.amount_cents + 1), True))
        result.append(Scenario("merchant", base, replace(base, merchant="shop-b"), True))
        result.append(Scenario("currency", base, replace(base, currency="USD"), True))
        result.append(Scenario("replay", base, base, True, True))
    return result

def naive_policy(proposed, already_seen):
    # Traditional limit + replay only: cannot detect merchant/amount drift within budget.
    if proposed.amount_cents <= 0 or proposed.amount_cents > 10000:
        return False
    if proposed.order_id in already_seen:
        return False
    return True

def score(predictions, truths):
    tp=sum(p and t for p,t in zip(predictions,truths))
    fp=sum(p and not t for p,t in zip(predictions,truths))
    fn=sum(not p and t for p,t in zip(predictions,truths))
    tn=sum(not p and not t for p,t in zip(predictions,truths))
    return {"tp":tp,"fp":fp,"fn":fn,"tn":tn,"recall":tp/(tp+fn),"false_positive_rate":fp/(fp+tn)}

def main():
    cases=scenarios()
    naive,integrity,truth=[],[],[]
    for case in cases:
        seen={case.proposed.order_id} if case.replay else set()
        naive.append(not naive_policy(case.proposed,seen))
        integrity.append(evaluate(case.original,case.proposed,seal(case.original,SECRET),SECRET,seen)!="ALLOW")
        truth.append(case.malicious)
    report={
        "dataset":"250 constructed examples (50 base intents x 5 scenarios)",
        "baseline":score(naive,truth),
        "integrity":score(integrity,truth),
        "limitations":"Synthetic cases encode exact-match attacks; not a real-world efficacy test. Integrity system sees the original signed intent; baseline does not. This comparison is intentionally illustrative, not apples-to-apples.",
        "paypal_calls":0
    }
    print(json.dumps(report,indent=2))
    assert report["integrity"]["fn"]==0 and report["integrity"]["fp"]==0
    return report

if __name__=="__main__":
    main()
