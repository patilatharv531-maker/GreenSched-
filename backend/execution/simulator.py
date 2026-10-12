import time


def execute_job(
    job_name: str,
    duration_minutes: int
):
    """
    Simulate the execution of a cloud job.

    For development purposes, each simulated minute
    is represented by one second.
    """

    print(f"Starting job: {job_name}")

    simulated_seconds = duration_minutes

    for minute in range(simulated_seconds):

        print(
            f"Job '{job_name}' running... "
            f"{minute + 1}/{duration_minutes} minutes"
        )

        time.sleep(1)

    print(f"Job '{job_name}' completed successfully.")

    return {
        "job_name": job_name,
        "duration_minutes": duration_minutes,
        "status": "COMPLETED"
    }