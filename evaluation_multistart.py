import requests

from datetime import datetime, timedelta

from backend.scheduler.temporal import find_best_time_slot
from backend.scheduler.combined import find_best_schedule
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

# Six different starting points
START_OFFSETS_HOURS = [
    0,
    4,
    8,
    12,
    16,
    20
]


# =========================================================
# REALISTIC SYNTHETIC WORKLOAD
# =========================================================
#
# release_hours:
#   How long after the experiment start the job becomes
#   available.
#
# deadline_hours:
#   How long after the job release the deadline occurs.
#
# This prevents every job from seeing exactly the same
# scheduling window.
# =========================================================

WORKLOAD = [

    {
        "name": "Job-01",
        "cpu": 2,
        "memory": 4,
        "duration_minutes": 30,
        "release_hours": 0,
        "deadline_hours": 4
    },

    {
        "name": "Job-02",
        "cpu": 4,
        "memory": 8,
        "duration_minutes": 60,
        "release_hours": 0.5,
        "deadline_hours": 8
    },

    {
        "name": "Job-03",
        "cpu": 2,
        "memory": 4,
        "duration_minutes": 90,
        "release_hours": 1,
        "deadline_hours": 6
    },

    {
        "name": "Job-04",
        "cpu": 8,
        "memory": 16,
        "duration_minutes": 30,
        "release_hours": 1.5,
        "deadline_hours": 12
    },

    {
        "name": "Job-05",
        "cpu": 1,
        "memory": 2,
        "duration_minutes": 120,
        "release_hours": 2,
        "deadline_hours": 8
    },

    {
        "name": "Job-06",
        "cpu": 4,
        "memory": 8,
        "duration_minutes": 45,
        "release_hours": 2.5,
        "deadline_hours": 10
    },

    {
        "name": "Job-07",
        "cpu": 2,
        "memory": 4,
        "duration_minutes": 60,
        "release_hours": 3,
        "deadline_hours": 12
    },

    {
        "name": "Job-08",
        "cpu": 8,
        "memory": 16,
        "duration_minutes": 90,
        "release_hours": 3.5,
        "deadline_hours": 16
    },

    {
        "name": "Job-09",
        "cpu": 1,
        "memory": 2,
        "duration_minutes": 30,
        "release_hours": 4,
        "deadline_hours": 5
    },

    {
        "name": "Job-10",
        "cpu": 4,
        "memory": 8,
        "duration_minutes": 120,
        "release_hours": 4.5,
        "deadline_hours": 18
    },

    {
        "name": "Job-11",
        "cpu": 2,
        "memory": 4,
        "duration_minutes": 45,
        "release_hours": 5,
        "deadline_hours": 6
    },

    {
        "name": "Job-12",
        "cpu": 8,
        "memory": 16,
        "duration_minutes": 60,
        "release_hours": 5.5,
        "deadline_hours": 12
    },

    {
        "name": "Job-13",
        "cpu": 2,
        "memory": 4,
        "duration_minutes": 120,
        "release_hours": 6,
        "deadline_hours": 18
    },

    {
        "name": "Job-14",
        "cpu": 4,
        "memory": 8,
        "duration_minutes": 30,
        "release_hours": 6.5,
        "deadline_hours": 5
    },

    {
        "name": "Job-15",
        "cpu": 1,
        "memory": 2,
        "duration_minutes": 60,
        "release_hours": 7,
        "deadline_hours": 10
    },

    {
        "name": "Job-16",
        "cpu": 8,
        "memory": 16,
        "duration_minutes": 120,
        "release_hours": 7.5,
        "deadline_hours": 20
    },

    {
        "name": "Job-17",
        "cpu": 2,
        "memory": 4,
        "duration_minutes": 30,
        "release_hours": 8,
        "deadline_hours": 4
    },

    {
        "name": "Job-18",
        "cpu": 4,
        "memory": 8,
        "duration_minutes": 90,
        "release_hours": 8.5,
        "deadline_hours": 12
    },

    {
        "name": "Job-19",
        "cpu": 1,
        "memory": 2,
        "duration_minutes": 45,
        "release_hours": 9,
        "deadline_hours": 8
    },

    {
        "name": "Job-20",
        "cpu": 4,
        "memory": 8,
        "duration_minutes": 60,
        "release_hours": 9.5,
        "deadline_hours": 18
    }
]


# =========================================================
# FETCH REAL NESO HISTORICAL DATA
# =========================================================

def get_historical_forecast():

    url = API_URL.format(
        HISTORICAL_DATE + "T12:00Z"
    )

    print("Fetching REAL NESO historical data...")
    print(
        f"Requested anchor: "
        f"{HISTORICAL_DATE}T12:00Z"
    )

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

            name = region["shortname"]

            if name not in regional_forecasts:
                continue

            regional_forecasts[name].append({
                "time": slot_time,
                "carbon_intensity":
                    region["intensity"]["forecast"]
            })

    return regional_forecasts


# =========================================================
# POSITIVE-CARBON FILTER
# =========================================================

def positive_forecast(forecast):

    """
    Keep only positive NESO carbon-intensity values.

    IMPORTANT:
    We are NOT changing the NESO values.
    We are only excluding zero-valued candidates
    for the robustness/sensitivity experiment.
    """

    return [
        slot
        for slot in forecast
        if slot["carbon_intensity"] > 0
    ]


def positive_carbon_forecasts(carbon_forecasts):

    return {
        region: positive_forecast(forecast)
        for region, forecast in carbon_forecasts.items()
    }


# =========================================================
# BASELINE
# =========================================================

def find_baseline_positive(
    current_time,
    duration_minutes,
    deadline,
    carbon_forecasts
):

    if BASELINE_REGION not in carbon_forecasts:
        return None

    forecast = positive_forecast(
        carbon_forecasts[BASELINE_REGION]
    )

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

        return {
            "region": BASELINE_REGION,
            "scheduled_time": slot_time,
            "finish_time": finish_time,
            "carbon_intensity":
                slot["carbon_intensity"]
        }

    return None


# =========================================================
# TEMPORAL-ONLY
# =========================================================

def find_temporal_positive(
    current_time,
    duration_minutes,
    deadline,
    carbon_forecasts
):

    if BASELINE_REGION not in carbon_forecasts:
        return None

    forecast = positive_forecast(
        carbon_forecasts[BASELINE_REGION]
    )

    return find_best_time_slot(
        current_time=current_time,
        duration_minutes=duration_minutes,
        deadline=deadline,
        carbon_forecast=forecast
    )


# =========================================================
# SPATIAL-ONLY
# =========================================================

def find_spatial_only_positive(
    current_time,
    duration_minutes,
    deadline,
    carbon_forecasts
):

    """
    Spatial-only policy:

    1. For every region, find its EARLIEST feasible
       positive-carbon slot.
    2. Choose the region with the lowest carbon
       intensity among those earliest feasible slots.

    Therefore:
        Spatial-only = spatial optimization
        + earliest feasible execution time

    It does NOT optimize time within a region.
    """

    best_schedule = None
    best_carbon = float("inf")

    for region, forecast in carbon_forecasts.items():

        positive_slots = positive_forecast(forecast)

        for slot in positive_slots:

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

            # IMPORTANT:
            # only earliest feasible slot of each
            # region is considered
            break

    return best_schedule


# =========================================================
# GREENSCHED COMBINED
# =========================================================

def find_greensched_positive(
    current_time,
    duration_minutes,
    deadline,
    carbon_forecasts
):

    """
    GreenSched:

    Searches all positive-carbon feasible
    region + time combinations and selects
    the lowest-carbon one.
    """

    positive_forecasts = (
        positive_carbon_forecasts(
            carbon_forecasts
        )
    )

    return find_best_schedule(
        current_time=current_time,
        duration_minutes=duration_minutes,
        deadline=deadline,
        carbon_forecasts=positive_forecasts
    )


# =========================================================
# EVALUATE ONE START TIME
# =========================================================

def evaluate_start_time(
    start_time,
    carbon_forecasts
):

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

    results = []

    for job in WORKLOAD:

        # -------------------------------------------------
        # JOB RELEASE TIME
        # -------------------------------------------------

        current_time = (
            start_time +
            timedelta(
                hours=job["release_hours"]
            )
        )

        # -------------------------------------------------
        # JOB DEADLINE
        # -------------------------------------------------

        deadline = (
            current_time +
            timedelta(
                hours=job["deadline_hours"]
            )
        )

        # -------------------------------------------------
        # ENERGY
        # -------------------------------------------------

        energy = calculate_energy_consumption(
            cpu=job["cpu"],
            memory=job["memory"],
            duration_minutes=job["duration_minutes"]
        )

        job_result = {
            "name": job["name"],
            "release": current_time,
            "deadline": deadline,
            "energy": energy
        }

        # -------------------------------------------------
        # BASELINE
        # -------------------------------------------------

        baseline = find_baseline_positive(
            current_time=current_time,
            duration_minutes=job["duration_minutes"],
            deadline=deadline,
            carbon_forecasts=carbon_forecasts
        )

        if baseline:

            emissions = calculate_emissions(
                energy_kwh=energy,
                carbon_intensity=
                    baseline["carbon_intensity"]
            )

            totals["baseline"] += emissions
            feasible["baseline"] += 1

            if baseline["finish_time"] > deadline:
                violations["baseline"] += 1

            job_result["baseline"] = {
                "region": baseline["region"],
                "carbon": baseline["carbon_intensity"],
                "emissions": emissions
            }

        else:

            job_result["baseline"] = None

        # -------------------------------------------------
        # TEMPORAL
        # -------------------------------------------------

        temporal = find_temporal_positive(
            current_time=current_time,
            duration_minutes=job["duration_minutes"],
            deadline=deadline,
            carbon_forecasts=carbon_forecasts
        )

        if temporal:

            emissions = calculate_emissions(
                energy_kwh=energy,
                carbon_intensity=
                    temporal["carbon_intensity"]
            )

            totals["temporal"] += emissions
            feasible["temporal"] += 1

            if temporal["finish_time"] > deadline:
                violations["temporal"] += 1

            job_result["temporal"] = {
                "region": BASELINE_REGION,
                "carbon": temporal["carbon_intensity"],
                "emissions": emissions
            }

        else:

            job_result["temporal"] = None

        # -------------------------------------------------
        # SPATIAL
        # -------------------------------------------------

        spatial = find_spatial_only_positive(
            current_time=current_time,
            duration_minutes=job["duration_minutes"],
            deadline=deadline,
            carbon_forecasts=carbon_forecasts
        )

        if spatial:

            emissions = calculate_emissions(
                energy_kwh=energy,
                carbon_intensity=
                    spatial["carbon_intensity"]
            )

            totals["spatial"] += emissions
            feasible["spatial"] += 1

            if spatial["finish_time"] > deadline:
                violations["spatial"] += 1

            job_result["spatial"] = {
                "region": spatial["region"],
                "carbon": spatial["carbon_intensity"],
                "emissions": emissions
            }

        else:

            job_result["spatial"] = None

        # -------------------------------------------------
        # GREENSCHED
        # -------------------------------------------------

        greensched = find_greensched_positive(
            current_time=current_time,
            duration_minutes=job["duration_minutes"],
            deadline=deadline,
            carbon_forecasts=carbon_forecasts
        )

        if greensched:

            emissions = calculate_emissions(
                energy_kwh=energy,
                carbon_intensity=
                    greensched["carbon_intensity"]
            )

            totals["greensched"] += emissions
            feasible["greensched"] += 1

            if greensched["finish_time"] > deadline:
                violations["greensched"] += 1

            job_result["greensched"] = {
                "region": greensched["region"],
                "carbon": greensched["carbon_intensity"],
                "emissions": emissions
            }

        else:

            job_result["greensched"] = None

        results.append(job_result)

    return totals, feasible, violations, results


# =========================================================
# PRINT JOB RESULTS
# =========================================================

def print_job_results(results):

    print("\n")
    print("-" * 130)
    print("PER-JOB RESULTS")
    print("-" * 130)

    print(
        f"{'Job':<9}"
        f"{'Release':<20}"
        f"{'Base gCO2':<14}"
        f"{'Temp gCO2':<14}"
        f"{'Spatial gCO2':<15}"
        f"{'GreenSched gCO2':<18}"
        f"{'GS Region'}"
    )

    print("-" * 130)

    for r in results:

        def value(policy, field):

            if r[policy] is None:
                return "N/A"

            return f"{r[policy][field]:.4f}"

        gs_region = (
            r["greensched"]["region"]
            if r["greensched"]
            else "N/A"
        )

        print(
            f"{r['name']:<9}"
            f"{str(r['release'].strftime('%H:%M')):<20}"
            f"{value('baseline', 'emissions'):<14}"
            f"{value('temporal', 'emissions'):<14}"
            f"{value('spatial', 'emissions'):<15}"
            f"{value('greensched', 'emissions'):<18}"
            f"{gs_region}"
        )


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 90)
    print("GreenSched Positive-Carbon Robustness Evaluation")
    print("=" * 90)

    print("\nIMPORTANT:")
    print(
        "Real NESO historical carbon-intensity data is used."
    )
    print(
        "Zero-carbon candidates are EXCLUDED, not modified."
    )
    print(
        "Workloads are synthetic and energy is estimated."
    )

    # -----------------------------------------------------
    # FETCH DATA
    # -----------------------------------------------------

    carbon_forecasts = get_historical_forecast()

    all_times = sorted(
        {
            slot["time"]
            for forecast in carbon_forecasts.values()
            for slot in forecast
        }
    )

    print(
        f"\nNESO slots available: {len(all_times)}"
    )

    print(
        f"First slot: {all_times[0]}"
    )

    print(
        f"Last slot:  {all_times[-1]}"
    )

    # -----------------------------------------------------
    # OVERALL RESULTS
    # -----------------------------------------------------

    overall = {
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

    successful_starts = 0

    # -----------------------------------------------------
    # SIX START TIMES
    # -----------------------------------------------------

    for offset in START_OFFSETS_HOURS:

        start_time = (
            all_times[0] +
            timedelta(hours=offset)
        )

        # Make sure the start exists in dataset
        if start_time not in all_times:

            closest = min(
                all_times,
                key=lambda t:
                    abs(t - start_time)
            )

            start_time = closest

        print("\n")
        print("=" * 90)
        print(
            f"START TIME: {start_time}"
        )
        print("=" * 90)

        totals, feasible, violations, results = (
            evaluate_start_time(
                start_time,
                carbon_forecasts
            )
        )

        # -------------------------------------------------
        # PER JOB RESULTS
        # -------------------------------------------------

        print_job_results(results)

        # -------------------------------------------------
        # SUMMARY
        # -------------------------------------------------

        print("\n")
        print("-" * 70)
        print("TOTAL EMISSIONS")
        print("-" * 70)

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

        # -------------------------------------------------
        # REDUCTION
        # -------------------------------------------------

        if totals["baseline"] > 0:

            print("\nReduction vs baseline:")

            print(
                f"Temporal-only:  "
                f"{(totals['baseline'] - totals['temporal']) / totals['baseline'] * 100:.2f}%"
            )

            print(
                f"Spatial-only:   "
                f"{(totals['baseline'] - totals['spatial']) / totals['baseline'] * 100:.2f}%"
            )

            print(
                f"GreenSched:     "
                f"{(totals['baseline'] - totals['greensched']) / totals['baseline'] * 100:.2f}%"
            )

        # -------------------------------------------------
        # FEASIBILITY
        # -------------------------------------------------

        print("\nFeasibility:")

        print(
            f"Baseline:       "
            f"{feasible['baseline']}/20"
        )

        print(
            f"Temporal-only:  "
            f"{feasible['temporal']}/20"
        )

        print(
            f"Spatial-only:   "
            f"{feasible['spatial']}/20"
        )

        print(
            f"GreenSched:     "
            f"{feasible['greensched']}/20"
        )

        # -------------------------------------------------
        # DEADLINE VIOLATIONS
        # -------------------------------------------------

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

        # -------------------------------------------------
        # ACCUMULATE
        # -------------------------------------------------

        for key in overall:

            overall[key] += totals[key]

            overall_feasible[key] += (
                feasible[key]
            )

            overall_violations[key] += (
                violations[key]
            )

        successful_starts += 1

    # =====================================================
    # OVERALL RESULTS
    # =====================================================

    print("\n\n")
    print("=" * 90)
    print("OVERALL POSITIVE-CARBON ROBUSTNESS RESULTS")
    print("=" * 90)

    print(
        f"\nSuccessful start times: "
        f"{successful_starts}/"
        f"{len(START_OFFSETS_HOURS)}"
    )

    print("\nTotal estimated emissions:")

    print(
        f"Baseline:       "
        f"{overall['baseline']:.4f} gCO2"
    )

    print(
        f"Temporal-only:  "
        f"{overall['temporal']:.4f} gCO2"
    )

    print(
        f"Spatial-only:   "
        f"{overall['spatial']:.4f} gCO2"
    )

    print(
        f"GreenSched:     "
        f"{overall['greensched']:.4f} gCO2"
    )

    # -----------------------------------------------------
    # OVERALL REDUCTION
    # -----------------------------------------------------

    if overall["baseline"] > 0:

        print("\nOverall reduction vs baseline:")

        print(
            f"Temporal-only:  "
            f"{(overall['baseline'] - overall['temporal']) / overall['baseline'] * 100:.2f}%"
        )

        print(
            f"Spatial-only:   "
            f"{(overall['baseline'] - overall['spatial']) / overall['baseline'] * 100:.2f}%"
        )

        print(
            f"GreenSched:     "
            f"{(overall['baseline'] - overall['greensched']) / overall['baseline'] * 100:.2f}%"
        )

    # -----------------------------------------------------
    # FEASIBILITY
    # -----------------------------------------------------

    total_jobs = (
        successful_starts *
        len(WORKLOAD)
    )

    print("\nOverall feasibility:")

    print(
        f"Baseline:       "
        f"{overall_feasible['baseline']}/"
        f"{total_jobs}"
    )

    print(
        f"Temporal-only:  "
        f"{overall_feasible['temporal']}/"
        f"{total_jobs}"
    )

    print(
        f"Spatial-only:   "
        f"{overall_feasible['spatial']}/"
        f"{total_jobs}"
    )

    print(
        f"GreenSched:     "
        f"{overall_feasible['greensched']}/"
        f"{total_jobs}"
    )

    # -----------------------------------------------------
    # DEADLINE VIOLATIONS
    # -----------------------------------------------------

    print("\nOverall deadline violations:")

    print(
        f"Baseline:       "
        f"{overall_violations['baseline']}"
    )

    print(
        f"Temporal-only:  "
        f"{overall_violations['temporal']}"
    )

    print(
        f"Spatial-only:   "
        f"{overall_violations['spatial']}"
    )

    print(
        f"GreenSched:     "
        f"{overall_violations['greensched']}"
    )

    print("\n" + "=" * 90)
    print("Evaluation completed.")
    print("=" * 90)


if __name__ == "__main__":
    main()