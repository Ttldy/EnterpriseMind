import pytest

from app.database_agent.validator import (
    SqlPolicy,
    UnsafeSqlError,
    validate_sql,
)

POLICY = SqlPolicy(
    views=frozenset({"expense_summary_view"}),
    columns=frozenset(
        {
            "department",
            "month",
            "category",
            "total_amount",
            "claim_count",
        }
    ),
    max_rows=200,
)


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE users",
        ("UPDATE expense_summary_view " "SET total_amount = 0"),
        "DELETE FROM expense_summary_view",
        ("SELECT department " "FROM expense_summary_view; " "SELECT 1"),
        ("SELECT secret_column " "FROM expense_summary_view"),
        ("SELECT department " "FROM pg_catalog.pg_tables"),
        "SELECT pg_sleep(30)",
        "SELECT * FROM expense_summary_view",
        ("SELECT department " "FROM public.expense_summary_view"),
        ("SELECT department " "FROM expense_summary_view -- bypass"),
    ],
)
def test_rejects_unsafe_sql(
    sql: str,
) -> None:
    with pytest.raises(UnsafeSqlError):
        validate_sql(sql, POLICY)


def test_adds_limit_to_safe_select() -> None:
    sql = validate_sql(
        ("SELECT department, total_amount " "FROM expense_summary_view"),
        POLICY,
    )

    assert sql.endswith("LIMIT 200")


def test_clamps_excessive_limit() -> None:
    sql = validate_sql(
        ("SELECT department, total_amount " "FROM expense_summary_view " "LIMIT 9999"),
        POLICY,
    )

    assert sql.endswith("LIMIT 200")


def test_allows_safe_aggregate() -> None:
    sql = validate_sql(
        (
            "SELECT department, "
            "SUM(total_amount) AS total_amount "
            "FROM expense_summary_view "
            "GROUP BY department"
        ),
        POLICY,
    )

    assert "SUM(total_amount)" in sql
