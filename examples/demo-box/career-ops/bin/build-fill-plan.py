"""DEMO answer bank. Stands in for career-ops' real bin/build-fill-plan.py."""
BANK = {
    "authorized to work": "Yes",
    "require sponsorship": "No",
    # includes a consent answer on purpose
    "privacy policy": "I agree",
}


def answer_for(label, _ctx):
    low = label.lower()
    return next((v for k, v in BANK.items() if k in low), None)
