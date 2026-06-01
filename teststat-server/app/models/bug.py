from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BugSnapshot(Base):
    """Testing ID（親 Work Item）の子チケット Bug の現時点スナップショット。

    Testing ID 単位で洗替（delete → insert）する。日次履歴は持たず、起票日・完了日・State から
    任意日付断面の検出累積／見送り／完了を計算で再現する。
    """

    __tablename__ = "bug_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    testing_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.testing_id", ondelete="CASCADE"), nullable=False, index=True
    )
    bug_work_item_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    state: Mapped[str | None] = mapped_column(String(255))
    created_date: Mapped[date | None] = mapped_column(Date)   # 起票日
    finish_date: Mapped[date | None] = mapped_column(Date)    # 完了日／見送り確定日（NULL=未解消）
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
