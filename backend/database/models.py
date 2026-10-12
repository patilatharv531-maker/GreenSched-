from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime

from .database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    cpu = Column(Float, nullable=False)

    memory = Column(Float, nullable=False)

    duration_minutes = Column(Integer, nullable=False)

    deadline = Column(DateTime, nullable=False)

    priority = Column(String, nullable=False)

    status = Column(String, default="PENDING")

    scheduled_region = Column(String, nullable=True)

    scheduled_time = Column(DateTime, nullable=True)

    finish_time = Column(DateTime, nullable=True)

    predicted_carbon = Column(Float, nullable=True)

    actual_energy_kwh = Column(Float, nullable=True)

    actual_emissions_grams = Column(Float, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class ExecutionFeedback(Base):
    __tablename__ = "execution_feedback"

    id = Column(Integer, primary_key=True, index=True)

    job_id = Column(Integer, nullable=False)

    region = Column(String, nullable=False)

    predicted_carbon = Column(Float, nullable=False)

    actual_energy_kwh = Column(Float, nullable=False)

    actual_emissions_grams = Column(Float, nullable=False)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )