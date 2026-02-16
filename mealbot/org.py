"""Organization domain handlers and database logic.

Migrated from org.go:
- GetOrganizationsHandler (GET /orgs)
- CreateOrganizationHandler (POST /org)
- CrossMatchTraitHandler (POST /crossmatchtrait)
- getOrganizations(admin) — DB query
- createOrganization(name, admin) — DB insert
- GetCrossMatchTrait(orgname) — DB query (exported, used by pairing and members)
- setCrossMatchTrait(orgname, trait) — DB update
"""

import json

from flask import make_response, request

from mealbot.db import get_db_connection
from mealbot.log import (
    log_and_write,
    log_and_write_err,
    log_and_write_status_bad_request,
    log_and_write_status_internal_server_error,
)
from mealbot.utils import err_to_bytes, get_query_param, str_to_bytes


# ---------------------------------------------------------------------------
# Database functions
# ---------------------------------------------------------------------------


def get_organizations(admin):
    """Query organization names by admin email.

    Go equivalent: getOrganizations(admin string) ([]string, error)
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM organizations WHERE admin = %s",
            (admin,),
        )
        organizations = [row[0] for row in cur.fetchall()]
        cur.close()
        return organizations
    finally:
        conn.close()


def create_organization(name, admin):
    """Insert a new organization. Validates that name is non-empty.

    Go equivalent: createOrganization(name string, admin string) error
    """
    if name == "":
        raise ValueError("Organization name cannot be an empty string")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO organizations (name, admin) VALUES (%s, %s)",
            (name, admin),
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()


def get_cross_match_trait(orgname):
    """Retrieve the cross_match_trait for an organization, returning empty string for NULL.

    Go equivalent: GetCrossMatchTrait(orgname string) (string, error)

    This function is exported (public) because it is called by the pairing
    algorithm (Milestone 4) and the members handler (Milestone 2).
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT cross_match_trait FROM organizations WHERE name = %s",
            (orgname,),
        )
        row = cur.fetchone()
        cur.close()
        if row is None:
            return ""
        # psycopg2 returns None for SQL NULL
        return row[0] if row[0] is not None else ""
    finally:
        conn.close()


def set_cross_match_trait(orgname, trait):
    """Update the cross_match_trait column for an organization.

    Go equivalent: setCrossMatchTrait(orgname string, crossMatchTrait string) error
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE organizations SET cross_match_trait = %s WHERE name = %s",
            (trait, orgname),
        )
        conn.commit()
        cur.close()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# HTTP Handlers
# ---------------------------------------------------------------------------


def get_organizations_handler():
    """HTTP handler for fetching all organizations an admin manages.

    Go equivalent: GetOrganizationsHandler
    Route: GET /orgs?admin=<email>
    """
    function = "GetOrganizationsHandler"

    if request.method != "GET":
        return log_and_write_err(
            Exception("Only GET requests are allowed at this route"),
            405,
            function,
        )

    queries = request.args.getlist("admin")
    if len(queries) == 0 or len(queries) > 1:
        return log_and_write_err(
            Exception("request query parameters must contain 'admin'"),
            400,
            function,
        )

    try:
        organizations = get_organizations(queries[0])
    except Exception as e:
        return log_and_write_status_internal_server_error(e, function)

    resp = {"orgs": organizations}
    try:
        body = json.dumps(resp)
    except Exception as e:
        return log_and_write_status_internal_server_error(e, function)

    return log_and_write(body, 200, function)


def create_organization_handler():
    """HTTP handler for creating a new organization.

    Go equivalent: CreateOrganizationHandler
    Route: POST /org?admin=<email>
    Body: {"org": "name"}
    """
    function = "CreateOrganizationHandler"

    if request.method != "POST":
        return log_and_write_err(
            Exception("Only POST requests are allowed at this route"),
            405,
            function,
        )

    body = request.get_json(force=True, silent=True)
    if body is None:
        return log_and_write_status_bad_request(
            Exception("Failed to parse request body"),
            function,
        )

    queries = request.args.getlist("admin")
    if len(queries) == 0 or len(queries) > 1:
        return log_and_write_err(
            Exception("request query parameters must contain 'admin'"),
            400,
            function,
        )
    admin = queries[0]

    org_name = body.get("org", "")
    print(org_name, admin)

    try:
        create_organization(org_name, admin)
    except Exception as e:
        return log_and_write_status_internal_server_error(e, function)

    return log_and_write(
        str_to_bytes("Successfully created new organization"),
        201,
        function,
    )


def cross_match_trait_handler():
    """HTTP handler for setting a cross match trait for an organization.

    Go equivalent: CrossMatchTraitHandler
    Route: POST /crossmatchtrait?org=<name>
    Body: {"trait": "value"}
    """
    function = "CrossMatchTraitHandler"

    if request.method != "POST":
        return log_and_write_err(
            Exception("Only POST requests are allowed at this route"),
            405,
            function,
        )

    try:
        orgname = get_query_param("org")
    except ValueError as e:
        return log_and_write_status_bad_request(e, function)

    body = request.get_json(force=True, silent=True)
    if body is None:
        return log_and_write_err(
            Exception("Request body is malformed"),
            400,
            function,
        )

    trait = body.get("trait", "")

    try:
        set_cross_match_trait(orgname, trait)
    except Exception as e:
        # Go code writes directly without LogAndWriteErr for this 500 case
        response = make_response(err_to_bytes(e), 500)
        response.content_type = "application/json"
        return response

    return log_and_write(
        str_to_bytes("Successfully set the cross match trait"),
        201,
        function,
    )
