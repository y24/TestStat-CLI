from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProgressStatusSetting(Base):
    __tablename__ = "progress_status_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    caution_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=90)
    warning_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=60)


class PbChartSetting(Base):
    __tablename__ = "pb_chart_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    bug_axis_max: Mapped[int] = mapped_column(Integer, nullable=False, default=30)


class BugStateColorSetting(Base):
    __tablename__ = "bug_state_color_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    state: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    background_color: Mapped[str] = mapped_column(String(7), nullable=False)
    text_color: Mapped[str] = mapped_column(String(7), nullable=False)
    border_color: Mapped[str] = mapped_column(String(7), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

