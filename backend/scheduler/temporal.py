from datetime import datetime, timedelta


def find_best_time_slot(
    current_time: datetime,
    duration_minutes: int,
    deadline: datetime,
    carbon_forecast: list
):
    """
    Find the lowest-carbon feasible time slot for a job.

    A slot is feasible only if:
        1. It is not in the past.
        2. The job can finish before the deadline.

    carbon_forecast is expected to contain:
        {
            "time": datetime,
            "carbon_intensity": float
        }
    """

    best_slot = None
    best_carbon = float("inf")

    for slot in carbon_forecast:

        slot_time = slot["time"]
        carbon_intensity = slot["carbon_intensity"]

        # Ignore slots that are already in the past
        if slot_time < current_time:
            continue

        # Calculate when the job would finish
        finish_time = slot_time + timedelta(
            minutes=duration_minutes
        )

        # Reject slots that violate the deadline
        if finish_time > deadline:
            continue

        # Select the lowest-carbon feasible slot
        if carbon_intensity < best_carbon:
            best_carbon = carbon_intensity

            best_slot = {
                "scheduled_time": slot_time,
                "carbon_intensity": carbon_intensity,
                "finish_time": finish_time
            }

    return best_slot