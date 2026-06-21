from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError


class UnsafeSqlError(ValueError):
    pass


@dataclass(frozen=True)
class SqlPolicy:
    views: frozenset[str]
    columns: frozenset[str]
    max_rows: int = 200


_ALLOWED_FUNCTIONS = frozenset(
    {
        "avg",
        "coalesce",
        "count",
        "date_trunc",
        "max",
        "min",
        "round",
        "sum",
    }
)


def validate_sql(
    sql: str,
    policy: SqlPolicy,
) -> str:
    normalized = sql.strip()
    _reject_comments(normalized)

    try:
        statements = sqlglot.parse(
            normalized,
            read="postgres",
        )
    except ParseError as exc:
        raise UnsafeSqlError("SQL 语法无法解析") from exc

    if len(statements) != 1:
        raise UnsafeSqlError("只允许执行一条 SQL")

    tree = statements[0]
    if not isinstance(
        tree,
        exp.Select | exp.Union,
    ):
        raise UnsafeSqlError("只允许 SELECT 查询")

    if tree.find(exp.Star) is not None:
        raise UnsafeSqlError("禁止 SELECT *，必须显式选择字段")

    if tree.find(exp.Offset) is not None:
        raise UnsafeSqlError("阶段 2 禁止 OFFSET")

    cte_names = {cte.alias_or_name for cte in tree.find_all(exp.CTE)}
    tables = {table.name for table in tree.find_all(exp.Table) if table.name not in cte_names}
    if not tables:
        raise UnsafeSqlError("查询必须引用授权视图")
    if not tables <= policy.views:
        raise UnsafeSqlError("查询引用了未授权视图")

    for table in tree.find_all(exp.Table):
        if table.catalog or table.db:
            raise UnsafeSqlError("禁止跨数据库或跨 Schema 查询")

    columns = {column.name for column in tree.find_all(exp.Column)}
    if not columns <= policy.columns:
        raise UnsafeSqlError("查询引用了未授权字段")

    functions = {function.key.lower() for function in tree.find_all(exp.Func)}
    if not functions <= _ALLOWED_FUNCTIONS:
        raise UnsafeSqlError("查询包含未授权函数")

    limit = tree.args.get("limit")
    if limit is None:
        tree.set(
            "limit",
            exp.Limit(expression=exp.Literal.number(policy.max_rows)),
        )
    else:
        expression = limit.expression
        if (
            not isinstance(
                expression,
                exp.Literal,
            )
            or not expression.is_int
        ):
            raise UnsafeSqlError("LIMIT 必须是整数")
        if int(expression.this) > policy.max_rows:
            limit.set(
                "expression",
                exp.Literal.number(policy.max_rows),
            )

    return tree.sql(dialect="postgres")


def _reject_comments(sql: str) -> None:
    comment_tokens = ("--", "/*", "*/")
    if any(token in sql for token in comment_tokens):
        raise UnsafeSqlError("禁止 SQL 注释")
