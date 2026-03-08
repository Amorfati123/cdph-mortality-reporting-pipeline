print("HELLO FROM TEST SCRIPT", flush=True)
import requests

BASE_URL = "https://data.chhs.ca.gov/api/3/action/datastore_search"
RESOURCE_ID = "3192c0ff-e380-4314-8a88-16a3bdace8b7"

print("Starting API test...")

try:
    response = requests.get(
        BASE_URL,
        params={"resource_id": RESOURCE_ID, "limit": 5},
        timeout=30
    )

    print("HTTP status:", response.status_code)
    print("Final URL:", response.url)
    print("First 500 characters of response:")
    print(response.text[:500])

    response.raise_for_status()
    payload = response.json()

    print("Success flag:", payload.get("success"))
    print("Number of records returned:", len(payload["result"]["records"]))

except Exception as e:
    print("API test failed:")
    print(repr(e))