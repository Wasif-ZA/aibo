"""aibō — 相棒, "partner".

The machine this was built for already had a job hunter, an email triager, an
outreach sender, a research fetcher and a liveness monitor. What it did not have
was anything that knew they existed. Five pipelines, five state files, five alert
channels, and not one of them could reach the single human they all depended on.

aibō is not a sixth pipeline. It is the layer that reads them all, works out what
only a human can decide, and pushes that -- and only that -- at you.

  aibo brief     one screen: what happened, what is stuck, what needs you
  aibo doctor    honest health, measured by outcome, never by "it ran"
  aibo asks      the queue of things only a human can answer
  aibo answers   what your tools get asked, and what it may answer for you
  aibo push      prove the phone channel works
  aibo fix       apply a staged plumbing fix
"""
from __future__ import annotations

import argparse
import subprocess
import sys

from .core import answers, asks, doctor, facts, notify

G, R, Y, B, DIM, X = "\033[32m", "\033[31m", "\033[33m", "\033[1m", "\033[2m", "\033[0m"


def _tick(ok: bool | None) -> str:
    if ok is None:
        return f"{DIM}n/a{X} "
    return f"{G}ok{X}  " if ok else f"{R}BAD{X} "


def cmd_doctor(_a) -> int:
    checks = doctor.run()
    bad = [c for c in checks if c.failed]
    live = [c for c in checks if c.ok is not None]
    print(f"\n{B}aibō doctor{X}  {DIM}— outcome, not uptime{X}\n")
    for c in checks:
        print(f"  {_tick(c.ok)} {c.name:<14} {c.detail}")
    print()
    if bad:
        print(f"  {R}{len(bad)} of {len(live)} checks failing.{X} Run {B}aibo asks{X} for what to do.\n")
    else:
        print(f"  {G}All {len(live)} applicable checks pass.{X}\n")
    return 1 if bad else 0


def cmd_asks(a) -> int:
    items = asks.collect()
    asks.save(items)

    if not items:
        print(f"\n  {G}Nothing needs you.{X}\n")
        return 0

    print(f"\n{B}aibō asks{X}  {DIM}— {len(items)} thing(s) only you can do{X}\n")
    for i, k in enumerate(items, 1):
        colour = R if k.severity == "critical" else (Y if k.severity == "blocking" else DIM)
        print(f"  {colour}{i}. [{k.severity}] {k.title}{X}")
        print(f"     {DIM}blocking:{X} {k.blocking}")
        print(f"     {B}do:{X} {k.action}")
        if k.detail:
            print(f"     {DIM}{k.detail}{X}")
        print()

    if a.push:
        body = "\n".join(f"{i}. {k.title}\n   -> {k.action}" for i, k in enumerate(items, 1))
        d = notify.notify(f"aibō: {len(items)} thing(s) need you", body, priority="high", tags="warning")
        print(f"  {G if d.reached_phone else Y}push: {d.detail}{X}\n")
    return 0


def cmd_answers(_a) -> int:
    cov = answers.coverage()
    print(f"\n{B}aibō answers{X}  {DIM}— questions that actually stopped an application{X}\n")

    if not cov["total"]:
        print(f"  {G}No application has been blocked by an unanswerable question recently.{X}\n")
        return 0

    for q in cov["answered"]:
        val = q.answer[0] if isinstance(q.answer, list) else q.answer
        print(f"  {G}can answer{X}  {q.label[:64]}")
        print(f"              {DIM}-> {str(val)[:64]}{X}")

    for q in cov["unanswered_facts"]:
        print(f"  {R}NO ANSWER{X}  {q.label[:64]}  {DIM}({q.company}){X}")
        print(f"              {DIM}a fact about you that aibō could not find. Add it to profile.yml.{X}")

    for q in cov["unanswered_consent"]:
        print(f"  {Y}YOUR CALL{X}  {q.label[:64]}  {DIM}({q.company}){X}")

    if cov["unanswered_consent"]:
        print(f"\n  {B}The {len(cov['unanswered_consent'])} 'your call' items are consent checkboxes,{X}")
        print("  not facts. aibō will not tick a privacy-policy or keep-my-resume-on-file box")
        print("  for you: consent is a decision, not a lookup. Tell it what you want once and")
        print("  it stops asking.\n")
    print()
    return 0


def cmd_brief(_a) -> int:
    checks = doctor.run()
    items = asks.collect()
    asks.save(items)
    bad = [c for c in checks if c.failed]
    live = [c for c in checks if c.ok is not None]
    f = facts.known()

    print(f"\n{B}aibō{X}  {DIM}partner — brief{X}\n")
    print(f"  Knows {len(f)} facts about you, each with a source.")
    print(f"  {len(live) - len(bad)}/{len(live)} systems healthy."
          f"{'' if not bad else '  ' + R + ', '.join(c.name for c in bad) + X}")
    print(f"  {len(items)} thing(s) need you"
          f"{'' if not items else ': ' + R + items[0].title + X}")
    print(f"\n  {DIM}aibo doctor · aibo asks · aibo answers{X}\n")
    return 0


def cmd_push(a) -> int:
    d = notify.notify("aibō", a.message or "If you can read this, the loop is closed.",
                      priority="default", tags="wave")
    if d.reached_phone:
        print(f"\n  {G}Delivered to your phone.{X}\n")
        return 0
    print(f"\n  {Y}Not delivered.{X} {d.detail}\n")
    return 1


def cmd_fix(a) -> int:
    if a.what == "browser":
        from .core import paths
        reaper = paths.AGENT_LAPTOP / "scripts" / "apply-browser-reaper.sh"
        if not reaper.exists():
            print(f"\n  {Y}No reaper script at {reaper}.{X}\n")
            return 1
        line = f"*/20 * * * * {reaper} >/dev/null 2>&1 # aibo browser-reaper (delete this line to disable)"
        cur = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        if "apply-browser-reaper" in cur:
            print("\n  Already installed.\n")
            return 0
        subprocess.run(["crontab", "-"], input=cur.rstrip("\n") + "\n" + line + "\n", text=True, check=True)
        print(f"\n  {G}Installed the guarded reaper (*/20).{X} It refuses to restart the browser")
        print("  during an apply window or while a form is parked for review.")
        print(f"  {DIM}Undo: crontab -e and delete the aibo browser-reaper line.{X}\n")
        return 0
    print(f"  unknown fix: {a.what}")
    return 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="aibo", description="aibō — your partner on this box")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("brief", help="one screen: state of everything").set_defaults(fn=cmd_brief)
    sub.add_parser("doctor", help="honest health, by outcome").set_defaults(fn=cmd_doctor)

    a = sub.add_parser("asks", help="what only you can do")
    a.add_argument("--push", action="store_true", help="also send it to your phone")
    a.set_defaults(fn=cmd_asks)

    sub.add_parser("answers", help="what the box may answer for you").set_defaults(fn=cmd_answers)

    pu = sub.add_parser("push", help="test the phone channel")
    pu.add_argument("message", nargs="?")
    pu.set_defaults(fn=cmd_push)

    fx = sub.add_parser("fix", help="apply a staged plumbing fix")
    fx.add_argument("what", choices=["browser"])
    fx.set_defaults(fn=cmd_fix)

    args = p.parse_args(argv)
    if not getattr(args, "fn", None):
        return cmd_brief(args)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
