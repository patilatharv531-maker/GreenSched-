from datetime import datetime, timedelta


# Conventional cloud scheduling baseline.
# The job is assigned to a fixed/default region
# and starts at the earliest feasible forecast slot.

DEFAULT_REGION = "London"


def find_baseline_schedule(
    current_time: datetime,
    duration_minutes: int,
    deadline: datetime,
    carbon_forecasts: dict
):
    """
    Baseline scheduler for comparison with GreenSched.

    The baseline:
        1. Uses a fixed/default cloud region.
        2. Starts the job at the earliest feasible time.
        3. Does not optimize for carbon intensity.

    This provides a conventional scheduling baseline
    against which GreenSched's carbon-aware scheduling
    can be evaluated.
    """

    if DEFAULT_REGION not in carbon_forecasts:
        return None

    forecast = carbon_forecasts[DEFAULT_REGION]

    for slot in forecast:

        slot_time = slot["time"]

        # Ignore slots that are already in the past
        if slot_time < current_time:
            continue

        # Calculate job completion time
        finish_time = slot_time + timedelta(
            minutes=duration_minutes
        )

        # Reject slots that violate the deadline
        if finish_time > deadline:
            continue

        return {
            "region": DEFAULT_REGION,
            "scheduled_time": slot_time,
            "finish_time": finish_time,
            "carbon_intensity": slot["carbon_intensity"]
        }

    return None