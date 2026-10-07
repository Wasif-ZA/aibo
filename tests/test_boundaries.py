"""Boundary tests run against the invented demo box in examples/demo-box."""
import importlib
import io
import os
import shutil
import subprocess
import tempfile
import unittest
import urllib.request
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest import mock

from aibo import cli
from aibo.core import answers, asks, doctor, facts, notify, paths

DEMO = Path(__file__).resolve().parents[1] / "examples" / "demo-box"


class DemoBox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.agent = Path(self.tmp) / "agent-laptop"
        shutil.copytree(DEMO / "agent-laptop", self.agent)
        env = {
            "AIBO_HOME": str(Path(self.tmp) / "home"),
            "AIBO_TODAY": "2026-09-26",
            "AIBO_CAREER_OPS": str(DEMO / "career-ops"),
            "AIBO_AGENT_HOME": str(self.agent),
        }
        self.env = mock.patch.dict(os.environ, env)
        self.env.start()
        importlib.reload(paths)

    def tearDown(self):
        self.env.stop()
        importlib.reload(paths)
        shutil.rmtree(self.tmp, ignore_errors=True)


class ConsentNeverAnswered(DemoBox):
    def test_consent_stays_unanswered_even_when_the_bank_has_an_answer(self):
        cov = answers.coverage()
        consent = {q.label for q in cov["unanswered_consent"]}
        self.assertIn("I agree to the Recruitment Privacy Policy", consent)
        self.assertFalse([q for q in cov["answered"] if q.kind == "consent"])

    def test_missing_bank_is_a_failure_not_a_clean_bill(self):
        with mock.patch.object(paths, "CAREER_OPS", Path(self.tmp)):
            cov = answers.coverage()
        self.assertTrue(cov["failed"])

    def test_consent_phrasings_never_reach_the_answer_bank(self):
        consent_labels = [
            "Do you consent to a background check?",
            "Do you agree to the applicant terms?",
            "I authorize Example Corp to contact my references",
            "I acknowledge the applicant declaration",
            "May we have permission to retain your details?",
            "Accept the terms and conditions",
            "Please review the privacy notice",
            "Are you willing to complete a background check?",
        ]
        fact_label = "Are you legally authorized to work in Australia?"
        applied_log = Path(self.tmp) / "auto-applied-log.tsv"
        labels = "; ".join([*consent_labels, fact_label])
        applied_log.write_text(
            "2026-09-26T08:00\tauto\tExample Corp\tRole\thttps://example.test\t"
            f"hard-stop\thard-stop:unknown_required_field ({labels})\n",
            encoding="utf-8",
        )
        bank = mock.Mock()
        bank.answer_for.return_value = "Yes"

        with (
            mock.patch.object(paths, "CO_APPLIED_LOG", applied_log),
            mock.patch.object(answers, "_bank", return_value=bank),
        ):
            questions = {q.label: q for q in answers.blocking_questions()}

        for label in consent_labels:
            with self.subTest(label=label):
                self.assertEqual(questions[label].kind, "consent")
                self.assertIsNone(questions[label].answer)
        self.assertEqual(questions[fact_label].kind, "fact")
        self.assertEqual(questions[fact_label].answer, "Yes")
        bank.answer_for.assert_called_once_with(fact_label, {})

    def test_missing_application_log_is_an_unavailable_failure(self):
        missing = Path(self.tmp) / "missing-auto-applied-log.tsv"
        with mock.patch.object(paths, "CO_APPLIED_LOG", missing):
            cov = answers.coverage()
        self.assertTrue(cov["failed"])
        self.assertIn("applied log", cov["unavailable"])


class FactsCarryProvenance(DemoBox):
    def test_every_fact_names_its_source(self):
        known = facts.known()
        self.assertIn("full_name", known)
        for f in known.values():
            self.assertTrue(f.source.strip(), f"fact {f.key} has no source")


class SilenceIsFailure(DemoBox):
    def test_installed_but_silent_pipeline_fails(self):
        with mock.patch.object(paths, "CO_APPLIED_LOG", Path(self.tmp) / "missing.tsv"):
            self.assertIs(doctor.applications_submitted().ok, False)

    def test_running_without_submitting_fails(self):
        self.assertIs(doctor.job_hunt_ran().ok, True)
        self.assertIs(doctor.applications_submitted().ok, False)

    def test_absent_system_is_not_applicable(self):
        with mock.patch.object(paths, "CAREER_OPS", Path(self.tmp) / "nope"):
            self.assertIsNone(doctor.applications_submitted().ok)

    def test_unsupported_platform_check_is_not_a_false_ok(self):
        with mock.patch.object(doctor.shutil, "which", return_value=None):
            self.assertIsNone(doctor.memory_pressure().ok)
            self.assertEqual(asks._leaked_browser(), [])

    def test_memory_check_requires_proc_meminfo_even_when_pgrep_exists(self):
        with (
            mock.patch.object(doctor, "renderer_count", return_value=3),
            mock.patch.object(doctor, "_mem_available_mb", return_value=None),
        ):
            result = doctor.memory_pressure()
        self.assertIsNone(result.ok)
        self.assertIn("not available on this platform", result.detail)

    def test_yesterdays_email_report_is_valid_only_before_seven(self):
        agent = Path(self.tmp) / "triage-agent"
        reports = agent / "reports"
        reports.mkdir(parents=True)
        (reports / "email-triage-2026-09-25.md").write_text("done\n", encoding="utf-8")

        with mock.patch.object(paths, "AGENT_LAPTOP", agent):
            with mock.patch.object(paths, "now", return_value=datetime(2026, 9, 26, 6, 59)):
                self.assertIs(doctor.email_drafts().ok, True)
            with mock.patch.object(paths, "now", return_value=datetime(2026, 9, 26, 7, 0)):
                self.assertIs(doctor.email_drafts().ok, False)


class BrowserFixProtectsCrontab(DemoBox):
    def setUp(self):
        super().setUp()
        scripts = self.agent / "scripts"
        scripts.mkdir(exist_ok=True)
        (scripts / "apply-browser-reaper.sh").write_text("#!/bin/sh\n", encoding="utf-8")

    def test_crontab_read_failure_aborts_without_writing(self):
        failed = subprocess.CompletedProcess(
            ["crontab", "-l"], 1, stdout="", stderr="permission denied"
        )
        with (
            mock.patch.object(cli.shutil, "which", return_value="/usr/bin/crontab"),
            mock.patch.object(cli.subprocess, "run", return_value=failed) as run,
            redirect_stdout(io.StringIO()) as out,
        ):
            code = cli.cmd_fix(mock.Mock(what="browser"))

        self.assertEqual(code, 1)
        run.assert_called_once_with(["crontab", "-l"], capture_output=True, text=True)
        self.assertIn("permission denied", out.getvalue())

    def test_no_existing_crontab_is_treated_as_empty(self):
        missing = subprocess.CompletedProcess(
            ["crontab", "-l"], 1, stdout="", stderr="no crontab for test-user"
        )
        installed = subprocess.CompletedProcess(["crontab", "-"], 0)
        with (
            mock.patch.object(cli.shutil, "which", return_value="/usr/bin/crontab"),
            mock.patch.object(cli.subprocess, "run", side_effect=[missing, installed]) as run,
            redirect_stdout(io.StringIO()),
        ):
            code = cli.cmd_fix(mock.Mock(what="browser"))

        self.assertEqual(code, 0)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[1].args, (["crontab", "-"],))
        self.assertIn("apply-browser-reaper", run.call_args_list[1].kwargs["input"])


class UnarmedPushIsNotDelivery(DemoBox):
    def test_unarmed_push_exits_nonzero_and_never_opens_a_url(self):
        self.assertFalse(notify.armed())
        with mock.patch.object(urllib.request, "urlopen") as net, redirect_stdout(io.StringIO()) as out:
            code = cli.main(["push"])
        net.assert_not_called()
        self.assertEqual(code, 1)
        self.assertIn("Not delivered", out.getvalue())
        self.assertIn(str(paths.NTFY_TOPIC_FILE), out.getvalue())


class CrashingCollectorFilesAnAsk(DemoBox):
    def test_crash_becomes_an_ask_and_others_still_run(self):
        def boom():
            raise RuntimeError("collector exploded")

        with mock.patch.object(asks, "COLLECTORS", (boom, asks._unarmed_push)):
            out = asks.collect()
        ids = {a.id for a in out}
        self.assertIn("collector-error-boom", ids)
        self.assertIn("arm-push", ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class HeaderSafe(unittest.TestCase):
    def test_long_non_latin_title_stays_one_header_line(self):
        from email.header import decode_header
        title = "aibō: " + "x" * 120
        out = notify._header_safe(title)
        self.assertNotIn("\n", out)
        self.assertEqual(decode_header(out)[0][0].decode(), title)
