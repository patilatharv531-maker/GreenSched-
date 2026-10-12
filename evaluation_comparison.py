from datetime import datetime, timezone, timedelta

from backend.carbon.neso import get_regional_carbon_forecasts
from backend.scheduler.temporal import find_best_time_slot
from backend.scheduler.combined import find_best_schedule
from backend.scheduler.baseline import find_baseline_schedule
from backend.emissions.energy import calculate_energy_consumption
from backend.emissions.emissions import calculate_emissions


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

NUM_JOBS = 8

# Fixed region used by the conventional baseline
BASELINE_REGION = "London"

# Job configuration
CPU = 2
MEMORY = 4
DURATION_MINUTES = 30

# Deadline: one day from the current time
DEADLINE_HOURS = 24


# ---------------------------------------------------------
# SPATIAL-ONLY SCHEDULER
# ---------------------------------------------------------

def find_spatial_only_schedule(
    current_time,
    duration_minutes,
    deadline,
    carbon_forecasts
):
    """
    Spatial-only scheduling:

    - Region can change
    - Time is fixed to the earliest feasible slot
    - Carbon intensity is NOT optimized across time

    The scheduler examines the earliest feasible slot
    available for each region and chooses the region
    with the lowest carbon intensity.
    """

    best_schedule = None
    best_carbon = float("inf")

    for region, forecast in carbon_forecasts.items():

        for slot in forecast:

            slot_time = slot["time"]

            # Ignore past slots
            if slot_time < current_time:
                continue

            finish_time = slot_time + timedelta(
                minutes=duration_minutes
            )

            # Check deadline
            if finish_time > deadline:
                continue

            # First feasible slot = earliest feasible time
            carbon = slot["carbon_intensity"]

            if carbon < best_carbon:
                best_carbon = carbon

                best_schedule = {
                    "region": region,
                    "scheduled_time": slot_time,
                    "finish_time": finish_time,
                    "carbon_intensity": carbon
                }

            # Only the earliest feasible slot for
            # this region is considered
            break

    return best_schedule


# ---------------------------------------------------------
# TEMPORAL-ONLY SCHEDULER
# ---------------------------------------------------------

def find_temporal_only_schedule(
    current_time,
    duration_minutes,
    deadline,
    carbon_forecasts
):
    """
    Temporal-only scheduling:

    - Region remains fixed to London
    - Time can change
    - Lowest-carbon feasible time is selected
    """

    if BASELINE_REGION not in carbon_forecasts:
        return None

    return find_best_time_slot(
        current_time=current_time,
        duration_minutes=duration_minutes,
        deadline=deadline,
        carbon_forecast=carbon_forecasts[BASELINE_REGION]
    )


# ---------------------------------------------------------
# EVALUATION
# ---------------------------------------------------------

def evaluate():

    print("=" * 70)
    print("GreenSched Four-Way Evaluation")
    print("=" * 70)

    print("\nFetching real NESO regional carbon forecasts...")

    carbon_forecasts = get_regional_carbon_forecasts()

    print(f"Regions available: {len(carbon_forecasts)}")

    current_time = datetime.now(timezone.utc)

    deadline = current_time + timedelta(
        hours=DEADLINE_HOURS
    )

    print(f"Current time: {current_time}")
    print(f"Deadline:     {deadline}")

    # -----------------------------------------------------
    # ENERGY MODEL
    # -----------------------------------------------------

    energy_per_job = calculate_energy_consumption(
        cpu=CPU,
        memory=MEMORY,
        duration_minutes=DURATION_MINUTES
    )

    print(f"\nEnergy per job: {energy_per_job} kWh")
    print(f"Number of jobs: {NUM_JOBS}")

    # -----------------------------------------------------
    # TOTALS
    # -----------------------------------------------------

    baseline_total = 0
    temporal_total = 0
    spatial_total = 0
    greensched_total = 0

    feasible_counts = {
        "baseline": 0,
        "temporal": 0,
        "spatial": 0,
        "greensched": 0
    }

    deadline_violations = {
        "baseline": 0,
        "temporal": 0,
        "spatial": 0,
        "greensched": 0
    }

    # -----------------------------------------------------
    # RUN JOBS
    # -----------------------------------------------------

    for job_number in range(1, NUM_JOBS + 1):

        print("\n" + "-" * 70)
        print(f"JOB {job_number}")
        print("-" * 70)

        # Each job gets the same deadline
        job_deadline = deadline

        # -------------------------------------------------
        # 1. BASELINE
        # -------------------------------------------------

        baseline = find_baseline_schedule(
            current_time=current_time,
            duration_minutes=DURATION_MINUTES,
            deadline=job_deadline,
            carbon_forecasts=carbon_forecasts
        )

        if baseline:

            baseline_emissions = calculate_emissions(
                energy_kwh=energy_per_job,
                carbon_intensity=baseline["carbon_intensity"]
            )

            baseline_total += baseline_emissions
            feasible_counts["baseline"] += 1

            if baseline["finish_time"] > job_deadline:
                deadline_violations["baseline"] += 1

            print("\nBASELINE")
            print(f"  Region:     {baseline['region']}")
            print(f"  Time:       {baseline['scheduled_time']}")
            print(f"  Carbon:     {baseline['carbon_intensity']} gCO2/kWh")
            print(f"  Emissions:  {baseline_emissions} gCO2")

        else:

            print("\nBASELINE")
            print("  No feasible schedule")

        # -------------------------------------------------
        # 2. TEMPORAL ONLY
        # -------------------------------------------------

        temporal = find_temporal_only_schedule(
            current_time=current_time,
            duration_minutes=DURATION_MINUTES,
            deadline=job_deadline,
            carbon_forecasts=carbon_forecasts
        )

        if temporal:

            temporal_emissions = calculate_emissions(
                energy_kwh=energy_per_job,
                carbon_intensity=temporal["carbon_intensity"]
            )

            temporal_total += temporal_emissions
            feasible_counts["temporal"] += 1

            if temporal["finish_time"] > job_deadline:
                deadline_violations["temporal"] += 1

            print("\nTEMPORAL-ONLY")
            print(f"  Region:     {BASELINE_REGION}")
            print(f"  Time:       {temporal['scheduled_time']}")
            print(f"  Carbon:     {temporal['carbon_intensity']} gCO2/kWh")
            print(f"  Emissions:  {temporal_emissions} gCO2")

        else:

            print("\nTEMPORAL-ONLY")
            print("  No feasible schedule")

        # -------------------------------------------------
        # 3. SPATIAL ONLY
        # -------------------------------------------------

        spatial = find_spatial_only_schedule(
            current_time=current_time,
            duration_minutes=DURATION_MINUTES,
            deadline=job_deadline,
            carbon_forecasts=carbon_forecasts
        )

        if spatial:

            spatial_emissions = calculate_emissions(
                energy_kwh=energy_per_job,
                carbon_intensity=spatial["carbon_intensity"]
            )

            spatial_total += spatial_emissions
            feasible_counts["spatial"] += 1

            if spatial["finish_time"] > job_deadline:
                deadline_violations["spatial"] += 1

            print("\nSPATIAL-ONLY")
            print(f"  Region:     {spatial['region']}")
            print(f"  Time:       {spatial['scheduled_time']}")
            print(f"  Carbon:     {spatial['carbon_intensity']} gCO2/kWh")
            print(f"  Emissions:  {spatial_emissions} gCO2")

        else:

            print("\nSPATIAL-ONLY")
            print("  No feasible schedule")

        # -------------------------------------------------
        # 4. GREENSCHED COMBINED
        # -------------------------------------------------

        greensched = find_best_schedule(
            current_time=current_time,
            duration_minutes=DURATION_MINUTES,
            deadline=job_deadline,
            carbon_forecasts=carbon_forecasts
        )

        if greensched:

            greensched_emissions = calculate_emissions(
                energy_kwh=energy_per_job,
                carbon_intensity=greensched["carbon_intensity"]
            )

            greensched_total += greensched_emissions
            feasible_counts["greensched"] += 1

            if greensched["finish_time"] > job_deadline:
                deadline_violations["greensched"] += 1

            print("\nGREENSCHED")
            print(f"  Region:     {greensched['region']}")
            print(f"  Time:       {greensched['scheduled_time']}")
            print(f"  Carbon:     {greensched['carbon_intensity']} gCO2/kWh")
            print(f"  Emissions:  {greensched_emissions} gCO2")

        else:

            print("\nGREENSCHED")
            print("  No feasible schedule")

    # -----------------------------------------------------
    # RESULTS
    # -----------------------------------------------------

    print("\n")
    print("=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)

    print("\nTotal estimated emissions:")

    print(
        f"Baseline:       {baseline_total:.4f} gCO2"
    )

    print(
        f"Temporal-only:  {temporal_total:.4f} gCO2"
    )

    print(
        f"Spatial-only:   {spatial_total:.4f} gCO2"
    )

    print(
        f"GreenSched:     {greensched_total:.4f} gCO2"
    )

    # -----------------------------------------------------
    # REDUCTIONS
    # -----------------------------------------------------

    print("\nEmission reduction compared with baseline:")

    if baseline_total > 0:

        temporal_reduction = (
            (baseline_total - temporal_total)
            / baseline_total
        ) * 100

        spatial_reduction = (
            (baseline_total - spatial_total)
            / baseline_total
        ) * 100

        greensched_reduction = (
            (baseline_total - greensched_total)
            / baseline_total
        ) * 100

        print(
            f"Temporal-only:  {temporal_reduction:.2f}%"
        )

        print(
            f"Spatial-only:   {spatial_reduction:.2f}%"
        )

        print(
            f"GreenSched:     {greensched_reduction:.2f}%"
        )

    # -----------------------------------------------------
    # FEASIBILITY
    # -----------------------------------------------------

    print("\nFeasibility:")

    print(
        f"Baseline:       {feasible_counts['baseline']}/{NUM_JOBS}"
    )

    print(
        f"Temporal-only:  {feasible_counts['temporal']}/{NUM_JOBS}"
    )

    print(
        f"Spatial-only:   {feasible_counts['spatial']}/{NUM_JOBS}"
    )

    print(
        f"GreenSched:     {feasible_counts['greensched']}/{NUM_JOBS}"
    )

    # -----------------------------------------------------
    # DEADLINE VIOLATIONS
    # -----------------------------------------------------

    print("\nDeadline violations:")

    print(
        f"Baseline:       {deadline_violations['baseline']}"
    )

    print(
        f"Temporal-only:  {deadline_violations['temporal']}"
    )

    print(
        f"Spatial-only:   {deadline_violations['spatial']}"
    )

    print(
        f"GreenSched:     {deadline_violations['greensched']}"
    )

    print("\n" + "=" * 70)
    print("Evaluation completed.")
    print("=" * 70)


if __name__ == "__main__":
    evaluate()