"""Organizations domain module: routes, models, and data access.

This module implements the Organizations API endpoints:
- GET /orgs?admin=X - List organizations for an admin
- POST /org?admin=X - Create a new organization
- POST /crossmatchtrait?org=X - Set/update cross-match trait for an organization

Reference: Go implementation org.go
- Lines 14-29: Organization struct and request body structs
- Lines 31-69: GetOrganizationsHandler (GET /orgs)
- Lines 71-124: CreateOrganizationHandler (POST /org)
- Lines 126-162: CrossMatchTraitHandler (POST /crossmatchtrait)
- Lines 164-192: getOrganizations data access function
- Lines 194-215: createOrganization data access function
- Lines 217-248: GetCrossMatchTrait data access function (exported)
- Lines 250-267: setCrossMatchTrait data access function

Design Decisions:
- #3 Error Response Format: Use {"Message": "..."} format matching Go implementation
- #4 Query Parameter Handling: Use FastAPI Query with custom validation for Go-style errors
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from .auth import ErrorResponse, get_current_user
from .database import get_connection, get_connection_context
from .logging_config import get_logger

logger = get_logger("mealbot.organizations")

# Create router for organizations endpoints
router = APIRouter(tags=["organizations"])


# ============================================================================
# Pydantic Models
# ============================================================================


class CreateOrganizationRequestBody(BaseModel):
    """Request body for creating a new organization.

    Reference: Go org.go lines 22-24
    """

    org: str  # JSON field name matches Go's `json:"org"`


class SetCrossMatchTraitRequestBody(BaseModel):
    """Request body for setting cross-match trait.

    Reference: Go org.go lines 26-29
    """

    trait: str  # JSON field name matches Go's `json:"trait"`


class OrganizationsResponse(BaseModel):
    """Response model for GET /orgs endpoint.

    Reference: Go org.go lines 61 - {"orgs": organizations}
    """

    orgs: list[str]


class MessageResponse(BaseModel):
    """Generic message response model.

    Reference: Go vendor/github.com/johnamadeo/server/response.go
    """

    Message: str


# ============================================================================
# Data Access Functions
# ============================================================================


async def get_organizations(
    admin: str, conn: AsyncConnection
) -> list[str]:
    """Fetch all organization names for a given admin.

    Reference: Go org.go lines 164-192

    Args:
        admin: The admin email to filter organizations by.
        conn: Async database connection.

    Returns:
        List of organization names.
    """
    result = await conn.execute(
        text("SELECT name FROM organizations WHERE admin = :admin"),
        {"admin": admin},
    )
    rows = result.fetchall()
    return [row[0] for row in rows]


async def create_organization(
    name: str, admin: str, conn: AsyncConnection
) -> None:
    """Create a new organization.

    Reference: Go org.go lines 194-215

    Args:
        name: Organization name (must not be empty).
        admin: Admin email.
        conn: Async database connection.

    Raises:
        ValueError: If organization name is empty.
    """
    if not name:
        raise ValueError("Organization name cannot be an empty string")

    await conn.execute(
        text("INSERT INTO organizations (name, admin) VALUES (:name, :admin)"),
        {"name": name, "admin": admin},
    )
    await conn.commit()


async def get_cross_match_trait(
    orgname: str, conn: AsyncConnection
) -> str:
    """Get the cross-match trait for an organization.

    Reference: Go org.go lines 217-248
    Handles SQL NULL by returning empty string (matching Go behavior).

    Args:
        orgname: Organization name.
        conn: Async database connection.

    Returns:
        Cross-match trait string, or empty string if NULL.
    """
    result = await conn.execute(
        text("SELECT cross_match_trait FROM organizations WHERE name = :name"),
        {"name": orgname},
    )
    row = result.fetchone()

    if row is None or row[0] is None:
        return ""
    return row[0]


async def set_cross_match_trait(
    orgname: str, cross_match_trait: str, conn: AsyncConnection
) -> None:
    """Set the cross-match trait for an organization.

    Reference: Go org.go lines 250-267

    Args:
        orgname: Organization name.
        cross_match_trait: The trait to set.
        conn: Async database connection.
    """
    await conn.execute(
        text(
            "UPDATE organizations SET cross_match_trait = :trait WHERE name = :name"
        ),
        {"trait": cross_match_trait, "name": orgname},
    )
    await conn.commit()


# ============================================================================
# Exported Function for Milestone 4
# ============================================================================


async def GetCrossMatchTrait(orgname: str) -> str:
    """Get cross-match trait for an organization (exported for Milestone 4).

    This function is designed to be called from other modules (e.g., pairing
    algorithm) and manages its own database connection.

    Reference: Go org.go lines 217-248

    Args:
        orgname: Organization name.

    Returns:
        Cross-match trait string, or empty string if NULL.
    """
    async with get_connection_context() as conn:
        return await get_cross_match_trait(orgname, conn)


# ============================================================================
# Route Handlers
# ============================================================================


@router.get("/orgs", response_model=OrganizationsResponse)
async def get_organizations_handler(
    admin: str = Query(
        ...,
        description="Admin email to filter organizations by",
    ),
    conn: AsyncConnection = Depends(get_connection),
    _user: dict[str, Any] = Depends(get_current_user),
) -> OrganizationsResponse:
    """List organizations for an admin.

    Reference: Go org.go lines 31-69 (GetOrganizationsHandler)

    Args:
        admin: Admin email query parameter.
        conn: Database connection (injected).
        _user: Authenticated user claims (injected, used for auth check).

    Returns:
        OrganizationsResponse with list of organization names.
    """
    logger.info(f"Getting organizations for admin: {admin}")

    try:
        organizations = await get_organizations(admin, conn)
        logger.debug(f"Found {len(organizations)} organizations for admin: {admin}")
        return OrganizationsResponse(orgs=organizations)
    except Exception as e:
        logger.log_error(e, 500, "get_organizations_handler")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(str(e)),
        )


@router.post("/org", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_organization_handler(
    body: CreateOrganizationRequestBody,
    admin: str = Query(
        ...,
        description="Admin email for the new organization",
    ),
    conn: AsyncConnection = Depends(get_connection),
    _user: dict[str, Any] = Depends(get_current_user),
) -> MessageResponse:
    """Create a new organization.

    Reference: Go org.go lines 71-124 (CreateOrganizationHandler)

    Args:
        body: Request body with organization name.
        admin: Admin email query parameter.
        conn: Database connection (injected).
        _user: Authenticated user claims (injected, used for auth check).

    Returns:
        MessageResponse confirming creation.

    Raises:
        HTTPException: 400 if organization name is empty, 500 on DB error.
    """
    logger.info(f"Creating organization: {body.org} for admin: {admin}")

    try:
        await create_organization(body.org, admin, conn)
        logger.debug(f"Successfully created organization: {body.org}")
        return MessageResponse(Message="Successfully created new organization")
    except ValueError as e:
        # Empty organization name
        logger.log_error(e, 400, "create_organization_handler")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse.create(str(e)),
        )
    except Exception as e:
        logger.log_error(e, 500, "create_organization_handler")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(str(e)),
        )


@router.post(
    "/crossmatchtrait",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def cross_match_trait_handler(
    body: SetCrossMatchTraitRequestBody,
    org: str = Query(
        ...,
        description="Organization name to set cross-match trait for",
    ),
    conn: AsyncConnection = Depends(get_connection),
    _user: dict[str, Any] = Depends(get_current_user),
) -> MessageResponse:
    """Set or update cross-match trait for an organization.

    Reference: Go org.go lines 126-162 (CrossMatchTraitHandler)

    Args:
        body: Request body with trait value.
        org: Organization name query parameter.
        conn: Database connection (injected).
        _user: Authenticated user claims (injected, used for auth check).

    Returns:
        MessageResponse confirming update.

    Raises:
        HTTPException: 500 on DB error.
    """
    logger.info(f"Setting cross-match trait for org: {org} to: {body.trait}")

    try:
        await set_cross_match_trait(org, body.trait, conn)
        logger.debug(f"Successfully set cross-match trait for org: {org}")
        return MessageResponse(Message="Successfully set the cross match trait")
    except Exception as e:
        logger.log_error(e, 500, "cross_match_trait_handler")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse.create(str(e)),
        )


__all__ = [
    # Models
    "CreateOrganizationRequestBody",
    "SetCrossMatchTraitRequestBody",
    "OrganizationsResponse",
    "MessageResponse",
    # Data access functions
    "get_organizations",
    "create_organization",
    "get_cross_match_trait",
    "set_cross_match_trait",
    # Exported function for Milestone 4
    "GetCrossMatchTrait",
    # Router
    "router",
]
