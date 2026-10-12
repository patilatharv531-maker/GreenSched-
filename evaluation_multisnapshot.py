from datetime import datetime, timedelta, timezone
import time

from backend.carbon.neso import get_regional_carbon_forecasts
from backend.scheduler.baseline import find_baseline_schedule
from backend.scheduler.combined import find_best_schedule
from backend.emissions.energy import calculate_energy_consumption
from backend.emissions.emissions import calculate_emissions


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

NUM_SNAPSHOTS = 5

# Use positive-only values for the sensitivity analysis.
# This does NOT modify GreenSched itself.
EXCLUDE_ZERO_VALUES = True


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
# EVALUATION
# --------------------------------------------------

print("=" * 70)
print("GREENSCHED MULTI-SNAPSHOT EVALUATION")
print("=" * 70)

all_snapshot_results = []

total_baseline_emissions = 0
total_greensched_emissions = 0

total_baseline_jobs = 0
total_greensched_jobs = 0

total_deadline_violations = 0


# --------------------------------------------------
# RUN MULTIPLE SNAPSHOTS
# --------------------------------------------------

for snapshot_number in range(1, NUM_SNAPSHOTS + 1):

    print("\n")
    print("=" * 70)
    print(f"SNAPSHOT {snapshot_number}/{NUM_SNAPSHOTS}")
    print("=" * 70)

    print("\nFetching NESO regional forecast...")

    carbon_forecasts = get_regional_carbon_forecasts()

    # ------------------------------------------------
    # OPTIONAL POSITIVE-VALUE SENSITIVITY FILTER
    # ------------------------------------------------

    if EXCLUDE_ZERO_VALUES:

        evaluation_forecasts = {}

        for region, forecast in carbon_forecasts.items():

            valid_slots = [
                slot
                for slot in forecast
                if slot["carbon_intensity"] > 0
            ]

            if valid_slots:
                evaluation_forecasts[region] = valid_slots

    else:

        evaluation_forecasts = carbon_forecasts

    print(
        f"Regions available: "
        f"{len(evaluation_forecasts)}"
    )

    current_time = datetime.now(timezone.utc)

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

        baseline = find_baseline_schedule(
            current_time=current_time,
            duration_minutes=job["duration_minutes"],
            deadline=deadline,
            carbon_forecasts=evaluation_forecasts
        )

        greensched = find_best_schedule(
            current_time=current_time,
            duration_minutes=job["duration_minutes"],
            deadline=deadline,
            carbon_forecasts=evaluation_forecasts
        )

        # ------------------------------------------------
        # BASELINE
        # ------------------------------------------------

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

        # ------------------------------------------------
        # GREENSCHED
        # ------------------------------------------------

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

            # Deadline verification
            if greensched["finish_time"] > deadline:
                snapshot_deadline_violations += 1
                total_deadline_violations += 1

    # ------------------------------------------------
    # SNAPSHOT REDUCTION
    # ------------------------------------------------

    if snapshot_baseline > 0:

        reduction = (
            (snapshot_baseline - snapshot_greensched)
            / snapshot_baseline
        ) * 100

    else:

        reduction = None

    print(
        f"\nBaseline emissions: "
        f"{round(snapshot_baseline, 4)} gCO2"
    )

    print(
        f"GreenSched emissions: "
        f"{round(snapshot_greensched, 4)} gCO2"
    )

    if reduction is not None:

        print(
            f"Emission reduction: "
            f"{round(reduction, 2)}%"
        )

    else:

        print("Emission reduction: N/A")

    print(
        f"GreenSched feasible jobs: "
        f"{snapshot_greensched_jobs}/{len(JOBS)}"
    )

    print(
        f"Deadline violations: "
        f"{snapshot_deadline_violations}"
    )

    all_snapshot_results.append({
        "snapshot": snapshot_number,
        "baseline_emissions": snapshot_baseline,
        "greensched_emissions": snapshot_greensched,
        "reduction": reduction
    })

    # Small delay before requesting another live forecast.
    if snapshot_number < NUM_SNAPSHOTS:

        print("\nWaiting before next NESO request...")
        time.sleep(5)


# --------------------------------------------------
# FINAL AGGREGATE RESULTS
# --------------------------------------------------

print("\n")
print("=" * 70)
print("AGGREGATE RESULTS")
print("=" * 70)

print(
    f"\nTotal baseline emissions: "
    f"{round(total_baseline_emissions, 4)} gCO2"
)

print(
    f"Total GreenSched emissions: "
    f"{round(total_greensched_emissions, 4)} gCO2"
)

print(
    f"\nBaseline feasible jobs: "
    f"{total_baseline_jobs}/{NUM_SNAPSHOTS * len(JOBS)}"
)

print(
    f"GreenSched feasible jobs: "
    f"{total_greensched_jobs}/{NUM_SNAPSHOTS * len(JOBS)}"
)

print(
    f"Total deadline violations: "
    f"{total_deadline_violations}"
)


# --------------------------------------------------
# OVERALL EMISSION REDUCTION
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
        f"\nOverall emission reduction: "
        f"{round(overall_reduction, 2)}%"
    )


# --------------------------------------------------
# SNAPSHOT SUMMARY
# --------------------------------------------------

print("\n")
print("=" * 70)
print("SNAPSHOT SUMMARY")
print("=" * 70)

for result in all_snapshot_results:

    print(
        f"Snapshot {result['snapshot']}: "
        f"Baseline = "
        f"{round(result['baseline_emissions'], 4)} gCO2 | "
        f"GreenSched = "
        f"{round(result['greensched_emissions'], 4)} gCO2 | "
        f"Reduction = "
        f"{round(result['reduction'], 2) if result['reduction'] is not None else 'N/A'}%"
    )


print("\nMulti-snapshot evaluation completed.")