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
from app.tenancy.context import OrgContext, require

router = APIRouter(prefix="/orgs/{org_slug}/websites", tags=["websites"])


@router.get("", response_model=Page[WebsiteOut],
            summary="Websites (client-portal users see only their clients' sites)")
def list_websites(db: DB, paging: Paging,
                  q: Annotated[str | None, Query(max_length=100)] = None,
                  client_id: uuid.UUID | None = None,
                  status_: Annotated[WebsiteStatus | None, Query(alias="status")] = None,
                  sort: Annotated[str | None, Query(max_length=40)] = None,
                  ctx: OrgContext = Depends(require("websites.read"))):
    items, total = service.list_websites(db, ctx, paging, q=q, client_id=client_id,
                                         status=status_, sort=sort)
    return Page(items=items, total=total, page=paging.page, page_size=paging.page_size)


@router.post("", response_model=WebsiteOut, status_code=status.HTTP_201_CREATED)
def create_website(body: WebsiteCreateIn, request: Request, db: DB,
                   ctx: OrgContext = Depends(require("websites.write"))):
    return service.create_website(db, ctx, client_id=body.client_id, url=body.url,
                                  name=body.name, status=body.status, ip=client_ip(request))


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
