"""Organization model helpers for database operations.

This module provides database operations for organizations, mirroring
the Go implementation in org.go. It includes functions for:
- Fetching organizations by admin email
- Creating new organizations
- Getting and setting cross-match traits
"""

from sqlalchemy import text

from mealbot.db import get_db_connection


def get_organizations(admin: str) -> list[str]:
    """Fetch all organization names for a given admin.

    This mirrors the Go getOrganizations() function.

    Args:
        admin: The admin email to filter organizations by.

    Returns:
        List of organization names for the admin.
    """
    with get_db_connection() as conn:
        result = conn.execute(
            text("SELECT name FROM organizations WHERE admin = :admin"),
            {"admin": admin},
        )
        organizations = [row[0] for row in result.fetchall()]
    return organizations


def create_organization(name: str, admin: str) -> None:
    """Create a new organization.

    This mirrors the Go createOrganization() function.

    Args:
        name: The name of the organization to create.
        admin: The admin email for the organization.

    Raises:
        ValueError: If the organization name is empty.
        Exception: If the database insert fails (e.g., duplicate key).
    """
    if name == "":
        raise ValueError("Organization name cannot be an empty string")

    with get_db_connection() as conn:
        conn.execute(
            text("INSERT INTO organizations (name, admin) VALUES (:name, :admin)"),
            {"name": name, "admin": admin},
        )
        conn.commit()


def get_cross_match_trait(orgname: str) -> str:
    """Get the cross-match trait for an organization.

    This mirrors the Go GetCrossMatchTrait() function. Returns an empty
    string if the trait is NULL or the organization doesn't exist.

    Args:
        orgname: The organization name to look up.

    Returns:
        The cross-match trait value, or empty string if not set.
    """
    with get_db_connection() as conn:
        result = conn.execute(
            text("SELECT cross_match_trait FROM organizations WHERE name = :name"),
            {"name": orgname},
        )
        row = result.fetchone()
        if row is None or row[0] is None:
            return ""
        return row[0]


def set_cross_match_trait(orgname: str, cross_match_trait: str) -> None:
    """Set the cross-match trait for an organization.

    This mirrors the Go setCrossMatchTrait() function.

    Args:
        orgname: The organization name to update.
        cross_match_trait: The trait value to set.
    """
    with get_db_connection() as conn:
        conn.execute(
            text(
                "UPDATE organizations SET cross_match_trait = :trait WHERE name = :name"
            ),
            {"trait": cross_match_trait, "name": orgname},
        )
        conn.commit()
