import os
import typing

import dotenv
from fastmcp import Client, Context, FastMCP
from py_venus_step.ml_star import (
    Channel1000ulDispenseChannelConfig,
    Channel1000ulDispenseCommand,
)
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
# VENUS_CHANNEL_1000UL_DISPENSE_PORT: The port number for the 1000uL channel dispense MCP server if MCP_TRANSPORT is 'http'. Defaults to 57002.

MCP_TRANSPORT = typing.cast("typing.Literal['stdio', 'http']", os.getenv("MCP_TRANSPORT", "stdio"))

if MCP_TRANSPORT not in ("stdio", "http"):
    raise ValueError(f"Invalid MCP_TRANSPORT: {MCP_TRANSPORT}. Must be 'stdio' or 'http'.")

CHANNEL_1000UL_DISPENSE_PORT = int(os.getenv("VENUS_CHANNEL_1000UL_DISPENSE_PORT", "57002"))

#
# MCP Server
#
mcp = FastMCP(
    "Hamilton Liquid Handling 1000uL Channel Dispense",
    instructions="Exposes dispense functionality for 1mL channels on Hamilton liquid handler.",
    lifespan=executor_client_lifespan,
)


#
# Tool implementation
#
class BaseDispenseOptions(BaseModel):
    channel_number: int
    labware_id: str
    labware_position_id: str
    volume_ul: float
    dispense_mode: typing.Literal[
        "Jet part volume",
        "Jet empty tip",
        "Surface part volume",
        "Surface empty tip",
        "Drain tip in jet mode",
        "From liquid class definition",
        "Blowout tip",
    ] = "From liquid class definition"
    retract_distance_for_transport_air_mm: float = 5
    liquid_class: str
    liquid_following: bool = True
    mix_cycles: int = 0
    mix_volume_ul: float = 0


class LiquidLevelDetectionDispenseOptions(BaseDispenseOptions):
    submerge_depth_mm: float = 2


class HeightBasedDispenseOptions(BaseDispenseOptions):
    height_from_bottom_mm: float


class ChannelDispenseResult(BaseModel):
    channel_number: int
    exception: str | None
    dispensed_volume_ul: float | None
    labware_id: str
    labware_position_id: str


def parse_response_data(
    channel_options: list[BaseDispenseOptions],
    response_json: dict,
) -> list[ChannelDispenseResult]:
    response = Channel1000ulDispenseCommand.parse_response(response_json)

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
                ChannelDispenseResult(
                    channel_number=block_data.num,
                    exception=exception_name,
                    dispensed_volume_ul=block_data.step_data,
                    labware_id=block_data.labware_name,
                    labware_position_id=block_data.labware_pos,
                ),
            )

    return result


@mcp.tool
async def dispense_with_capacitive_liquid_level_detection(
    context: Context,
    channel_options: list[LiquidLevelDetectionDispenseOptions],
) -> list[ChannelDispenseResult]:
    """Dispenses a specified volume of liquid from a location using capacitive liquid level detection to detect the surface of the liquid. Returns a dictionary mapping channel numbers to the result of the operation."""
    channel_configs = []
    for option in channel_options:
        config = Channel1000ulDispenseChannelConfig(
            channel_number=typing.cast(
                "typing.Literal[1, 2, 3, 4, 5, 6, 7, 8,9,10,11,12,13,14,15,16]",
                option.channel_number,
            ),
            sequence_labware=option.labware_id,
            sequence_position=option.labware_position_id,
            volume_ul=option.volume_ul,
            dispense_mode=option.dispense_mode,
            fix_height_from_bottom_mm=0,  # Field does not matter in this context but included for brevity.
            capacitive_lld_sensitivity="From labware definition",
            touch_off=False,
            retract_distance_for_transport_air_mm=option.retract_distance_for_transport_air_mm,
            submerge_depth_mm=option.submerge_depth_mm,
            dispense_position_above_touch_mm=0,  # Field does not matter in this context but included for brevity.
            liquid_class=option.liquid_class,
            liquid_following_during_dispense_and_mix=option.liquid_following,
            mix_cycles=option.mix_cycles,
            mix_position_mm=option.submerge_depth_mm,  # Use submerge depth to align aspiration position and mix position.
            mix_volume_ul=option.mix_volume_ul,
        )
        channel_configs.append(config)

    command = Channel1000ulDispenseCommand(channel_configs=tuple(channel_configs))

    executor_client: Client = context.lifespan_context["executor_client"]
    call_tool_data = await executor_client.call_tool("execute_command", {"command_json": command.as_dict()})

    response_data = call_tool_data.data

    return parse_response_data(typing.cast("list[BaseDispenseOptions]", channel_options), response_data)


@mcp.tool
async def dispense_at_height(
    context: Context,
    channel_options: list[HeightBasedDispenseOptions],
) -> list[ChannelDispenseResult]:
    """Dispenses a specified volume of liquid from a location at a specified height. Returns a dictionary mapping channel numbers to the result of the operation."""
    channel_configs = []
    for option in channel_options:
        config = Channel1000ulDispenseChannelConfig(
            channel_number=typing.cast(
                "typing.Literal[1, 2, 3, 4, 5, 6, 7, 8,9,10,11,12,13,14,15,16]",
                option.channel_number,
            ),
            sequence_labware=option.labware_id,
            sequence_position=option.labware_position_id,
            volume_ul=option.volume_ul,
            dispense_mode=option.dispense_mode,
            fix_height_from_bottom_mm=option.height_from_bottom_mm,
            capacitive_lld_sensitivity="Off",
            touch_off=False,
            retract_distance_for_transport_air_mm=option.retract_distance_for_transport_air_mm,
            submerge_depth_mm=0,  # Field does not matter in this context but included for brevity.
            dispense_position_above_touch_mm=0,  # Field does not matter in this context but included for brevity.
            liquid_class=option.liquid_class,
            liquid_following_during_dispense_and_mix=option.liquid_following,
            mix_cycles=option.mix_cycles,
            mix_position_mm=0,  # Field does not matter in this context but included for brevity.
            mix_volume_ul=option.mix_volume_ul,
        )
        channel_configs.append(config)

    command = Channel1000ulDispenseCommand(channel_configs=tuple(channel_configs))

    executor_client: Client = context.lifespan_context["executor_client"]
    call_tool_data = await executor_client.call_tool("execute_command", {"command_json": command.as_dict()})

    response_data = call_tool_data.data

    return parse_response_data(typing.cast("list[BaseDispenseOptions]", channel_options), response_data)


if __name__ == "__main__":
    if MCP_TRANSPORT == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="http", port=CHANNEL_1000UL_DISPENSE_PORT)
