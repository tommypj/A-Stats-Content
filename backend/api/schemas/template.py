"""Article template schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    project_id: str | None = None
    target_audience: str | None = Field(None, max_length=500)
    tone: str | None = Field(None, max_length=50)
    word_count_target: int = Field(1500, ge=100, le=20000)
    writing_style: str | None = Field(None, max_length=100)
    voice: str | None = Field(None, max_length=100)
    custom_instructions: str | None = Field(None, max_length=5000)
    sections: list[dict] | None = None


class TemplateUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    target_audience: str | None = None
    tone: str | None = None
    word_count_target: int | None = Field(None, ge=100, le=20000)
    writing_style: str | None = None
    voice: str | None = None
    custom_instructions: str | None = None
    sections: list[dict] | None = None


class TemplateResponse(BaseModel):
    id: str
    user_id: str
    project_id: str | None
    name: str
    description: str | None
    target_audience: str | None
    tone: str | None
    word_count_target: int
    writing_style: str | None
    voice: str | None
    custom_instructions: str | None
    sections: list[dict] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TemplateListResponse(BaseModel):
    items: list[TemplateResponse]
    total: int
    page: int
    page_size: int
    pages: int
