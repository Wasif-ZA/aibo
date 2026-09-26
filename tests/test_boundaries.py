"""Boundary tests run against the invented demo box in examples/demo-box."""
import importlib
import io
import os
import shutil
import tempfile
import unittest
import urllib.request
from contextlib import redirect_stdout
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
