def calculate_energy_consumption(
    cpu: float,
    memory: float,
    duration_minutes: int
):
    """
    Estimate energy consumption of a cloud job.

    CPU is represented as number of CPU cores.
    Memory is represented in GB.
    Duration is represented in minutes.

    Returns energy consumption in kWh.
    """

    # Assumed power consumption
    CPU_POWER_WATTS = 50
    MEMORY_POWER_WATTS_PER_GB = 5

    # Calculate approximate power usage
    cpu_power = cpu * CPU_POWER_WATTS

    memory_power = memory * MEMORY_POWER_WATTS_PER_GB

    total_power_watts = cpu_power + memory_power

    # Convert duration from minutes to hours
    duration_hours = duration_minutes / 60

    # Energy = Power × Time
    energy_kwh = (
        total_power_watts * duration_hours
    ) / 1000

    return round(energy_kwh, 4)