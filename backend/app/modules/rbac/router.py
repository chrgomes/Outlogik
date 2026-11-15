import uuid

from fastapi import APIRouter, Depends, Request, Response, status

from app.core.pagination import Page, Paging
from app.core.request import client_ip
from app.modules.auth.deps import DB
from app.modules.rbac import roles
from app.modules.rbac.catalogue import PERMISSIONS, permission_group
from app.modules.rbac.models import Role
from app.modules.rbac.schemas import PermissionOut, RoleCreateIn, RoleOut, RoleUpdateIn
from app.tenancy.context import OrgContext, require
from app.tenancy.scoped import get_scoped

router = APIRouter(prefix="/orgs/{org_slug}", tags=["roles"])


@router.get("/permissions", response_model=list[PermissionOut],
            summary="The permission catalogue, for building role editors")
def list_permissions(_: OrgContext = Depends(require("roles.read"))):
    return [PermissionOut(code=c, description=d, group=permission_group(c))
            for c, d in PERMISSIONS.items()]


@router.get("/roles", response_model=Page[RoleOut])
def list_roles(db: DB, paging: Paging, ctx: OrgContext = Depends(require("roles.read"))):
    items, total = roles.list_roles(db, ctx, paging)
    return Page(items=items, total=total, page=paging.page, page_size=paging.page_size)


@router.get("/roles/{role_id}", response_model=RoleOut)
def get_role(role_id: uuid.UUID, db: DB, ctx: OrgContext = Depends(require("roles.read"))):
    return roles.to_out(db, get_scoped(db, Role, role_id, ctx, label="Role"))


@router.post("/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_role(body: RoleCreateIn, request: Request, db: DB,
                ctx: OrgContext = Depends(require("roles.manage"))):
    return roles.create_role(db, ctx, name=body.name, description=body.description,
                             permissions=body.permissions, ip=client_ip(request))


@router.patch("/roles/{role_id}", response_model=RoleOut)
def update_role(role_id: uuid.UUID, body: RoleUpdateIn, request: Request, db: DB,
                ctx: OrgContext = Depends(require("roles.manage"))):
    return roles.update_role(db, ctx, role_id, name=body.name, description=body.description,
                             permissions=body.permissions, ip=client_ip(request))


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(role_id: uuid.UUID, request: Request, db: DB,
                ctx: OrgContext = Depends(require("roles.manage"))) -> Response:
    roles.delete_role(db, ctx, role_id, client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
