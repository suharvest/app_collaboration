"""
Face Enrollment Logic - Collect embeddings and store averaged result

Domain-specific logic for face enrollment:
1. Register as frame callback on SerialCameraSession
2. Collect N seconds of high-confidence embeddings
3. Average and normalize the collected embeddings
4. Store via SerialCrudClient
"""

import logging
import math
import time
from typing import List, Optional

logger = logging.getLogger(__name__)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _average_embeddings(embeddings: List[List[float]]) -> List[float]:
    """Average and L2-normalize a list of embedding vectors."""
    if not embeddings:
        return []

    dim = len(embeddings[0])
    avg = [0.0] * dim
    for emb in embeddings:
        for i in range(dim):
            avg[i] += emb[i]

    n = len(embeddings)
    avg = [v / n for v in avg]

    # L2 normalize
    norm = math.sqrt(sum(v * v for v in avg))
    if norm > 0:
        avg = [v / norm for v in avg]

    return avg


class FaceEnrollmentSession:
    """Collects face embeddings over a time window and stores the result.

    Usage:
        enrollment = FaceEnrollmentSession(camera_session, crud_client, "Alice")
        enrollment.start()
        # ... frames arrive, enrollment progresses ...
        # When done, enrollment.result is set
    """

    def __init__(
        self,
        camera_session,  # SerialCameraSession
        crud_client,  # SerialCrudClient
        name: str,
        duration: float = 5.0,
        min_samples: int = 3,
        min_confidence: float = 0.5,
    ):
        self.camera_session = camera_session
        self.crud_client = crud_client
        self.name = name
        self.duration = duration
        self.min_samples = min_samples
        self.min_confidence = min_confidence

        self._samples: List[List[float]] = []
        self._start_time: Optional[float] = None
        self._active = False
        self.result: Optional[dict] = None  # {ok, error?}

    @property
    def active(self) -> bool:
        return self._active

    def start(self):
        """Start collecting embeddings."""
        self._active = True
        self._start_time = time.time()
        self._samples = []
        self.result = None

        # Update enrollment state on camera session
        self._update_state()

        # Register frame callback
        self.camera_session.add_frame_callback(self._on_frame)
        logger.info("Enrollment started for '%s' (%.1fs)", self.name, self.duration)

    def cancel(self):
        """Cancel enrollment."""
        self._active = False
        self.camera_session.remove_frame_callback(self._on_frame)
        self.camera_session.enrollment_state = None
        self.result = {"ok": False, "error": "cancelled"}
        logger.info("Enrollment cancelled for '%s'", self.name)

    def _on_frame(self, frame: dict):
        """Frame callback - collect high-confidence embeddings."""
        if not self._active:
            return

        elapsed = time.time() - self._start_time
        if elapsed >= self.duration:
            self._finish()
            return

        # Collect embeddings from detected faces
        for face in frame.get("faces", []):
            confidence = face.get("confidence", 0)
            if confidence < self.min_confidence:
                continue

            embedding = face.get("embedding", [])
            if isinstance(embedding, list) and len(embedding) > 0:
                self._samples.append(embedding)

        self._update_state()

    def _update_state(self):
        """Update enrollment state on camera session for WebSocket broadcast."""
        if not self._active:
            self.camera_session.enrollment_state = None
            return

        elapsed = time.time() - self._start_time
        remaining = max(0, self.duration - elapsed)

        self.camera_session.enrollment_state = {
            "active": True,
            "name": self.name,
            "samples": len(self._samples),
            "min_samples": self.min_samples,
            "remaining_seconds": round(remaining, 1),
        }

    def _finish(self):
        """Finalize enrollment - average embeddings and prepare result."""
        self._active = False
        self.camera_session.remove_frame_callback(self._on_frame)
        # Signal completion to frontend (keep broadcasting active=False for a few frames)
        self.camera_session.enrollment_state = {
            "active": False,
            "name": self.name,
            "samples": len(self._samples),
            "min_samples": self.min_samples,
            "remaining_seconds": 0,
        }

        if len(self._samples) < self.min_samples:
            self.result = {
                "ok": False,
                "error": f"Only {len(self._samples)} samples collected, need at least {self.min_samples}",
            }
            logger.warning(
                "Enrollment failed for '%s': insufficient samples (%d/%d)",
                self.name,
                len(self._samples),
                self.min_samples,
            )
            return

        # Check variance: minimum pairwise similarity
        if len(self._samples) >= 2:
            min_sim = 1.0
            for i in range(len(self._samples)):
                for j in range(i + 1, min(i + 3, len(self._samples))):
                    sim = _cosine_similarity(self._samples[i], self._samples[j])
                    min_sim = min(min_sim, sim)

            if min_sim < 0.8:
                logger.warning(
                    "Enrollment warning for '%s': low consistency (min_sim=%.2f)",
                    self.name,
                    min_sim,
                )

        # Average and normalize
        averaged = _average_embeddings(self._samples)
        self.result = {
            "ok": True,
            "embedding": averaged,
            "samples_collected": len(self._samples),
        }
        logger.info(
            "Enrollment completed for '%s': %d samples collected",
            self.name,
            len(self._samples),
        )

    async def store(self) -> dict:
        """Store the enrollment result via CRUD client.

        Must be called after enrollment finishes successfully.
        Returns the CRUD response.
        """
        if not self.result or not self.result.get("ok"):
            return {"ok": False, "error": "No valid enrollment result"}

        embedding = self.result["embedding"]
        logger.info(
            "Storing face '%s': embedding_dim=%d, first_3=%s",
            self.name,
            len(embedding),
            embedding[:3],
        )
        return await self.crud_client.add_face(self.name, embedding)
