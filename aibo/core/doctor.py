"""Is the box actually doing its job?

The old monitoring asked "did the pipeline run?" and answered yes for seven days
while box-apply died on a 404 every morning. Running is not succeeding. Every
check here asks for EVIDENCE OF AN OUTCOME -- an application submitted, a draft
written, a report produced -- and treats silence as failure, never as health.
"""
from __future__ import annotations

import csv
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta

from . import paths


@dataclass
class Check:
    name: str
    ok: bool | None      # True pass · False fail · None not applicable (system absent)
    detail: str

    @property
    def failed(self) -> bool:
        return self.ok is False


def _absent(name: str, what) -> Check:
    """A system that isn't installed is ABSENT, not broken.

    "Silence is failure" applies to a system that exists and said nothing. It does
    not apply to one that was never here — reporting a missing career-ops as a
    failure would cry wolf on every fresh install, and a monitor that cries wolf
    gets ignored, which is the exact disease aibō exists to treat.
    """
    return Check(name, None, f"not installed ({what})")


def _days_ago(n: int) -> str:
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


def applications_submitted(days: int = 7) -> Check:
    """The outcome floor. A job-hunt pipeline that submits nothing is not working."""
    if not paths.CAREER_OPS.exists():
        return _absent("applications", "no career-ops checkout")
    cutoff = _days_ago(days)
    try:
        rows = list(csv.reader(paths.CO_APPLIED_LOG.open(), delimiter="\t"))
    except OSError as e:
        return Check("applications", False, f"cannot read the applied log: {e}")

    recent = [r for r in rows if len(r) > 5 and r[0] >= cutoff]
    submitted = [r for r in recent if r[5] == "submitted"]
    stopped = [r for r in recent if r[5].startswith("hard-stop")]

    if submitted:
        last = max(r[0] for r in submitted)[:10]
        return Check("applications", True,
                     f"{len(submitted)} submitted in {days}d (most recent {last})")
    return Check(
        "applications", False,
        f"0 submitted in {days}d, though the pipeline ran and reached {len(stopped)} "
        f"forms. It is filling applications and abandoning them.",
    )


def job_hunt_ran() -> Check:
    if not paths.CAREER_OPS.exists():
        return _absent("job-hunt", "no career-ops checkout")
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        log = paths.CO_DAILY_LOG.read_text()
    except OSError:
        return Check("job-hunt", False, "no daily.log at all")
    lines = [l for l in log.splitlines() if today in l]
    if not lines:
        return Check("job-hunt", False, f"did not run today ({today})")
    failed = [l for l in lines if "FAILED" in l]
    if failed:
        return Check("job-hunt", False,
                     f"ran, but {len(failed)} stage(s) FAILED: {failed[-1].split('|')[-1].strip()[:70]}")
    return Check("job-hunt", True, "ran today, no failed stages")


def alerts_acked() -> Check:
    try:
        txt = paths.ALERTS_PENDING.read_text().strip()
    except OSError:
        return Check("alerts", True, "no pending alerts")
    if not txt:
        return Check("alerts", True, "no pending alerts")
    import re
    from . import notify
    m = re.findall(r"UNACKED (?:for )?(\d+)h", txt)
    age = max((int(x) for x in m), default=0)
    n = len([l for l in txt.splitlines() if l.strip()])
    # Do not claim unreachability once the push channel is armed -- that WAS true, and
    # saying it after it stops being true is exactly the kind of stale alert text that
    # trains a person to ignore the alerter.
    why = ("Backlog from before the push channel existed; read and ack it."
           if notify.armed() else
           "Nothing on this box can reach you.")
    return Check("alerts", False, f"{n} lines unread, oldest unacked {age}h. {why}")


def push_channel() -> Check:
    from . import notify
    if notify.armed():
        return Check("push", True, "push channel armed")
    return Check("push", False,
                 "NOT armed. Every alert is a file you must remember to open. "
                 "This is the root cause of every stale item below.")


def memory_pressure() -> Check:
    try:
        n = int(subprocess.run(["pgrep", "-fc", "chrome --type=renderer"],
                               capture_output=True, text=True, timeout=10).stdout.strip() or 0)
    except (subprocess.SubprocessError, ValueError):
        return Check("memory", True, "could not sample renderers")
    avail = 0
    try:
        for line in open("/proc/meminfo"):
            if line.startswith("MemAvailable"):
                avail = int(line.split()[1]) // 1024
                break
    except OSError:
        pass
    if n > 20:
        return Check("memory", False,
                     f"{n} leaked Chromium renderers, {avail}MB available. The box is swapping.")
    return Check("memory", True, f"{n} renderers, {avail}MB available")


def email_drafts() -> Check:
    if not (paths.AGENT_LAPTOP / "reports").exists():
        return _absent("email-triage", "no agent-laptop reports dir")
    today = datetime.now().strftime("%Y-%m-%d")
    p = paths.AGENT_LAPTOP / "reports" / f"email-triage-{today}.md"
    if p.exists():
        return Check("email-triage", True, f"produced {p.name}")
    y = paths.AGENT_LAPTOP / "reports" / f"email-triage-{_days_ago(1)}.md"
    if y.exists():
        return Check("email-triage", True, "no report yet today (07:00 cron); yesterday's exists")
    return Check("email-triage", False, "no triage report today or yesterday")


CHECKS = (push_channel, alerts_acked, applications_submitted, job_hunt_ran,
          email_drafts, memory_pressure)


def run() -> list[Check]:
    out = []
    for c in CHECKS:
        try:
            out.append(c())
        except Exception as e:
            out.append(Check(c.__name__, False, f"check crashed: {e!r}"))
    return out
