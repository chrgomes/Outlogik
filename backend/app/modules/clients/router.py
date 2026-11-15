import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.core.pagination import Page, Paging
from app.core.request import client_ip
from app.modules.auth.deps import DB
from app.modules.clients import service
from app.modules.clients.schemas import (
    ClientCreateIn,
    ClientOut,
    ClientStatus,
    ClientUpdateIn,
    ClientUserLinkIn,
    ClientUserOut,
)
from app.tenancy.context import OrgContext, require

router = APIRouter(prefix="/orgs/{org_slug}/clients", tags=["clients"])


@router.get("", response_model=Page[ClientOut],
            summary="Clients (client-portal users see only their own)")
def list_clients(db: DB, paging: Paging,
                 q: Annotated[str | None, Query(max_length=100)] = None,
                 status_: Annotated[ClientStatus | None, Query(alias="status")] = None,
                 sort: Annotated[str | None, Query(max_length=40)] = None,
                 ctx: OrgContext = Depends(require("clients.read"))):
    items, total = service.list_clients(db, ctx, paging, q=q, status=status_, sort=sort)
    return Page(items=items, total=total, page=paging.page, page_size=paging.page_size)


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(body: ClientCreateIn, request: Request, db: DB,
                  ctx: OrgContext = Depends(require("clients.write"))):
    return service.create_client(db, ctx, body.model_dump(), client_ip(request))


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: uuid.UUID, db: DB,
               ctx: OrgContext = Depends(require("clients.read"))):
    return service.to_out(db, ctx, service.get_client(db, ctx, client_id))


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(client_id: uuid.UUID, body: ClientUpdateIn, request: Request, db: DB,
                  ctx: OrgContext = Depends(require("clients.write"))):
    data = body.model_dump(exclude_unset=True)
    # name and status can't be cleared; contact_email and notes can (send null).
    data = {k: v for k, v in data.items() if v is not None or k in {"contact_email", "notes"}}
    return service.update_client(db, ctx, client_id, data, client_ip(request))


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a client with its websites and portal access")
def delete_client(client_id: uuid.UUID, request: Request, db: DB,
                  ctx: OrgContext = Depends(require("clients.delete"))) -> Response:
    service.delete_client(db, ctx, client_id, client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{client_id}/users", response_model=list[ClientUserOut],
            summary="People with client-portal access to this client")
def list_client_users(client_id: uuid.UUID, db: DB,
                      ctx: OrgContext = Depends(require("client_users.manage"))):
    return service.list_client_users(db, ctx, client_id)


@router.post("/{client_id}/users", response_model=list[ClientUserOut],
             summary="Give an existing client-portal member access to this client too")
def link_client_user(client_id: uuid.UUID, body: ClientUserLinkIn, request: Request, db: DB,
                     ctx: OrgContext = Depends(require("client_users.manage"))):
    return service.link_client_user(db, ctx, client_id, body.member_id, client_ip(request))


@router.delete("/{client_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_client_user(client_id: uuid.UUID, user_id: uuid.UUID, request: Request, db: DB,
                       ctx: OrgContext = Depends(require("client_users.manage"))) -> Response:
    service.unlink_client_user(db, ctx, client_id, user_id, client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
