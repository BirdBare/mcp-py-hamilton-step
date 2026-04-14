import os
import typing

import dotenv
from fastmcp import Client, Context, FastMCP
from py_venus_step.ml_star import Channel1000ulTipPickupChannelConfig, Channel1000ulTipPickupCommand
from pydantic import BaseModel

from mcp_py_venus_step.shared.executor import executor_client_lifespan

dotenv.load_dotenv()

#
# ENV Variables
#
# Required environment variables:
# MCP_TRANSPORT: Determines the transport method for the MCP server. Can be either 'stdio' or 'http'. Defaults to 'stdio'.
# VENUS_EXECUTOR_PORT: The port number for the Hamilton executor server. Always runs in http mode. Defaults to 57000.
#
# Optional environment variables:
# VENUS_CHANNEL_1000UL_ATTACH_TIP_PORT: The port number for the 1000uL channel tip attach MCP server if MCP_TRANSPORT is 'http'. Defaults to 57001.

MCP_TRANSPORT = typing.cast("typing.Literal['stdio', 'http']", os.getenv("MCP_TRANSPORT", "stdio"))

if MCP_TRANSPORT not in ("stdio", "http"):
    raise ValueError(f"Invalid MCP_TRANSPORT: {MCP_TRANSPORT}. Must be 'stdio' or 'http'.")

CHANNEL_1000UL_TIP_ATTACH_PORT = int(os.getenv("VENUS_CHANNEL_1000UL_ATTACH_TIP_PORT", "57001"))

#
# MCP Server
#
mcp = FastMCP(
    "Hamilton Liquid Handling 1000uL Channel Tip Attach",
    instructions="Exposes tip attach functionality for 1mL channels on Hamilton liquid handler.",
    lifespan=executor_client_lifespan,
)


#
# Tool implementation
#
class AttachTipOptions(BaseModel):
    channel_number: int
    labware_id: str
    labware_position_id: str


class AttachTipResult(BaseModel):
    channel_number: int
    exception: str | None
    labware_id: str
    labware_position_id: str


def parse_response_data(
    channel_options: list[AttachTipOptions],
    response_json: dict,
) -> list[AttachTipResult]:
    response = Channel1000ulTipPickupCommand.parse_response(response_json)

    executed_channels = [option.channel_number for option in channel_options]
    result = []

    for block_data in response.channel_sequences_with_recovery_details.block_data:
        if block_data.num in executed_channels:
            if response.channel_sequences_with_recovery_details.err_flag == "Fatal error":
                exception_name = "FatalError"

            elif block_data.main_err is None:
                exception_name = None

            else:
                exception_name = block_data.main_err.__name__

            result.append(
                AttachTipResult(
                    channel_number=block_data.num,
                    exception=exception_name,
                    labware_id=block_data.labware_name,
                    labware_position_id=block_data.labware_pos,
                ),
            )

    return result


@mcp.tool
async def attach_tips(
    context: Context,
    channel_options: list[AttachTipOptions],
) -> list[AttachTipResult]:
    """Attaches tips for the specified channels. Returns a dictionary mapping channel numbers to the result of the operation."""
    channel_configs = []
    for option in channel_options:
        config = Channel1000ulTipPickupChannelConfig(
            channel_number=typing.cast(
                "typing.Literal[1, 2, 3, 4, 5, 6, 7, 8,9,10,11,12,13,14,15,16]",
                option.channel_number,
            ),
            sequence_labware=option.labware_id,
            sequence_position=option.labware_position_id,
        )
        channel_configs.append(config)

    command = Channel1000ulTipPickupCommand(channel_configs=tuple(channel_configs))

    executor_client: Client = context.lifespan_context["executor_client"]
    call_tool_data = await executor_client.call_tool("execute_command", {"command_json": command.as_dict()})

    response_data = call_tool_data.data

    return parse_response_data(typing.cast("list[AttachTipOptions]", channel_options), response_data)


if __name__ == "__main__":
    if MCP_TRANSPORT == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="http", port=CHANNEL_1000UL_TIP_ATTACH_PORT)
