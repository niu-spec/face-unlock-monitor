from unittest.mock import patch
import json

from django.test import SimpleTestCase

from apps.video_stream.services import (
    ensure_worker_for_query,
    resolve_video_stream_id,
)


class ResolveVideoStreamIdTests(SimpleTestCase):
    def test_video_layer_ids(self):
        self.assertEqual(resolve_video_stream_id("1"), "1")
        self.assertEqual(resolve_video_stream_id("2"), "2")

    def test_business_layer_ids(self):
        self.assertEqual(resolve_video_stream_id("living_room"), "1")
        self.assertEqual(resolve_video_stream_id("kitchen"), "2")

    def test_empty(self):
        self.assertIsNone(resolve_video_stream_id(None))
        self.assertIsNone(resolve_video_stream_id(""))


class EnsureWorkerForQueryTests(SimpleTestCase):
    @patch("apps.video_stream.services.get_worker")
    def test_starts_worker_for_video_stream_id(self, mock_get_worker):
        ensure_worker_for_query("2")
        mock_get_worker.assert_called_once_with("2")

    @patch("apps.video_stream.services.get_worker")
    def test_starts_worker_for_business_stream_id(self, mock_get_worker):
        ensure_worker_for_query("kitchen")
        mock_get_worker.assert_called_once_with("2")

    @patch("apps.video_stream.services.get_worker")
    def test_skips_invalid_stream_id(self, mock_get_worker):
        ensure_worker_for_query("not-a-stream")
        mock_get_worker.assert_not_called()


class VideoStatusViewTests(SimpleTestCase):
    @patch("apps.video_stream.views.ensure_worker_for_query")
    @patch("apps.face.services.get_face_service")
    @patch("apps.video_stream.views.get_liveness_status", return_value={})
    @patch("apps.video_stream.views.get_workers_status", return_value={})
    def test_status_triggers_worker(
        self,
        _mock_workers,
        _mock_liveness,
        mock_face_service,
        mock_ensure_worker,
    ):
        mock_face_service.return_value.get_presence.return_value = {}
        mock_face_service.return_value.get_all_presence.return_value = {}

        from django.test import RequestFactory

        from apps.video_stream.views import video_status

        request = RequestFactory().get("/api/video/status", {"stream_id": "2"})
        response = video_status(request)

        self.assertEqual(response.status_code, 200)
        mock_ensure_worker.assert_called_once_with("2")


class VideoPresenceViewTests(SimpleTestCase):
    @patch("apps.video_stream.views.ensure_worker_for_query")
    @patch("apps.face.services.get_face_service")
    @patch("apps.video_stream.views.get_liveness_status", return_value={"kitchen": {"status": "passed"}})
    @patch("apps.video_stream.services.worker_presence_is_stale", return_value=False)
    @patch(
        "apps.video_stream.views.get_workers_status",
        return_value={"2": {"last_frame_at": 1.0}},
    )
    def test_presence_returns_lightweight_payload(
        self,
        _mock_workers,
        _mock_liveness,
        mock_face_service,
        mock_ensure_worker,
    ):
        mock_face_service.return_value.get_presence.return_value = {
            "total": 1,
            "stream_id": "kitchen",
        }

        from django.test import RequestFactory

        from apps.video_stream.views import video_presence

        request = RequestFactory().get("/api/video/presence", {"stream_id": "2"})
        response = video_presence(request)
        payload = json.loads(response.content.decode())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["presence"]["total"], 1)
        self.assertTrue(payload["stream_live"])
        self.assertEqual(payload["liveness"]["status"], "passed")
        self.assertIsNotNone(payload["last_frame_at"])
        mock_ensure_worker.assert_called_once_with("2")
