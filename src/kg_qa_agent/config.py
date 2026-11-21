from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    llm_base_url: str = os.getenv("LLM_BASE_URL", "").rstrip("/")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_username: str = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")
    request_timeout: int = int(os.getenv("LLM_REQUEST_TIMEOUT", "60"))
    retrieval_limit: int = int(os.getenv("GRAPH_RETRIEVAL_LIMIT", "20"))

    def require_llm(self) -> None:
        missing = [
            name
            for name, value in {
                "LLM_BASE_URL": self.llm_base_url,
                "LLM_API_KEY": self.llm_api_key,
                "LLM_MODEL": self.llm_model,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing LLM configuration: {', '.join(missing)}")

    def require_neo4j(self) -> None:
        if not self.neo4j_password:
            raise RuntimeError("Missing Neo4j configuration: NEO4J_PASSWORD")


settings = Settings()

