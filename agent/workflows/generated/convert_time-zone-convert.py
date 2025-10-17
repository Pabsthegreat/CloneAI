from agent.workflows import register_workflow
from agent.workflows.registry import ParameterSpec, WorkflowContext
from typing import Dict, Any
import datetime
import pytz

# Supported Australian time zones and their pytz names
AU_TZ_MAP = {
    'AEST': 'Australia/Brisbane',   # UTC+10:00, no DST
    'AEDT': 'Australia/Sydney',     # UTC+11:00 (DST)
    'ACST': 'Australia/Adelaide',   # UTC+09:30, DST to ACDT
    'ACDT': 'Australia/Adelaide',   # UTC+10:30 (DST)
}

IST_TZ = pytz.timezone('Asia/Kolkata')  # UTC+05:30

@register_workflow(
    namespace="convert",
    name="time-zone-convert",
    summary="Convert time from IST to a specified Australian time zone (AEST, AEDT, ACST, or ACDT).",
    description="Given a time in Indian Standard Time (IST, UTC+05:30), convert it to a specified Australian time zone (AEST, AEDT, ACST, or ACDT). Input and output are in 'HH:MM AM/PM' format. Handles daylight saving time as appropriate.",
    parameters=(
        ParameterSpec(name="ist_time", description="Time in IST in 'HH:MM AM/PM' format (e.g., 09:59 AM)", type=str, required=True),
        ParameterSpec(name="target_tz", description="Target Australian time zone (AEST, AEDT, ACST, or ACDT)", type=str, required=True),
    ),
    metadata={
        "category": "DOCUMENT COMMANDS",
        "usage": "convert:time-zone-convert ist_time:'09:59 AM' target_tz:AEST",
        "examples": [
            "convert:time-zone-convert ist_time:'09:59 AM' target_tz:AEST",
            "convert:time-zone-convert ist_time:'11:15 PM' target_tz:AEDT",
            "convert:time-zone-convert ist_time:'06:30 AM' target_tz:ACST"
        ],
    }
)
def convert_time_zone_convert_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    ist_time_str = params.get("ist_time")
    target_tz_key = params.get("target_tz", "AEST").upper()

    if not ist_time_str:
        return "Error: 'ist_time' parameter is required."
    if target_tz_key not in AU_TZ_MAP:
        return f"Error: Unsupported target_tz '{target_tz_key}'. Supported: {', '.join(AU_TZ_MAP.keys())}."

    try:
        # Parse IST time string
        ist_time = datetime.datetime.strptime(ist_time_str.strip(), "%I:%M %p")
        # Use today's date for conversion
        now = datetime.datetime.now(IST_TZ)
        ist_dt = IST_TZ.localize(datetime.datetime(now.year, now.month, now.day, ist_time.hour, ist_time.minute))
    except Exception as e:
        return f"Error: Could not parse 'ist_time' ('{ist_time_str}'). Please use 'HH:MM AM/PM' format."

    # Get target pytz timezone
    target_pytz_name = AU_TZ_MAP[target_tz_key]
    target_tz = pytz.timezone(target_pytz_name)

    # Convert IST datetime to target Australian timezone
    try:
        aus_dt = ist_dt.astimezone(target_tz)
        # Output in 'HH:MM AM/PM' format
        result = aus_dt.strftime("%I:%M %p")
        return result.lstrip('0') if result.startswith('0') else result
    except Exception as e:
        return f"Error: Failed to convert time: {str(e)}"
