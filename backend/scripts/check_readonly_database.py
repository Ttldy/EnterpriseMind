import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
)

from app.shared.config import get_settings


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.readonly_database_url)

    async with engine.connect() as connection:
        result = await connection.execute(
            text("SELECT department, total_amount " "FROM expense_summary_view " "LIMIT 2")
        )
        print([dict(row._mapping) for row in result.fetchall()])

        try:
            await connection.execute(text("UPDATE business_expenses " "SET amount = 0"))
        except Exception as exc:
            print("写操作按预期失败：" f"{type(exc).__name__}")
        else:
            raise RuntimeError("危险：只读账号竟然可以写入")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
