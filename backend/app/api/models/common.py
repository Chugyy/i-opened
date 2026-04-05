"""Shared Pydantic base and helpers."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict
from pydantic.alias_generators import to_camel

# Coerce UUID to str before validation
StrUUID = Annotated[str, BeforeValidator(lambda v: str(v) if isinstance(v, UUID) else v)]


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class PaginationInfo(BaseSchema):
    page: int
    limit: int
    total: int
    total_pages: int
