import os
import typing

import dotenv
from fastmcp import Client, Context, FastMCP
from py_hamilton_step.ml_star import Channel1000ulAspirateChannelConfig, Channel1000ulAspirateCommand
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
# HAMILTON_CHANNEL_1000UL_ASPIRATE_PORT: The port number for the 1000uL channel aspirate MCP server if MCP_TRANSPORT is 'http'. Defaults to 57002.

MCP_TRANSPORT = typing.cast("typing.Literal['stdio', 'http']", os.getenv("MCP_TRANSPORT", "stdio"))

if MCP_TRANSPORT not in ("stdio", "http"):
    raise ValueError(f"Invalid MCP_TRANSPORT: {MCP_TRANSPORT}. Must be 'stdio' or 'http'.")

CHANNEL_1000UL_ASPIRATE_PORT = int(os.getenv("HAMILTON_CHANNEL_1000UL_ASPIRATE_PORT", "57002"))

#
# MCP Server
#
mcp = FastMCP(
    "Hamilton Liquid Handling 1000uL Channel Aspirate",
    instructions="Exposes aspirate functionality for 1mL channels on Hamilton liquid handler.",
    lifespan=device_operation_lifespan,
)


#
# Tool implementation
#
class BaseAspirateOptions(BaseModel):
    channel_number: int
    labware_id: str
    labware_position_id: str
    volume_ul: float
    aspirate_mode: typing.Literal["Aspiration", "Consecutive aspiration", "Aspirate all"] = "Aspiration"
    liquid_class: str
    retract_distance_for_transport_air_mm: float = 5
    liquid_following: typing.Literal["Off", "On"] = "On"
    mix_cycles: int = 0
    mix_volume_ul: float = 0


class LiquidLevelDetectionAspirateOptions(BaseAspirateOptions):
    submerge_depth_mm: float = 2


class HeightBasedAspirateOptions(BaseAspirateOptions):
    height_from_bottom_mm: float


class ChannelAspirationResult(BaseModel):
    exception: str | None
    aspirated_volume_ul: float | None
    labware_id: str
    labware_position_id: str


def parse_response_data(
    channel_options: list[BaseAspirateOptions],
    response_json: dict,
) -> dict[int, ChannelAspirationResult]:
    response = Channel1000ulAspirateCommand.parse_response(response_json)

    result: dict[int, typing.Any] = {option.channel_number: None for option in channel_options}

    for block_data in response.channel_sequences_with_recovery_details.block_data:
        if block_data.num in result:
            if response.channel_sequences_with_recovery_details.err_flag == "Fatal error":
                exception_name = "FatalError"

            elif block_data.main_err is None:
                exception_name = "None"

            else:
                exception_name = block_data.main_err.__name__

            result[block_data.num] = ChannelAspirationResult(
                exception=exception_name,
                aspirated_volume_ul=block_data.step_data,
                labware_id=block_data.labware_name,
                labware_position_id=block_data.labware_pos,
            )

    return result


@mcp.tool
async def aspirate_with_capacitive_liquid_level_detection(
    context: Context,
    channel_options: list[LiquidLevelDetectionAspirateOptions],
) -> dict[int, ChannelAspirationResult]:
    """Aspirates a specified volume of liquid from a location using capacitive liquid level detection to detect the surface of the liquid. Returns a dictionary mapping channel numbers to the result of the operation."""
    channel_configs = []
    for option in channel_options:
        config = Channel1000ulAspirateChannelConfig(
            channel_number=typing.cast("typing.Literal[1, 2, 3, 4, 5, 6, 7, 8]", option.channel_number),
            sequence_labware=option.labware_id,
            sequence_position=option.labware_position_id,
            volume_ul=option.volume_ul,
            aspirate_mode=option.aspirate_mode,
            liquid_class=option.liquid_class,
            capacitive_lld_sensitivity="From labware definition",
            pressure_lld_sensitivity="Off",
            fix_height_from_bottom_mm=0,  # Field does not matter in this context but included for brevity.
            touch_off="Off",
            submerge_depth_mm=option.submerge_depth_mm,
            max_height_difference_mm=0,  # Field does not matter in this context but included for brevity.
            retract_distance_for_transport_air_mm=option.retract_distance_for_transport_air_mm,
            aspiration_position_above_touch_mm=0,  # Field does not matter in this context but included for brevity.
            liquid_following_during_aspirate_and_mix=option.liquid_following,
            cycles=option.mix_cycles,
            mix_position_mm=option.submerge_depth_mm,  # Use submerge depth to align aspiration position and mix position.
            mix_volume_ul=option.mix_volume_ul,
        )
        channel_configs.append(config)

    command = Channel1000ulAspirateCommand(channel_configs=tuple(channel_configs))

    device_client: Client = context.lifespan_context["device_client"]
    call_tool_data = await device_client.call_tool("execute_command", {"command_json": command.as_dict()})

    response_data = call_tool_data.data

    return parse_response_data(typing.cast("list[BaseAspirateOptions]", channel_options), response_data)


@mcp.tool
async def aspirate_with_pressure_liquid_level_detection(
    context: Context,
    channel_options: list[LiquidLevelDetectionAspirateOptions],
) -> dict[int, ChannelAspirationResult]:
    """Aspirates a specified volume of liquid from a location using pressure liquid level detection to detect the surface of the liquid. Returns a dictionary mapping channel numbers to the result of the operation."""
    channel_configs = []
    for option in channel_options:
        config = Channel1000ulAspirateChannelConfig(
            channel_number=typing.cast("typing.Literal[1, 2, 3, 4, 5, 6, 7, 8]", option.channel_number),
            sequence_labware=option.labware_id,
            sequence_position=option.labware_position_id,
            volume_ul=option.volume_ul,
            aspirate_mode=option.aspirate_mode,
            liquid_class=option.liquid_class,
            capacitive_lld_sensitivity="Off",
            pressure_lld_sensitivity="From labware definition",
            fix_height_from_bottom_mm=0,  # Field does not matter in this context but included for brevity.
            touch_off="Off",
            submerge_depth_mm=option.submerge_depth_mm,
            max_height_difference_mm=0,  # Field does not matter in this context but included for brevity.
            retract_distance_for_transport_air_mm=option.retract_distance_for_transport_air_mm,
            aspiration_position_above_touch_mm=0,  # Field does not matter in this context but included for brevity.
            liquid_following_during_aspirate_and_mix=option.liquid_following,
            cycles=option.mix_cycles,
            mix_position_mm=option.submerge_depth_mm,  # Use submerge depth to align aspiration position and mix position.
            mix_volume_ul=option.mix_volume_ul,
        )
        channel_configs.append(config)

    command = Channel1000ulAspirateCommand(channel_configs=tuple(channel_configs))

    device_client: Client = context.lifespan_context["device_client"]
    call_tool_data = await device_client.call_tool("execute_command", {"command_json": command.as_dict()})

    response_data = call_tool_data.data

    return parse_response_data(typing.cast("list[BaseAspirateOptions]", channel_options), response_data)


@mcp.tool
async def aspirate_at_height(
    context: Context,
    channel_options: list[HeightBasedAspirateOptions],
) -> dict[int, ChannelAspirationResult]:
    """Aspirates a specified volume of liquid from a location at a specified height. Returns a dictionary mapping channel numbers to the result of the operation."""
    channel_configs = []
    for option in channel_options:
        config = Channel1000ulAspirateChannelConfig(
            channel_number=typing.cast("typing.Literal[1, 2, 3, 4, 5, 6, 7, 8]", option.channel_number),
            sequence_labware=option.labware_id,
            sequence_position=option.labware_position_id,
            volume_ul=option.volume_ul,
            aspirate_mode=option.aspirate_mode,
            liquid_class=option.liquid_class,
            capacitive_lld_sensitivity="Off",
            pressure_lld_sensitivity="Off",
            fix_height_from_bottom_mm=option.height_from_bottom_mm,
            touch_off="Off",
            submerge_depth_mm=0,  # Field does not matter in this context but included for brevity.
            max_height_difference_mm=0,  # Field does not matter in this context but included for brevity.
            retract_distance_for_transport_air_mm=option.retract_distance_for_transport_air_mm,
            aspiration_position_above_touch_mm=0,  # Field does not matter in this context but included for brevity.
            liquid_following_during_aspirate_and_mix=option.liquid_following,
            cycles=option.mix_cycles,
            mix_position_mm=0,  # Field does not matter in this context but included for brevity.
            mix_volume_ul=option.mix_volume_ul,
        )
        channel_configs.append(config)

    command = Channel1000ulAspirateCommand(channel_configs=tuple(channel_configs))

    device_client: Client = context.lifespan_context["device_client"]
    call_tool_data = await device_client.call_tool("execute_command", {"command_json": command.as_dict()})

    response_data = call_tool_data.data

    return parse_response_data(typing.cast("list[BaseAspirateOptions]", channel_options), response_data)


if __name__ == "__main__":
    if MCP_TRANSPORT == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="http", port=CHANNEL_1000UL_ASPIRATE_PORT)
