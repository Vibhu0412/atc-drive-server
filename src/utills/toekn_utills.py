import secrets
from http.client import HTTPException

import pytz

from typing import Optional
from jose import JWTError, jwt, ExpiredSignatureError
from datetime import datetime, timedelta

from starlette import status

from src.config.config import Settings
from src.config.logger import logger

settings = Settings()

class Token:
    def __init__(self):
        self.secret_key = settings.JWTSECRETKEY
        self.algorithm = settings.JWTALGORITHM
        self.expiry_time = datetime.now(pytz.utc) + timedelta(hours=24)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        expire = datetime.now(pytz.utc) + expires_delta if expires_delta else self.expiry_time
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, self.algorithm)
        return encoded_jwt

    def decode_token(self, token):
        try:
            token = token.replace("Bearer ", "")

            print("Decoding token:", token)

            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            print("Decoded Payload:", payload)
            return payload

        except jwt.ExpiredSignatureError as e:
            logger.error(f"Token has expired: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except jwt.JWTClaimsError as e:
            logger.error(f"Invalid claims: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid claims in the token")
        except jwt.DecodeError as e:
            logger.error(f"Failed to decode the token: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token decoding error")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Unexpected error during token decoding")

    @staticmethod
    def create_link_token():
        return secrets.token_urlsafe(32)
