from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.db import get_engine


def test_app_role_identity_and_schema_privilege():
    with get_engine().connect() as connection:
        assert connection.execute(text("SELECT current_user")).scalar_one() == "sentrix_app"
        assert connection.execute(
            text("SELECT has_schema_privilege('sentrix_app', 'public', 'CREATE')")
        ).scalar_one() is False


def test_app_role_cannot_mutate_append_only_tables():
    with get_engine().connect() as connection:
        for table in ("audit_event", "finding_status_event", "prompt_template_version"):
            privileges = {
                row[0]
                for row in connection.execute(
                    text(
                        """
                        SELECT privilege_type
                        FROM information_schema.role_table_grants
                        WHERE grantee = 'sentrix_app' AND table_name = :table
                        """
                    ),
                    {"table": table},
                )
            }
            assert "DELETE" not in privileges, table
            assert "UPDATE" not in privileges, table


def test_app_role_delete_is_scoped_to_project_member():
    with get_engine().connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.role_table_grants
                    WHERE grantee = 'sentrix_app' AND privilege_type = 'DELETE'
                    """
                )
            )
        }
    assert tables == {"project_member", "revoked_token", "rate_limit_bucket"}


def test_app_role_cannot_delete_audit_rows():
    with get_engine().begin() as connection:
        with pytest.raises(ProgrammingError):
            connection.execute(text("DELETE FROM audit_event WHERE id = 'audit-seed-1'"))
