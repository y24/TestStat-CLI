from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Testing(Base):
    __tablename__ = "testings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    testing_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class FileProgress(Base):
    __tablename__ = "file_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    testing_id: Mapped[int] = mapped_column(Integer, ForeignKey("testings.testing_id", ondelete="CASCADE"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255))
    environment: Mapped[str | None] = mapped_column(String(255))
    total_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    excluded_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    executed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    not_run: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    executed_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    result_pass: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_fixed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_fail: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_blocked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_suspend: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_na: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_date: Mapped[date | None] = mapped_column(Date)
    latest_update: Mapped[date | None] = mapped_column(Date)
    sender: Mapped[str | None] = mapped_column(String(255))
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class DailyProgress(Base):
    __tablename__ = "daily_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    testing_id: Mapped[int] = mapped_column(Integer, ForeignKey("testings.testing_id", ondelete="CASCADE"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255))
    environment: Mapped[str | None] = mapped_column(String(255))
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    result_pass: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_fixed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_fail: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_blocked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_suspend: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_na: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    executed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    planned: Mapped[int | None] = mapped_column(Integer)


class DailyPersonProgress(Base):
    __tablename__ = "daily_person_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    testing_id: Mapped[int] = mapped_column(Integer, ForeignKey("testings.testing_id", ondelete="CASCADE"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255))
    environment: Mapped[str | None] = mapped_column(String(255))
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    person: Mapped[str] = mapped_column(String(255), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class TestResultBugSnapshot(Base):
    """実績取り込み時点の不具合扱いステータス件数。

    FileProgress/DailyProgress は Testing ID 単位で洗替されるため、PB図で日々の Fail/Suspend/Fixed
    の変化を出すために、テスト結果日付単位のスナップショットを別保存する。
    """

    __tablename__ = "test_result_bug_snapshots"
    __table_args__ = (
        UniqueConstraint("testing_id", "snapshot_date", name="uq_test_result_bug_snapshots_testing_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    testing_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("testings.testing_id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suspend_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fixed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
