"""Tag schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TagCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field("#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")
    project_id: str | None = None


class TagUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")


class TagResponse(BaseModel):
    id: str
    user_id: str
    project_id: str | None
    name: str
    color: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagListResponse(BaseModel):
    items: list[TagResponse]
    total: int
    page: int
    page_size: int
    pages: int


class TagAssignRequest(BaseModel):
    tag_ids: list[str] = Field(..., max_length=20)
