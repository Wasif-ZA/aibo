"""What aibō knows about you — and where it learned it.

Every fact carries provenance. That is the whole point: aibō is allowed to
ANSWER on your behalf only when it can point at where you already said it.
A fact with no source is not a fact, it is a guess, and a guess about
"do you require visa sponsorship" goes into a real application under your
real name. So guesses become Asks instead.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import paths


@dataclass
class Fact:
    key: str
    value: str
    source: str          # human-readable provenance
    confidence: str      # "stated" (you wrote it) | "derived" (inferred from what you wrote)

    @property
    def trustworthy(self) -> bool:
        return self.confidence == "stated"


def _load_yaml(p: Path) -> dict:
    try:
        return yaml.safe_load(p.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _load_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def known() -> dict[str, Fact]:
    """Collect every fact aibō can back with a source."""
    facts: dict[str, Fact] = {}
    prof = _load_yaml(paths.CO_PROFILE)

    def add(key: str, value, source: str, confidence: str = "stated") -> None:
        if value not in (None, "", [], {}):
            facts[key] = Fact(key, str(value), source, confidence)

    src = "career-ops config/profile.yml"
    cand = prof.get("candidate", {}) or {}
    add("full_name", cand.get("full_name"), src)
    add("email", cand.get("email"), src)
    add("phone", cand.get("phone"), src)
    add("linkedin", cand.get("linkedin"), src)
    add("github", cand.get("github"), src)

    loc = prof.get("location", {}) or {}
    add("location", cand.get("location") or loc.get("city"), src)
    add("visa_status", loc.get("visa_status"), src)

    comp = prof.get("compensation", {}) or {}
    add("salary_range", comp.get("target_range"), src)
    add("salary_minimum", comp.get("minimum"), src)
    add("work_location_pref", comp.get("location_flexibility"), src)

    edu = (prof.get("education") or [{}])[0]
    add("graduation", edu.get("period", "").split("-")[-1].strip() or None, src)
    add("degree", edu.get("qualification"), src)
    add("institution", edu.get("institution"), src)

    # Long-form answers you have already written and shipped in real applications.
    # These are the strongest provenance there is: he sent them to employers.
    ra = _load_json(paths.CO_ROLE_ANSWERS)
    for job_id, ans in ra.items():
        if isinstance(ans, dict) and ans.get("work_rights"):
            add(
                "work_rights_statement",
                ans["work_rights"],
                f"career-ops role-answers.json (your own words, submitted to job {job_id})",
            )
            break

    return facts


def get(key: str) -> Fact | None:
    return known().get(key)
