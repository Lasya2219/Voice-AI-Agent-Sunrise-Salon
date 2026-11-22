import asyncio
from datetime import time

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.business import Business
from app.models.stylist import Stylist
from app.models.service import Service
from app.models.stylist_service import StylistService
from app.models.working_hours import WorkingHours


async def seed_database():

    async with AsyncSessionLocal.begin() as session:

        # 1. Create the business
        existing = await session.scalar(
            select(Business).where(Business.slug == "sunrise-salon")
        )

        if existing:
            print("Sunrise Salon already exists. Skipping seed.")
            return

        business = Business(
            name="Sunrise Salon",
            slug="sunrise-salon",
            address="12 Lake Road, Indiranagar, Bengaluru",
            timezone="Asia/Kolkata",
            slot_duration_minutes=30,
            cancellation_window_minutes=120
        )

        session.add(business)
        await session.flush()

        # 2. Create stylists
        anita = Stylist(business_id=business.id, name="Anita")
        rahul = Stylist(business_id=business.id, name="Rahul")
        kavya = Stylist(business_id=business.id, name="Kavya")

        session.add_all([anita, rahul, kavya])
        await session.flush()

        # 3. Create services
        services = [
            Service(
                business_id=business.id,
                name="Women's Haircut",
                price=600,
                duration_minutes=30
            ),
            Service(
                business_id=business.id,
                name="Men's Haircut",
                price=400,
                duration_minutes=30
            ),
            Service(
                business_id=business.id,
                name="Blow Dry / Styling",
                price=500,
                duration_minutes=30
            ),
            Service(
                business_id=business.id,
                name="Hair Colour",
                price=2500,
                is_price_from=True,
                duration_minutes=30,
                notes="Final price depends on hair length."
            ),
            Service(
                business_id=business.id,
                name="Hair Spa",
                price=1200,
                duration_minutes=30
            ),
            Service(
                business_id=business.id,
                name="Facial",
                price=1500,
                duration_minutes=30
            ),
            Service(
                business_id=business.id,
                name="Clean-up",
                price=800,
                duration_minutes=30
            )
        ]

        session.add_all(services)
        await session.flush()

        # 4. Assign services to stylists
        assignments = [
            (anita, services[0]),
            (anita, services[1]),
            (anita, services[2]),
            (rahul, services[3]),
            (rahul, services[4]),
            (kavya, services[5]),
            (kavya, services[6])
        ]

        for stylist, service in assignments:
            session.add(
                StylistService(
                    business_id=business.id,
                    stylist_id=stylist.id,
                    service_id=service.id
                )
            )

        # 5. Add stylist working schedules
        schedules = [
            # Anita: Monday to Saturday, 10 AM - 2 PM
            (anita, [0, 1, 2, 3, 4, 5], time(10, 0), time(14, 0)),

            # Rahul: Tuesday, Thursday, Saturday, 4 PM - 8 PM
            (rahul, [1, 3, 5], time(16, 0), time(20, 0)),

            # Kavya: Monday, Wednesday, Friday, 9 AM - 1 PM
            (kavya, [0, 2, 4], time(9, 0), time(13, 0))
        ]

        for stylist, weekdays, start, end in schedules:
            for weekday in weekdays:
                session.add(
                    WorkingHours(
                        business_id=business.id,
                        stylist_id=stylist.id,
                        weekday=weekday,
                        start_time=start,
                        end_time=end
                    )
                )

    print("Sunrise Salon data seeded successfully!")


if __name__ == "__main__":
    async def main():
        try:
            await seed_database()
        finally:
            from app.database import engine
            await engine.dispose()

    asyncio.run(main())