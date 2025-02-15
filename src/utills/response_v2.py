# src/utils/response_utils.py

from typing import Any, Optional, Dict
from fastapi.responses import JSONResponse
from src.config.logger import logger


class ResponseStatus:
    """Constants for common HTTP status codes"""
    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_ERROR = 500


class CommonResponses:
    """Predefined common response messages"""

    @staticmethod
    def not_found(resource: str) -> Dict:
        return {
            "status_code": ResponseStatus.NOT_FOUND,
            "message": f"{resource} not found",
            "data": None
        }

    @staticmethod
    def unauthorized() -> Dict:
        return {
            "status_code": ResponseStatus.UNAUTHORIZED,
            "message": "Unauthorized access",
            "data": None
        }

    @staticmethod
    def validation_error(errors: Any) -> Dict:
        return {
            "status_code": ResponseStatus.BAD_REQUEST,
            "message": "Validation error",
            "data": errors
        }

    @staticmethod
    def success(data: Any = None, message: str = "Success") -> Dict:
        return {
            "status_code": ResponseStatus.OK,
            "message": message,
            "data": data
        }


class ResponseBuilder:
    """
    Enhanced response builder with predefined responses
    """

    def __init__(self, status_code: int, data: Any = None, message: str = None) -> None:
        self.status_code = status_code
        self.message = message
        self.data = data

    @classmethod
    def from_common_response(cls, common_response: Dict) -> 'ResponseBuilder':
        """Create ResponseBuilder instance from common response dictionary"""
        return cls(
            status_code=common_response["status_code"],
            data=common_response["data"],
            message=common_response["message"]
        )

    def send_success_response(self, **extra) -> Dict:
        """Send success response with optional extra metadata"""
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

    def send_error_response(self) -> JSONResponse:
        """Send error response with appropriate status code"""
        return JSONResponse(
            content={
                "detail": self.data,
                "meta": {
                    "code": self.status_code,
                    "message": self.message or "Error",
                }
            },
            status_code=self.status_code
        )