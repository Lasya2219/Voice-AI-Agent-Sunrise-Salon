
import asyncio
import httpx

URL = "http://localhost:8000/api/bookings"

booking_data = {
    "business_slug": "sunrise-salon",
    "customer_name": "Concurrency Test",
    "customer_phone": "9876543210",
    "service_id": 6,
    "stylist_id": 3,
    "start_time": "2026-11-23T09:00:00+05:30"
}

async def make_booking(client, caller):
    response = await client.post(URL, json=booking_data)
    print(f"\nCaller {caller}: HTTP {response.status_code}")
    print(response.json())
    return response

async def main():
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            make_booking(client, 1),
            make_booking(client, 2)
        )

    successes = sum(
        1 for r in results
        if r.status_code == 200 and r.json().get("success") is True
    )

    print("\nSuccessful bookings:", successes)
    print("Expected: exactly 1")

asyncio.run(main())
