import time

from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram

ROUTE_NOT_FOUND = "sem_rota"
KNOWN_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
OTHER_METHOD = "OUTRO"

REQUESTS = Counter(
    "orca_http_requests_total",
    "Requisicoes HTTP atendidas, por metodo, rota e status.",
    ["method", "route", "status"],
)
DURATION = Histogram(
    "orca_http_request_duration_seconds",
    "Duracao das requisicoes HTTP, por metodo e rota.",
    ["method", "route"],
)


def register_metrics_middleware(application: FastAPI) -> None:
    @application.middleware("http")
    async def measure_request(request: Request, call_next):
        started_at = time.perf_counter()
        status = "500"

        try:
            response = await call_next(request)
            status = str(response.status_code)
            return response
        finally:
            method = _method_label(request)
            route = _route_template(request)
            REQUESTS.labels(method, route, status).inc()
            DURATION.labels(method, route).observe(time.perf_counter() - started_at)


def _method_label(request: Request) -> str:
    if request.method not in KNOWN_METHODS:
        return OTHER_METHOD

    return request.method


def _route_template(request: Request) -> str:
    route = request.scope.get("route")

    if route is None:
        return ROUTE_NOT_FOUND

    return route.path
