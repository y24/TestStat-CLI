from pydantic import BaseModel, Field, model_validator


class ProgressStatusThresholds(BaseModel):
    caution: float = Field(..., ge=0, le=100)
    warning: float = Field(..., ge=0, le=100)

    @model_validator(mode="after")
    def validate_order(self) -> "ProgressStatusThresholds":
        if not (self.caution > self.warning):
            raise ValueError("しきい値は caution > warning の順で指定してください")
        return self


class PbChartSettings(BaseModel):
    bug_axis_max: int = Field(..., ge=1, le=100000)

