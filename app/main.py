"""
Defect Classifier API.

A small, stateless FastAPI service that does zero-shot defect
classification on images (e.g. hull/weld surfaces) using CLIP.
No fine-tuning, no training dataset required.

Endpoints:
  POST /predict   - classify an uploaded image against candidate labels
  POST /feedback   - record a thumbs-up/down + comment for a past prediction
  GET  /health     - liveness/readiness probe
  GET  /metrics    - Prometheus metrics
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.cache import cache, make_cache_key, uptime_seconds
from app.config import settings
from app.feedback import init_db, record_feedback
from app.metrics import ERRORS_TOTAL, LATENCY_SECONDS, REQUESTS_TOTAL, record_cost
from app.model import DefectClassifier, get_classifier

logging.basicConfig(level=settings.LOG_LEVEL.upper())  # logs go to stdout — 12-factor
logger = logging.getLogger(settings.APP_NAME)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse("app/static/index.html")


@app.get("/health")
def health():
    return {"status": "ok", "uptime_seconds": round(uptime_seconds(), 1)}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict")
@limiter.limit(settings.RATE_LIMIT)
async def predict(
    request: Request,
    image: UploadFile = File(...),
    labels: str = Form(default=""),
    classifier: DefectClassifier = Depends(get_classifier),
):
    candidate_labels = [item.strip() for item in labels.split(",") if item.strip()] or settings.DEFAULT_LABELS

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image upload")

    key = make_cache_key(image_bytes, candidate_labels)
    cached_result = cache.get(key)
    if cached_result is not None:
        REQUESTS_TOTAL.labels(cache_hit="true").inc()
        return {"request_id": str(uuid.uuid4()), "cached": True, "predictions": cached_result}

    start = time.time()
    try:
        predictions = classifier.classify(image_bytes, candidate_labels)
    except Exception as exc:
        ERRORS_TOTAL.labels(error_type=type(exc).__name__).inc()
        logger.exception("inference failed")
        raise HTTPException(status_code=500, detail="Inference failed") from exc
    elapsed = time.time() - start

    LATENCY_SECONDS.observe(elapsed)
    record_cost(elapsed)
    REQUESTS_TOTAL.labels(cache_hit="false").inc()
    cache.set(key, predictions)

    return {
        "request_id": str(uuid.uuid4()),
        "cached": False,
        "latency_seconds": round(elapsed, 3),
        "predictions": predictions,
    }


@app.post("/feedback")
async def feedback(request_id: str = Form(...), rating: int = Form(...), comment: str = Form(default="")):
    if rating not in (-1, 0, 1):
        raise HTTPException(status_code=400, detail="rating must be -1, 0, or 1")
    record_feedback(request_id, rating, comment)
    return {"status": "recorded"}
