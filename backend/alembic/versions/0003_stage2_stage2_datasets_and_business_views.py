from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_stage2"
down_revision: str | None = "4d3f7ad3c90d"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "name",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "view_name",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "schema_text",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "sensitivity",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "allowed_columns",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "keywords",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("view_name"),
    )
    op.create_index(
        op.f("ix_datasets_name"),
        "datasets",
        ["name"],
        unique=True,
    )

    op.create_table(
        "dataset_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "dataset_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "subject_type",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "subject_value",
            sa.String(length=64),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dataset_id",
            "subject_type",
            "subject_value",
            name="uq_dataset_permission_subject",
        ),
    )
    op.create_index(
        op.f("ix_dataset_permissions_dataset_id"),
        "dataset_permissions",
        ["dataset_id"],
        unique=False,
    )

    op.create_table(
        "business_employees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "employee_no",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "display_name",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "department",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "job_title",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "employment_status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_no"),
    )

    op.create_table(
        "business_leave_monthly",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "department",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "month",
            sa.String(length=7),
            nullable=False,
        ),
        sa.Column(
            "leave_days",
            sa.Numeric(10, 2),
            nullable=False,
        ),
        sa.Column(
            "employee_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "department",
            "month",
            name="uq_leave_department_month",
        ),
    )

    op.create_table(
        "business_expenses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "claim_no",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "department",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "month",
            sa.String(length=7),
            nullable=False,
        ),
        sa.Column(
            "category",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "amount",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_no"),
    )

    op.create_table(
        "business_it_tickets_monthly",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "department",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "month",
            sa.String(length=7),
            nullable=False,
        ),
        sa.Column(
            "category",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "ticket_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "resolved_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "department",
            "month",
            "category",
            name="uq_ticket_department_month_category",
        ),
    )

    op.execute(
        """
        CREATE VIEW employee_directory_view AS
        SELECT
            employee_no,
            display_name,
            department,
            job_title,
            employment_status
        FROM business_employees
        """
    )
    op.execute(
        """
        CREATE VIEW leave_statistics_view AS
        SELECT
            department,
            month,
            leave_days,
            employee_count
        FROM business_leave_monthly
        """
    )
    op.execute(
        """
        CREATE VIEW expense_summary_view AS
        SELECT
            department,
            month,
            category,
            SUM(amount) AS total_amount,
            COUNT(1) AS claim_count
        FROM business_expenses
        WHERE status = 'APPROVED'
        GROUP BY department, month, category
        """
    )
    op.execute(
        """
        CREATE VIEW it_ticket_statistics_view AS
        SELECT
            department,
            month,
            category,
            ticket_count,
            resolved_count
        FROM business_it_tickets_monthly
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_roles
                WHERE rolname = 'enterprisemind_reader'
            ) THEN
                CREATE ROLE enterprisemind_reader
                LOGIN
                PASSWORD 'reader-local-password';
            END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        GRANT CONNECT
        ON DATABASE enterprisemind
        TO enterprisemind_reader
        """
    )
    op.execute(
        """
        GRANT USAGE
        ON SCHEMA public
        TO enterprisemind_reader
        """
    )
    op.execute(
        """
        GRANT SELECT ON
            employee_directory_view,
            leave_statistics_view,
            expense_summary_view,
            it_ticket_statistics_view
        TO enterprisemind_reader
        """
    )


def downgrade() -> None:
    op.execute(
        """
        REVOKE ALL PRIVILEGES ON
            employee_directory_view,
            leave_statistics_view,
            expense_summary_view,
            it_ticket_statistics_view
        FROM enterprisemind_reader
        """
    )
    op.execute("DROP VIEW IF EXISTS " "it_ticket_statistics_view")
    op.execute("DROP VIEW IF EXISTS expense_summary_view")
    op.execute("DROP VIEW IF EXISTS leave_statistics_view")
    op.execute("DROP VIEW IF EXISTS employee_directory_view")
    op.drop_table("business_it_tickets_monthly")
    op.drop_table("business_expenses")
    op.drop_table("business_leave_monthly")
    op.drop_table("business_employees")
    op.drop_index(
        op.f("ix_dataset_permissions_dataset_id"),
        table_name="dataset_permissions",
    )
    op.drop_table("dataset_permissions")
    op.drop_index(
        op.f("ix_datasets_name"),
        table_name="datasets",
    )
    op.drop_table("datasets")
