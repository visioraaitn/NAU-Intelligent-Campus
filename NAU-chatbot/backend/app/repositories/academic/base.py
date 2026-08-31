from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar, cast

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import NotFoundError


ModelT = TypeVar("ModelT")
MAX_PAGE_SIZE = 100
MAX_SEARCH_LENGTH = 200
MAX_FILTER_VALUES = 100


@dataclass(frozen=True, slots=True)
class PageRequest:
    page: int = 1
    page_size: int = 20
    search: str | None = None
    include_inactive: bool = False
    filters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page must be at least 1")
        if not 1 <= self.page_size <= MAX_PAGE_SIZE:
            raise ValueError(f"page_size must be between 1 and {MAX_PAGE_SIZE}")

        normalized_search = self.search.strip() if self.search else None
        if normalized_search and len(normalized_search) > MAX_SEARCH_LENGTH:
            raise ValueError(f"search cannot exceed {MAX_SEARCH_LENGTH} characters")
        object.__setattr__(self, "search", normalized_search or None)
        object.__setattr__(self, "filters", dict(self.filters))

        for value in self.filters.values():
            if isinstance(value, Mapping):
                raise ValueError("nested filter values are not supported")
            if _is_filter_sequence(value) and len(value) > MAX_FILTER_VALUES:
                raise ValueError(f"a filter cannot contain more than {MAX_FILTER_VALUES} values")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass(frozen=True, slots=True)
class Page(Generic[ModelT]):
    items: list[ModelT]
    total: int
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def pages(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


def _is_filter_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


class AcademicRepository(Generic[ModelT]):
    """Async SQLAlchemy repository with bounded, allowlisted query inputs.

    Repositories never commit. Transaction ownership remains with the calling
    service so a mutation and all of its dependency checks are atomic.
    """

    model: type[ModelT]
    resource_name = "academic entity"
    writable_fields: frozenset[str] = frozenset()
    filter_fields: Mapping[str, InstrumentedAttribute[Any]] = {}
    search_fields: tuple[InstrumentedAttribute[Any], ...] = ()
    order_by: tuple[ColumnElement[Any] | InstrumentedAttribute[Any], ...] = ()

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @property
    def id_column(self) -> InstrumentedAttribute[int]:
        return cast(InstrumentedAttribute[int], getattr(self.model, "id"))

    @property
    def active_column(self) -> InstrumentedAttribute[bool]:
        return cast(InstrumentedAttribute[bool], getattr(self.model, "actif"))

    def _apply_scope(
        self,
        statement: Select[Any],
        *,
        include_inactive: bool,
    ) -> Select[Any]:
        if include_inactive:
            return statement
        return statement.where(self.active_column.is_(True))

    def _apply_search(self, statement: Select[Any], search: str | None) -> Select[Any]:
        if not search or not self.search_fields:
            return statement
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        return statement.where(
            or_(*(column.ilike(pattern, escape="\\") for column in self.search_fields))
        )

    def _apply_filters(
        self,
        statement: Select[Any],
        filters: Mapping[str, Any],
    ) -> Select[Any]:
        unknown = set(filters).difference(self.filter_fields)
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"unsupported filters: {names}")

        for name, value in filters.items():
            column = self.filter_fields[name]
            if value is None:
                statement = statement.where(column.is_(None))
            elif _is_filter_sequence(value):
                values = [item.value if isinstance(item, Enum) else item for item in value]
                statement = statement.where(column.in_(values))
            else:
                bound_value = value.value if isinstance(value, Enum) else value
                statement = statement.where(column == bound_value)
        return statement

    def _query(self, request: PageRequest) -> Select[Any]:
        statement = select(self.model)
        statement = self._apply_scope(statement, include_inactive=request.include_inactive)
        statement = self._apply_search(statement, request.search)
        return self._apply_filters(statement, request.filters)

    def _count_query(self, request: PageRequest) -> Select[Any]:
        statement = select(func.count(self.id_column)).select_from(self.model)
        statement = self._apply_scope(statement, include_inactive=request.include_inactive)
        statement = self._apply_search(statement, request.search)
        return self._apply_filters(statement, request.filters)

    async def list(self, request: PageRequest | None = None) -> Page[ModelT]:
        query = request or PageRequest()
        statement = self._query(query)
        if self.order_by:
            statement = statement.order_by(*self.order_by)
        statement = statement.offset(query.offset).limit(query.page_size)

        total = int((await self.session.scalar(self._count_query(query))) or 0)
        result = await self.session.scalars(statement)
        return Page(
            items=list(result.unique().all()),
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    async def get(
        self,
        entity_id: int,
        *,
        include_inactive: bool = False,
        for_update: bool = False,
    ) -> ModelT | None:
        statement = select(self.model).where(self.id_column == entity_id)
        statement = self._apply_scope(statement, include_inactive=include_inactive)
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def require(
        self,
        entity_id: int,
        *,
        include_inactive: bool = False,
        for_update: bool = False,
    ) -> ModelT:
        entity = await self.get(
            entity_id,
            include_inactive=include_inactive,
            for_update=for_update,
        )
        if entity is None:
            raise NotFoundError(self.resource_name, entity_id)
        return entity

    async def get_by_code(
        self,
        code: str,
        *,
        include_inactive: bool = False,
    ) -> ModelT | None:
        code_column = getattr(self.model, "code", None)
        if code_column is None:
            raise TypeError(f"{self.model.__name__} does not expose a code column")
        normalized = code.strip()
        if not normalized or len(normalized) > MAX_SEARCH_LENGTH:
            return None
        statement = select(self.model).where(code_column == normalized)
        statement = self._apply_scope(statement, include_inactive=include_inactive)
        return await self.session.scalar(statement)

    def _clean_write_values(self, values: Mapping[str, Any]) -> dict[str, Any]:
        unknown = set(values).difference(self.writable_fields)
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"unsupported writable fields: {names}")
        return dict(values)

    async def create(self, values: Mapping[str, Any]) -> ModelT:
        entity = self.model(**self._clean_write_values(values))
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: ModelT, values: Mapping[str, Any]) -> ModelT:
        for name, value in self._clean_write_values(values).items():
            setattr(entity, name, value)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def set_active(self, entity: ModelT, active: bool) -> ModelT:
        setattr(entity, "actif", active)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def dependency_counts(self, entity_id: int) -> dict[str, int]:
        """Return non-zero references that make destructive deletion unsafe."""

        return {}
