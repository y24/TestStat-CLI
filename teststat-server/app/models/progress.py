from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint, func
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
    __table_args__ = (
        Index("ix_file_progress_testing_label", "testing_id", "label"),
    )

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
    __table_args__ = (
        Index("ix_daily_progress_testing_label_date", "testing_id", "label", "date"),
    )

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
    """テスト結果由来の不具合バーンダウン用スナップショット（日付単位）。

    FileProgress/DailyProgress は Testing ID 単位で洗替され、かつ「結果が変わると日付も移す」運用のため、
    最新の取り込みだけでは過去の検出履歴を再現できない。そこで label（テスト種別）×日付ごとに以下を蓄積する:

    - detected_count: その日に新規検出された不具合数（増分）。検出累積は取り込み間で
      「総不具合数（Fail+Suspend+Fixed）累積の最大値（ハイウォーターマーク）」として保持し、
      一度検出した不具合は後で状態・日付が変わっても減らさない。
    - suspend_count / fixed_count: その日時点で見送り／完了になっている件数（最新取り込みの現在値）。

    PB図では各日について 未解消(open) = 検出累積 − 見送り累積 − 完了累積 で算出する（Azure DevOps と同じ考え方）。
    label 別に保持することで、表示対象がテスト別のときもそのテストの不具合だけを描画できる。
    (全て) 表示時は label をまたいで合算する。
    """

    __tablename__ = "test_result_bug_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "testing_id", "label", "snapshot_date", name="uq_test_result_bug_snapshots_testing_label_date"
        ),
        Index("ix_test_result_bug_snapshots_testing_label_date", "testing_id", "label", "snapshot_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    testing_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("testings.testing_id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str | None] = mapped_column(String(255))
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    detected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suspend_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fixed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
