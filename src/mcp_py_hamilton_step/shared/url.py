import os

from dotenv import load_dotenv

load_dotenv()

DEVICE_PORT = int(os.getenv("HAMILTON_DEVICE_PORT", "57000"))
CHANNEL_1000UL_ASPIRATE_PORT = int(os.getenv("HAMILTON_CHANNEL_1000UL_ASPIRATE_PORT", "57001"))


def make_url(port: int) -> str:
    return f"http://localhost:{port}/mcp"
