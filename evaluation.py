from datetime import datetime, timedelta

from backend.carbon.simulator import (
    get_available_regions,
    get_carbon_forecast
)

from backend.scheduler.baseline import (
    find_baseline_schedule
)

from backend.scheduler.combined import (
    find_best_schedule
)

from backend.emissions.energy import (
    calculate_energy_consumption
)

from backend.emissions.emissions import (
    calculate_emissions
)


# -----------------------------------------
# Job configuration
# -----------------------------------------

CPU = 2
MEMORY = 4
DURATION_MINUTES = 5

current_time = datetime.now()

deadline = current_time + timedelta(hours=1)


# -----------------------------------------
# Generate shared carbon forecasts
# -----------------------------------------

carbon_forecasts = {}

for region in get_available_regions():

    carbon_forecasts[region] = get_carbon_forecast(
        region,
        slots=6,
        interval_minutes=30
    )


# -----------------------------------------
# Run baseline scheduler
# -----------------------------------------

baseline_result = find_baseline_schedule(
    current_time=current_time,
    duration_minutes=DURATION_MINUTES,
    deadline=deadline,
    carbon_forecasts=carbon_forecasts
)


# -----------------------------------------
# Run GreenSched
# -----------------------------------------

greensched_result = find_best_schedule(
    current_time=current_time,
    duration_minutes=DURATION_MINUTES,
    deadline=deadline,
    carbon_forecasts=carbon_forecasts
)


# -----------------------------------------
# Calculate energy consumption
# -----------------------------------------

energy_kwh = calculate_energy_consumption(
    cpu=CPU,
    memory=MEMORY,
    duration_minutes=DURATION_MINUTES
)


# -----------------------------------------
# Calculate emissions
# -----------------------------------------

baseline_emissions = calculate_emissions(
    energy_kwh=energy_kwh,
    carbon_intensity=baseline_result["carbon_intensity"]
)


greensched_emissions = calculate_emissions(
    energy_kwh=energy_kwh,
    carbon_intensity=greensched_result["carbon_intensity"]
)


# -----------------------------------------
# Calculate emission reduction
# -----------------------------------------

emission_reduction = (
    (baseline_emissions - greensched_emissions)
    / baseline_emissions
) * 100


# -----------------------------------------
# Display results
# -----------------------------------------

print()
print("==============================================")
print("        GreenSched Evaluation")
print("==============================================")

print()
print("JOB")
print("----------------------------------------------")
print(f"CPU:              {CPU}")
print(f"Memory:           {MEMORY} GB")
print(f"Duration:         {DURATION_MINUTES} minutes")
print(f"Energy:           {energy_kwh} kWh")

print()
print("BASELINE SCHEDULER")
print("----------------------------------------------")
print(f"Region:           {baseline_result['region']}")
print(f"Scheduled time:   {baseline_result['scheduled_time']}")
print(f"Carbon intensity: {baseline_result['carbon_intensity']} gCO2/kWh")
print(f"Emissions:        {baseline_emissions} gCO2")

print()
print("GREENSCHED")
print("----------------------------------------------")
print(f"Region:           {greensched_result['region']}")
print(f"Scheduled time:   {greensched_result['scheduled_time']}")
print(f"Carbon intensity: {greensched_result['carbon_intensity']} gCO2/kWh")
print(f"Emissions:        {greensched_emissions} gCO2")

print()
print("RESULT")
print("----------------------------------------------")
print(f"Emission reduction: {emission_reduction:.2f}%")

print()
print("==============================================")