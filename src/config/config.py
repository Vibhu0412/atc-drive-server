import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)

class DatabaseSettings:
    DB_USER: str = os.getenv('DB_USER')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD')
    DB_HOST: str = os.getenv('DB_HOST')
    DB_NAME: str = os.getenv('DB_NAME')
    DB_PORT: int = int(os.getenv('DB_PORT', 5432))
    ALEMBIC_ENV: str = os.getenv('ALEMBIC_ENV', 'local')

class JWTSettings:
    JWTALGORITHM: str = os.getenv('JWTALGORITHM', 'HS256')
    JWTSECRETKEY: str = os.getenv('JWTSECRETKEY')

class DatabaseURLSettings:
    SQLALCHEMY_DATABASE_URL: str = (
        f"postgresql://{DatabaseSettings.DB_USER}:"
        f"{DatabaseSettings.DB_PASSWORD}@{DatabaseSettings.DB_HOST}:"
        f"{DatabaseSettings.DB_PORT}/{DatabaseSettings.DB_NAME}"
    )

class Settings(DatabaseSettings, DatabaseURLSettings, JWTSettings):
    pass

settings = Settings()

