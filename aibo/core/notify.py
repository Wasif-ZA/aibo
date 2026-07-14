"""Actually reaching the human.

The original sin of the machine this was built for: every channel was PULL. A
CRITICAL alert sat unread for 143 hours; a 7-day outage was written into the daily
brief seven times and read zero times. Writing to a file nobody opens is not a
notification.

So notify() has a ladder, and it is honest about which rung it reached:

  PUSH  — ntfy topic armed  -> lands on your phone.
  FILE  — no topic          -> queued to the ask log, and we SAY SO.

We never pretend a file write was a delivery.
"""
from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime

from . import paths


@dataclass
class Delivery:
    reached_phone: bool
    channel: str          # "push" | "file"
    detail: str


def topic() -> str | None:
    try:
        t = paths.NTFY_TOPIC_FILE.read_text().strip()
        return t or None
    except OSError:
        return None


def armed() -> bool:
    return topic() is not None


def notify(title: str, body: str, priority: str = "default", tags: str = "") -> Delivery:
    """Try to actually reach you. Return the truth about whether we did."""
    paths.ensure()
    stamp = datetime.now().isoformat(timespec="seconds")

    t = topic()
    if t:
        req = urllib.request.Request(
            f"https://ntfy.sh/{t}",
            data=body.encode("utf-8"),
            headers={"Title": title, "Priority": priority, "Tags": tags or "robot"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                if 200 <= r.status < 300:
                    _log(f"{stamp} PUSH ok    | {title}")
                    return Delivery(True, "push", "delivered to ntfy topic")
                detail = f"ntfy returned HTTP {r.status}"
        except (urllib.error.URLError, OSError) as e:
            detail = f"ntfy unreachable: {e}"
        _log(f"{stamp} PUSH FAIL | {title} | {detail}")
        return Delivery(False, "file", f"push failed ({detail}); queued to {paths.ASK_LOG}")

    _log(f"{stamp} FILE only | {title} | {body}")
    return Delivery(
        False,
        "file",
        "no push channel armed — this is sitting in a file you have to remember to open. "
        "Arm it: ~/agent-laptop/scripts/arm-push-alerts.sh",
    )


def _log(line: str) -> None:
    with paths.ASK_LOG.open("a") as f:
        f.write(line + "\n")
