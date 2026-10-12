from fastapi import APIRouter, HTTPException

from ..carbon.simulator import (
    get_available_regions,
    get_current_carbon_intensity,
    get_carbon_forecast
)


router = APIRouter(
    prefix="/carbon",
    tags=["Carbon"]
)


@router.get("/regions")
def get_regions():

    return {
        "regions": get_available_regions()
    }


@router.get("/current/{region}")
def get_current_carbon(region: str):

    try:

        carbon = get_current_carbon_intensity(region)

        return {
            "region": region,
            "carbon_intensity": carbon,
            "unit": "gCO2/kWh"
        }

    except ValueError as e:

        raise HTTPException(
            status_code=404,
            detail=str(e)
        )


@router.get("/forecast/{region}")
def get_forecast(region: str):

    try:

        forecast = get_carbon_forecast(region)

        return {
            "region": region,
            "forecast": forecast
        }

    except ValueError as e:

        raise HTTPException(
            status_code=404,
            detail=str(e)
        )