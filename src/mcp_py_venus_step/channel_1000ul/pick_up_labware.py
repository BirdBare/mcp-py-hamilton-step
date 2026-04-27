import os
import typing

import dotenv
from fastmcp import Client, Context, FastMCP
from py_venus_step.ml_star import Channel1000ulCoreGripGetPlateCommand
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
# VENUS_CHANNEL_1000UL_PICK_UP_LABWARE_PORT: The port number for the 1000uL channel pick up labware MCP server if MCP_TRANSPORT is 'http'. Defaults to 57005.

MCP_TRANSPORT = typing.cast("typing.Literal['stdio', 'http']", os.getenv("MCP_TRANSPORT", "stdio"))

if MCP_TRANSPORT not in ("stdio", "http"):
    raise ValueError(f"Invalid MCP_TRANSPORT: {MCP_TRANSPORT}. Must be 'stdio' or 'http'.")

CHANNEL_1000UL_PICK_UP_LABWARE_PORT = int(os.getenv("VENUS_CHANNEL_1000UL_PICK_UP_LABWARE_PORT", "57005"))

mcp = FastMCP(
    "Hamilton 1000uL Channel Pick Up Labware",
    instructions="Exposes pick up labware functionality for 1mL channels on Hamilton liquid handler.",
    lifespan=executor_client_lifespan,
)


class AttachToolOptions(BaseModel):
    gripper_tool_labware_id: str
    gripper_tool_used_front_channel: int = 8


class PickUpLabwareOptions(BaseModel):
    labware_id: str
    grip_offset_from_top_mm: float
    grip_width_mm: float
    pre_grip_width_mm: float
    check_if_labware_exists: bool = False
    grip_speed_mm_per_s: float = 277.8
    z_move_speed_mm_per_s: float = 128.7


class AttachToolResult(BaseModel):
    channel_number: int
    exception: str | None
    labware_id: str
    labware_position_id: str


class PickUpLabwareResult(BaseModel):
    exception: str | None
    labware_id: str


class CombinedResult(BaseModel):
    attach_tool_result: tuple[AttachToolResult, AttachToolResult]
    pick_up_labware_result: PickUpLabwareResult


@mcp.tool
async def get_tool_then_labware(
    context: Context,
    attach_tool_options: AttachToolOptions,
    pick_up_labware_options: PickUpLabwareOptions,
) -> CombinedResult:
    """Picks up the 1000uL channel gripper tool then uses it to get labware on the deck. Returns a result containing the result of the tool pickup and the get labware operation."""
    command = Channel1000ulCoreGripGetPlateCommand(
        transport_mode="Plate only",
        plate_sequence_labware=pick_up_labware_options.labware_id,
        lid_sequence_labware=None,
        gripper_tool_sequence_labware=attach_tool_options.gripper_tool_labware_id,
        used_front_channel=typing.cast(
            "typing.Literal[2, 3, 4, 5, 6, 7, 8,9,10,11,12,13,14,15,16]",
            attach_tool_options.gripper_tool_used_front_channel,
        ),
        grip_height_mm=pick_up_labware_options.grip_offset_from_top_mm,
        grip_width_mm=pick_up_labware_options.grip_width_mm,
        opening_width_before_access=pick_up_labware_options.pre_grip_width_mm,
        grip_speed_mm_per_s=pick_up_labware_options.grip_speed_mm_per_s,
        z_speed_mm_per_s=pick_up_labware_options.z_move_speed_mm_per_s,
        check_if_plate_exists=pick_up_labware_options.check_if_labware_exists,
    )

    executor_client: Client = context.lifespan_context["executor_client"]
    call_tool_data = await executor_client.call_tool("execute_command", {"command_json": command.as_dict()})

    response_data = call_tool_data.data

    response = Channel1000ulCoreGripGetPlateCommand.parse_response(response_data)

    gripper_front_channel_number = attach_tool_options.gripper_tool_used_front_channel
    gripper_back_channel_number = gripper_front_channel_number - 1
    executed_channels = [gripper_front_channel_number, gripper_back_channel_number]

    tool_pickup_results = []

    if response.channel_sequences_with_recovery_details is None:
        raise RuntimeError("Fatal Error: Response is missing channel sequence with recovery details.")

    for block_data in response.channel_sequences_with_recovery_details.block_data:
        if block_data.num in executed_channels:
            if response.channel_sequences_with_recovery_details.err_flag == "Fatal error":
                exception_name = "FatalError"

            elif block_data.main_err is None:
                exception_name = None

            else:
                exception_name = block_data.main_err.__name__

            tool_pickup_results.append(
                AttachToolResult(
                    channel_number=block_data.num,
                    exception=exception_name,
                    labware_id=block_data.labware_name,
                    labware_position_id=block_data.labware_pos,
                ),
            )

    block_data = response.get_plate_data_with_recovery_details.block_data[0]
    if response.get_plate_data_with_recovery_details.err_flag == "Fatal error":
        get_labware_exception_name = "FatalError"

    elif block_data.main_err is None:
        get_labware_exception_name = None

    else:
        get_labware_exception_name = block_data.main_err.__name__

    get_labware_result = PickUpLabwareResult(
        exception=get_labware_exception_name,
        labware_id=block_data.labware_name,
    )

    return CombinedResult(
        attach_tool_result=tuple(tool_pickup_results),
        pick_up_labware_result=get_labware_result,
    )


@mcp.tool
async def get_labware(
    context: Context,
    pick_up_labware_options: PickUpLabwareOptions,
) -> PickUpLabwareResult:
    """Pick up labware on the deck using the 1000uL channel gripper tool. The tool must already be picked up if using this tool.Returns the result of the get labware operation."""
    command = Channel1000ulCoreGripGetPlateCommand(
        transport_mode="Plate only",
        plate_sequence_labware=pick_up_labware_options.labware_id,
        lid_sequence_labware=None,
        gripper_tool_sequence_labware="Tool Already Picked Up",  # Not needed since this tool assumes the gripper tool is already picked up. Included for brevity.
        used_front_channel=8,  # Not needed since this tool assumes the gripper tool is already picked up. Included for brevity.
        grip_height_mm=pick_up_labware_options.grip_offset_from_top_mm,
        grip_width_mm=pick_up_labware_options.grip_width_mm,
        opening_width_before_access=pick_up_labware_options.pre_grip_width_mm,
        grip_speed_mm_per_s=pick_up_labware_options.grip_speed_mm_per_s,
        z_speed_mm_per_s=pick_up_labware_options.z_move_speed_mm_per_s,
        check_if_plate_exists=pick_up_labware_options.check_if_labware_exists,
    )

    executor_client: Client = context.lifespan_context["executor_client"]
    call_tool_data = await executor_client.call_tool("execute_command", {"command_json": command.as_dict()})

    response_data = call_tool_data.data

    response = Channel1000ulCoreGripGetPlateCommand.parse_response(response_data)

    block_data = response.get_plate_data_with_recovery_details.block_data[0]
    if response.get_plate_data_with_recovery_details.err_flag == "Fatal error":
        get_labware_exception_name = "FatalError"

    elif block_data.main_err is None:
        get_labware_exception_name = None

    else:
        get_labware_exception_name = block_data.main_err.__name__

    return PickUpLabwareResult(
        exception=get_labware_exception_name,
        labware_id=block_data.labware_name,
    )


if __name__ == "__main__":
    if MCP_TRANSPORT == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="http", port=CHANNEL_1000UL_PICK_UP_LABWARE_PORT)
