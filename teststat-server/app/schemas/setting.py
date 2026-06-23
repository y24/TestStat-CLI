import re

from pydantic import BaseModel, Field, model_validator


HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


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


class BugStateColorSetting(BaseModel):
    state: str = Field(..., min_length=1, max_length=255)
    background_color: str
    text_color: str
    border_color: str

    @model_validator(mode="after")
    def validate_colors(self) -> "BugStateColorSetting":
        self.state = self.state.strip()
        if not self.state:
            raise ValueError("State名を入力してください")
        for value in (self.background_color, self.text_color, self.border_color):
            if not HEX_COLOR_RE.match(value):
                raise ValueError("色は #RRGGBB 形式で指定してください")
        return self


class BugStateColorSettings(BaseModel):
    items: list[BugStateColorSetting]

    @model_validator(mode="after")
    def validate_unique_states(self) -> "BugStateColorSettings":
        states = [item.state.casefold() for item in self.items]
        if len(states) != len(set(states)):
            raise ValueError("State名が重複しています")
        return self

