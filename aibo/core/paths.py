"""Where everything lives.

aibo does not own the box's data. It reads the systems that already exist
(career-ops, agent-laptop, box-vault) and writes only under AIBO_HOME.
"""
from __future__ import annotations

import os
from pathlib import Path

HOME = Path(os.environ.get("AIBO_HOME", Path.home() / "projects" / "aibo"))

DATA = HOME / "data"
LOGS = HOME / "logs"

# aibo's own state
PROFILE = DATA / "profile.yml"
ANSWERS = DATA / "answer-bank.yml"
ASKS = DATA / "asks.json"
ASK_LOG = LOGS / "asks.log"

# --- foreign systems aibo federates over (read-mostly) ---
BOX = Path.home()
CAREER_OPS = BOX / "projects" / "career-ops-sydney"
CO_DATA = CAREER_OPS / "career-ops" / "data"
CO_PROFILE = CAREER_OPS / "career-ops" / "config" / "profile.yml"
CO_ROLE_ANSWERS = CO_DATA / "role-answers.json"
CO_APPLIED_LOG = CO_DATA / "auto-applied-log.tsv"
CO_DAILY_LOG = CAREER_OPS / "logs" / "daily.log"

AGENT_LAPTOP = BOX / "agent-laptop"
ALERTS_PENDING = AGENT_LAPTOP / "state" / "alerts-pending.txt"
NTFY_TOPIC_FILE = AGENT_LAPTOP / ".ntfy-topic"

VAULT = BOX / "box-vault"
DAILY_DIR = VAULT / "06 Daily"


def ensure() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
