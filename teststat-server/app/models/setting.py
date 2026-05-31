from sqlalchemy import Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProgressStatusSetting(Base):
    __tablename__ = "progress_status_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    caution_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=90)
    warning_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=60)
