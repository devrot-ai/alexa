"""Central configuration. Everything comes from environment variables.

No secrets are ever logged. Missing values fall back to safe, local-demo
defaults so the project runs out of the box with zero cloud accounts.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _load_dotenv(path: str = ".env") -> None:
    """Minimal dependency-free .env loader. Never overrides existing env vars."""
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass


_load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # --- MCP server ---
    mcp_host: str = os.environ.get("FRESHKEEP_MCP_HOST", "0.0.0.0")
    mcp_port: int = int(os.environ.get("FRESHKEEP_MCP_PORT", "8811"))
    mcp_path: str = "/mcp"

    # --- Simulator (web app) ---
    sim_host: str = os.environ.get("FRESHKEEP_SIM_HOST", "0.0.0.0")
    # Honor platform-injected PORT (Render / HF Spaces / fly.io / Lambda)
    sim_port: int = int(os.environ.get("PORT", os.environ.get("FRESHKEEP_SIM_PORT", "8800")))

    # --- Storage backend: "json" (default, local file) or "dynamodb" ---
    store_backend: str = os.environ.get("FRESHKEEP_STORE", "json")
    json_path: str = os.environ.get("FRESHKEEP_JSON_PATH", "data/household.json")
    dynamo_table: str = os.environ.get("FRESHKEEP_DYNAMO_TABLE", "FreshKeepHousehold")
    dynamo_region: str = os.environ.get("AWS_REGION", "us-east-1")

    # --- Household identity (demo single-household build) ---
    household_id: str = os.environ.get("FRESHKEEP_HOUSEHOLD_ID", "demo-household")
    household_name: str = os.environ.get("FRESHKEEP_HOUSEHOLD_NAME", "The demo kitchen")

    # --- Optional Bedrock mode for natural-language routing/planning ---
    bedrock_enabled: bool = _env_bool("FRESHKEEP_BEDROCK", False)
    bedrock_model_id: str = os.environ.get(
        "FRESHKEEP_BEDROCK_MODEL", "amazon.nova-lite-v1:0"
    )
    bedrock_region: str = os.environ.get("FRESHKEEP_BEDROCK_REGION", "us-east-1")

    # --- Safety ---
    rate_limit_per_minute: int = int(os.environ.get("FRESHKEEP_RATE_LIMIT", "30"))
    require_consent: bool = _env_bool("FRESHKEEP_REQUIRE_CONSENT", True)

    @property
    def mcp_url(self) -> str:
        host = "127.0.0.1" if self.mcp_host in {"0.0.0.0", "::"} else self.mcp_host
        return f"http://{host}:{self.mcp_port}{self.mcp_path}"


settings = Settings()
