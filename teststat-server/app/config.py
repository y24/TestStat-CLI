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

    azure_devops_testing_wit: str = Field("Testing", alias="AZURE_DEVOPS_TESTING_WIT")

    # === Azure DevOps バグ取得 ===
    azure_devops_bug_wit: str = Field("Bug", alias="AZURE_DEVOPS_BUG_WIT")
    azure_devops_bug_ignore_status: str = Field("", alias="AZURE_DEVOPS_BUG_IGNORE_STATUS")
    azure_devops_bug_suspend_status: str = Field("", alias="AZURE_DEVOPS_BUG_SUSPEND_STATUS")
    azure_devops_bug_created_date_field: str = Field(
        "System.CreatedDate", alias="AZURE_DEVOPS_BUG_CREATED_DATE_FIELD"
    )
    azure_devops_bug_finish_date_field: str = Field(
        "Microsoft.VSTS.Common.ClosedDate", alias="AZURE_DEVOPS_BUG_FINISH_DATE_FIELD"
    )
    azure_devops_bug_state_field: str = Field("System.State", alias="AZURE_DEVOPS_BUG_STATE_FIELD")

    # === SharePoint URL 登録済み識別子の自動収集 ===
    collect_enabled: bool = Field(True, alias="COLLECT_ENABLED")
    tstat_command: str = Field("", alias="TSTAT_COMMAND")
    tstat_config: str = Field("", alias="TSTAT_CONFIG")
    collect_work_dir: str = Field("", alias="COLLECT_WORK_DIR")
    collect_log_dir: str = Field("logs", alias="COLLECT_LOG_DIR")
    collect_timeout_sec: int = Field(600, alias="COLLECT_TIMEOUT_SEC")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        if self.allowed_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @staticmethod
    def _csv_set(value: str) -> set[str]:
        return {item.strip() for item in value.split(",") if item.strip()}

    @staticmethod
    def _csv_list(value: str) -> list[str]:
        result: list[str] = []
        for item in value.split(","):
            name = item.strip()
            if name and name not in result:
                result.append(name)
        return result

    @property
    def azure_devops_bug_ignore_status_set(self) -> set[str]:
        return self._csv_set(self.azure_devops_bug_ignore_status)

    @property
    def azure_devops_bug_suspend_status_set(self) -> set[str]:
        # IGNORE と重複した State は除外を優先（見送り集合からは外す）。
        return self._csv_set(self.azure_devops_bug_suspend_status) - self.azure_devops_bug_ignore_status_set

    @property
    def azure_devops_bug_created_date_fields(self) -> list[str]:
        return self._csv_list(self.azure_devops_bug_created_date_field)

    @property
    def azure_devops_bug_finish_date_fields(self) -> list[str]:
        return self._csv_list(self.azure_devops_bug_finish_date_field)


@lru_cache
def get_settings() -> Settings:
    return Settings()

