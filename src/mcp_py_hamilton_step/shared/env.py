import os
import typing

from dotenv import load_dotenv

load_dotenv()


MCP_TRANSPORT = typing.cast("typing.Literal['stdio', 'http']", os.getenv("MCP_TRANSPORT", "stdio"))
if MCP_TRANSPORT not in ("stdio", "http"):
    raise ValueError(f"Invalid MCP_TRANSPORT: {MCP_TRANSPORT}. Must be 'stdio' or 'http'.")

# Hamilton device connection
CONNECTION_MODE = os.getenv("HAMILTON_CONNECTION_MODE", "SOCKET")  # SOCKET or COM
CONNECTION_PATH = os.getenv(
    "HAMILTON_CONNECTION_PATH",
    "NOT_SET",
)  # either socket path or COM port depending on connection mode

# State tracking db path. SQLITE database.
DB_PATH = os.getenv("HAMILTON_DB_PATH", "hamilton.db")

# ports for each server if running in http transportmode
DEVICE_PORT = int(os.getenv("HAMILTON_DEVICE_PORT", "57000"))
CHANNEL_1000UL_ASPIRATE_PORT = int(os.getenv("HAMILTON_CHANNEL_1000UL_ASPIRATE_PORT", "57001"))
