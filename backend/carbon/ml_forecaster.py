import os
import joblib
import pandas as pd
import requests
from sklearn.ensemble import RandomForestRegressor


# ============================================================
# CONFIGURATION
# ============================================================

DATA_PATH = "data/regional_carbon_intensity.csv"

MODEL_PATH = "backend/carbon/greensched_rf.joblib"

NESO_BASE_URL = "https://api.carbonintensity.org.uk"


REGIONS = [
    "North West England",
    "North East England",
    "Yorkshire",
    "North Wales and Merseyside",
    "South Wales",
    "West Midlands",
    "East Midlands",
    "East England",
    "South West England",
    "South England",
    "London",
    "South East England"
]


FEATURES = [
    "carbon",
    "lag_1",
    "lag_2",
    "lag_4",
    "hour",
    "minute",
    "day_of_week"
]


# ============================================================
# PREPARE TRAINING DATA
# ============================================================

def prepare_training_data():

    df = pd.read_csv(DATA_PATH)

    df["datetime"] = pd.to_datetime(
        df["datetime"]
    )

    parts = []

    for region in REGIONS:

        region_df = df[
            ["datetime", region]
        ].copy()

        region_df = region_df.rename(
            columns={
                region: "carbon"
            }
        )

        region_df["region"] = region

        parts.append(region_df)

    data = pd.concat(
        parts,
        ignore_index=True
    )

    data = data.sort_values(
        ["region", "datetime"]
    )

    # Lag features
    data["lag_1"] = (
        data.groupby("region")["carbon"]
        .shift(1)
    )

    data["lag_2"] = (
        data.groupby("region")["carbon"]
        .shift(2)
    )

    data["lag_4"] = (
        data.groupby("region")["carbon"]
        .shift(4)
    )

    # Target: next 30-minute value
    data["target"] = (
        data.groupby("region")["carbon"]
        .shift(-1)
    )

    # Time features
    data["hour"] = (
        data["datetime"].dt.hour
    )

    data["minute"] = (
        data["datetime"].dt.minute
    )

    data["day_of_week"] = (
        data["datetime"].dt.dayofweek
    )

    # Remove incomplete rows
    data = data.dropna()

    data = data.reset_index(
        drop=True
    )

    # One-hot encode regions
    data = pd.get_dummies(
        data,
        columns=["region"],
        dtype=int
    )

    region_features = [
        column
        for column in data.columns
        if column.startswith("region_")
    ]

    feature_columns = (
        FEATURES +
        region_features
    )

    return data, feature_columns


# ============================================================
# TRAIN AND SAVE MODEL
# ============================================================

def train_and_save_model():

    print(
        "Loading NESO historical dataset..."
    )

    data, feature_columns = (
        prepare_training_data()
    )

    print(
        f"Training samples: {len(data)}"
    )

    print(
        f"Features: {len(feature_columns)}"
    )

    print(
        "Training Random Forest..."
    )

    X = data[feature_columns]

    y = data["target"]

    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=12,
        random_state=42,
        n_jobs=-1
    )

    model.fit(
        X,
        y
    )

    os.makedirs(
        os.path.dirname(MODEL_PATH),
        exist_ok=True
    )

    joblib.dump(
        {
            "model": model,
            "features": feature_columns,
            "regions": REGIONS
        },
        MODEL_PATH
    )

    print()
    print(
        "Model training completed."
    )

    print(
        f"Model saved to: {MODEL_PATH}"
    )


# ============================================================
# GET CURRENT REGIONAL NESO DATA
# ============================================================

def get_current_regional_carbon():

    response = requests.get(
        f"{NESO_BASE_URL}/regional/intensity/fw24h",
        timeout=30
    )

    response.raise_for_status()

    data = response.json()["data"]

    if not data:

        raise RuntimeError(
            "NESO returned no regional carbon data."
        )

    # First available half-hour slot
    current_slot = data[0]

    current_time = pd.to_datetime(
        current_slot["from"]
    )

    current_values = {}

    for region in current_slot["regions"]:

        region_name = region["shortname"]

        if region_name not in REGIONS:
            continue

        intensity = region["intensity"]

        carbon = intensity.get(
            "actual"
        )

        if carbon is None:

            carbon = intensity.get(
                "forecast"
            )

        if carbon is None:
            continue

        current_values[region_name] = {
            "carbon": float(carbon),
            "time": current_time
        }

    return current_values


# ============================================================
# GENERATE ML FORECAST
# ============================================================

def get_ml_carbon_forecasts(
    hours=2,
    interval_minutes=30
):

    # Load saved model
    saved_model = joblib.load(
        MODEL_PATH
    )

    model = saved_model["model"]

    feature_columns = (
        saved_model["features"]
    )

    regions = saved_model["regions"]

    print(
        "Fetching current regional carbon data..."
    )

    current_values = (
        get_current_regional_carbon()
    )

    if not current_values:

        raise RuntimeError(
            "No regional carbon data "
            "was received from NESO."
        )

    forecasts = {}

    slots = int(
        (hours * 60) /
        interval_minutes
    )

    # --------------------------------------------------------
    # Generate predictions for each region
    # --------------------------------------------------------

    for region in regions:

        if region not in current_values:

            print(
                f"Skipping {region}: "
                "no current NESO value."
            )

            continue

        current_carbon = (
            current_values[region]["carbon"]
        )

        current_time = (
            current_values[region]["time"]
        )

        # Load historical values for lag features
        historical = pd.read_csv(
            DATA_PATH,
            usecols=[
                "datetime",
                region
            ]
        )

        historical["datetime"] = (
            pd.to_datetime(
                historical["datetime"]
            )
        )

        historical = historical.dropna()

        # Last three historical values
        previous_values = list(
            historical[region].iloc[-3:]
        )

        # Add current live NESO value
        recent_values = (
            previous_values +
            [current_carbon]
        )

        region_forecast = []

        # ----------------------------------------------------
        # Recursive forecasting
        # ----------------------------------------------------

        for i in range(slots):

            prediction_time = (
                current_time
                + pd.Timedelta(
                    minutes=(
                        (i + 1)
                        * interval_minutes
                    )
                )
            )

            row = {
                "carbon":
                    recent_values[-1],

                "lag_1":
                    recent_values[-2],

                "lag_2":
                    recent_values[-3],

                "lag_4":
                    recent_values[-4],

                "hour":
                    prediction_time.hour,

                "minute":
                    prediction_time.minute,

                "day_of_week":
                    prediction_time.dayofweek
            }

            # Region encoding
            for model_region in regions:

                row[
                    f"region_{model_region}"
                ] = (
                    1
                    if model_region == region
                    else 0
                )

            X = pd.DataFrame(
                [row]
            )

            X = X[
                feature_columns
            ]

            prediction = (
                model.predict(X)[0]
            )

            prediction = max(
                0,
                float(prediction)
            )

            prediction = round(
                prediction,
                2
            )

            region_forecast.append(
                {
                    "time":
                        prediction_time,

                    "carbon_intensity":
                        prediction
                }
            )

            # Use prediction as input
            # for the next time step
            recent_values.append(
                prediction
            )

            recent_values = (
                recent_values[-4:]
            )

        forecasts[region] = (
            region_forecast
        )

    return forecasts


# ============================================================
# TEST ML FORECASTER
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "Generating 2-hour ML forecast "
        "from LIVE NESO data..."
    )

    forecasts = get_ml_carbon_forecasts(
        hours=2,
        interval_minutes=30
    )

    print()

    for region, forecast in (
        forecasts.items()
    ):

        print(
            f"--- {region} ---"
        )

        for slot in forecast:

            print(
                slot["time"],
                "->",
                slot["carbon_intensity"],
                "gCO2/kWh"
            )

        print()