import os

from dotenv import load_dotenv
from fastmcp import Client, Context, FastMCP
from fastmcp.server.lifespan import lifespan
from py_hamilton_step.hamilton import UnixSocketConnection, WindowsVirtualCOMConnection
from py_hamilton_step.hamilton.device import (
    HamiltonDevice,  # TODO This will eventually need to change to allow specific devices.
)

from mcp_py_hamilton_step.shared.url import DEVICE_PORT, make_url

load_dotenv()

CONNECTION_MODE = os.getenv("HAMILTON_CONNECTION_MODE", "SOCKET")

mcp = FastMCP("Device")


@mcp.tool
async def execute_command(context: Context, command_json: dict) -> dict:

    device = context.lifespan_context["device"]

    return await device._execute_command_json(command_json)


@lifespan
async def device_operation_lifespan(server):
    async with Client(make_url(DEVICE_PORT)) as device_client:
        yield {"device_client": device_client}


@lifespan
async def device_lifespan(server):

    if CONNECTION_MODE == "SOCKET":
        socket_path = os.getenv("HAMILTON_CONNECTION_PATH", "NOT_SET")

        if socket_path == "NOT_SET":
            raise ValueError(
                "Connection mode is set to SOCKET but no connection path is provided. Please check your environment variables.",
            )

        if socket_path.startswith("COM"):
            raise ValueError(
                "Connection mode is set to SOCKET but the connection path looks like a COM port. Please check your environment variables.",
            )

        connection = UnixSocketConnection(socket_path)
        await connection.connect()

        device = HamiltonDevice(connection)

    elif CONNECTION_MODE == "COM":
        com_port = os.getenv("HAMILTON_CONNECTION_PATH", "NOT_SET")

        if com_port == "NOT_SET":
            raise ValueError(
                "Connection mode is set to COM but no connection path is provided. Please check your environment variables.",
            )

        if not com_port.startswith("COM"):
            raise ValueError(
                "Connection mode is set to COM but the connection path does not look like a COM port. Please check your environment variables.",
            )

        connection = WindowsVirtualCOMConnection(com_port)
        await connection.connect()

        device = HamiltonDevice(connection)
    else:
        raise ValueError(f"Invalid connection mode: {CONNECTION_MODE}")

    try:
        yield {"device": device}
    finally:
        await device.connection.disconnect()


if __name__ == "__main__":
    mcp.run(transport="http", port=DEVICE_PORT)
