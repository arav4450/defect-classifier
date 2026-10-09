"""
Model wrapper.

Uses CLIP zero-shot image classification: no fine-tuning, no dataset.
You give it candidate text labels at request time and it scores the image
against each one. This is deliberately isolated behind a small class so
tests can swap in a fake classifier without downloading model weights.
"""

import logging
from io import BytesIO
from typing import Optional

from PIL import Image

from app.config import settings

logger = logging.getLogger(settings.APP_NAME)


class DefectClassifier:
    def __init__(self, model_name: str):
        self._model_name = model_name
        self._pipeline = None  # lazy-loaded on first use

    def _ensure_loaded(self):
        if self._pipeline is None:
            from transformers import pipeline  # heavy import, deferred

            logger.info("loading model %s", self._model_name)
            self._pipeline = pipeline(
                "zero-shot-image-classification", model=self._model_name
            )

    def classify(self, image_bytes: bytes, labels: list[str]) -> list[dict]:
        self._ensure_loaded()
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        results = self._pipeline(image, candidate_labels=labels)
        # normalize to a stable, minimal shape
        return [{"label": r["label"], "score": round(float(r["score"]), 4)} for r in results]


_classifier: Optional[DefectClassifier] = None


def get_classifier() -> DefectClassifier:
    """FastAPI dependency. Overridden in tests to avoid loading real weights."""
    global _classifier
    if _classifier is None:
        _classifier = DefectClassifier(settings.MODEL_NAME)
    return _classifier
