"""
Unit tests verifying that all warnings, popups, and proctoring locks
are completely silenced once the exam is marked finished.
"""

import unittest
from unittest.mock import MagicMock
import numpy as np

from proctoring_system.logger import IncidentLogger
from proctoring_system.vision.vision_worker import VisionWorker


class TestExamFinishSilence(unittest.TestCase):

    def test_vision_worker_silenced(self):
        logger = MagicMock(spec=IncidentLogger)
        worker = VisionWorker(incident_logger=logger)
        worker.using_mock = True

        # When silence_incidents is True
        worker.silence_incidents = True

        # Process a blank frame (which would normally trigger NO_FACE violation)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        _, metrics = worker._process_frame(frame)

        self.assertEqual(metrics["status"], "NORMAL")
        self.assertEqual(metrics["warnings"], [])
        # Logger should never be called when silenced
        logger.log_incident.assert_not_called()

    def test_silence_incident_check(self):
        logger = MagicMock(spec=IncidentLogger)
        worker = VisionWorker(incident_logger=logger)
        worker.silence_incidents = True

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        from proctoring_system.logger import IncidentType
        worker._check_and_log_incident(IncidentType.LOOKING_AWAY, frame, {"duration": 2.0})

        logger.log_incident.assert_not_called()


if __name__ == "__main__":
    unittest.main()
