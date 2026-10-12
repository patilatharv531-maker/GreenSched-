from datetime import datetime, timedelta


# Simulated carbon intensity values
# Unit: grams of CO2 per kWh
CARBON_DATA = {
    "Mumbai": 650,
    "Singapore": 420,
    "Oregon": 280,
    "Ireland": 240,
}


def get_current_carbon_intensity(region: str) -> float:
    """
    Return the current simulated carbon intensity
    for a given region.
    """

    if region not in CARBON_DATA:
        raise ValueError(f"Unknown region: {region}")

    return CARBON_DATA[region]


def get_available_regions():
    """
    Return all regions supported by GreenSched.
    """

    return list(CARBON_DATA.keys())


def get_carbon_forecast(
    region: str,
    slots: int = 6,
    interval_minutes: int = 30
):
    """
    Generate a simple short-horizon carbon forecast.

    Returns carbon-intensity predictions for future
    time slots.
    """

    if region not in CARBON_DATA:
        raise ValueError(f"Unknown region: {region}")

    base_value = CARBON_DATA[region]

    forecast = []

    current_time = datetime.now()

    # Simple simulated variation pattern
    variation = [0, -20, -40, -70, -50, -10]

    for i in range(slots):

        future_time = current_time + timedelta(
            minutes=i * interval_minutes
        )

        carbon_value = base_value + variation[i % len(variation)]

        forecast.append({
            "region": region,
            "time": future_time,
            "carbon_intensity": max(carbon_value, 50)
        })

    return forecast

if __name__ == "__main__":

    print("Available regions:")
    print(get_available_regions())

    print("\nCurrent carbon intensity:")

    for region in get_available_regions():
        value = get_current_carbon_intensity(region)
        print(f"{region}: {value} gCO2/kWh")

    print("\nCarbon forecast for Ireland:")

    forecast = get_carbon_forecast("Ireland")

    for item in forecast:
        print(item)