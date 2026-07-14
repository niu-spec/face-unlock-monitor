import sys
from contextlib import nullcontext
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import Mock, patch

import numpy as np

from apps.detection.audio_service import (
    AUDIO_SERVICE_CONFIG,
    AudioDetectionService,
    _prepare_panns_input,
)


class FakeTensor:
    """Minimal tensor surface used by AudioDetectionService._classify_chunk."""

    def __init__(self, values):
        self.values = np.asarray(values)

    @property
    def shape(self):
        return self.values.shape

    def float(self):
        return self

    def squeeze(self, axis):
        return FakeTensor(np.squeeze(self.values, axis=axis))

    def numpy(self):
        return self.values

    def cpu(self):
        return self


def _fake_sigmoid(x):
    """Element-wise sigmoid that works with FakeTensor or numpy."""
    import numpy as np
    values = x.values if hasattr(x, "values") else np.asarray(x)
    return FakeTensor(1.0 / (1.0 + np.exp(-values)))


class AudioDetectionServiceTests(TestCase):
    def test_load_uses_fallback_when_github_is_unavailable(self):
        service = AudioDetectionService()
        service._github_available = Mock(return_value=False)
        service._load_panns_fallback = Mock()
        hub_load = Mock()
        fake_torch = SimpleNamespace(hub=SimpleNamespace(load=hub_load))

        with patch.dict(sys.modules, {"torch": fake_torch}):
            service._load_panns_model()

        hub_load.assert_not_called()
        service._load_panns_fallback.assert_called_once_with()

    def test_prepare_panns_input_transposes_log_mel_to_time_first(self):
        log_mel = np.zeros((64, 301), dtype=np.float32)

        model_input = _prepare_panns_input(log_mel)

        self.assertEqual(model_input.shape, (1, 1, 301, 64))
        self.assertEqual(model_input.dtype, log_mel.dtype)
        self.assertTrue(model_input.flags.c_contiguous)

    def test_log_mel_uses_panns_decibel_scale(self):
        service = AudioDetectionService()
        mel = np.ones((64, 2), dtype=np.float64)
        power_to_db = Mock(return_value=np.full((64, 2), -20.0))
        fake_librosa = SimpleNamespace(
            feature=SimpleNamespace(melspectrogram=Mock(return_value=mel)),
            power_to_db=power_to_db,
        )

        with patch.dict(sys.modules, {"librosa": fake_librosa}):
            output = service._compute_log_mel(np.zeros(1024, dtype=np.float32))

        power_to_db.assert_called_once_with(
            mel, ref=1.0, amin=1e-10, top_db=None
        )
        self.assertEqual(output.dtype, np.float32)
        self.assertTrue(np.all(output == -20.0))

    def test_audio_alerts_use_very_low_thresholds(self):
        self.assertEqual(AUDIO_SERVICE_CONFIG["AUDIO_MULTI_LABEL_THRESHOLD"], 0.01)
        self.assertEqual(
            AUDIO_SERVICE_CONFIG["AUDIO_CONFIDENCE_THRESHOLDS"],
            {
                "SCREAM": 0.01,
                "CRYING": 0.01,
                "GLASS_BREAK": 0.01,
                "FIGHT": 0.01,
            },
        )
        self.assertEqual(AUDIO_SERVICE_CONFIG["CRYING_CONSECUTIVE_FRAMES"], 1)

    def test_classify_converts_numpy_input_to_torch_tensor_at_inference(self):
        service = AudioDetectionService()
        service._model = Mock(return_value=FakeTensor(np.zeros((1, 527))))
        service._compute_log_mel = Mock(
            return_value=np.zeros((64, 301), dtype=np.float32)
        )
        service._alert_type_indices = {}
        service._detect_fight_multilabel = Mock(return_value=(0.0, 0.0, 0.0))
        fake_torch = SimpleNamespace(
            from_numpy=FakeTensor,
            no_grad=nullcontext,
            sigmoid=_fake_sigmoid,
        )

        with patch.dict(sys.modules, {"torch": fake_torch}):
            service._classify_chunk(np.zeros(96000, dtype=np.float32))

        model_input = service._model.call_args.args[0]
        self.assertEqual(tuple(model_input.shape), (1, 1, 301, 64))


if __name__ == "__main__":
    main()
