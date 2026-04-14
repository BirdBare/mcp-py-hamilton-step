import os

import dotenv
from peewee import Model, SqliteDatabase

dotenv.load_dotenv()

DB_PATH = os.getenv("VENUS_DB_PATH", "venus.db")

db = SqliteDatabase(DB_PATH)


class BaseModel(Model):
    """All models inherit this to share the database connection."""

    class Meta:
        database = db
