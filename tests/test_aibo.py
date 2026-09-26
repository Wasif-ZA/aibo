"""aibō's tests.

The important ones are not "does the code run" but "does aibō refuse to overstep".
A partner that quietly ticks a consent box on your behalf is worse than no partner,
so that boundary gets a test.
"""
import unittest

from aibo.core import answers, asks, notify
from tests.test_boundaries import DemoBox


class ConsentBoundary(unittest.TestCase):
    """aibō may state a fact about you. It may not give consent for you."""

    def test_consent_questions_are_recognised(self):
        for label in [
            "I agree to the Privacy Policy",
            "I consent to the collection, use and/or disclosure of my personal data",
            "You can choose to have us keep your resume on file for future opportunities",
            "I acknowledge the terms and conditions",
        ]:
            self.assertTrue(
                answers.CONSENT_RE.search(label),
                f"consent question not recognised, aibō might answer it: {label!r}",
            )

    def test_facts_are_not_mistaken_for_consent(self):
        for label in [
            "Are you legally authorized to work in Australia?",
            "Will you now or in the future require sponsorship?",
            "What is your email address?",
            "First name",
        ]:
            self.assertIsNone(
                answers.CONSENT_RE.search(label),
                f"a plain factual question was classed as consent: {label!r}",
            )


class AskDiscipline(unittest.TestCase):
    """An Ask must be blocking something real, and must rank by severity."""

    def test_severity_ordering(self):
        mk = lambda sev, t: asks.Ask(  # noqa: E731
            id=t, title=t, severity=sev, blocking="x", action="y", source="z",
            first_seen="2026-01-01T00:00:00",
        )
        got = sorted([mk("advisory", "c"), mk("critical", "a"), mk("blocking", "b")],
                     key=lambda a: a.sort_key())
        self.assertEqual([a.title for a in got], ["a", "b", "c"])

    def test_a_broken_collector_does_not_silence_the_others(self):
        def boom():
            raise RuntimeError("collector exploded")

        real = asks.COLLECTORS
        try:
            asks.COLLECTORS = (boom, lambda: [])
            out = asks.collect()
        finally:
            asks.COLLECTORS = real
        # It must surface its own blindness rather than report "nothing needs you".
        self.assertTrue(any("collector" in a.id for a in out))


class NotifyHonesty(DemoBox):
    """notify() must never report a file write as a delivery."""

    def test_non_latin1_title_does_not_kill_the_alert(self):
        """Regression: HTTP headers are latin-1, and "aibō" is not.

        This threw UnicodeEncodeError on the very first real push, meaning the
        alerter died on its own name and the alert was never sent. A monitor whose
        failure mode is silence is the one thing this project exists to prevent.
        """
        out = notify._header_safe("aibō: 2 things need you")
        out.encode("latin-1")                      # must not raise
        self.assertTrue(out.startswith("=?utf-8?"), f"expected RFC 2047, got {out!r}")
        # plain ASCII must pass through untouched, not get needlessly encoded
        self.assertEqual(notify._header_safe("plain title"), "plain title")

    def test_unarmed_channel_does_not_claim_to_have_reached_the_phone(self):
        real = notify.topic
        try:
            notify.topic = lambda: None
            d = notify.notify("t", "b")
        finally:
            notify.topic = real
        self.assertFalse(d.reached_phone)
        self.assertEqual(d.channel, "file")
        self.assertIn("arm", d.detail.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
