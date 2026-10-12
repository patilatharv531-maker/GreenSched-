from datetime import datetime, timedelta, timezone

from backend.carbon.neso import get_regional_carbon_forecasts
from backend.scheduler.baseline import find_baseline_schedule
from backend.scheduler.combined import find_best_schedule
from backend.emissions.energy import calculate_energy_consumption
from backend.emissions.emissions import calculate_emissions


# --------------------------------------------------
# TEST WORKLOAD
# --------------------------------------------------

JOBS = [
    {
        "name": "Job 1",
        "cpu": 2,
        "memory": 4,
        "duration_minutes": 30,
        "deadline_hours": 12
    },
    {
        "name": "Job 2",
        "cpu": 4,
        "memory": 8,
        "duration_minutes": 60,
        "deadline_hours": 12
    },
    {
        "name": "Job 3",
        "cpu": 2,
        "memory": 8,
        "duration_minutes": 45,
        "deadline_hours": 18
    },
    {
        "name": "Job 4",
        "cpu": 8,
        "memory": 16,
        "duration_minutes": 120,
        "deadline_hours": 18
    },
    {
        "name": "Job 5",
        "cpu": 4,
        "memory": 4,
        "duration_minutes": 30,
        "deadline_hours": 24
    },
    {
        "name": "Job 6",
        "cpu": 2,
        "memory": 16,
        "duration_minutes": 90,
        "deadline_hours": 24
    },
    {
        "name": "Job 7",
        "cpu": 8,
        "memory": 8,
        "duration_minutes": 60,
        "deadline_hours": 24
    },
    {
        "name": "Job 8",
        "cpu": 4,
        "memory": 16,
        "duration_minutes": 120,
        "deadline_hours": 24
    },
]


# --------------------------------------------------
# LOAD REAL NESO DATA
# --------------------------------------------------

print("=" * 70)
print("GREENSCHED REAL-DATA ROBUSTNESS EVALUATION")
print("=" * 70)

print("\nFetching real NESO regional carbon forecasts...")

carbon_forecasts = get_regional_carbon_forecasts()

print(
    f"Loaded {len(carbon_forecasts)} regions "
    f"with {len(next(iter(carbon_forecasts.values())))} "
    f"forecast slots each."
)


# --------------------------------------------------
# REMOVE ZERO-CARBON VALUES FOR SENSITIVITY TEST
# --------------------------------------------------
#
# IMPORTANT:
# This does NOT modify GreenSched's real scheduler.
# It creates a separate evaluation dataset in which
# zero-valued forecasts are excluded.
#
# This is used only to measure scheduler performance
# when positive carbon-intensity values are available.
# --------------------------------------------------

positive_forecasts = {}

for region, forecast in carbon_forecasts.items():

    valid_slots = [
        slot
        for slot in forecast
        if slot["carbon_intensity"] > 0
    ]

    if valid_slots:
        positive_forecasts[region] = valid_slots


print(
    f"\nRegions with positive forecast values: "
    f"{len(positive_forecasts)}"
)

print(
    "Positive forecast regions:",
    list(positive_forecasts.keys())
)


# --------------------------------------------------
# CURRENT TIME
# --------------------------------------------------

current_time = datetime.now(timezone.utc)

print("\nEvaluation start time:")
print(current_time)


# --------------------------------------------------
# RESULTS
# --------------------------------------------------

results = []

baseline_total_emissions = 0
greensched_total_emissions = 0

baseline_completed = 0
greensched_completed = 0


# --------------------------------------------------
# RUN EACH JOB
# --------------------------------------------------

for job in JOBS:

    deadline = current_time + timedelta(
        hours=job["deadline_hours"]
    )

    print("\n" + "-" * 70)
    print(job["name"])

    print(
        f"CPU: {job['cpu']} | "
        f"Memory: {job['memory']} GB | "
        f"Duration: {job['duration_minutes']} min"
    )

    print(f"Deadline: {deadline}")

    # ------------------------------------------------
    # BASELINE
    # ------------------------------------------------

    baseline = find_baseline_schedule(
        current_time=current_time,
        duration_minutes=job["duration_minutes"],
        deadline=deadline,
        carbon_forecasts=positive_forecasts
    )

    # ------------------------------------------------
    # GREENSCHED
    # ------------------------------------------------

    greensched = find_best_schedule(
        current_time=current_time,
        duration_minutes=job["duration_minutes"],
        deadline=deadline,
        carbon_forecasts=positive_forecasts
    )

    # ------------------------------------------------
    # BASELINE EMISSIONS
    # ------------------------------------------------

    if baseline is not None:

        baseline_completed += 1

        baseline_energy = calculate_energy_consumption(
            cpu=job["cpu"],
            memory=job["memory"],
            duration_minutes=job["duration_minutes"]
        )

        baseline_emissions = calculate_emissions(
            energy_kwh=baseline_energy,
            carbon_intensity=baseline["carbon_intensity"]
        )

        baseline_total_emissions += baseline_emissions

    else:

        baseline_energy = None
        baseline_emissions = None

    # ------------------------------------------------
    # GREENSCHED EMISSIONS
    # ------------------------------------------------

    if greensched is not None:

        greensched_completed += 1

        greensched_energy = calculate_energy_consumption(
            cpu=job["cpu"],
            memory=job["memory"],
            duration_minutes=job["duration_minutes"]
        )

        greensched_emissions = calculate_emissions(
            energy_kwh=greensched_energy,
            carbon_intensity=greensched["carbon_intensity"]
        )

        greensched_total_emissions += greensched_emissions

    else:

        greensched_energy = None
        greensched_emissions = None

    # ------------------------------------------------
    # PRINT RESULTS
    # ------------------------------------------------

    print("\nBASELINE:")

    if baseline:

        print("Region:", baseline["region"])
        print("Scheduled:", baseline["scheduled_time"])
        print("Carbon:", baseline["carbon_intensity"], "gCO2/kWh")
        print("Energy:", baseline_energy, "kWh")
        print("Emissions:", baseline_emissions, "gCO2")

    else:

        print("No feasible slot")

    print("\nGREENSCHED:")

    if greensched:

        print("Region:", greensched["region"])
        print("Scheduled:", greensched["scheduled_time"])
        print("Carbon:", greensched["carbon_intensity"], "gCO2/kWh")
        print("Energy:", greensched_energy, "kWh")
        print("Emissions:", greensched_emissions, "gCO2")

    else:

        print("No feasible slot")

    # ------------------------------------------------
    # STORE RESULT
    # ------------------------------------------------

    results.append({
        "name": job["name"],
        "baseline": baseline,
        "greensched": greensched,
        "baseline_energy": baseline_energy,
        "baseline_emissions": baseline_emissions,
        "greensched_energy": greensched_energy,
        "greensched_emissions": greensched_emissions
    })


# --------------------------------------------------
# FINAL RESULTS
# --------------------------------------------------

print("\n")
print("=" * 70)
print("FINAL RESULTS")
print("=" * 70)

print(
    f"\nBaseline feasible jobs: "
    f"{baseline_completed}/{len(JOBS)}"
)

print(
    f"GreenSched feasible jobs: "
    f"{greensched_completed}/{len(JOBS)}"
)

print(
    f"\nBaseline total emissions: "
    f"{round(baseline_total_emissions, 4)} gCO2"
)

print(
    f"GreenSched total emissions: "
    f"{round(greensched_total_emissions, 4)} gCO2"
)


# --------------------------------------------------
# EMISSION REDUCTION
# --------------------------------------------------

if baseline_total_emissions > 0:

    emission_reduction = (
        (baseline_total_emissions - greensched_total_emissions)
        / baseline_total_emissions
    ) * 100

    print(
        f"\nEmission reduction: "
        f"{round(emission_reduction, 2)}%"
    )

else:

    print("\nEmission reduction: Cannot calculate")


# --------------------------------------------------
# DEADLINE VALIDATION
# --------------------------------------------------

greensched_deadline_violations = 0

for result in results:

    schedule = result["greensched"]

    if schedule is None:
        continue

    job = next(
        j for j in JOBS
        if j["name"] == result["name"]
    )

    deadline = current_time + timedelta(
        hours=job["deadline_hours"]
    )

    if schedule["finish_time"] > deadline:
        greensched_deadline_violations += 1


print(
    f"\nGreenSched deadline violations: "
    f"{greensched_deadline_violations}"
)

print("\nRobustness evaluation completed.")