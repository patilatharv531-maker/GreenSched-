# GreenSched: Carbon-Aware Job Scheduling Framework

GreenSched is a cloud computing project that explores how computational jobs can be scheduled across different regions and time slots to reduce estimated carbon emissions while respecting job deadlines.

## Overview

Traditional job schedulers often prioritize execution time and resource availability. GreenSched adds carbon intensity to the scheduling decision, helping identify feasible execution windows and regions with lower-carbon electricity.

## Features

- **Carbon intensity integration:** Retrieves carbon intensity information using the NESO Carbon Intensity API.
- **Machine learning forecasting:** Uses a Random Forest model trained on historical regional carbon intensity data.
- **Carbon-aware scheduling:** Evaluates candidate regions and execution times while considering job deadlines.
- **Job management API:** Creates and tracks scheduled jobs through FastAPI.
- **Execution simulation:** Simulates job execution and estimates energy consumption and carbon emissions.
- **Feedback storage:** Stores execution results in a database.
- **Evaluation scripts:** Compares scheduling strategies using historical carbon intensity data.
- **Interactive API documentation:** Provides Swagger UI through FastAPI.

## Technology Stack

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Scikit-learn
- Random Forest
- Pandas and NumPy
- NESO Carbon Intensity API
- Uvicorn

## System Workflow

1. Submit a computational job through the API.
2. Retrieve carbon intensity data and generate forecasts.
3. Evaluate feasible regions and execution times.
4. Select a schedule that considers carbon intensity and the job deadline.
5. Simulate execution.
6. Estimate energy consumption and carbon emissions.
7. Store the results and execution feedback.

## Project Structure

```text
GreenSched/
├── backend/
│   └── carbon/
│       ├── greensched_rf.joblib
│       ├── ml_forecaster.py
│       ├── neso.py
│       └── simulator.py
├── data/
│   └── regional_carbon_intensity.csv
├── check_historical_data.py
├── evaluation.py
├── evaluation_comparison.py
├── evaluation_historical.py
├── evaluation_historical_fourway.py
├── evaluation_multisnapshot.py
├── evaluation_multistart.py
├── evaluation_real.py
├── realistic_workload_evaluation.py
├── requirements.txt
└── README.md
```

## Running the Project

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd GreenSched
```

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Start the FastAPI application

Run the following command from the project root, adjusting the module path if your FastAPI application is located elsewhere:

```powershell
uvicorn backend.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to access Swagger UI.

## Evaluation

GreenSched includes scripts for comparing scheduling strategies using historical carbon intensity data. Results depend on the dataset, workload, time window, and scheduling assumptions.

## Important Note

Job execution is simulated. Energy consumption and carbon emissions are estimates based on configured resource assumptions; they are not measurements from a physical data center.

## Data and Attribution

The project uses historical regional carbon intensity data and the NESO Carbon Intensity API. Refer to the relevant data provider's terms and attribution requirements when using or redistributing the data.

## Future Improvements

- Validate forecasting performance on unseen time periods.
- Evaluate scheduling across more workload types and deadlines.
- Integrate measured energy consumption from real execution environments.
- Extend evaluation to additional regions and carbon intensity sources.

## License

No license has been specified yet. All rights remain with the project authors unless a license is added.
