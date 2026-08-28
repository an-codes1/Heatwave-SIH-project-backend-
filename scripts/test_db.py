import asyncio

from sqlalchemy import text

from app.db.session import engine


async def main() -> None:
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))

            print("Database connection successful!")
            print("Test result:", result.scalar())

    except Exception as exc:
        print("Database connection failed.")
        print("Error:", exc)

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())