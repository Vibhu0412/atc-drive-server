import secrets
from http.client import HTTPException

import pytz

from typing import Optional
from jose import JWTError, jwt, ExpiredSignatureError
from datetime import datetime, timedelta

from passlib.exc import InvalidTokenError
from starlette import status

from src.config.config import Settings

settings = Settings()

class Token:
    def __init__(self):
        self.secret_key = settings.JWTSECRETKEY
        self.algorithm = settings.JWTALGORITHM
        self.access_token_expiry = timedelta(minutes=60)
        self.refresh_token_expiry = timedelta(days=7)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        expire = datetime.now(pytz.utc) + (expires_delta if expires_delta else self.access_token_expiry)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, self.algorithm)
        return encoded_jwt

    def create_refresh_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.now(pytz.utc) + self.refresh_token_expiry
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, self.algorithm)
        return encoded_jwt

    def decode_token(self, token):
        try:
            token = token.replace("Bearer ", "")
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except ExpiredSignatureError:
            # Re-raise with more specific error
            raise JWTError("Token signature has expired")
        except InvalidTokenError as e:
            # Handle other JWT errors
            raise JWTError(f"Invalid token: {str(e)}")
