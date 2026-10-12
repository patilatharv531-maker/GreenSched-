from datetime import datetime

from .temporal import find_best_time_slot


def find_best_schedule(
    current_time: datetime,
    duration_minutes: int,
    deadline: datetime,
    carbon_forecasts: dict
):
    """
    Find the best region and time combination
    while satisfying the job deadline.

    The scheduler receives pre-generated carbon forecasts
    so that the same data can be used for fair comparison
    with the baseline scheduler.
    """

    best_schedule = None
    best_carbon = float("inf")

    for region, forecast in carbon_forecasts.items():

        # Find the best feasible time in this region
        decision = find_best_time_slot(
            current_time=current_time,
            duration_minutes=duration_minutes,
            deadline=deadline,
            carbon_forecast=forecast
        )

        # No feasible slot in this region
        if decision is None:
            continue

        # Compare this region's best feasible slot
        if decision["carbon_intensity"] < best_carbon:

            best_carbon = decision["carbon_intensity"]

            best_schedule = {
                "region": region,
                "scheduled_time": decision["scheduled_time"],
                "finish_time": decision["finish_time"],
                "carbon_intensity": decision["carbon_intensity"]
            }

    return best_schedule