from fastapi import FastAPI

from .database.database import engine, Base

from .api.jobs import router as jobs_router
from .api.carbon import router as carbon_router
from .api.scheduler import router as scheduler_router
from .api.execution import router as execution_router
from .api.dashboard import router as dashboard_router


# Create database tables
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="GreenSched",
    description="Carbon-Aware Job Scheduling Framework for Sustainable Cloud Data Centers",
    version="1.0.0"
)


# Register API routers
app.include_router(jobs_router)
app.include_router(carbon_router)
app.include_router(scheduler_router)
app.include_router(execution_router)
app.include_router(dashboard_router)


@app.get("/")
def root():
    return {
        "message": "GreenSched API is running",
        "status": "online"
    }