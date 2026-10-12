from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..database.models import Job, ExecutionFeedback
from ..execution.simulator import execute_job
from ..emissions.energy import calculate_energy_consumption
from ..emissions.emissions import calculate_emissions


router = APIRouter(
    prefix="/execution",
    tags=["Execution"]
)


@router.post("/{job_id}")
def run_job(
    job_id: int,
    db: Session = Depends(get_db)
):

    # Find the job
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    # Job must be scheduled before execution
    if job.status != "SCHEDULED":
        raise HTTPException(
            status_code=400,
            detail="Job must be SCHEDULED before execution"
        )

    # Mark job as running
    job.status = "RUNNING"
    db.commit()

    # Execute the simulated job
    result = execute_job(
        job_name=job.name,
        duration_minutes=job.duration_minutes
    )

    # Calculate energy consumption
    energy_kwh = calculate_energy_consumption(
        cpu=job.cpu,
        memory=job.memory,
        duration_minutes=job.duration_minutes
    )

    # Calculate CO2 emissions
    emissions_grams = calculate_emissions(
        energy_kwh=energy_kwh,
        carbon_intensity=job.predicted_carbon
    )

    # Save execution metrics in Job
    job.actual_energy_kwh = energy_kwh
    job.actual_emissions_grams = emissions_grams

    # -------------------------------------------------
    # FEEDBACK LOOP
    # -------------------------------------------------

    feedback = ExecutionFeedback(
        job_id=job.id,
        region=job.scheduled_region,
        predicted_carbon=job.predicted_carbon,
        actual_energy_kwh=energy_kwh,
        actual_emissions_grams=emissions_grams
    )

    db.add(feedback)

    # Mark job as completed
    job.status = "COMPLETED"

    db.commit()
    db.refresh(job)

    return {
        "job_id": job.id,
        "job_name": job.name,
        "status": job.status,
        "duration_minutes": job.duration_minutes,
        "region": job.scheduled_region,
        "scheduled_time": job.scheduled_time,
        "finish_time": job.finish_time,
        "predicted_carbon": job.predicted_carbon,
        "actual_energy_kwh": job.actual_energy_kwh,
        "actual_emissions_grams": job.actual_emissions_grams,
        "feedback_recorded": True
    }