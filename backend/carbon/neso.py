import requests
from datetime import datetime


NESO_BASE_URL = "https://api.carbonintensity.org.uk"


def get_current_carbon_intensity():
    """
    Get the latest real carbon intensity for Great Britain.
    """

    response = requests.get(
        f"{NESO_BASE_URL}/intensity",
        timeout=10
    )

    response.raise_for_status()

    data = response.json()["data"][0]

    return {
        "from": data["from"],
        "to": data["to"],
        "forecast": data["intensity"]["forecast"],
        "actual": data["intensity"]["actual"],
        "index": data["intensity"]["index"],
        "unit": "gCO2/kWh"
    }


def get_carbon_forecast():
    """
    Get the real 24-hour carbon-intensity forecast
    for Great Britain.

    Returns 48 half-hour forecast slots.
    """

    response = requests.get(
        f"{NESO_BASE_URL}/intensity/fw24h",
        timeout=10
    )

    response.raise_for_status()

    return response.json()["data"]


def get_regional_carbon_forecasts():
    """
    Get the real 24-hour regional carbon-intensity
    forecast from NESO.

    Only the 14 geographical regions are used
    for GreenSched spatial scheduling.

    Aggregate regions such as England, Scotland,
    Wales and GB are excluded.
    """

    response = requests.get(
        f"{NESO_BASE_URL}/regional/intensity/fw24h",
        timeout=10
    )

    response.raise_for_status()

    data = response.json()["data"]

    regional_forecasts = {}

    # The 14 geographical regions used for
    # spatial scheduling.
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

    for slot in data:

        slot_time = datetime.fromisoformat(
            slot["from"].replace("Z", "+00:00")
        )

        for region in slot["regions"]:

            region_name = region["shortname"]

            # Ignore aggregate regions such as
            # England, Scotland, Wales and GB.
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