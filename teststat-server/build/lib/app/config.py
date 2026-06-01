from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(..., alias="DATABASE_URL")
    allowed_origins: str = Field("*", alias="ALLOWED_ORIGINS")

    # === Azure DevOps 連携 ===
    azure_devops_pat: str = Field("", alias="AZURE_DEVOPS_PAT")
    azure_devops_use_mock: bool = Field(False, alias="AZURE_DEVOPS_USE_MOCK")
    azure_devops_organization: str = Field("", alias="AZURE_DEVOPS_ORGANIZATION")
    azure_devops_project: str = Field("", alias="AZURE_DEVOPS_PROJECT")
    azure_devops_api_version: str = Field("7.1", alias="AZURE_DEVOPS_API_VERSION")
    azure_devops_title_field: str = Field("System.Title", alias="AZURE_DEVOPS_TITLE_FIELD")
    azure_devops_start_date_field: str = Field(
        "Microsoft.VSTS.Scheduling.StartDate", alias="AZURE_DEVOPS_START_DATE_FIELD"
    )
    azure_devops_end_date_field: str = Field(
        "Microsoft.VSTS.Scheduling.FinishDate", alias="AZURE_DEVOPS_END_DATE_FIELD"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        if self.allowed_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
