import os
import json

from fastapi.responses import JSONResponse
from typing import Any

from src.config.logger import logger

class Response:
    """
    Return success and error response.
    """
    def __init__(self, status_code: int, data: Any = None, message: str = None) -> None:
        self.status_code = status_code
        self.message = message
        self.data = data

    def send_success_response(self, **extra):
        res = {
            "detail": self.data,
            "meta": {
                "message": self.message or "Success",
                "code": self.status_code,
                **extra
            }
        }
        logger.info(self.message)
        return res

    def send_error_response(self):
        """
        Return error response with status RESPONSE_STATUS_ERROR
        :return: error response
        """
        return JSONResponse(
            content={
                "detail": self.data,
                "meta": {
                    "code": self.status_code,
                    "message": self.message or "Error",
                }
            },
            status_code=self.status_code)
