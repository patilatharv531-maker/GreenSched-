from datetime import datetime, timedelta, timezone
import requests

from backend.scheduler.baseline import find_baseline_schedule
from backend.scheduler.combined import find_best_schedule
from backend.emissions.energy import calculate_energy_consumption
from backend.emissions.emissions import calculate_emissions


NESO_BASE_URL = "https://api.carbonintensity.org.uk"


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

# Historical starting points.
# Each represents a different 24-hour historical period.
HISTORICAL_PERIODS = [
    "2026-10-02T12:00Z",
    "2026-10-01T12:00Z",
    "2026-09-30T12:00Z",
    "2026-09-29T12:00Z",
    "2026-09-28T12:00Z",
]


# --------------------------------------------------
# ONLY THE 14 GEOGRAPHICAL REGIONS
# --------------------------------------------------

VALID_REGIONS = {
    "North Scotland",
    "South Scotland",
    "North West England",
    "North East England",
    "Yorkshire",
    "North Wales & Merseyside",
    "South Wales",
    "West Midlands",
    "East Midlands",
    "East England",
    "South West England",
    "South England",
    "London",
    "South East England"
}


# --------------------------------------------------
# TEST WORKLOAD
# --------------------------------------------------

JOBS = [
    {
        "name": "Job 1",
        "cpu": 2,
        "memory": 4,
        "duration_minutes": 30,
        "deadline_hours": 6
    },
    {
        "name": "Job 2",
        "cpu": 4,
        "memory": 8,
        "duration_minutes": 60,
        "deadline_hours": 8
    },
    {
        "name": "Job 3",
        "cpu": 2,
        "memory": 8,
        "duration_minutes": 45,
        "deadline_hours": 10
    },
    {
        "name": "Job 4",
        "cpu": 8,
        "memory": 16,
        "duration_minutes": 120,
        "deadline_hours": 12
    },
    {
        "name": "Job 5",
        "cpu": 4,
        "memory": 4,
        "duration_minutes": 30,
        "deadline_hours": 14
    },
    {
        "name": "Job 6",
        "cpu": 2,
        "memory": 16,
        "duration_minutes": 90,
        "deadline_hours": 16
    },
    {
        "name": "Job 7",
        "cpu": 8,
        "memory": 8,
        "duration_minutes": 60,
        "deadline_hours": 18
    },
    {
        "name": "Job 8",
        "cpu": 4,
        "memory": 16,
        "duration_minutes": 120,
        "deadline_hours": 20
    }
]


# --------------------------------------------------
# FETCH HISTORICAL NESO DATA
# --------------------------------------------------

def get_historical_regional_forecast(start_time):

    response = requests.get(
        f"{NESO_BASE_URL}/regional/intensity/{start_time}/pt24h",
        timeout=10
    )

    response.raise_for_status()

    data = response.json()["data"]

    regional_forecasts = {}

    for slot in data:

        slot_time = datetime.fromisoformat(
            slot["from"].replace("Z", "+00:00")
        )

        for region in slot["regions"]:

            region_name = region["shortname"]

            if region_name not in VALID_REGIONS:
                continue

            carbon_intensity = region["intensity"]["forecast"]

            if region_name not in regional_forecasts:
                regional_forecasts[region_name] = []

            regional_forecasts[region_name].append({
                "time": slot_time,
                "carbon_intensity": carbon_intensity
            })

    return regional_forecasts


# --------------------------------------------------
# MAIN EVALUATION
# --------------------------------------------------

print("=" * 70)
print("GREENSCHED HISTORICAL NESO EVALUATION")
print("=" * 70)


total_baseline_emissions = 0
total_greensched_emissions = 0

total_baseline_jobs = 0
total_greensched_jobs = 0

total_deadline_violations = 0

snapshot_results = []


# --------------------------------------------------
# EVALUATE EACH HISTORICAL PERIOD
# --------------------------------------------------

for period_number, start_time in enumerate(
    HISTORICAL_PERIODS,
    start=1
):

    print("\n")
    print("=" * 70)
    print(
        f"HISTORICAL PERIOD "
        f"{period_number}/{len(HISTORICAL_PERIODS)}"
    )
    print("=" * 70)

    print("Starting point:", start_time)

    print("\nFetching historical NESO data...")

    carbon_forecasts = get_historical_regional_forecast(
        start_time
    )

    print(
        "Regions loaded:",
        len(carbon_forecasts)
    )

    print(
        "Forecast slots:",
        len(next(iter(carbon_forecasts.values())))
    )


    # ------------------------------------------------
    # USE FIRST FORECAST SLOT AS EVALUATION START
    # ------------------------------------------------

    current_time = min(
        slot["time"]
        for forecast in carbon_forecasts.values()
        for slot in forecast
    )


    snapshot_baseline = 0
    snapshot_greensched = 0

    snapshot_baseline_jobs = 0
    snapshot_greensched_jobs = 0

    snapshot_deadline_violations = 0


    # ------------------------------------------------
    # RUN WORKLOAD
    # ------------------------------------------------

    for job in JOBS:

        deadline = current_time + timedelta(
            hours=job["deadline_hours"]
        )


        # --------------------------------------------
        # BASELINE
        # --------------------------------------------

        baseline = find_baseline_schedule(
            current_time=current_time,
            duration_minutes=job["duration_minutes"],
            deadline=deadline,
            carbon_forecasts=carbon_forecasts
        )


        # --------------------------------------------
        # GREENSCHED
        # --------------------------------------------

        greensched = find_best_schedule(
            current_time=current_time,
            duration_minutes=job["duration_minutes"],
            deadline=deadline,
            carbon_forecasts=carbon_forecasts
        )


        # --------------------------------------------
        # BASELINE EMISSIONS
        # --------------------------------------------

        if baseline is not None:

            snapshot_baseline_jobs += 1
            total_baseline_jobs += 1

            energy = calculate_energy_consumption(
                cpu=job["cpu"],
                memory=job["memory"],
                duration_minutes=job["duration_minutes"]
            )

            emissions = calculate_emissions(
                energy_kwh=energy,
                carbon_intensity=baseline["carbon_intensity"]
            )

            snapshot_baseline += emissions
            total_baseline_emissions += emissions


        # --------------------------------------------
        # GREENSCHED EMISSIONS
        # --------------------------------------------

        if greensched is not None:

            snapshot_greensched_jobs += 1
            total_greensched_jobs += 1

            energy = calculate_energy_consumption(
                cpu=job["cpu"],
                memory=job["memory"],
                duration_minutes=job["duration_minutes"]
            )

            emissions = calculate_emissions(
                energy_kwh=energy,
                carbon_intensity=greensched["carbon_intensity"]
            )

            snapshot_greensched += emissions
            total_greensched_emissions += emissions


            # Deadline check
            if greensched["finish_time"] > deadline:

                snapshot_deadline_violations += 1
                total_deadline_violations += 1


    # ------------------------------------------------
    # SNAPSHOT RESULT
    # ------------------------------------------------

    if snapshot_baseline > 0:

        reduction = (
            (
                snapshot_baseline
                - snapshot_greensched
            )
            / snapshot_baseline
        ) * 100

    else:

        reduction = None


    print("\nBaseline emissions:")
    print(
        round(snapshot_baseline, 4),
        "gCO2"
    )

    print("\nGreenSched emissions:")
    print(
        round(snapshot_greensched, 4),
        "gCO2"
    )

    if reduction is not None:

        print(
            "\nEmission reduction:",
            round(reduction, 2),
            "%"
        )

    else:

        print("\nEmission reduction: N/A")


    print(
        "\nBaseline feasible jobs:",
        f"{snapshot_baseline_jobs}/{len(JOBS)}"
    )

    print(
        "GreenSched feasible jobs:",
        f"{snapshot_greensched_jobs}/{len(JOBS)}"
    )

    print(
        "Deadline violations:",
        snapshot_deadline_violations
    )


    snapshot_results.append({
        "period": start_time,
        "baseline": snapshot_baseline,
        "greensched": snapshot_greensched,
        "reduction": reduction
    })


# --------------------------------------------------
# FINAL AGGREGATE RESULTS
# --------------------------------------------------

print("\n")
print("=" * 70)
print("FINAL HISTORICAL EVALUATION")
print("=" * 70)

print(
    "\nTotal baseline emissions:",
    round(total_baseline_emissions, 4),
    "gCO2"
)

print(
    "Total GreenSched emissions:",
    round(total_greensched_emissions, 4),
    "gCO2"
)

print(
    "\nBaseline feasible jobs:",
    f"{total_baseline_jobs}/"
    f"{len(HISTORICAL_PERIODS) * len(JOBS)}"
)

print(
    "GreenSched feasible jobs:",
    f"{total_greensched_jobs}/"
    f"{len(HISTORICAL_PERIODS) * len(JOBS)}"
)

print(
    "Total deadline violations:",
    total_deadline_violations
)


# --------------------------------------------------
# OVERALL REDUCTION
# --------------------------------------------------

if total_baseline_emissions > 0:

    overall_reduction = (
        (
            total_baseline_emissions
            - total_greensched_emissions
        )
        / total_baseline_emissions
    ) * 100

    print(
        "\nOverall emission reduction:",
        round(overall_reduction, 2),
        "%"
    )


# --------------------------------------------------
# PERIOD-BY-PERIOD SUMMARY
# --------------------------------------------------

print("\n")
print("=" * 70)
print("PERIOD SUMMARY")
print("=" * 70)

for result in snapshot_results:

    reduction_text = (
        f"{result['reduction']:.2f}%"
        if result["reduction"] is not None
        else "N/A"
    )

    print(
        f"\n{result['period']}"
        f"\n  Baseline: "
        f"{result['baseline']:.4f} gCO2"
        f"\n  GreenSched: "
        f"{result['greensched']:.4f} gCO2"
        f"\n  Reduction: "
        f"{reduction_text}"
    )


print("\nHistorical evaluation completed.")