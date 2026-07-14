"""Asks — the one queue of things only you can decide.

This machine never lacked information. It has lacked a single place where
"a human must act on this" is collected, ranked, and PUSHED. Alerts went to
alerts-pending.txt. Stalled applications went to a TSV. Security rotations
went to a research note. Each channel was separately ignorable, and each was
separately ignored.

An Ask has exactly one property that matters: it is BLOCKING something real.
If nothing is blocked, it is not an Ask, it is a log line, and it does not
get to interrupt you.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

from . import paths

SEVERITY = {"critical": 0, "blocking": 1, "advisory": 2}


@dataclass
class Ask:
    id: str
    title: str
    severity: str            # critical | blocking | advisory
    blocking: str            # what is NOT happening because this is unanswered
    action: str              # the literal thing you do to resolve it
    source: str
    detail: str = ""
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def sort_key(self):
        return (SEVERITY.get(self.severity, 9), self.first_seen)


# ---------- collectors: each reads a system that already exists ----------

def _security_rotations() -> list[Ask]:
    """Surface a standing credential-rotation alert without restating the secret.

    Deliberately does NOT hardcode the remediation. The alert file already says what
    to rotate and how; duplicating it here would mean a security runbook drifting in
    two places, and would bake one machine's private layout into a public repo. So
    aibō points at the alert and gets out of the way.
    """
    try:
        txt = paths.ALERTS_PENDING.read_text()
    except OSError:
        return []
    if "ROTATE NOW" not in txt:
        return []

    age = ""
    m = re.findall(r"UNACKED (?:for )?(\d+)h", txt)
    if m:
        age = f" Unacked for {max(int(x) for x in m)}h."

    return [
        Ask(
            id="sec-rotate",
            title="A credential rotation is outstanding",
            severity="critical",
            blocking=(
                "Nothing is blocked, which is exactly the problem: the exposed credential "
                "still works, so every pipeline that uses it keeps running on it." + age
            ),
            action=f"cat {paths.ALERTS_PENDING}   then, once done: {paths.AGENT_LAPTOP}/scripts/alert-ack.sh",
            source=str(paths.ALERTS_PENDING),
        )
    ]


def _unarmed_push() -> list[Ask]:
    from . import notify

    if notify.armed():
        return []
    return [
        Ask(
            id="arm-push",
            title="Arm the push channel — nothing on this box can reach you",
            severity="critical",
            blocking=(
                "Every ask below this line. They are all sitting in files. The last critical "
                "alert waited 143 hours to be read. Until this is armed, aibō is writing "
                "letters it cannot post."
            ),
            action="~/agent-laptop/scripts/arm-push-alerts.sh   then subscribe on your phone (ntfy app)",
            source="agent-laptop/.ntfy-topic is absent",
            detail="Publishes alert text to ntfy.sh (public third-party). That is why it is your call, not aibō's.",
        )
    ]


def _stalled_applications() -> list[Ask]:
    """Roles that box-apply reached, filled, and could NOT submit."""
    asks: list[Ask] = []
    try:
        rows = list(csv.reader(paths.CO_APPLIED_LOG.open(), delimiter="\t"))
    except OSError:
        return []

    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    blocked_q: dict[str, list[str]] = {}
    review: list[str] = []

    for r in rows:
        if len(r) < 7 or r[0] < cutoff:
            continue
        ts, _mode, company, role, _url, status, notes = r[0], r[1], r[2], r[3], r[4], r[5], r[6]
        # status is the coarse bucket ("hard-stop"); the reason is in notes.
        if status == "needs_review":
            review.append(f"{company} — {role}")
        elif "unknown_required_field" in notes:
            qs = re.findall(r"\(([^)]*)\)", notes)
            blocked_q.setdefault(f"{company} — {role}", []).extend(
                q.strip() for q in (qs[0].split(";") if qs else [])
            )

    if blocked_q:
        roles = "; ".join(blocked_q)
        asks.append(
            Ask(
                id="apply-unknown-fields",
                title=f"{len(blocked_q)} application(s) filled out and then abandoned at the last step",
                severity="blocking",
                blocking=(
                    f"These roles: {roles}. box-apply filled every field it knew, hit a "
                    "screening question it had no answer for, and hard-stopped. It has "
                    "submitted 0 applications for several days running while the cap sat unused."
                ),
                action="aibo answers   (shows exactly which question stopped each one)",
                source="career-ops auto-applied-log.tsv (hard-stop:unknown_required_field)",
                detail=(
                    "Root cause was found and fixed on 2026-07-14: match_option() stringified "
                    "the list of acceptable answers, so work-rights and sponsorship questions "
                    "resolved to nothing. What remains is consent checkboxes, which are yours "
                    "to decide. These rows are historical -- the next run (Mon 07:52) is the test."
                ),
            )
        )

    if review:
        asks.append(
            Ask(
                id="apply-needs-review",
                title=f"{len(review)} application(s) parked with a live browser tab waiting for you",
                severity="blocking",
                blocking=f"{'; '.join(review)}. Each has a real tab open that only you can finish (captcha / emailed code).",
                action="VNC into the apply browser and finish the form by hand.",
                source="career-ops auto-applied-log.tsv (status needs_review)",
            )
        )
    return asks


def _leaked_browser() -> list[Ask]:
    import subprocess

    try:
        n = int(subprocess.run(
            ["pgrep", "-fc", "chrome --type=renderer"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip() or 0)
    except (subprocess.SubprocessError, ValueError):
        return []
    if n <= 20:
        return []
    return [
        Ask(
            id="browser-leak",
            title=f"apply-browser has leaked {n} renderer processes",
            severity="advisory",
            blocking="Nothing yet, but the box is swapping, which slows every other pipeline.",
            action="aibo fix browser   (installs the guarded reaper cron; it refuses to restart during an apply window)",
            source=f"pgrep: {n} chrome renderers",
        )
    ]


COLLECTORS = (_unarmed_push, _security_rotations, _stalled_applications, _leaked_browser)


def collect() -> list[Ask]:
    out: list[Ask] = []
    for c in COLLECTORS:
        try:
            out.extend(c())
        except Exception as e:  # a broken collector must not silence the others
            out.append(Ask(
                id=f"collector-error-{c.__name__}",
                title=f"aibō's own {c.__name__} collector crashed",
                severity="advisory",
                blocking="aibō may be blind to a whole class of asks.",
                action=f"Debug {c.__name__} in aibo/core/asks.py",
                source="aibo",
                detail=repr(e),
            ))
    return sorted(out, key=lambda a: a.sort_key())


def save(items: list[Ask]) -> None:
    paths.ensure()
    prior = {a["id"]: a for a in load_raw()}
    payload = []
    for a in items:
        d = asdict(a)
        if a.id in prior:                       # preserve original first_seen
            d["first_seen"] = prior[a.id].get("first_seen", d["first_seen"])
        payload.append(d)
    paths.ASKS.write_text(json.dumps(payload, indent=2))


def load_raw() -> list[dict]:
    try:
        return json.loads(paths.ASKS.read_text())
    except (OSError, ValueError):
        return []


def age_hours(a: Ask) -> float:
    try:
        return (datetime.now() - datetime.fromisoformat(a.first_seen)).total_seconds() / 3600
    except ValueError:
        return 0.0
