import os

import dotenv
from fastmcp import Client, Context, FastMCP
from fastmcp.server.lifespan import lifespan
from py_hamilton_step.hamilton import UnixSocketConnection, WindowsVirtualCOMConnection
from py_hamilton_step.hamilton.device import (
    HamiltonDevice,  # TODO This will eventually need to change to allow specific devices.
)

dotenv.load_dotenv()

#
# ENV Variables
#
# Required environment variables:
# HAMILTON_CONNECTION_MODE: The connection mode for the Hamilton device. Must be either "SOCKET" or "COM". Defaults to "SOCKET".
# HAMILTON_CONNECTION_PATH: The connection path for the Hamilton device. If connection mode is "SOCKET", this should be the path to the Unix socket. If connection mode is "COM", this should be the virtual COM port. No default value.
# HAMILTON_DEVICE_PORT: The port number for the Hamilton device MCP server. Always runs in http mode. Defaults to 57000.


CONNECTION_MODE = os.getenv("HAMILTON_CONNECTION_MODE", "SOCKET")  # SOCKET or COM
CONNECTION_PATH = os.getenv(
    "HAMILTON_CONNECTION_PATH",
    "NOT_SET",
)  # either socket path or COM port depending on connection mode
DEVICE_PORT = int(os.getenv("HAMILTON_DEVICE_PORT", "57000"))


#
# Lifespan implementation
#
@lifespan
async def device_operation_lifespan(server):
    async with Client(f"http://localhost:{DEVICE_PORT}/mcp") as device_client:
        yield {"device_client": device_client}


@lifespan
async def device_lifespan(server):
    global CONNECTION_MODE, CONNECTION_PATH

    if CONNECTION_MODE == "SOCKET":
        if CONNECTION_PATH == "NOT_SET":
            raise ValueError(
                "Connection mode is set to SOCKET but no connection path is provided. Please check your environment variables.",
            )

        if CONNECTION_PATH.startswith("COM"):
            raise ValueError(
                "Connection mode is set to SOCKET but the connection path looks like a COM port. Please check your environment variables.",
            )

        connection = UnixSocketConnection(CONNECTION_PATH)
        await connection.connect()

        device = HamiltonDevice(connection)

    elif CONNECTION_MODE == "COM":
        CONNECTION_PATH = os.getenv("HAMILTON_CONNECTION_PATH", "NOT_SET")

        if CONNECTION_PATH == "NOT_SET":
            raise ValueError(
                "Connection mode is set to COM but no connection path is provided. Please check your environment variables.",
            )

        if not CONNECTION_PATH.startswith("COM"):
            raise ValueError(
                "Connection mode is set to COM but the connection path does not look like a COM port. Please check your environment variables.",
            )

        connection = WindowsVirtualCOMConnection(CONNECTION_PATH)
        await connection.connect()

        device = HamiltonDevice(connection)
    else:
        raise ValueError(f"Invalid connection mode: {CONNECTION_MODE}")

    try:
        yield {"device": device}
    finally:
        await device.connection.disconnect()


#
# MCP Server
#
mcp = FastMCP("Hamilton Device Command Execution", lifespan=device_lifespan)


#
# Tool Implementation
#
@mcp.tool
async def execute_command(context: Context, command_json: dict) -> dict:

    device = context.lifespan_context["device"]

    return await device._execute_command_json(command_json)


if __name__ == "__main__":
    # Device will always run as http port because it is only called from clients. So we need http to connect.
    mcp.run(transport="http", port=DEVICE_PORT)
