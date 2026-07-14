from unittest import TestCase

from apps.detection import audio_service as audio_service_module
from apps.detection.av_correlation import (
    AV_CORRELATION_CONFIG,
    CORRELATION_RULES,
    AVCorrelationBuffer,
)


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

    def test_correlation_window_covers_intrusion_cooldown(self):
        self.assertGreaterEqual(AV_CORRELATION_CONFIG["WINDOW_SECONDS"], 10.0)


class AudioServiceCorrelationInjectionTests(TestCase):
    def tearDown(self):
        audio_service_module._audio_service = None

    def test_get_audio_service_attaches_buffer_after_early_create(self):
        early = audio_service_module.get_audio_service()
        self.assertIsNone(early._av_correlation)

        buffer = AVCorrelationBuffer()
        again = audio_service_module.get_audio_service(av_correlation_buffer=buffer)

        self.assertIs(again, early)
        self.assertIs(again._av_correlation, buffer)
