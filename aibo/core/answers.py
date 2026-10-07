"""What your tools get asked, and what aibō can answer on your behalf.

This does not keep a second copy of the answer bank. career-ops already has one
(BANK in bin/build-fill-plan.py), and a duplicate would drift within a week.
Instead aibō loads the REAL bank and probes it with the REAL questions that have
actually hard-stopped an application, so coverage is measured, never assumed.

The split that matters:

  FACT:    "Are you legally authorized to work in Australia?"  aibō may answer.
             You have stated it in profile.yml and submitted it, in your own words,
             to four employers.

  CONSENT: "I agree to the Recruitment Privacy Policy."         aibō may NOT.
             Consent is not a fact about you to look up. It is a decision to make.
             So it becomes an Ask, and he clears the whole class in one command.
"""
from __future__ import annotations

import csv
import importlib.util
import re
from dataclasses import dataclass

from . import paths

CONSENT_RE = re.compile(
    r"\b(?:consent(?:ed|ing)?|agree(?:d|ing)?|authori[sz](?:e|es|ed(?!\s+to\s+work)|ing|ation)|"
    r"acknowledge(?:d|ment)?|confirm(?:ed|ation)?|permission)\b|"
    r"\bprivacy(?:\s+(?:policy|statement|notice|terms))?\b|"
    r"\bterms(?:\s+(?:and|&)\s+conditions|\s+of\s+(?:use|service))\b|"
    r"\bbackground\s+(?:checks?|screenings?)\b|"
    r"keep (my |your )?(resume|cv) on file|data protection",
    re.I,
)
WORK_AUTHORIZATION_RE = re.compile(
    r"\b(?:legally\s+)?authori[sz]ed\s+to\s+work\b|"
    r"\bauthori[sz]ation\s+to\s+work\b|\bwork\s+authori[sz]ation\b",
    re.I,
)


@dataclass
class Question:
    label: str
    company: str
    answer: object | None
    kind: str            # "fact" | "consent"

    @property
    def answered(self) -> bool:
        return self.answer is not None


class BankUnavailable(Exception):
    """career-ops is installed but its answer data could not be loaded."""


def _consent_like(label: str) -> bool:
    factual_label = WORK_AUTHORIZATION_RE.sub("", label)
    return CONSENT_RE.search(factual_label) is not None


def _bank():
    """Load career-ops' real answer bank module."""
    p = paths.CAREER_OPS / "bin" / "build-fill-plan.py"
    if not p.exists():
        raise BankUnavailable(f"no answer bank at {p}")
    import sys

    sys.path.insert(0, str(p.parent))          # ats_mappers is a sibling import
    spec = importlib.util.spec_from_file_location("_co_fillplan", p)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    except Exception as e:
        raise BankUnavailable(f"{p} failed to load: {e!r}") from e
    if not hasattr(mod, "answer_for"):
        raise BankUnavailable(f"{p} has no answer_for()")
    return mod


def blocking_questions(days: int = 14) -> list[Question]:
    """The exact questions that have hard-stopped a real application recently."""
    mod = _bank()

    from datetime import timedelta

    cutoff = (paths.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    seen: dict[str, Question] = {}

    try:
        with paths.CO_APPLIED_LOG.open(encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f, delimiter="\t"))
    except (OSError, UnicodeError, csv.Error) as e:
        raise BankUnavailable(f"cannot read the applied log at {paths.CO_APPLIED_LOG}: {e}") from e

    for r in rows:
        if len(r) < 7 or r[0] < cutoff:
            continue
        # The status column is the coarse bucket ("hard-stop"); the specific reason
        # and the offending question labels live in notes.
        if "unknown_required_field" not in r[6]:
            continue
        company = r[2]
        inner = re.findall(r"\(([^)]*)\)", r[6])
        if not inner:
            continue
        for label in (q.strip() for q in inner[0].split(";")):
            if not label or label in seen:
                continue
            kind = "consent" if _consent_like(label) else "fact"
            ans = None
            if kind == "fact":                  # consent is never looked up, whatever the bank says
                try:
                    ans = mod.answer_for(label, {})
                except Exception:
                    ans = None
            seen[label] = Question(label=label, company=company, answer=ans, kind=kind)

    return list(seen.values())


def coverage() -> dict:
    """Split blocking questions by what aibo may answer. 'unavailable' says why none were checked."""
    if not paths.CAREER_OPS.exists():
        return {"total": 0, "unavailable": "not installed (no career-ops checkout)", "failed": False}
    try:
        qs = blocking_questions()
    except BankUnavailable as e:
        return {"total": 0, "unavailable": str(e), "failed": True}
    return {
        "unavailable": None,
        "failed": False,
        "total": len(qs),
        "answered": [q for q in qs if q.answered],
        "unanswered_facts": [q for q in qs if not q.answered and q.kind == "fact"],
        "unanswered_consent": [q for q in qs if not q.answered and q.kind == "consent"],
    }
