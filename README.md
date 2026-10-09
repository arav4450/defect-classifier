# Defect Classifier API

A small, stateless FastAPI service that does **zero-shot** defect
classification on images (hull corrosion, weld defects, cracks, etc.)
using CLIP from Hugging Face. No fine-tuning, no training dataset —
you supply candidate text labels at request time and the model scores
the image against each one.


## Features

- **Caching** — identical (image, labels) pairs skip re-running the model. Backend is swappable: in-memory for local dev, Redis for multi-replica deployments — one env var, no code change.
- **Rate limiting** — per-client-IP limit via `slowapi`, configurable.
- **Metrics** — Prometheus endpoint (`/metrics`) exposing p95/p99-ready latency histograms, throughput, error rate, and estimated cost.
- **Feedback capture** — `/feedback` records a rating + comment against a `request_id`.


## Project layout

```
app/
  main.py       FastAPI app and routes
  config.py     All configuration, sourced from environment variables
  cache.py      Cache abstraction (memory or Redis)
  model.py      CLIP zero-shot classifier wrapper
  metrics.py    Prometheus metrics
  feedback.py   SQLite-backed feedback storage
tests/
  test_api.py   API tests using a fake classifier
```

## Running locally

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open http://localhost:8000 in a browser to upload an image, choose comparison labels,
and view ranked predictions. The interactive API documentation remains available at
http://localhost:8000/docs.

Try it:

```bash
curl -F "image=@sample.jpg" -F "labels=weld defect,clean surface" \
  http://localhost:8000/predict
```

Run tests:

```bash
pytest -v
```

### Watching metrics

If you have Prometheus running locally, scrape `http://localhost:8000/metrics` and graph:

```
histogram_quantile(0.95, rate(predict_latency_seconds_bucket[5m]))   # p95
histogram_quantile(0.99, rate(predict_latency_seconds_bucket[5m]))   # p99
rate(predict_requests_total[5m])                                     # throughput
rate(predict_errors_total[5m]) / rate(predict_requests_total[5m])    # error rate
```

