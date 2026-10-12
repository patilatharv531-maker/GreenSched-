from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from ..database.database import get_db
from ..database.models import Job


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)


class JobCreate(BaseModel):
    name: str
    cpu: float
    memory: float
    duration_minutes: int
    deadline: datetime
    priority: str


@router.post("/")
def create_job(
    job_data: JobCreate,
    db: Session = Depends(get_db)
):

    job = Job(
        name=job_data.name,
        cpu=job_data.cpu,
        memory=job_data.memory,
        duration_minutes=job_data.duration_minutes,
        deadline=job_data.deadline,
        priority=job_data.priority
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "message": "Job created successfully",
        "job_id": job.id,
        "job": {
            "name": job.name,
            "cpu": job.cpu,
            "memory": job.memory,
            "duration_minutes": job.duration_minutes,
            "deadline": job.deadline,
            "priority": job.priority,
            "status": job.status
        }
    }


@router.get("/")
def get_jobs(db: Session = Depends(get_db)):

    jobs = db.query(Job).all()

    return [
        {
            "id": job.id,
            "name": job.name,
            "cpu": job.cpu,
            "memory": job.memory,
            "duration_minutes": job.duration_minutes,
            "deadline": job.deadline,
            "priority": job.priority,
            "status": job.status,
            "scheduled_region": job.scheduled_region,
            "scheduled_time": job.scheduled_time,
            "finish_time": job.finish_time,
            "predicted_carbon": job.predicted_carbon,
            "actual_energy_kwh": job.actual_energy_kwh,
            "actual_emissions_grams": job.actual_emissions_grams,
            "created_at": job.created_at
        }
        for job in jobs
    ]