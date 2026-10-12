def calculate_emissions(
    energy_kwh: float,
    carbon_intensity: float
):
    """
    Calculate CO2 emissions for a cloud job.

    energy_kwh:
        Energy consumed by the job in kWh.

    carbon_intensity:
        Carbon intensity of the selected region
        in grams of CO2 per kWh.

    Returns CO2 emissions in grams.
    """

    emissions_grams = energy_kwh * carbon_intensity

    return round(emissions_grams, 4)