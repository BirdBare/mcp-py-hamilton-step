import os

from fastmcp import Client, Context, FastMCP
from fastmcp.server.lifespan import lifespan
from py_hamilton_step.hamilton import UnixSocketConnection, WindowsVirtualCOMConnection
from py_hamilton_step.hamilton.device import (
    HamiltonDevice,  # TODO This will eventually need to change to allow specific devices.
)

from mcp_py_hamilton_step.shared.env import CONNECTION_MODE, CONNECTION_PATH, DEVICE_PORT


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


mcp = FastMCP("Hamilton Device", lifespan=device_lifespan)


@mcp.tool
async def execute_command(context: Context, command_json: dict) -> dict:

    device = context.lifespan_context["device"]

    return await device._execute_command_json(command_json)


if __name__ == "__main__":
    # Device will always run as http port because it is only called from clients. So we need http to connect.
    mcp.run(transport="http", port=DEVICE_PORT)
