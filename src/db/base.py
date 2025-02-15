from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from src.v1_modules.folder_managment import model
from src.v1_modules.auth import model

