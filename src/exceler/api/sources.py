from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from exceler.api.deps import get_source_service, require_dev_token_if_configured
from exceler.application.sources.dto import (
    SourceCreate,
    SourceList,
    SourceRead,
    SourceStatusUpdate,
    SourceUpdate,
    SourceValidationResult,
)
from exceler.application.sources.service import SourceService

router = APIRouter(
    prefix="/api/v1/sources",
    tags=["sources"],
    dependencies=[Depends(require_dev_token_if_configured)],
)


@router.get("", response_model=SourceList)
def list_sources(
    service: Annotated[SourceService, Depends(get_source_service)],
    include_archived: bool = False,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SourceList:
    return service.list(include_archived=include_archived, offset=offset, limit=limit)


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source(
    payload: SourceCreate,
    service: Annotated[SourceService, Depends(get_source_service)],
) -> SourceRead:
    return service.create(payload)


@router.get("/{source_id}", response_model=SourceRead)
def get_source(
    source_id: UUID,
    service: Annotated[SourceService, Depends(get_source_service)],
) -> SourceRead:
    return service.get(source_id)


@router.put("/{source_id}", response_model=SourceRead)
def update_source(
    source_id: UUID,
    payload: SourceUpdate,
    service: Annotated[SourceService, Depends(get_source_service)],
) -> SourceRead:
    return service.update(source_id, payload)


@router.patch("/{source_id}/status", response_model=SourceRead)
def patch_source_status(
    source_id: UUID,
    payload: SourceStatusUpdate,
    service: Annotated[SourceService, Depends(get_source_service)],
) -> SourceRead:
    return service.set_status(source_id, payload)


@router.delete("/{source_id}", response_model=SourceRead)
def archive_source(
    source_id: UUID,
    service: Annotated[SourceService, Depends(get_source_service)],
) -> SourceRead:
    """Archive (soft-delete) a discovery source. Does not remove the row."""
    return service.archive(source_id)


@router.post("/{source_id}/validate", response_model=SourceValidationResult)
def validate_source(
    source_id: UUID,
    service: Annotated[SourceService, Depends(get_source_service)],
) -> SourceValidationResult:
    return service.validate(source_id)
