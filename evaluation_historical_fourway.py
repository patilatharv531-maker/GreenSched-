import requests
import time

from datetime import datetime, timezone, timedelta

from backend.scheduler.temporal import find_best_time_slot
from backend.scheduler.combined import find_best_schedule
from backend.scheduler.baseline import find_baseline_schedule

from backend.emissions.energy import calculate_energy_consumption
from backend.emissions.emissions import calculate_emissions


# =========================================================
# CONFIGURATION
# =========================================================

DATES = [
    "2026-10-03",
    "2026-10-02",
    "2026-10-01",
    "2026-09-30",
    "2026-09-29"
]

API_URL = (
    "https://api.carbonintensity.org.uk/"
    "regional/intensity/{}/pt24h"
)

# We use the 12 geographical regions with reliable
# positive-value coverage in our validation.
REGIONS = [
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
]

BASELINE_REGION = "London"

NUM_JOBS = 8

CPU = 2
MEMORY = 4
DURATION_MINUTES = 30

# Jobs have a 24-hour deadline window.
DEADLINE_HOURS = 24


# =========================================================
# FETCH HISTORICAL NESO DATA
# =========================================================

def get_historical_forecast(date):

    url = API_URL.format(
        date + "T12:00Z"
    )

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()["data"]

    regional_forecasts = {}

    for region_name in REGIONS:

        regional_forecasts[region_name] = []

    for slot in data:

        slot_time = datetime.fromisoformat(
            slot["from"].replace("Z", "+00:00")
        )

        for region in slot["regions"]:

            region_name = region["shortname"]

            if region_name not in regional_forecasts:
                continue

            carbon = region["intensity"]["forecast"]

            regional_forecasts[region_name].append(
                {
                    "time": slot_time,
                    "carbon_intensity": carbon
                }
            )

    return regional_forecasts


# =========================================================
# SPATIAL-ONLY SCHEDULER
# =========================================================

def find_spatial_only_schedule(
    current_time,
    duration_minutes,
    deadline,
    carbon_forecasts
):
    """
    Spatial-only:

    Region can change.

    Time is restricted to the earliest feasible
    slot for each region.

    Among those earliest feasible slots,
    choose the lowest-carbon region.
    """

    best_schedule = None
    best_carbon = float("inf")

    for region, forecast in carbon_forecasts.items():

        for slot in forecast:

            slot_time = slot["time"]

            if slot_time < current_time:
                continue

            finish_time = (
                slot_time +
                timedelta(minutes=duration_minutes)
            )

            if finish_time > deadline:
                continue

            carbon = slot["carbon_intensity"]

            if carbon < best_carbon:

                best_carbon = carbon

                best_schedule = {
                    "region": region,
                    "scheduled_time": slot_time,
                    "finish_time": finish_time,
                    "carbon_intensity": carbon
                }

            # Only earliest feasible slot
            # for this region
            break

    return best_schedule


# =========================================================
# TEMPORAL-ONLY SCHEDULER
# =========================================================

def find_temporal_only_schedule(
    current_time,
    duration_minutes,
    deadline,
    carbon_forecasts
):

    if BASELINE_REGION not in carbon_forecasts:
        return None

    return find_best_time_slot(
        current_time=current_time,
        duration_minutes=duration_minutes,
        deadline=deadline,
        carbon_forecast=carbon_forecasts[
            BASELINE_REGION
        ]
    )


# =========================================================
# EVALUATION FOR ONE HISTORICAL PERIOD
# =========================================================

def evaluate_period(
    date,
    carbon_forecasts,
    energy_per_job
):

    print("\n" + "=" * 70)
    print(f"HISTORICAL PERIOD: {date}")
    print("=" * 70)

    # Use first available forecast timestamp
    # as the beginning of the evaluation window.
    first_slot = min(
        slot["time"]
        for forecast in carbon_forecasts.values()
        for slot in forecast
    )

    current_time = first_slot

    deadline = (
        current_time +
        timedelta(hours=DEADLINE_HOURS)
    )

    print(f"Evaluation start: {current_time}")
    print(f"Deadline:         {deadline}")

    totals = {
        "baseline": 0.0,
        "temporal": 0.0,
        "spatial": 0.0,
        "greensched": 0.0
    }

    feasible = {
        "baseline": 0,
        "temporal": 0,
        "spatial": 0,
        "greensched": 0
    }

    violations = {
        "baseline": 0,
        "temporal": 0,
        "spatial": 0,
        "greensched": 0
    }

    for job_number in range(
        1,
        NUM_JOBS + 1
    ):

        # -------------------------------------------------
        # BASELINE
        # -------------------------------------------------

        baseline = find_baseline_schedule(
            current_time=current_time,
            duration_minutes=DURATION_MINUTES,
            deadline=deadline,
            carbon_forecasts=carbon_forecasts
        )

        if baseline:

            emissions = calculate_emissions(
                energy_kwh=energy_per_job,
                carbon_intensity=baseline[
                    "carbon_intensity"
                ]
            )

            totals["baseline"] += emissions
            feasible["baseline"] += 1

            if baseline["finish_time"] > deadline:
                violations["baseline"] += 1

        # -------------------------------------------------
        # TEMPORAL ONLY
        # -------------------------------------------------

        temporal = find_temporal_only_schedule(
            current_time=current_time,
            duration_minutes=DURATION_MINUTES,
            deadline=deadline,
            carbon_forecasts=carbon_forecasts
        )

        if temporal:

            emissions = calculate_emissions(
                energy_kwh=energy_per_job,
                carbon_intensity=temporal[
                    "carbon_intensity"
                ]
            )

            totals["temporal"] += emissions
            feasible["temporal"] += 1

            if temporal["finish_time"] > deadline:
                violations["temporal"] += 1

        # -------------------------------------------------
        # SPATIAL ONLY
        # -------------------------------------------------

        spatial = find_spatial_only_schedule(
            current_time=current_time,
            duration_minutes=DURATION_MINUTES,
            deadline=deadline,
            carbon_forecasts=carbon_forecasts
        )

        if spatial:

            emissions = calculate_emissions(
                energy_kwh=energy_per_job,
                carbon_intensity=spatial[
                    "carbon_intensity"
                ]
            )

            totals["spatial"] += emissions
            feasible["spatial"] += 1

            if spatial["finish_time"] > deadline:
                violations["spatial"] += 1

        # -------------------------------------------------
        # GREENSCHED
        # -------------------------------------------------

        greensched = find_best_schedule(
            current_time=current_time,
            duration_minutes=DURATION_MINUTES,
            deadline=deadline,
            carbon_forecasts=carbon_forecasts
        )

        if greensched:

            emissions = calculate_emissions(
                energy_kwh=energy_per_job,
                carbon_intensity=greensched[
                    "carbon_intensity"
                ]
            )

            totals["greensched"] += emissions
            feasible["greensched"] += 1

            if greensched["finish_time"] > deadline:
                violations["greensched"] += 1

    # -----------------------------------------------------
    # PERIOD RESULTS
    # -----------------------------------------------------

    print("\nTotal emissions:")

    print(
        f"  Baseline:       {totals['baseline']:.4f} gCO2"
    )

    print(
        f"  Temporal-only:  {totals['temporal']:.4f} gCO2"
    )

    print(
        f"  Spatial-only:   {totals['spatial']:.4f} gCO2"
    )

    print(
        f"  GreenSched:     {totals['greensched']:.4f} gCO2"
    )

    if totals["baseline"] > 0:

        print("\nReduction vs baseline:")

        temporal_reduction = (
            (
                totals["baseline"]
                - totals["temporal"]
            )
            / totals["baseline"]
        ) * 100

        spatial_reduction = (
            (
                totals["baseline"]
                - totals["spatial"]
            )
            / totals["baseline"]
        ) * 100

        greensched_reduction = (
            (
                totals["baseline"]
                - totals["greensched"]
            )
            / totals["baseline"]
        ) * 100

        print(
            f"  Temporal-only:  {temporal_reduction:.2f}%"
        )

        print(
            f"  Spatial-only:   {spatial_reduction:.2f}%"
        )

        print(
            f"  GreenSched:     {greensched_reduction:.2f}%"
        )

    print("\nFeasibility:")

    print(
        f"  Baseline:       "
        f"{feasible['baseline']}/{NUM_JOBS}"
    )

    print(
        f"  Temporal-only:  "
        f"{feasible['temporal']}/{NUM_JOBS}"
    )

    print(
        f"  Spatial-only:   "
        f"{feasible['spatial']}/{NUM_JOBS}"
    )

    print(
        f"  GreenSched:     "
        f"{feasible['greensched']}/{NUM_JOBS}"
    )

    print("\nDeadline violations:")

    print(
        f"  Baseline:       {violations['baseline']}"
    )

    print(
        f"  Temporal-only:  {violations['temporal']}"
    )

    print(
        f"  Spatial-only:   {violations['spatial']}"
    )

    print(
        f"  GreenSched:     {violations['greensched']}"
    )

    return totals, feasible, violations


# =========================================================
# MAIN EVALUATION
# =========================================================

def main():

    print("=" * 70)
    print("GreenSched Historical Four-Way Evaluation")
    print("=" * 70)

    energy_per_job = calculate_energy_consumption(
        cpu=CPU,
        memory=MEMORY,
        duration_minutes=DURATION_MINUTES
    )

    print(
        f"\nEnergy per job: {energy_per_job} kWh"
    )

    print(
        f"Jobs per historical period: {NUM_JOBS}"
    )

    overall_totals = {
        "baseline": 0.0,
        "temporal": 0.0,
        "spatial": 0.0,
        "greensched": 0.0
    }

    overall_feasible = {
        "baseline": 0,
        "temporal": 0,
        "spatial": 0,
        "greensched": 0
    }

    overall_violations = {
        "baseline": 0,
        "temporal": 0,
        "spatial": 0,
        "greensched": 0
    }

    successful_periods = 0

    for date in DATES:

        print("\n")
        print(
            f"Fetching historical NESO data for {date}..."
        )

        try:

            forecasts = get_historical_forecast(
                date
            )

            totals, feasible, violations = (
                evaluate_period(
                    date,
                    forecasts,
                    energy_per_job
                )
            )

            successful_periods += 1

            for key in overall_totals:
                overall_totals[key] += totals[key]
                overall_feasible[key] += feasible[key]
                overall_violations[key] += violations[key]

        except requests.exceptions.RequestException as e:

            print(
                f"Could not retrieve {date}: {e}"
            )

        time.sleep(2)

    # =====================================================
    # OVERALL RESULTS
    # =====================================================

    print("\n\n")
    print("=" * 70)
    print("OVERALL HISTORICAL RESULTS")
    print("=" * 70)

    print(
        f"\nSuccessfully evaluated periods: "
        f"{successful_periods}/{len(DATES)}"
    )

    print("\nTotal estimated emissions:")

    print(
        f"Baseline:       "
        f"{overall_totals['baseline']:.4f} gCO2"
    )

    print(
        f"Temporal-only:  "
        f"{overall_totals['temporal']:.4f} gCO2"
    )

    print(
        f"Spatial-only:   "
        f"{overall_totals['spatial']:.4f} gCO2"
    )

    print(
        f"GreenSched:     "
        f"{overall_totals['greensched']:.4f} gCO2"
    )

    # -----------------------------------------------------
    # OVERALL REDUCTION
    # -----------------------------------------------------

    if overall_totals["baseline"] > 0:

        temporal_reduction = (
            (
                overall_totals["baseline"]
                - overall_totals["temporal"]
            )
            / overall_totals["baseline"]
        ) * 100

        spatial_reduction = (
            (
                overall_totals["baseline"]
                - overall_totals["spatial"]
            )
            / overall_totals["baseline"]
        ) * 100

        greensched_reduction = (
            (
                overall_totals["baseline"]
                - overall_totals["greensched"]
            )
            / overall_totals["baseline"]
        ) * 100

        print("\nOverall reduction vs baseline:")

        print(
            f"Temporal-only:  "
            f"{temporal_reduction:.2f}%"
        )

        print(
            f"Spatial-only:   "
            f"{spatial_reduction:.2f}%"
        )

        print(
            f"GreenSched:     "
            f"{greensched_reduction:.2f}%"
        )

    # -----------------------------------------------------
    # OVERALL FEASIBILITY
    # -----------------------------------------------------

    total_possible = (
        successful_periods * NUM_JOBS
    )

    print("\nOverall feasibility:")

    for key, label in [
        ("baseline", "Baseline"),
        ("temporal", "Temporal-only"),
        ("spatial", "Spatial-only"),
        ("greensched", "GreenSched")
    ]:

        print(
            f"{label:<16}"
            f"{overall_feasible[key]}/"
            f"{total_possible}"
        )

    # -----------------------------------------------------
    # DEADLINE VIOLATIONS
    # -----------------------------------------------------

    print("\nOverall deadline violations:")

    for key, label in [
        ("baseline", "Baseline"),
        ("temporal", "Temporal-only"),
        ("spatial", "Spatial-only"),
        ("greensched", "GreenSched")
    ]:

        print(
            f"{label:<16}"
            f"{overall_violations[key]}"
        )

    print("\n" + "=" * 70)
    print("Historical evaluation completed.")
    print("=" * 70)


if __name__ == "__main__":
    main()