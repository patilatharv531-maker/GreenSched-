from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database.database import get_db
from ..database.models import Job, ExecutionFeedback


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("/")
def get_dashboard(db: Session = Depends(get_db)):

    total_jobs = db.query(Job).count()

    completed_jobs = (
        db.query(Job)
        .filter(Job.status == "COMPLETED")
        .count()
    )

    scheduled_jobs = (
        db.query(Job)
        .filter(Job.status == "SCHEDULED")
        .count()
    )

    running_jobs = (
        db.query(Job)
        .filter(Job.status == "RUNNING")
        .count()
    )

    total_energy = (
        db.query(func.sum(Job.actual_energy_kwh))
        .filter(Job.actual_energy_kwh.isnot(None))
        .scalar()
    )

    total_emissions = (
        db.query(func.sum(Job.actual_emissions_grams))
        .filter(Job.actual_emissions_grams.isnot(None))
        .scalar()
    )

    feedback_count = db.query(
        ExecutionFeedback
    ).count()

    return {
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "scheduled_jobs": scheduled_jobs,
        "running_jobs": running_jobs,
        "total_energy_kwh": round(total_energy or 0, 4),
        "total_emissions_grams": round(total_emissions or 0, 4),
        "feedback_records": feedback_count
    }


@router.get("/view", response_class=HTMLResponse)
def dashboard_view():

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GreenSched Dashboard</title>

        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                background: #f4f6f8;
                color: #222;
            }

            .header {
                background: #1f2937;
                color: white;
                padding: 25px 40px;
            }

            .header h1 {
                margin: 0;
            }

            .header p {
                margin-top: 8px;
                color: #d1d5db;
            }

            .container {
                padding: 30px 40px;
            }

            .cards {
                display: grid;
                grid-template-columns:
                    repeat(auto-fit, minmax(180px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }

            .card {
                background: white;
                padding: 22px;
                border-radius: 10px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }

            .card h3 {
                margin: 0;
                color: #6b7280;
                font-size: 14px;
            }

            .value {
                font-size: 30px;
                font-weight: bold;
                margin-top: 10px;
            }

            .section {
                background: white;
                padding: 25px;
                border-radius: 10px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }

            .status {
                display: inline-block;
                padding: 6px 12px;
                border-radius: 15px;
                background: #e5e7eb;
                margin-right: 8px;
            }

            .footer {
                margin-top: 25px;
                color: #6b7280;
                font-size: 13px;
            }
        </style>
    </head>

    <body>

        <div class="header">
            <h1>GreenSched</h1>
            <p>
                Carbon-Aware Job Scheduling Framework
                for Sustainable Cloud Data Centers
            </p>
        </div>

        <div class="container">

            <div class="cards">

                <div class="card">
                    <h3>Total Jobs</h3>
                    <div class="value" id="total_jobs">-</div>
                </div>

                <div class="card">
                    <h3>Completed Jobs</h3>
                    <div class="value" id="completed_jobs">-</div>
                </div>

                <div class="card">
                    <h3>Scheduled Jobs</h3>
                    <div class="value" id="scheduled_jobs">-</div>
                </div>

                <div class="card">
                    <h3>Running Jobs</h3>
                    <div class="value" id="running_jobs">-</div>
                </div>

                <div class="card">
                    <h3>Total Energy</h3>
                    <div class="value" id="energy">-</div>
                </div>

                <div class="card">
                    <h3>Total Emissions</h3>
                    <div class="value" id="emissions">-</div>
                </div>

            </div>

            <div class="section">

                <h2>GreenSched System Status</h2>

                <p>
                    <span class="status">
                        Carbon Data: NESO
                    </span>

                    <span class="status">
                        Scheduling: Active
                    </span>

                    <span class="status">
                        Feedback: Active
                    </span>
                </p>

                <p>
                    Feedback records:
                    <strong id="feedback">-</strong>
                </p>

            </div>

            <div class="footer">
                GreenSched | VIT Vellore
            </div>

        </div>


        <script>

            async function loadDashboard() {

                const response =
                    await fetch("/dashboard/");

                const data =
                    await response.json();

                document.getElementById(
                    "total_jobs"
                ).textContent = data.total_jobs;

                document.getElementById(
                    "completed_jobs"
                ).textContent = data.completed_jobs;

                document.getElementById(
                    "scheduled_jobs"
                ).textContent = data.scheduled_jobs;

                document.getElementById(
                    "running_jobs"
                ).textContent = data.running_jobs;

                document.getElementById(
                    "energy"
                ).textContent =
                    data.total_energy_kwh + " kWh";

                document.getElementById(
                    "emissions"
                ).textContent =
                    data.total_emissions_grams + " gCO₂";

                document.getElementById(
                    "feedback"
                ).textContent =
                    data.feedback_records;
            }

            loadDashboard();

        </script>

    </body>
    </html>
    """