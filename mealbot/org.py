"""Organization handlers and database access functions.

Ports the Go app's org.go: HTTP handlers for /orgs, /org, and
/crossmatchtrait endpoints, plus the underlying database functions
(getOrganizations, createOrganization, GetCrossMatchTrait, setCrossMatchTrait).
"""

import json

from flask import request

from mealbot.db import get_db
from mealbot.log import (
    log_and_write,
    log_and_write_err,
    log_and_write_status_bad_request,
    log_and_write_status_internal_server_error,
    str_to_response,
)


# --- Database functions ---


def get_organizations(admin):
    """Fetch all organization names for a given admin.

    Equivalent to Go's getOrganizations function.

    Args:
        admin: The admin email to filter by.

    Returns:
        tuple: (list_of_org_names, None) on success, or (None, error_message) on failure.
    """
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "SELECT name FROM organizations WHERE admin = %s",
            (admin,),
        )
        rows = cur.fetchall()
        cur.close()
        organizations = [row[0] for row in rows]
        return organizations, None
    except Exception as e:
        return None, str(e)


def create_organization(name, admin):
    """Create a new organization.

    Equivalent to Go's createOrganization function.

    Args:
        name: The organization name.
        admin: The admin email.

    Returns:
        None on success, or error message string on failure.
    """
    if not name:
        return "Organization name cannot be an empty string"

    try:
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO organizations (name, admin) VALUES (%s, %s)",
            (name, admin),
        )
        db.commit()
        cur.close()
        return None
    except Exception as e:
        db.rollback()
        return str(e)


def get_cross_match_trait(orgname):
    """Get the cross-match trait for an organization.

    Equivalent to Go's GetCrossMatchTrait function.
    Exported for use by the pairing algorithm in Milestone 4.

    Args:
        orgname: The organization name.

    Returns:
        tuple: (trait_string, None) on success, or (None, error_message) on failure.
            trait_string will be "" if the column is NULL.
    """
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "SELECT cross_match_trait FROM organizations WHERE name = %s",
            (orgname,),
        )
        row = cur.fetchone()
        cur.close()

        if row is None:
            return "", None

        cross_match_trait = row[0] if row[0] is not None else ""
        return cross_match_trait, None
    except Exception as e:
        return None, str(e)


def set_cross_match_trait(orgname, cross_match_trait):
    """Set the cross-match trait for an organization.

    Equivalent to Go's setCrossMatchTrait function.

    Args:
        orgname: The organization name.
        cross_match_trait: The trait value to set.

    Returns:
        None on success, or error message string on failure.
    """
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "UPDATE organizations SET cross_match_trait = %s WHERE name = %s",
            (cross_match_trait, orgname),
        )
        db.commit()
        cur.close()
        return None
    except Exception as e:
        db.rollback()
        return str(e)


# --- HTTP Handlers ---


def get_organizations_handler():
    """HTTP handler for GET /orgs.

    Fetches all organizations an admin manages.
    Requires ?admin= query parameter.

    Returns:
        Flask Response with {"orgs": [...]} JSON body.
    """
    function = "GetOrganizationsHandler"

    if request.method != "GET":
        return log_and_write_err(
            "Only GET requests are allowed at this route",
            405,
            function,
        )

    queries = request.args.getlist("admin")
    if not queries or len(queries) > 1:
        return log_and_write_err(
            "request query parameters must contain 'admin'",
            400,
            function,
        )

    admin = queries[0]
    organizations, err = get_organizations(admin)
    if err is not None:
        return log_and_write_status_internal_server_error(err, function)

    return log_and_write({"orgs": organizations}, 200, function)


def create_organization_handler():
    """HTTP handler for POST /org.

    Creates a new organization.
    Requires ?admin= query parameter and {"org": "..."} JSON body.

    Returns:
        Flask Response with success/error message.
    """
    function = "CreateOrganizationHandler"

    if request.method != "POST":
        return log_and_write_err(
            "Only POST requests are allowed at this route",
            405,
            function,
        )

    try:
        body = request.get_json(force=True)
    except Exception as e:
        return log_and_write_status_bad_request(str(e), function)

    if body is None:
        return log_and_write_status_bad_request("Invalid JSON body", function)

    queries = request.args.getlist("admin")
    if not queries or len(queries) > 1:
        return log_and_write_err(
            "request query parameters must contain 'admin'",
            400,
            function,
        )
    admin = queries[0]

    org_name = body.get("org", "")
    print(org_name, admin)

    err = create_organization(org_name, admin)
    if err is not None:
        return log_and_write_status_internal_server_error(err, function)

    return str_to_response("Successfully created new organization", 201)


def cross_match_trait_handler():
    """HTTP handler for POST /crossmatchtrait.

    Sets or changes the cross-match trait for an organization.
    Requires ?org= query parameter and {"trait": "..."} JSON body.

    Returns:
        Flask Response with success/error message.
    """
    function = "CrossMatchTraitHandler"

    if request.method != "POST":
        return log_and_write_err(
            "Only POST requests are allowed at this route",
            405,
            function,
        )

    from mealbot.utils import get_query_param

    orgname, err = get_query_param("org")
    if err is not None:
        return log_and_write_status_bad_request(err, function)

    try:
        body = request.get_json(force=True)
    except Exception:
        return log_and_write_err("Malformed body.", 400, function)

    if body is None:
        return log_and_write_err("Request body is malformed", 400, function)

    trait = body.get("trait")
    if trait is None:
        return log_and_write_err("Request body is malformed", 400, function)

    err = set_cross_match_trait(orgname, trait)
    if err is not None:
        from mealbot.log import err_to_response
        return err_to_response(err, 500)

    return str_to_response("Successfully set the cross match trait", 201)
