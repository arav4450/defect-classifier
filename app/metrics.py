"""
Metrics.

Exposes a Prometheus /metrics endpoint. Point any Prometheus server
(including one running on your minikube cluster) at this to get
p95/p99 latency, throughput, error rate, and estimated cost.

Cost is a rough proxy: CPU-seconds spent in inference * an assumed
$/CPU-second rate. Swap ESTIMATED_COST_PER_SECOND for your real number.
"""

from prometheus_client import Counter, Histogram

REQUESTS_TOTAL = Counter(
    "predict_requests_total", "Total prediction requests", ["cache_hit"]
)
ERRORS_TOTAL = Counter(
    "predict_errors_total", "Total prediction errors", ["error_type"]
)
LATENCY_SECONDS = Histogram(
    "predict_latency_seconds",
    "End-to-end prediction latency",
    buckets=[0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10],
)
COST_TOTAL = Counter(
    "predict_estimated_cost_total", "Estimated cumulative inference cost"
)

# A placeholder rate — replace with your real compute cost per second.
ESTIMATED_COST_PER_SECOND = 0.0002


def record_cost(inference_seconds: float) -> None:
    COST_TOTAL.inc(inference_seconds * ESTIMATED_COST_PER_SECOND)
