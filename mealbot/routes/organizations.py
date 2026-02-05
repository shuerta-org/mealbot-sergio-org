"""Organization API endpoints.

This module implements the organization-related HTTP endpoints, mirroring
the Go implementation in org.go:
- GET /orgs - Fetch organizations by admin email
- POST /org - Create a new organization
- POST /crossmatchtrait - Set cross-match trait for an organization
"""

from flask import request
from flask_restful import Resource

from mealbot.models.organization import (
    create_organization,
    get_organizations,
    set_cross_match_trait,
)
from mealbot.utils import get_query_param, logger


class OrganizationsResource(Resource):
    """Resource for GET /orgs endpoint.

    Handles fetching organizations by admin email.
    """

    def get(self) -> tuple[dict, int]:
        """Handle GET /orgs requests.

        Query Parameters:
            admin: The admin email to filter organizations by (required).

        Returns:
            JSON response with {"orgs": [...]} and 200 OK on success,
            or error response with appropriate status code.
        """
        function = "GetOrganizationsHandler"

        try:
            admin = get_query_param(key="admin")
        except ValueError:
            logger.error(
                "Error in %s: missing admin param",
                function,
            )
            return {"message": "request query parameters must contain 'admin'"}, 400

        try:
            organizations = get_organizations(admin)
        except Exception as err:
            logger.error("Error in %s: %s", function, str(err))
            return {"message": str(err)}, 500

        logger.debug("Success in %s", function)
        return {"orgs": organizations}, 200


class CreateOrganizationResource(Resource):
    """Resource for POST /org endpoint.

    Handles creating new organizations.
    """

    def post(self) -> tuple[dict, int]:
        """Handle POST /org requests.

        Query Parameters:
            admin: The admin email for the organization (required).

        Request Body:
            JSON with {"org": "organization_name"}

        Returns:
            JSON response with success message and 201 Created on success,
            or error response with appropriate status code.
        """
        function = "CreateOrganizationHandler"

        # Parse request body first
        try:
            body = request.get_json(force=True)
        except Exception as err:
            logger.error("Error in %s: %s", function, str(err))
            return {"message": str(err)}, 400

        if body is None or "org" not in body:
            logger.error("Error in %s: missing org in body", function)
            return {"message": "Request body must contain 'org' field"}, 400

        # Get admin query parameter
        try:
            admin = get_query_param(key="admin")
        except ValueError:
            logger.error("Error in %s: missing admin param", function)
            return {"message": "request query parameters must contain 'admin'"}, 400

        org_name = body["org"]

        # Create the organization
        try:
            create_organization(org_name, admin)
        except Exception as err:
            logger.error("Error in %s: %s", function, str(err))
            return {"message": str(err)}, 500

        logger.debug("Success in %s", function)
        return {"message": "Successfully created new organization"}, 201


class CrossMatchTraitResource(Resource):
    """Resource for POST /crossmatchtrait endpoint.

    Handles setting cross-match trait for an organization.
    """

    def post(self) -> tuple[dict, int]:
        """Handle POST /crossmatchtrait requests.

        Query Parameters:
            org: The organization name (required).

        Request Body:
            JSON with {"trait": "trait_name"}

        Returns:
            JSON response with success message and 201 Created on success,
            or error response with appropriate status code.
        """
        function = "CrossMatchTraitHandler"

        # Get org query parameter
        try:
            orgname = get_query_param(key="org")
        except ValueError:
            logger.error("Error in %s: missing org param", function)
            return {"message": "Request query parameters must contain org"}, 400

        # Parse request body
        try:
            body = request.get_json(force=True)
        except Exception:
            logger.error("Error in %s: Malformed body", function)
            return {"message": "Malformed body."}, 400

        if body is None:
            logger.error("Error in %s: Request body is malformed", function)
            return {"message": "Request body is malformed"}, 400

        # The Go implementation checks if body parses, but doesn't explicitly
        # require the 'trait' field - it just uses whatever value is there
        trait = body.get("trait", "")

        # Set the cross match trait
        try:
            set_cross_match_trait(orgname, trait)
        except Exception as err:
            logger.error("Error in %s: %s", function, str(err))
            return {"message": str(err)}, 500

        logger.debug("Success in %s", function)
        return {"message": "Successfully set the cross match trait"}, 201


def register_organization_routes(api) -> None:
    """Register organization routes with the Flask-RESTful API.

    Args:
        api: Flask-RESTful Api instance.
    """
    api.add_resource(OrganizationsResource, "/orgs")
    api.add_resource(CreateOrganizationResource, "/org")
    api.add_resource(CrossMatchTraitResource, "/crossmatchtrait")
