def find_cleanest_region(
    regions: list,
    carbon_data: dict
):
    """
    Find the region with the lowest carbon intensity.
    """

    best_region = None
    best_carbon = float("inf")

    for region in regions:

        carbon_intensity = carbon_data.get(region)

        if carbon_intensity is None:
            continue

        if carbon_intensity < best_carbon:
            best_carbon = carbon_intensity
            best_region = region

    if best_region is None:
        return None

    return {
        "region": best_region,
        "carbon_intensity": best_carbon
    }