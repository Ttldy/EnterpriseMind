import asyncio
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.database_agent.models import (
    Dataset,
    DatasetPermission,
)
from app.shared.database import SessionFactory

DATASETS = [
    {
        "name": "employee_directory",
        "view_name": "employee_directory_view",
        "description": "在职员工目录",
        "schema_text": (
            "employee_directory_view("
            "employee_no text, "
            "display_name text, "
            "department text, "
            "job_title text, "
            "employment_status text)"
        ),
        "allowed_columns": [
            "employee_no",
            "display_name",
            "department",
            "job_title",
            "employment_status",
        ],
        "keywords": [
            "员工名单",
            "员工目录",
            "在职员工",
            "岗位",
        ],
        "roles": ["hr_staff", "admin"],
    },
    {
        "name": "leave_statistics",
        "view_name": "leave_statistics_view",
        "description": "部门月度请假统计",
        "schema_text": (
            "leave_statistics_view("
            "department text, "
            "month text, "
            "leave_days numeric, "
            "employee_count integer)"
        ),
        "allowed_columns": [
            "department",
            "month",
            "leave_days",
            "employee_count",
        ],
        "keywords": [
            "请假统计",
            "请假趋势",
            "请假天数",
        ],
        "roles": ["hr_staff", "admin"],
    },
    {
        "name": "expense_summary",
        "view_name": "expense_summary_view",
        "description": "已审批报销汇总",
        "schema_text": (
            "expense_summary_view("
            "department text, "
            "month text, "
            "category text, "
            "total_amount numeric, "
            "claim_count bigint)"
        ),
        "allowed_columns": [
            "department",
            "month",
            "category",
            "total_amount",
            "claim_count",
        ],
        "keywords": [
            "报销统计",
            "报销金额",
            "各部门报销",
            "费用汇总",
        ],
        "roles": ["finance_staff", "admin"],
    },
    {
        "name": "it_ticket_statistics",
        "view_name": ("it_ticket_statistics_view"),
        "description": "部门月度 IT 工单统计",
        "schema_text": (
            "it_ticket_statistics_view("
            "department text, "
            "month text, "
            "category text, "
            "ticket_count integer, "
            "resolved_count integer)"
        ),
        "allowed_columns": [
            "department",
            "month",
            "category",
            "ticket_count",
            "resolved_count",
        ],
        "keywords": [
            "工单统计",
            "故障趋势",
            "解决率",
            "IT 工单",
        ],
        "roles": ["it_staff", "admin"],
    },
]


EMPLOYEES = [
    ("E001", "张敏", "HR", "HRBP", "ACTIVE"),
    ("E002", "李强", "HR", "招聘专员", "ACTIVE"),
    ("E003", "王磊", "IT", "运维工程师", "ACTIVE"),
    ("E004", "赵静", "IT", "后端工程师", "ACTIVE"),
    ("E005", "陈晨", "FINANCE", "会计", "ACTIVE"),
    ("E006", "刘洋", "FINANCE", "财务分析", "ACTIVE"),
    ("E007", "周宁", "SALES", "销售经理", "ACTIVE"),
    ("E008", "吴迪", "SALES", "客户经理", "ACTIVE"),
    ("E009", "孙悦", "R&D", "算法工程师", "ACTIVE"),
    ("E010", "郑伟", "R&D", "前端工程师", "ACTIVE"),
    ("E011", "冯雪", "GENERAL", "行政", "ACTIVE"),
    ("E012", "何平", "GENERAL", "助理", "ACTIVE"),
]

LEAVE_ROWS = [
    ("HR", "2026-06", Decimal("5.5"), 2),
    ("IT", "2026-06", Decimal("7.0"), 2),
    ("FINANCE", "2026-06", Decimal("4.0"), 2),
    ("SALES", "2026-06", Decimal("8.5"), 2),
    ("R&D", "2026-06", Decimal("6.0"), 2),
]

EXPENSE_ROWS = [
    (
        "C001",
        "HR",
        "2026-06",
        "差旅",
        Decimal("1800.00"),
        "APPROVED",
    ),
    (
        "C002",
        "IT",
        "2026-06",
        "设备",
        Decimal("8500.00"),
        "APPROVED",
    ),
    (
        "C003",
        "FINANCE",
        "2026-06",
        "差旅",
        Decimal("2300.00"),
        "APPROVED",
    ),
    (
        "C004",
        "SALES",
        "2026-06",
        "招待",
        Decimal("5200.00"),
        "APPROVED",
    ),
    (
        "C005",
        "R&D",
        "2026-06",
        "云服务",
        Decimal("12800.00"),
        "APPROVED",
    ),
    (
        "C006",
        "IT",
        "2026-06",
        "差旅",
        Decimal("900.00"),
        "REJECTED",
    ),
]

TICKET_ROWS = [
    ("HR", "2026-06", "账号", 8, 8),
    ("IT", "2026-06", "网络", 12, 10),
    ("FINANCE", "2026-06", "权限", 6, 6),
    ("SALES", "2026-06", "VPN", 15, 13),
    ("R&D", "2026-06", "开发环境", 11, 9),
]


async def seed_datasets(session) -> None:
    for item in DATASETS:
        dataset = await session.scalar(
            select(Dataset)
            .where(Dataset.name == item["name"])
            .options(selectinload(Dataset.permissions))
        )

        if dataset is None:
            dataset = Dataset(
                name=item["name"],
                view_name=item["view_name"],
                description=item["description"],
                schema_text=item["schema_text"],
                sensitivity="sensitive",
                allowed_columns=item["allowed_columns"],
                keywords=item["keywords"],
                is_active=True,
                permissions=[],
            )
            session.add(dataset)
            await session.flush()

        existing = {permission.subject_value for permission in dataset.permissions}

        for role in item["roles"]:
            if role not in existing:
                dataset.permissions.append(
                    DatasetPermission(
                        subject_type="ROLE",
                        subject_value=role,
                    )
                )


async def seed_business_rows(session) -> None:
    for row in EMPLOYEES:
        await session.execute(
            text(
                """
                INSERT INTO business_employees (
                    employee_no,
                    display_name,
                    department,
                    job_title,
                    employment_status
                )
                VALUES (
                    :employee_no,
                    :display_name,
                    :department,
                    :job_title,
                    :employment_status
                )
                ON CONFLICT (employee_no) DO NOTHING
                """
            ),
            {
                "employee_no": row[0],
                "display_name": row[1],
                "department": row[2],
                "job_title": row[3],
                "employment_status": row[4],
            },
        )

    for row in LEAVE_ROWS:
        await session.execute(
            text(
                """
                INSERT INTO business_leave_monthly (
                    department,
                    month,
                    leave_days,
                    employee_count
                )
                VALUES (
                    :department,
                    :month,
                    :leave_days,
                    :employee_count
                )
                ON CONFLICT (
                    department,
                    month
                ) DO NOTHING
                """
            ),
            {
                "department": row[0],
                "month": row[1],
                "leave_days": row[2],
                "employee_count": row[3],
            },
        )

    for row in EXPENSE_ROWS:
        await session.execute(
            text(
                """
                INSERT INTO business_expenses (
                    claim_no,
                    department,
                    month,
                    category,
                    amount,
                    status
                )
                VALUES (
                    :claim_no,
                    :department,
                    :month,
                    :category,
                    :amount,
                    :status
                )
                ON CONFLICT (claim_no) DO NOTHING
                """
            ),
            {
                "claim_no": row[0],
                "department": row[1],
                "month": row[2],
                "category": row[3],
                "amount": row[4],
                "status": row[5],
            },
        )

    for row in TICKET_ROWS:
        await session.execute(
            text(
                """
                INSERT INTO
                    business_it_tickets_monthly (
                        department,
                        month,
                        category,
                        ticket_count,
                        resolved_count
                    )
                VALUES (
                    :department,
                    :month,
                    :category,
                    :ticket_count,
                    :resolved_count
                )
                ON CONFLICT (
                    department,
                    month,
                    category
                ) DO NOTHING
                """
            ),
            {
                "department": row[0],
                "month": row[1],
                "category": row[2],
                "ticket_count": row[3],
                "resolved_count": row[4],
            },
        )


async def main() -> None:
    async with SessionFactory() as session:
        await seed_datasets(session)
        await seed_business_rows(session)
        await session.commit()

    print("stage2 demo data seeded")


if __name__ == "__main__":
    asyncio.run(main())
