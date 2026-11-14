import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Url = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=2048)]
WebsiteStatus = Literal["active", "paused", "archived"]


class WebsiteCreateIn(BaseModel):
    client_id: uuid.UUID
    url: Url
    # Defaults to the domain when omitted.
    name: Name | None = None
    status: WebsiteStatus = "active"


class WebsiteUpdateIn(BaseModel):
    client_id: uuid.UUID | None = None
    url: Url | None = None
    name: Name | None = None
    status: WebsiteStatus | None = None


class WebsiteOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    client_name: str
    name: str
    url: str
    domain: str
    status: str
    created_at: datetime
    updated_at: datetime
