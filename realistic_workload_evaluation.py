import requests
import time

from datetime import datetime, timedelta

from backend.scheduler.temporal import find_best_time_slot
from backend.scheduler.combined import find_best_schedule
from backend.scheduler.baseline import find_baseline_schedule

from backend.emissions.energy import calculate_energy_consumption
from backend.emissions.emissions import calculate_emissions


# =========================================================
# CONFIGURATION
# =========================================================

HISTORICAL_DATE = "2026-10-03"

API_URL = (
    "https://api.carbonintensity.org.uk/"
    "regional/intensity/{}/pt24h"
)

# 12 geographical regions used for spatial scheduling.
# Scottish regions are excluded because the historical
# dataset contains persistent zero forecasts for them.
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


# =========================================================
# REALISTIC SYNTHETIC WORKLOAD
# =========================================================
#
# These are simulated jobs, but they have different
# resource requirements, durations and deadlines.
#
# The carbon data used later comes from real NESO
# historical forecasts.
# =========================================================

WORKLOAD = [
    {
        "name": "Job-01",
        "cpu": 2,
        "memory": 4,
        "duration_minutes": 30,
        "deadline_hours": 4,
        "priority": "HIGH"
    },
    {
        "name": "Job-02",
        "cpu": 4,
        "memory": 8,
        "duration_minutes": 60,
        "deadline_hours": 12,
        "priority": "MEDIUM"
    },
    {
        "name": "Job-03",
        "cpu": 2,
        "memory": 4,
        "duration_minutes": 90,
        "deadline_hours": 6,
        "priority": "HIGH"
    },
    {
        "name": "Job-04",
        "cpu": 8,
        "memory": 16,
        "duration_minutes": 30,
        "deadline_hours": 24,
        "priority": "LOW"
    },
    {
        "name": "Job-05",
        "cpu": 1,
        "memory": 2,
        "duration_minutes": 120,
        "deadline_hours": 8,
        "priority": "MEDIUM"
    },
    {
        "name": "Job-06",
        "cpu": 4,
        "memory": 8,
        "duration_minutes": 45,
        "deadline_hours": 10,
        "priority": "HIGH"
    },
    {
        "name": "Job-07",
        "cpu": 2,
        "memory": 4,
        "duration_minutes": 60,
        "deadline_hours": 18,
        "priority": "LOW"
    },
    {
        "name": "Job-08",
        "cpu": 8,
        "memory": 16,
        "duration_minutes": 90,
        "deadline_hours": 24,
        "priority": "MEDIUM"
    },
    {
        "name": "Job-09",
        "cpu": 1,
        "memory": 2,
        "duration_minutes": 30,
        "deadline_hours": 3,
        "priority": "HIGH"
    },
    {
        "name": "Job-10",
        "cpu": 4,
        "memory": 8,
        "duration_minutes": 120,
        "deadline_hours": 24,
        "priority": "LOW"
    },
    {
        "name": "Job-11",
        "cpu": 2,
        "memory": 4,
        "duration_minutes": 45,
        "deadline_hours": 6,
        "priority": "MEDIUM"
    },
    {
        "name": "Job-12",
        "cpu": 8,
        "memory": 16,
        "duration_minutes": 60,
        "deadline_hours": 12,
        "priority": "HIGH"
    },
    {
        "name": "Job-13",
        "cpu": 2,
        "memory": 4,
        "duration_minutes": 120,
        "deadline_hours": 18,
        "priority": "LOW"
    },
    {
        "name": "Job-14",
        "cpu": 4,
        "memory": 8,
        "duration_minutes": 30,
        "deadline_hours": 5,
        "priority": "HIGH"
    },
    {
        "name": "Job-15",
        "cpu": 1,
        "memory": 2,
        "duration_minutes": 60,
        "deadline_hours": 10,
        "priority": "MEDIUM"
    },
    {
        "name": "Job-16",
        "cpu": 8,
        "memory": 16,
        "duration_minutes": 120,
        "deadline_hours": 24,
        "priority": "LOW"
    },
    {
        "name": "Job-17",
        "cpu": 2,
        "memory": 4,
        "duration_minutes": 30,
        "deadline_hours": 4,
        "priority": "HIGH"
    },
    {
        "name": "Job-18",
        "cpu": 4,
        "memory": 8,
        "duration_minutes": 90,
        "deadline_hours": 12,
        "priority": "MEDIUM"
    },
    {
        "name": "Job-19",
        "cpu": 1,
        "memory": 2,
        "duration_minutes": 45,
        "deadline_hours": 8,
        "priority": "LOW"
    },
    {
        "name": "Job-20",
        "cpu": 4,
        "memory": 8,
        "duration_minutes": 60,
        "deadline_hours": 18,
        "priority": "HIGH"
    }
]


# =========================================================
# FETCH HISTORICAL NESO DATA
# =========================================================

def get_historical_forecast(date):

    url = API_URL.format(
        date + "T12:00Z"
    )

    print("\nFetching real NESO historical data...")
    print(f"Date requested: {date}")

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()["data"]

    regional_forecasts = {
        region: []
        for region in REGIONS
    }

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

    - Region can change.
    - Each region uses its earliest feasible slot.
    - The region with the lowest carbon at that
      earliest feasible slot is selected.
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
            # for this region.
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
# MAIN EVALUATION
# =========================================================

def main():

    print("=" * 70)
    print("GreenSched Realistic Workload Evaluation")
    print("=" * 70)

    print(f"\nNumber of simulated jobs: {len(WORKLOAD)}")
    print(f"Historical carbon date: {HISTORICAL_DATE}")

    # -----------------------------------------------------
    # GET REAL NESO DATA
    # -----------------------------------------------------

    carbon_forecasts = get_historical_forecast(
        HISTORICAL_DATE
    )

    print(
        f"Regions used: {len(carbon_forecasts)}"
    )

    # -----------------------------------------------------
    # EVALUATION START
    # -----------------------------------------------------

    first_slot = min(
        slot["time"]
        for forecast in carbon_forecasts.values()
        for slot in forecast
    )

    evaluation_start = first_slot

    print(
        f"Evaluation start: {evaluation_start}"
    )

    # -----------------------------------------------------
    # TOTALS
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # RUN EACH JOB
    # -----------------------------------------------------

    for job in WORKLOAD:

        job_name = job["name"]

        deadline = (
            evaluation_start +
            timedelta(
                hours=job["deadline_hours"]
            )
        )

        energy = calculate_energy_consumption(
            cpu=job["cpu"],
            memory=job["memory"],
            duration_minutes=job[
                "duration_minutes"
            ]
        )

        print("\n" + "-" * 70)

        print(
            f"{job_name} | "
            f"CPU={job['cpu']} | "
            f"RAM={job['memory']}GB | "
            f"Duration={job['duration_minutes']}min | "
            f"Deadline={job['deadline_hours']}h"
        )

        print(
            f"Estimated energy: {energy} kWh"
        )

        # -------------------------------------------------
        # BASELINE
        # -------------------------------------------------

        baseline = find_baseline_schedule(
            current_time=evaluation_start,
            duration_minutes=job[
                "duration_minutes"
            ],
            deadline=deadline,
            carbon_forecasts=carbon_forecasts
        )

        if baseline:

            emissions = calculate_emissions(
                energy_kwh=energy,
                carbon_intensity=baseline[
                    "carbon_intensity"
                ]
            )

            totals["baseline"] += emissions
            feasible["baseline"] += 1

            if baseline["finish_time"] > deadline:
                violations["baseline"] += 1

            print(
                f"Baseline       : "
                f"{baseline['region']}, "
                f"{baseline['carbon_intensity']} gCO2/kWh, "
                f"{emissions} gCO2"
            )

        else:

            print("Baseline       : NO FEASIBLE SLOT")

        # -------------------------------------------------
        # TEMPORAL-ONLY
        # -------------------------------------------------

        temporal = find_temporal_only_schedule(
            current_time=evaluation_start,
            duration_minutes=job[
                "duration_minutes"
            ],
            deadline=deadline,
            carbon_forecasts=carbon_forecasts
        )

        if temporal:

            emissions = calculate_emissions(
                energy_kwh=energy,
                carbon_intensity=temporal[
                    "carbon_intensity"
                ]
            )

            totals["temporal"] += emissions
            feasible["temporal"] += 1

            if temporal["finish_time"] > deadline:
                violations["temporal"] += 1

            print(
                f"Temporal-only : "
                f"{BASELINE_REGION}, "
                f"{temporal['carbon_intensity']} gCO2/kWh, "
                f"{emissions} gCO2"
            )

        else:

            print(
                "Temporal-only : NO FEASIBLE SLOT"
            )

        # -------------------------------------------------
        # SPATIAL-ONLY
        # -------------------------------------------------

        spatial = find_spatial_only_schedule(
            current_time=evaluation_start,
            duration_minutes=job[
                "duration_minutes"
            ],
            deadline=deadline,
            carbon_forecasts=carbon_forecasts
        )

        if spatial:

            emissions = calculate_emissions(
                energy_kwh=energy,
                carbon_intensity=spatial[
                    "carbon_intensity"
                ]
            )

            totals["spatial"] += emissions
            feasible["spatial"] += 1

            if spatial["finish_time"] > deadline:
                violations["spatial"] += 1

            print(
                f"Spatial-only  : "
                f"{spatial['region']}, "
                f"{spatial['carbon_intensity']} gCO2/kWh, "
                f"{emissions} gCO2"
            )

        else:

            print(
                "Spatial-only  : NO FEASIBLE SLOT"
            )

        # -------------------------------------------------
        # GREENSCHED
        # -------------------------------------------------

        greensched = find_best_schedule(
            current_time=evaluation_start,
            duration_minutes=job[
                "duration_minutes"
            ],
            deadline=deadline,
            carbon_forecasts=carbon_forecasts
        )

        if greensched:

            emissions = calculate_emissions(
                energy_kwh=energy,
                carbon_intensity=greensched[
                    "carbon_intensity"
                ]
            )

            totals["greensched"] += emissions
            feasible["greensched"] += 1

            if greensched["finish_time"] > deadline:
                violations["greensched"] += 1

            print(
                f"GreenSched    : "
                f"{greensched['region']}, "
                f"{greensched['carbon_intensity']} gCO2/kWh, "
                f"{emissions} gCO2"
            )

        else:

            print(
                "GreenSched    : NO FEASIBLE SLOT"
            )

    # =====================================================
    # FINAL RESULTS
    # =====================================================

    print("\n\n")
    print("=" * 70)
    print("REALISTIC WORKLOAD RESULTS")
    print("=" * 70)

    print("\nTotal estimated emissions:")

    print(
        f"Baseline:       "
        f"{totals['baseline']:.4f} gCO2"
    )

    print(
        f"Temporal-only:  "
        f"{totals['temporal']:.4f} gCO2"
    )

    print(
        f"Spatial-only:   "
        f"{totals['spatial']:.4f} gCO2"
    )

    print(
        f"GreenSched:     "
        f"{totals['greensched']:.4f} gCO2"
    )

    # -----------------------------------------------------
    # REDUCTIONS
    # -----------------------------------------------------

    if totals["baseline"] > 0:

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

        print("\nEmission reduction vs baseline:")

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
    # FEASIBILITY
    # -----------------------------------------------------

    print("\nFeasibility:")

    total_jobs = len(WORKLOAD)

    print(
        f"Baseline:       "
        f"{feasible['baseline']}/{total_jobs}"
    )

    print(
        f"Temporal-only:  "
        f"{feasible['temporal']}/{total_jobs}"
    )

    print(
        f"Spatial-only:   "
        f"{feasible['spatial']}/{total_jobs}"
    )

    print(
        f"GreenSched:     "
        f"{feasible['greensched']}/{total_jobs}"
    )

    # -----------------------------------------------------
    # DEADLINE VIOLATIONS
    # -----------------------------------------------------

    print("\nDeadline violations:")

    print(
        f"Baseline:       "
        f"{violations['baseline']}"
    )

    print(
        f"Temporal-only:  "
        f"{violations['temporal']}"
    )

    print(
        f"Spatial-only:   "
        f"{violations['spatial']}"
    )

    print(
        f"GreenSched:     "
        f"{violations['greensched']}"
    )

    print("\n" + "=" * 70)
    print("Evaluation completed.")
    print("=" * 70)


if __name__ == "__main__":
    main()