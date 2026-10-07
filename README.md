<p align="center">
  <a href="#try-it-in-30-seconds"><strong>Try it</strong></a> &middot;
  <a href="#commands"><strong>Commands</strong></a> &middot;
  <a href="#how-it-works"><strong>How it works</strong></a> &middot;
  <a href="#configuration"><strong>Configuration</strong></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/dependencies-pyyaml-1a7f64" alt="One dependency: pyyaml">
  <img src="https://img.shields.io/badge/tested%20on-Windows%2011-0078D4" alt="Tested on Windows 11">
  <img src="https://img.shields.io/badge/status-v0.1-c47f00" alt="v0.1">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT">
</p>

<br>

```
aibō doctor  — outcome, not uptime

  BAD  push           NOT armed. Every alert is a file you must remember to open.
  BAD  alerts         35 lines unread, oldest unacked 143h.
  ok   applications   3 submitted in 7d (most recent 2026-07-11)
  BAD  job-hunt       ran, but 1 stage(s) FAILED
  ok   email-triage   produced email-triage-2026-07-14.md
  BAD  memory         43 leaked renderers, 2068MB available. The box is swapping.
```

<p align="center"><i>The first time it ran: four of six red, while every system said "fine".</i></p>

<br>

# aibō knows who you are, so your tools stop asking.

An assistant layer over the automations you already run. *aibō (相棒): partner.*

**If your automations are the _crew_, aibō is the _partner_ who knows your answers and when to call you.**

An always-on box ran six job-search systems: a scraper, a scorer, an auto-applier, an email
triager, an outreach sender and a monitor. All of them worked. For six days it applied to zero
jobs. The applier stopped at "Are you legally authorized to work in this country?" every
morning. The alert saying so sat unread in a text file for 143 hours.

aibō fixes the two real failures: nothing knew who you were, and nothing could reach you.

**Stop being asked what you already said.**

|        | Step         | Example                                                    |
| ------ | ------------ | ---------------------------------------------------------- |
| **01** | Install it   | _`pip install -e .`_                                       |
| **02** | Check health | _`aibo doctor`_                                            |
| **03** | Clear asks   | _`aibo asks --push` sends what only you can decide to your phone._ |

> [!TIP]
> **🤝 Or hand it to your agent.** Paste this into Claude Code or Codex:
>
> ```text
> Clone https://github.com/Wasif-ZA/aibo, make a venv, run `pip install -e .`,
> then run `aibo doctor` against examples/demo-box with AIBO_TODAY=2026-09-26,
> AIBO_CAREER_OPS=examples/demo-box/career-ops and AIBO_AGENT_HOME=examples/demo-box/agent-laptop.
> ```

<br>

## aibō is right for you if

- ✅ You run **automations that ask you the same questions** in forms
- ✅ Your monitoring says **"it ran"** while nothing actually got done
- ✅ Your alerts land in **files nobody opens**
- ✅ You want answers given for you **only when you said them first**
- ✅ You never want a tool to **tick a consent box** on your behalf

<br>

## Problems aibō solves

| Without aibō | With aibō |
| --- | --- |
| ❌ A form asks a question already answered in your config, and the application is thrown away. | ✅ `aibo answers` finds where you said it and answers with the source. |
| ❌ The monitor reports green because the pipeline ran. | ✅ `aibo doctor` needs evidence of an outcome. Silence is failure. |
| ❌ A critical alert waits 143 hours in a text file. | ✅ `aibo push` proves the channel works; `notify` never calls a file write a delivery. |
| ❌ A tool quietly agrees to a privacy policy as you. | ✅ Consent is never a fact. aibō refuses, and a test covers it. |
| ❌ Ten small notices bury the one that matters. | ✅ An Ask must name what it is blocking, or it stays a log line. |

<br>

## Why aibō is different

|                                  |                                                                       |
| -------------------------------- | --------------------------------------------------------------------- |
| **Facts carry provenance.**      | Every fact records where it was learned. No source, no answer.        |
| **Outcomes, not uptime.**        | A check passes on a submitted application, not a finished run.        |
| **Fact and consent are split.**  | It may answer a fact you stated. It never gives consent.              |
| **Auto-fix plumbing, block on contract.** | It fixes a leaked process. Anything leaving under your name waits for you. |
| **Not a seventh pipeline.**      | It sits over your existing systems and keeps no second answer bank.   |

<br>

## Try it in 30 seconds

`examples/demo-box/` is a fake box: an invented person, invented companies, invented alerts.

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

You will see the job hunt ran today while zero applications went in. `aibo answers` shows a
consent box it could fill and refuses to. `aibo push` says "Not delivered", because the demo has
no push channel.

## Commands

| You want to | Run |
| --- | --- |
| One screen: what happened, what is stuck, what needs you | `aibo brief` |
| Health, measured by outcome | `aibo doctor` |
| The queue only you can decide | `aibo asks` (`--push` to your phone) |
| What tools get asked, and what aibō may answer | `aibo answers` |
| Prove notifications reach you | `aibo push` |

`aibo doctor` exits non-zero when anything fails, so it drops into cron or CI.

## How it works

<details>
<summary>Open: the five core files</summary>

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

`answers.py` loads your job-search tool's real answer bank and probes it with the real questions
that stopped an application. Coverage is measured, never assumed.

</details>

## Configuration

<details>
<summary>Open: where aibō looks for your systems</summary>

| Variable | Default | What |
|---|---|---|
| `AIBO_HOME` | the repo checkout, else `~/.aibo` | aibō's own state |
| `AIBO_CAREER_OPS` | `~/projects/career-ops-sydney` | a [career-ops](https://github.com/santifer/career-ops) checkout |
| `AIBO_AGENT_HOME` | `~/agent-laptop` | automation root (alerts, scripts, reports) |
| `AIBO_VAULT` | `~/box-vault` | notes vault |
| `AIBO_TODAY` | unset (real clock) | pin "today" to a `YYYY-MM-DD`, for the demo and tests |

Missing systems drop out quietly. A collector that crashes files an Ask against itself.

</details>

## Platforms

<details>
<summary>Open: Windows tested, two Linux-only checks</summary>

- **Windows 11**: tested against the demo box.
- **Linux only**: the memory check needs `pgrep` and `/proc`; `aibo fix browser` needs
  `crontab`. On other platforms both say so and do nothing.

</details>

## Status

v0.1. Built against one box, then made to install anywhere. The adapters still assume a
career-ops checkout and an agent-laptop style alerts folder.

Tests: `python -m unittest -v` (standard library only).

## License

MIT.
