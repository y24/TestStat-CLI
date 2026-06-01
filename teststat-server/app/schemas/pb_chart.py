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
    bug_open: int | None = None          # 未解消（赤エリアの高さ）
    bug_suspended: int | None = None     # 対応見送り累積（黄エリアの高さ）
    bug_resolved: int | None = None      # 完了累積（緑エリアの高さ）


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
    has_bugs: bool = False           # 1件でも bug_snapshots があるか
    bugs_updated_at: datetime | None = None  # max(fetched_at)
