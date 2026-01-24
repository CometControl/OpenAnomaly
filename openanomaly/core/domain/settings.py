from pydantic import BaseModel, Field

class SystemSettings(BaseModel):
    """
    Global system configuration settings.
    """
    redis_url: str = Field(default="redis://localhost:6379/0", description="Celery broker and backend URL")
    victoriametrics_url: str = Field(default="http://localhost:8428", description="VictoriaMetrics base URL")
    victoriametrics_write_url: str | None = Field(default=None, description="VictoriaMetrics Remote Write URL")
    pipelines_file: str = Field(default="pipelines.yaml", description="Path to pipelines configuration file")

    def get_write_url(self) -> str:
        """Get effective write URL."""
        if self.victoriametrics_write_url:
            return self.victoriametrics_write_url
        return f"{self.victoriametrics_url}/api/v1/write"
