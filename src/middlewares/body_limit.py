from fastapi import FastAPI, Request

from constants import MAXIMUM_BODY_BYTES
from errors.base_error import LengthRequired, PayloadTooLarge
from errors.handlers import qi_exception_to_response

METHODS_WITH_BODY = ["POST", "PUT", "PATCH"]


def register_body_limit_middleware(application: FastAPI) -> None:
    @application.middleware("http")
    async def limit_body(request: Request, call_next):
        if request.method not in METHODS_WITH_BODY:
            return await call_next(request)

        if request.headers.get("transfer-encoding") is not None:
            return qi_exception_to_response(LengthRequired())

        content_length = request.headers.get("content-length")

        if content_length is None:
            return await call_next(request)

        if not content_length.isdigit() or int(content_length) > MAXIMUM_BODY_BYTES:
            return qi_exception_to_response(PayloadTooLarge(MAXIMUM_BODY_BYTES))

        return await call_next(request)
