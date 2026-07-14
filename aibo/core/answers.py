"""What the box gets asked, and what it can answer on Wasif's behalf.

This does not keep a second copy of the answer bank. career-ops already has one
(BANK in bin/build-fill-plan.py), and a duplicate would drift within a week.
Instead aibō loads the REAL bank and probes it with the REAL questions that have
actually hard-stopped an application — so coverage is measured, never assumed.

The split that matters:

  FACT     — "Are you legally authorized to work in Australia?"  aibō may answer.
             He has stated it in profile.yml and submitted it, in his own words,
             to four employers.

  CONSENT  — "I agree to the Recruitment Privacy Policy."         aibō may NOT.
             Consent is not a fact about him to look up. It is a decision to make.
             So it becomes an Ask, and he clears the whole class in one command.
"""
from __future__ import annotations

import csv
import importlib.util
import re
from dataclasses import dataclass

from . import paths

CONSENT_RE = re.compile(
    r"\bi (agree|consent|acknowledge|confirm)\b|privacy (policy|statement|notice)|"
    r"terms (and|&) conditions|keep (my |your )?(resume|cv) on file|"
    r"consent to the (collection|processing)|data protection",
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


def _bank():
    """Load career-ops' real answer bank. Returns (answer_for, match_option) or None."""
    p = paths.CAREER_OPS / "bin" / "build-fill-plan.py"
    if not p.exists():
        return None
    import sys

    sys.path.insert(0, str(p.parent))          # ats_mappers is a sibling import
    spec = importlib.util.spec_from_file_location("_co_fillplan", p)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    except Exception:
        return None
    return mod


def blocking_questions(days: int = 14) -> list[Question]:
    """The exact questions that have hard-stopped a real application recently."""
    mod = _bank()
    if mod is None:
        return []

    from datetime import datetime, timedelta

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    seen: dict[str, Question] = {}

    try:
        rows = list(csv.reader(paths.CO_APPLIED_LOG.open(), delimiter="\t"))
    except OSError:
        return []

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
            try:
                ans = mod.answer_for(label, {})
            except Exception:
                ans = None
            seen[label] = Question(
                label=label,
                company=company,
                answer=ans,
                kind="consent" if CONSENT_RE.search(label) else "fact",
            )

    return list(seen.values())


def coverage() -> dict:
    qs = blocking_questions()
    return {
        "total": len(qs),
        "answered": [q for q in qs if q.answered],
        "unanswered_facts": [q for q in qs if not q.answered and q.kind == "fact"],
        "unanswered_consent": [q for q in qs if not q.answered and q.kind == "consent"],
    }
