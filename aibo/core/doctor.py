"""Is the box actually doing its job?

The old monitoring asked "did the pipeline run?" and answered yes for seven days
while box-apply died on a 404 every morning. Running is not succeeding. Every
check here asks for EVIDENCE OF AN OUTCOME (an application submitted, a draft
written, a report produced) and treats silence as failure, never as health.
"""
from __future__ import annotations

import csv
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from . import paths


@dataclass
class Check:
    name: str
    ok: bool | None      # True pass, False fail, None not applicable (system absent or unsupported)
    detail: str

    @property
    def failed(self) -> bool:
        return self.ok is False


def _absent(name: str, what) -> Check:
    """A system that isn't installed is ABSENT, not broken.

    "Silence is failure" applies to a system that exists and said nothing. It does
    not apply to one that was never here: reporting a missing career-ops as a
    failure would cry wolf on every fresh install, and a monitor that cries wolf
    gets ignored, which is the exact disease aibo exists to treat.
    """
    return Check(name, None, f"not installed ({what})")


def _days_ago(n: int) -> str:
    return (paths.now() - timedelta(days=n)).strftime("%Y-%m-%d")


def _today() -> str:
    return paths.now().strftime("%Y-%m-%d")


def renderer_count() -> int | None:
    """Chromium renderer processes on this machine, or None where pgrep is unavailable."""
    if not shutil.which("pgrep"):
        return None
    try:
        out = subprocess.run(["pgrep", "-fc", "chrome --type=renderer"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        return int(out or 0)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def applications_submitted(days: int = 7) -> Check:
    """The outcome floor. A job-hunt pipeline that submits nothing is not working."""
    if not paths.CAREER_OPS.exists():
        return _absent("applications", "no career-ops checkout")
    cutoff = _days_ago(days)
    try:
        with paths.CO_APPLIED_LOG.open(encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f, delimiter="\t"))
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
    today = _today()
    try:
        log = paths.CO_DAILY_LOG.read_text(encoding="utf-8")
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
    from . import notify
    if not paths.AGENT_LAPTOP.exists():
        return _absent("alerts", "no agent-laptop dir")
    try:
        txt = paths.ALERTS_PENDING.read_text(encoding="utf-8").strip()
    except OSError:
        return Check("alerts", True, "no pending alerts")
    if not txt:
        return Check("alerts", True, "no pending alerts")
    m = re.findall(r"UNACKED (?:for )?(\d+)h", txt)
    age = max((int(x) for x in m), default=0)
    n = len([l for l in txt.splitlines() if l.strip()])
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


def _mem_available_mb() -> int | None:
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemAvailable"):
                    return int(line.split()[1]) // 1024
    except (OSError, ValueError):
        pass
    return None


def memory_pressure() -> Check:
    n = renderer_count()
    if n is None:
        return Check("memory", None, "not available on this platform (needs pgrep)")
    avail = _mem_available_mb()
    if avail is None:
        return Check("memory", None, "not available on this platform (needs /proc/meminfo)")
    mem = f"{avail}MB available"
    if n > 20:
        return Check("memory", False, f"{n} leaked Chromium renderers, {mem}. The box is swapping.")
    return Check("memory", True, f"{n} renderers, {mem}")


def email_drafts() -> Check:
    reports = paths.AGENT_LAPTOP / "reports"
    if not reports.exists():
        return _absent("email-triage", "no agent-laptop reports dir")
    now = paths.now()
    p: Path = reports / f"email-triage-{now:%Y-%m-%d}.md"
    if p.exists():
        return Check("email-triage", True, f"produced {p.name}")
    yesterday = reports / f"email-triage-{now - timedelta(days=1):%Y-%m-%d}.md"
    if now.hour < 7 and yesterday.exists():
        return Check("email-triage", True, "no report yet today (07:00 cron); yesterday's exists")
    if now.hour < 7:
        return Check("email-triage", False, "no triage report today or yesterday")
    return Check("email-triage", False, "no triage report today after 07:00")


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
