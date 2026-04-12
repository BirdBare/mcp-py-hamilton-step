import os

from dotenv import load_dotenv
from peewee import Model, SqliteDatabase

load_dotenv()

db = SqliteDatabase(os.getenv("HAMILTON_DB_PATH", "hamilton.db"))


class BaseModel(Model):
    """All models inherit this to share the database connection."""

    class Meta:
        database = db
