from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..database.database import get_db
from ..database.models import Job

from ..scheduler.combined import find_best_schedule
from ..carbon.ml_forecaster import get_ml_carbon_forecasts


router = APIRouter(
    prefix="/scheduler",
    tags=["Scheduler"]
)


@router.post("/{job_id}")
def schedule_job(
    job_id: int,
    db: Session = Depends(get_db)
):

    # --------------------------------------------------------
    # Find job
    # --------------------------------------------------------

    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    # --------------------------------------------------------
    # Get ML carbon forecasts
    # --------------------------------------------------------

    try:

        carbon_forecasts = (
            get_ml_carbon_forecasts(
                hours=6,
                interval_minutes=30
            )
        )

    except Exception as e:

        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to generate ML carbon "
                f"forecast: {str(e)}"
            )
        )

    # --------------------------------------------------------
    # Current time
    # --------------------------------------------------------

    current_time = datetime.now(
        timezone.utc
    )

    # --------------------------------------------------------
    # Normalize deadline
    # --------------------------------------------------------

    deadline = job.deadline

    if deadline.tzinfo is None:

        deadline = deadline.replace(
            tzinfo=timezone.utc
        )

    # --------------------------------------------------------
    # Find lowest-carbon feasible schedule
    # --------------------------------------------------------

    decision = find_best_schedule(

        current_time=current_time,

        duration_minutes=
            job.duration_minutes,

        deadline=deadline,

        carbon_forecasts=
            carbon_forecasts
    )

    # --------------------------------------------------------
    # No feasible slot
    # --------------------------------------------------------

    if decision is None:

        return {

            "job_id": job.id,

            "job_name": job.name,

            "status":
                "NO_FEASIBLE_SLOT",

            "message": (
                "No feasible region and "
                "time combination was found "
                "before the deadline."
            ),

            "data_source":
                "NESO + Random Forest ML"
        }

    # --------------------------------------------------------
    # Save scheduling decision
    # --------------------------------------------------------

    job.status = "SCHEDULED"

    job.scheduled_region = (
        decision["region"]
    )

    job.scheduled_time = (
        decision["scheduled_time"]
    )

    job.finish_time = (
        decision["finish_time"]
    )

    job.predicted_carbon = (
        decision["carbon_intensity"]
    )

    db.commit()

    db.refresh(job)

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {

        "job_id": job.id,

        "job_name": job.name,

        "status": job.status,

        "region":
            job.scheduled_region,

        "scheduled_time":
            job.scheduled_time,

        "finish_time":
            job.finish_time,

        "carbon_intensity":
            job.predicted_carbon,

        "unit":
            "gCO2/kWh",

        "data_source":
            "NESO live data + Random Forest ML",

        "forecast_horizon":
            "6 hours",

        "decision": (
            "Lowest-carbon feasible "
            "region and time slot "
            "predicted by the ML "
            "carbon forecast while "
            "satisfying the job deadline."
        )
    }