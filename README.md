# aibō (相棒) — partner

A personal assistant layer for a student / founder / researcher, running on the box.

## Why this exists, and why it is not another pipeline

Before writing a line of code I searched the box for what was already here. The
answer was: **everything, and none of it connected.**

| Need | Already existed |
|---|---|
| Job searching | `career-ops-sydney` — discovery, fit-scoring council, auto-apply via headless Chromium, 5 ATS mappers |
| Email replying | `agent-laptop/scripts/email-triage.sh` — 07:00 cron, drafts Gmail replies, never sends |
| Outreach | `career-ops-sydney/bin/outreach.py` — Jina + GitHub contact resolution, SMTP, A/B templates |
| Research | `research-fetch`, `/research`, `/deep-research` |
| Monitoring | `agent-laptop/scripts/pipeline-liveness.sh` — 10 outcome checks |

So aibō is **not** a sixth pipeline. Building one would have been the single worst
thing to do to this box.

What was actually missing was a **partner**: something that reads all five, knows
who Wasif is, decides what only a human can decide, and can *reach him*.

The box's disease, in one line: **every alert channel is PULL.** A CRITICAL
"your Gmail password leaked" alert sat unread for 143 hours. A 7-day outage was
written into the daily brief seven times and read zero times. Writing to a file
the human never opens is not a notification. aibō's first job is to fix that.

## The four objects

**Facts** (`core/facts.py`) — what aibō knows about Wasif, *each with provenance*.
A fact with no source is a guess, and a guess about "do you require visa
sponsorship" goes into a real application under his real name. Guesses become Asks.

**Answers** (`core/answers.py`) — it does not keep a second answer bank. career-ops
already has one; a duplicate would drift within a week. aibō loads the **real** bank
and probes it with the **real** questions that have actually hard-stopped an
application, so coverage is measured, never assumed. It splits them:

- *fact* → "Are you legally authorized to work in Australia?" — aibō may answer.
- *consent* → "I agree to the Recruitment Privacy Policy." — aibō may **not**.
  Consent is a decision, not a lookup.

**Asks** (`core/asks.py`) — the one queue of things only Wasif can decide. An Ask
must be **blocking something real**. If nothing is blocked it is a log line, and it
does not get to interrupt him.

**Notify** (`core/notify.py`) — has a ladder and is honest about which rung it
reached. PUSH (ntfy armed) → lands on his phone. FILE (not armed) → *and it says so*.
It never reports a file write as a delivery.

## Commands

```
aibo brief      one screen: what happened, what is stuck, what needs you
aibo doctor     honest health — measured by outcome, never by "it ran"
aibo asks       the queue of human-only decisions   (--push to send it to his phone)
aibo answers    what the box gets asked, and what it may answer for him
aibo push       prove the phone channel works
aibo fix browser  install the guarded apply-browser reaper
```

`doctor` exits non-zero when anything is failing, so it is cron- and script-safe.

## What "outcome, not uptime" means

The old monitoring asked *"did the pipeline run?"* and answered **yes** for seven
days while box-apply died on a 404 every morning. Running is not succeeding. Every
check in `doctor` demands *evidence of an outcome* — an application submitted, a
draft written, a report produced — and treats silence as failure, never as health.

## What aibō will not do

- **Arm the push channel itself.** Doing so publishes alert text to ntfy.sh, a public
  third party. That is a consent gate, and flipping another person's consent gate for
  them is not aibō's call. It is one command: `~/agent-laptop/scripts/arm-push-alerts.sh`
- **Tick a consent checkbox.** See above.
- **Install a cron he did not ask for.**

The rule, inherited from the box's own design notes: **auto-fix plumbing, block on
contract.** Contract = bytes leaving under his name in a new shape.

## Layout

```
aibo/core/    paths · facts · answers · asks · doctor · notify
aibo/cli.py   the six commands
bin/aibo      entrypoint (uses aibo's own venv, never the caller's)
data/         asks.json — aibō's only state
```

aibō reads the other systems and writes only under its own root.
