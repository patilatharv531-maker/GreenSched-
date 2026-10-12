import requests
import time

DATES = [
    "2026-10-03",
    "2026-10-02",
    "2026-10-01",
    "2026-09-30",
    "2026-09-29"
]

URL = "https://api.carbonintensity.org.uk/regional/intensity/{}/pt24h"

REGIONS = [
    "North West England",
    "North East England",
    "Yorkshire",
    "North Wales & Merseyside",
    "South Wales",
    "West Midlands",
    "East Midlands",
    "East England",
    "South West England",
    "South England",
    "London",
    "South East England"
]


for date in DATES:

    print("\n" + "=" * 60)
    print(f"Checking {date}")
    print("=" * 60)

    url = URL.format(date + "T12:00Z")

    try:
        response = requests.get(
            url,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()["data"]

        print(f"Slots returned: {len(data)}")

        for region in REGIONS:

            positive_count = 0
            zero_count = 0

            for slot in data:

                for item in slot["regions"]:

                    if item["shortname"] == region:

                        value = item["intensity"]["forecast"]

                        if value > 0:
                            positive_count += 1
                        else:
                            zero_count += 1

                        break

            print(
                f"{region:<30} "
                f"positive: {positive_count:2d} "
                f"zero: {zero_count:2d}"
            )

    except requests.exceptions.RequestException as e:

        print(f"ERROR: Could not retrieve {date}")
        print(f"Reason: {e}")

    # Small pause between requests
    time.sleep(2)


print("\nHistorical data check completed.")