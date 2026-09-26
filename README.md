<div align="center">

# aibō 相棒

**An assistant that knows who you are, so your tools stop asking.**

*aibō (n.) — partner; the one who works alongside you.*

</div>

---

## The problem it was built for

I have an always-on Linux box that job-hunts for me. It has a job scraper, a
fit-scoring council, an auto-applier that drives a real browser, an email triager,
a cold-outreach sender, and a liveness monitor. Six systems. All of them work.

For six days straight, it applied to **zero jobs**.

Not because anything crashed. The pipeline ran every morning, found roles, scored
them, opened the forms, and filled in thirteen of twenty fields. Then it hit a
question it had no answer for — *"Are you legally authorized to work in this
country?"* — and threw the application away. Every morning. While a critical alert
telling me so sat unread in a text file for **143 hours**.

Two failures, and neither is a bug in any of those six systems:

1. **Nothing knew who I was.** The answer to that question was already written down
   — in a config file, and in my own words in four applications I'd already sent.
   No system thought to look.
2. **Nothing could reach me.** Every alert channel was *pull*. Writing to a file
   that nobody opens is not a notification.

aibō is the layer that fixes both. It is deliberately **not** a seventh pipeline.

## What it does

```
aibo brief      one screen: what happened, what is stuck, what needs you
aibo doctor     honest health — measured by outcome, never by "it ran"
aibo asks       the queue of things only a human can decide  (--push to your phone)
aibo answers    what your tools get asked, and what aibō may answer for you
aibo push       prove the notification channel actually works
```

## Four ideas, and they are the whole design

### 1. Facts carry provenance

aibō knows things about you. Every one of them records *where it learned it*.

A fact with no source is a guess — and a guess about *"do you require visa
sponsorship?"* goes into a real application, under your real name, to a real
employer. So aibō is allowed to answer on your behalf **only when it can point at
where you already said it**. Everything else becomes a question for you.

### 2. It measures outcomes, not uptime

The monitoring this replaced asked *"did the pipeline run?"* and cheerfully answered
**yes** for seven days while the applier died on a 404 every single morning.

Running is not succeeding. Every check in `aibo doctor` demands **evidence of an
outcome** — an application actually submitted, a draft actually written — and treats
silence as failure, never as health.

```
aibō doctor  — outcome, not uptime

  BAD  push           NOT armed. Every alert is a file you must remember to open.
  BAD  alerts         35 lines unread, oldest unacked 143h.
  ok   applications   3 submitted in 7d (most recent 2026-07-11)
  BAD  job-hunt       ran, but 1 stage(s) FAILED
  ok   email-triage   produced email-triage-2026-07-14.md
  BAD  memory         43 leaked renderers, 2068MB available. The box is swapping.
```

That output is from the first time it ever ran. Four of six, red. Nothing was on
fire; everything was "fine".

### 3. It will not give consent for you

When aibō meets a question a tool couldn't answer, it sorts it into one of two piles:

| | | aibō may answer? |
|---|---|---|
| **Fact** | *"Are you authorized to work in Australia?"* | **Yes** — you've stated it, it has the receipt |
| **Consent** | *"I agree to the Recruitment Privacy Policy."* | **No** |

Consent is not a fact about you to be looked up. It is a decision to be made. An
assistant that quietly ticks that box on your behalf is worse than no assistant, so
that boundary is enforced in code and covered by a test.

### 4. An Ask must be blocking something real

`aibo asks` is the single queue of things only a human can resolve. Every entry has
to name **what is not happening because it is unanswered.** If nothing is blocked,
it is a log line, and it does not get to interrupt you.

And `notify` is honest about whether it actually reached you. If no push channel is
armed, it says *"this is sitting in a file you have to remember to open"* — it never
reports a file write as a delivery. That distinction is the entire reason the 143
hours happened.

## The rule it follows

> **Auto-fix plumbing. Block on contract.**

Plumbing is a leaked process, a stringified list, a stale lock — fix it, say so.
**Contract is bytes leaving under your name in a new shape.** That always waits for
a human. In its first hour aibō fixed a bug that was silently destroying every job
application, and it *declined* to arm a notification channel, tick a consent box, or
install a cron job, because those were not its call to make.

## Try it in 30 seconds

`examples/demo-box/` is a fake box: an invented person, invented companies, invented
alerts. Point aibo at it and every command shows real outcome-based output.

```bash
git clone https://github.com/Wasif-ZA/aibo && cd aibo
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .
export AIBO_TODAY=2026-09-26 AIBO_CAREER_OPS=examples/demo-box/career-ops AIBO_AGENT_HOME=examples/demo-box/agent-laptop
aibo doctor
```

PowerShell:

```powershell
$env:AIBO_TODAY="2026-09-26"; $env:AIBO_CAREER_OPS="examples/demo-box/career-ops"; $env:AIBO_AGENT_HOME="examples/demo-box/agent-laptop"
aibo doctor
```

`AIBO_TODAY` pins the clock to the fixture's dates. You will see the job hunt *ran*
today while *zero* applications were submitted, which is the whole point of measuring
outcomes. `aibo answers` shows one consent checkbox the fake answer bank *could*
answer, and aibo refusing to. `aibo push` says "Not delivered": the demo has no push
channel, and aibo never calls a file write a delivery.

## Install

With uv:

```bash
uv venv && uv pip install -e .
.venv/bin/aibo brief          # Windows: .venv\Scripts\aibo brief
```

With plain pip:

```bash
python -m venv .venv && .venv/bin/pip install -e .     # Windows: .venv\Scripts\pip install -e .
.venv/bin/aibo brief
```

`bin/aibo` also runs it from a checkout without activating the venv.
`aibo doctor` exits non-zero when anything is failing, so it drops straight into cron
or CI.

Tests use the standard library only:

```bash
python -m unittest -v
```

**Windows.** Everything runs. Two parts are Linux-only and say so instead of
guessing: the memory check needs `pgrep` and `/proc` (it shows `n/a  not available on
this platform`), and `aibo fix browser` needs `crontab` (it refuses and installs
nothing).

## Configuration

aibō is an integration layer, so the one machine-specific thing about it is *where
the systems it federates over live*. All env-overridable, nothing baked in:

| Variable | Default | What |
|---|---|---|
| `AIBO_HOME` | the repo checkout, else `~/.aibo` | where aibo keeps its own state |
| `AIBO_CAREER_OPS` | `~/projects/career-ops-sydney` | a [career-ops](https://github.com/santifer/career-ops) job-search checkout |
| `AIBO_AGENT_HOME` | `~/agent-laptop` | automation root (alerts, scripts, reports) |
| `AIBO_VAULT` | `~/box-vault` | notes vault |
| `AIBO_TODAY` | unset (real clock) | pin "today" to a `YYYY-MM-DD`, for the demo and tests |

Collectors degrade quietly: point aibō at a box with no career-ops and the job checks
simply drop out. A collector that *crashes*, though, files an Ask against itself —
because a monitor that has gone blind must never report "nothing needs you."

## Layout

```
aibo/core/
  facts.py     what it knows about you, each with a source
  answers.py   what your tools get asked, and which of those it may answer
  asks.py      the human-only queue
  doctor.py    health, by outcome
  notify.py    delivery, honestly reported
aibo/cli.py    the commands
tests/         the boundaries that matter
```

`answers.py` deliberately keeps **no second copy** of the answer bank. Your job-search
tool already has one; a duplicate would drift within a week. aibō loads the *real*
bank and probes it with the *real* questions that actually stopped an application, so
coverage is always measured and never assumed.

## Status

v0.1, and honest about it. Built in one session against one box, then made to
install and run anywhere. Tested on Windows 11 against the demo box; the adapters still
assume a career-ops checkout and an agent-laptop style alerts folder, and they drop
out quietly when those are absent. The memory check and `aibo fix browser` are
Linux-only and report that rather than guessing.

MIT.
