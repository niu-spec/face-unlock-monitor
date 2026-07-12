import sys
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import Mock, patch

import numpy as np

from apps.detection.audio_service import AudioDetectionService


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

    def test_classify_transposes_log_mel_to_time_first(self):
        import torch

        service = AudioDetectionService()
        service._model = Mock(return_value=torch.zeros((1, 527)))
        service._compute_log_mel = Mock(
            return_value=np.zeros((64, 301), dtype=np.float32)
        )
        service._alert_type_indices = {}
        service._detect_fight_multilabel = Mock(return_value=0.0)

        service._classify_chunk(np.zeros(96000, dtype=np.float32))

        model_input = service._model.call_args.args[0]
        self.assertEqual(tuple(model_input.shape), (1, 1, 301, 64))


if __name__ == "__main__":
    main()
