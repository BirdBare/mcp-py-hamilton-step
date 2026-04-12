from peewee import Model, SqliteDatabase

from mcp_py_hamilton_step.shared.env import HAMILTON_DB_PATH

db = SqliteDatabase(HAMILTON_DB_PATH)


class BaseModel(Model):
    """All models inherit this to share the database connection."""

    class Meta:
        database = db
