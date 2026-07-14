from unittest import TestCase

from apps.detection.av_correlation import CORRELATION_RULES


class AVCorrelationRulesTests(TestCase):
    def test_only_crying_and_glass_break_audio_rules_are_enabled(self):
        audio_types = set().union(*(audio for audio, *_ in CORRELATION_RULES))
        rule_pairs = {(frozenset(audio), frozenset(video)) for audio, video, *_ in CORRELATION_RULES}

        self.assertEqual(audio_types, {"CRYING", "GLASS_BREAK"})
        self.assertEqual(
            rule_pairs,
            {
                (frozenset({"CRYING"}), frozenset({"FALL"})),
                (frozenset({"CRYING"}), frozenset({"INTRUSION"})),
                (frozenset({"GLASS_BREAK"}), frozenset({"FALL"})),
                (frozenset({"GLASS_BREAK"}), frozenset({"INTRUSION"})),
            },
        )
