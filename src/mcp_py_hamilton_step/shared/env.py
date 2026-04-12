import os

from dotenv import load_dotenv

load_dotenv()

MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio").upper()
CONNECTION_MODE = os.getenv("HAMILTON_CONNECTION_MODE", "SOCKET")
HAMILTON_DB_PATH = os.getenv("HAMILTON_DB_PATH", "hamilton.db")

# ports for each server
DEVICE_PORT = int(os.getenv("HAMILTON_DEVICE_PORT", "57000"))
CHANNEL_1000UL_ASPIRATE_PORT = int(os.getenv("HAMILTON_CHANNEL_1000UL_ASPIRATE_PORT", "57001"))
