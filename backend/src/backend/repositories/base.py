from collections.abc import Mapping, Sequence
from typing import Any, Generic, TypeVar

from backend.db.base import Base
from sqlalchemy import (
    ColumnExpressionArgument,
    UnaryExpression,
    delete,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.base import ExecutableOption

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository providing typed data access patterns for SQLAlchemy 2.0 models.

    All mutating operations rely on the surrounding transaction lifecycle
    (e.g., Unit of Work or Session middleware) and do not issue commits directly.
    """

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(
        self,
        ident: Any,
        *,
        options: Sequence[ExecutableOption] | None = None,
        populate_existing: bool = False,
    ) -> ModelType | None:
        """Fetch a single record by its primary key using session.get."""
        return await self.session.get(
            self.model,
            ident,
            options=options,
            populate_existing=populate_existing,
        )

    async def get_one_or_none(
        self,
        *clauses: ColumnExpressionArgument[bool],
        options: Sequence[ExecutableOption] | None = None,
    ) -> ModelType | None:
        """Return exactly one record matching the given clauses, or None."""
        stmt = select(self.model).where(*clauses)
        if options:
            stmt = stmt.options(*options)
        result = await self.session.execute(stmt)
        return result.scalars().one_or_none()

    async def list(
        self,
        *clauses: ColumnExpressionArgument[bool],
        order_by: Sequence[ColumnExpressionArgument[Any] | UnaryExpression[Any]]
        | None = None,
        limit: int | None = None,
        offset: int | None = None,
        options: Sequence[ExecutableOption] | None = None,
    ) -> Sequence[ModelType]:
        """Fetch a list of records matching filter conditions with pagination and sorting."""
        stmt = select(self.model).where(*clauses)
        if options:
            stmt = stmt.options(*options)
        if order_by is not None:
            stmt = stmt.order_by(*order_by)
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self, *clauses: ColumnExpressionArgument[bool]) -> int:
        """Count rows matching filter criteria using SQL COUNT(*)."""
        stmt = select(func.count()).select_from(self.model).where(*clauses)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists(self, *clauses: ColumnExpressionArgument[bool]) -> bool:
        """Check row existence using an optimized SQL EXISTS query."""
        stmt = select(func.count()).select_from(self.model).where(*clauses).limit(1)
        result = await self.session.execute(stmt)
        return bool(result.scalar_one() > 0)

    async def create(self, entity: ModelType) -> ModelType:
        """Attach a new entity to the session and flush to obtain auto-generated IDs."""
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def create_many(self, entities: Sequence[ModelType]) -> Sequence[ModelType]:
        """Batch-insert multiple entities into the current persistence context."""
        self.session.add_all(entities)
        await self.session.flush()
        return entities

    async def update(
        self,
        entity: ModelType,
        attributes: Mapping[str, Any],
    ) -> ModelType:
        """Update an existing loaded entity with attribute key-values."""
        for key, value in attributes.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        await self.session.flush()
        return entity

    async def delete(self, entity: ModelType) -> None:
        """Mark an entity for removal and flush."""
        await self.session.delete(entity)
        await self.session.flush()

    async def delete_by_id(self, ident: Any) -> bool:
        """Delete a record by primary key using a direct SQL DELETE statement."""
        pk_column = self.model.__table__.primary_key.columns.values()[0]
        stmt = delete(self.model).where(pk_column == ident)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0
