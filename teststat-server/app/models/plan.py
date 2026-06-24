from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, false, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (
        Index("ix_plans_testing_label_active", "testing_id", "label", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    testing_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(255))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reason: Mapped[str | None] = mapped_column(String(500))
    planned_total_cases: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(String(255))


class PlanLabel(Base):
    __tablename__ = "plan_labels"
    __table_args__ = (
        UniqueConstraint("testing_id", "label", name="uq_plan_labels_testing_label"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    testing_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    is_disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    source_url: Mapped[str | None] = mapped_column(String(2048))
    subtask_id: Mapped[int | None] = mapped_column(Integer)
    target_sheets: Mapped[list[str] | None] = mapped_column(JSON)
    ignore_sheets: Mapped[list[str] | None] = mapped_column(JSON)
    include_hidden_sheets: Mapped[bool | None] = mapped_column(Boolean)
    target_environments: Mapped[list[str] | None] = mapped_column(JSON)
    ignore_environments: Mapped[list[str] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class PlanDaily(Base):
    __tablename__ = "plan_daily"
    __table_args__ = (
        Index("ix_plan_daily_plan_date", "plan_id", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    planned_count: Mapped[int] = mapped_column(Integer, nullable=False)


