import os
import typing

import dotenv
from fastmcp import Client, Context, FastMCP
from py_hamilton_step.ml_star import Channel1000ulTipPickupChannelConfig, Channel1000ulTipPickupCommand
from pydantic import BaseModel

from mcp_py_hamilton_step.shared.device import device_operation_lifespan

dotenv.load_dotenv()

#
# ENV Variables
#
# Required environment variables:
# MCP_TRANSPORT: Determines the transport method for the MCP server. Can be either 'stdio' or 'http'. Defaults to 'stdio'.
# HAMILTON_DEVICE_PORT: The port number for the Hamilton device MCP server. Always runs in http mode. Defaults to 57000.
#
# Optional environment variables:
# HAMILTON_CHANNEL_1000UL_TIP_PICKUP_PORT: The port number for the 1000uL channel tip pickup MCP server if MCP_TRANSPORT is 'http'. Defaults to 57001.

MCP_TRANSPORT = typing.cast("typing.Literal['stdio', 'http']", os.getenv("MCP_TRANSPORT", "stdio"))

if MCP_TRANSPORT not in ("stdio", "http"):
    raise ValueError(f"Invalid MCP_TRANSPORT: {MCP_TRANSPORT}. Must be 'stdio' or 'http'.")

DEVICE_PORT = int(os.getenv("HAMILTON_DEVICE_PORT", "57000"))
CHANNEL_1000UL_TIP_PICKUP_PORT = int(os.getenv("HAMILTON_CHANNEL_1000UL_TIP_PICKUP_PORT", "57001"))

mcp = FastMCP(
    "Hamilton 1000uL Channel Tip Pickup",
    instructions="Exposes tip pickup functionality for 1mL channels on Hamilton liquid handler.",
    lifespan=device_operation_lifespan,
)


class TipPickupOptions(BaseModel):
    channel_number: int
    labware_id: str
    labware_position_id: str


class ChannelPickupResult(BaseModel):
    exception: str | None
    labware_id: str
    labware_position_id: str


def parse_response_data(
    channel_options: list[TipPickupOptions],
    response_json: dict,
) -> dict[int, ChannelPickupResult]:
    response = Channel1000ulTipPickupCommand.parse_response(response_json)

    result: dict[int, typing.Any] = {option.channel_number: None for option in channel_options}

    for block_data in response.channel_sequences_with_recovery_details.block_data:
        if block_data.num in result:
            if response.channel_sequences_with_recovery_details.err_flag == "Fatal error":
                exception_name = "FatalError"

            elif block_data.main_err is None:
                exception_name = "None"

            else:
                exception_name = block_data.main_err.__name__

            result[block_data.num] = ChannelPickupResult(
                exception=exception_name,
                labware_id=block_data.labware_name,
                labware_position_id=block_data.labware_pos,
            )

    return result


@mcp.tool
async def tip_pickup(
    context: Context,
    channel_options: list[TipPickupOptions],
) -> dict[int, ChannelPickupResult]:
    """Picks up tips for the specified channels. Returns a dictionary mapping channel numbers to the result of the operation."""
    channel_configs = []
    for option in channel_options:
        config = Channel1000ulTipPickupChannelConfig(
            channel_number=typing.cast("typing.Literal[1, 2, 3, 4, 5, 6, 7, 8]", option.channel_number),
            sequence_labware=option.labware_id,
            sequence_position=option.labware_position_id,
        )
        channel_configs.append(config)

    command = Channel1000ulTipPickupCommand(channel_configs=tuple(channel_configs))

    device_client: Client = context.lifespan_context["device_client"]
    call_tool_data = await device_client.call_tool("execute_command", {"command_json": command.as_dict()})

    response_data = call_tool_data.data

    return parse_response_data(typing.cast("list[TipPickupOptions]", channel_options), response_data)


if __name__ == "__main__":
    if MCP_TRANSPORT == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="http", port=CHANNEL_1000UL_TIP_PICKUP_PORT)
