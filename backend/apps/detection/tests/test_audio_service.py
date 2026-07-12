import sys
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import Mock, patch

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


if __name__ == "__main__":
    main()
