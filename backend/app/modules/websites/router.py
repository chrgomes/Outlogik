import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.core.pagination import Page, Paging
from app.core.request import client_ip
from app.modules.auth.deps import DB
from app.modules.websites import service
from app.modules.websites.schemas import (
    WebsiteCreateIn,
    WebsiteOut,
    WebsiteStatus,
    WebsiteUpdateIn,
)
from app.modules.workspaces.context import WorkspaceContext, require_workspace
from app.tenancy.context import OrgContext, require

# Organization-wide: every website the caller can see, across workspaces.
router = APIRouter(prefix="/orgs/{org_slug}/websites", tags=["websites"])
# One workspace's websites.
workspace_router = APIRouter(prefix="/orgs/{org_slug}/workspaces/{workspace_id}/websites",
                             tags=["websites"])

Q = Annotated[str | None, Query(max_length=100)]
Sort = Annotated[str | None, Query(max_length=40)]
StatusFilter = Annotated[WebsiteStatus | None, Query(alias="status")]


@router.get("", response_model=Page[WebsiteOut],
            summary="Websites (client-portal users see only their clients' sites)")
def list_websites(db: DB, paging: Paging, q: Q = None, client_id: uuid.UUID | None = None,
                  workspace_id: uuid.UUID | None = None, status_: StatusFilter = None,
                  sort: Sort = None, ctx: OrgContext = Depends(require("websites.read"))):
    items, total = service.list_websites(db, ctx, paging, q=q, client_id=client_id,
                                         workspace_id=workspace_id, status=status_, sort=sort)
    return Page(items=items, total=total, page=paging.page, page_size=paging.page_size)


@router.post("", response_model=WebsiteOut, status_code=status.HTTP_201_CREATED,
             summary="Add a website to a client's workspace, or without client_id to the "
                     "organization's own workspace")
def create_website(body: WebsiteCreateIn, request: Request, db: DB,
                   ctx: OrgContext = Depends(require("websites.write"))):
    workspace = service.workspace_for_client(db, ctx, body.client_id)
    return service.create_website(db, ctx, workspace=workspace, url=body.url, name=body.name,
                                  status=body.status, ip=client_ip(request))


@router.get("/{website_id}", response_model=WebsiteOut)
def get_website(website_id: uuid.UUID, db: DB,
                ctx: OrgContext = Depends(require("websites.read"))):
    return service.to_out(db, service.get_website(db, ctx, website_id))


@router.patch("/{website_id}", response_model=WebsiteOut)
def update_website(website_id: uuid.UUID, body: WebsiteUpdateIn, request: Request, db: DB,
                   ctx: OrgContext = Depends(require("websites.write"))):
    return service.update_website(db, ctx, website_id, body.model_dump(exclude_unset=True),
                                  client_ip(request))


@router.delete("/{website_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_website(website_id: uuid.UUID, request: Request, db: DB,
                   ctx: OrgContext = Depends(require("websites.delete"))) -> Response:
    service.delete_website(db, ctx, website_id, client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- one workspace --------------------------------------------------------------------------

@workspace_router.get("", response_model=Page[WebsiteOut])
def list_workspace_websites(db: DB, paging: Paging, q: Q = None, status_: StatusFilter = None,
                            sort: Sort = None,
                            w: WorkspaceContext = Depends(require_workspace("websites.read"))):
    items, total = service.list_websites(db, w.org, paging, q=q, workspace_id=w.workspace.id,
                                         status=status_, sort=sort)
    return Page(items=items, total=total, page=paging.page, page_size=paging.page_size)


@workspace_router.post("", response_model=WebsiteOut, status_code=status.HTTP_201_CREATED)
def create_workspace_website(body: WebsiteCreateIn, request: Request, db: DB,
                             w: WorkspaceContext = Depends(require_workspace("websites.write"))):
    return service.create_website(db, w.org, workspace=w.workspace, url=body.url,
                                  name=body.name, status=body.status, ip=client_ip(request))


@workspace_router.get("/{website_id}", response_model=WebsiteOut)
def get_workspace_website(website_id: uuid.UUID, db: DB,
                          w: WorkspaceContext = Depends(require_workspace("websites.read"))):
    return service.to_out(db, service.get_website(db, w.org, website_id, workspace=w.workspace))


@workspace_router.patch("/{website_id}", response_model=WebsiteOut)
def update_workspace_website(website_id: uuid.UUID, body: WebsiteUpdateIn, request: Request,
                             db: DB,
                             w: WorkspaceContext = Depends(require_workspace("websites.write"))):
    return service.update_website(db, w.org, website_id, body.model_dump(exclude_unset=True),
                                  client_ip(request), workspace=w.workspace)


@workspace_router.delete("/{website_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace_website(website_id: uuid.UUID, request: Request, db: DB,
                             w: WorkspaceContext = Depends(require_workspace("websites.delete"))
                             ) -> Response:
    service.delete_website(db, w.org, website_id, client_ip(request), workspace=w.workspace)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
