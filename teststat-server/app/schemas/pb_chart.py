from datetime import date, datetime

from pydantic import BaseModel


class PbChartRange(BaseModel):
    from_date: date
    to_date: date

    # JSON では "from" / "to" にする（Python 予約語 from を回避）
    def model_dump_json_friendly(self) -> dict:
        return {"from": self.from_date.isoformat(), "to": self.to_date.isoformat()}


class PbChartSeriesItem(BaseModel):
    date: date
    planned_remaining: int | None
    actual_remaining: int | None
    planned_completed_daily: int | None
    actual_completed_daily: int | None


class PastPlanSeriesItem(BaseModel):
    date: date
    planned_remaining: int
    planned_completed_daily: int


class PastPlanSeries(BaseModel):
    plan_id: int
    version: int
    label: str | None
    reason: str | None
    planned_total_cases: int
    series: list[PastPlanSeriesItem]


class PbChartResponse(BaseModel):
    testing_id: int
    label: str | None
    range: dict | None          # {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"}
    actuals_updated_at: datetime | None
    available_cases: int        # 実績の available_cases 合計（0 = 実績なし）
    planned_total_cases: int | None  # 有効計画の planned_total_cases 合計（None = 計画なし）
    series: list[PbChartSeriesItem]
    past_plans: list[PastPlanSeries]
