import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # DigitalOcean Gradient AI
    do_api_token: str = ""
    do_agent_endpoint: str = "https://inference.do-ai.run/v1"
    do_agent_key: str = ""

    # App
    repos_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "repos")
    frontend_url: str = "http://localhost:3000"
    demo_mode: bool = False  # Auto-enabled when no API key is set

    model_config = {
        "env_file": os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"),
        "env_file_encoding": "utf-8",
    }

    @property
    def is_demo(self) -> bool:
        """True if no API key is configured — runs in demo mode."""
        return self.demo_mode or not self.do_agent_key


@lru_cache()
def get_settings() -> Settings:
    return Settings()
