from fastapi import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


class MetricsResource:
    def on_get(self) -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
