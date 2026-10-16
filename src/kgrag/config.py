"""Configuration management using Pydantic Settings and YAML (PRD §13)."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Ensure .env is loaded
load_dotenv()


class LLMSettings(BaseModel):
    runtime: str = "openrouter"  # "openrouter" | "ollama"
    provider: str = "openrouter"
    endpoint: str = "https://openrouter.ai/api/v1"
    model: str = "nvidia/nemotron-3.5-super-vl:free"
    temperature: float = 0.0
    timeout_seconds: float = 90.0
    max_retries: int = 2
    api_key_env: str = "OPENROUTER_API_KEY"

    @property
    def api_key(self) -> str:
        return os.getenv(self.api_key_env, "").strip()


class EmbeddingSettings(BaseModel):
    runtime: str = "openrouter"  # "openrouter" | "ollama"
    provider: str = "openrouter"
    endpoint: str = "https://openrouter.ai/api/v1"
    model: str = "nvidia/nemotron-3-embed-1b:free"
    dimension: int = 2048
    batch_size: int = 16
    api_key_env: str = "OPENROUTER_API_KEY"

    @property
    def api_key(self) -> str:
        return os.getenv(self.api_key_env, "").strip()


class SystemOneSettings(BaseModel):
    runtime: str = "openrouter"
    provider: str = "openrouter"
    endpoint: str = "https://openrouter.ai/api/alpha/decisions"
    model: str = "inception/mercury-decide:free"
    timeout_seconds: float = 30.0
    api_key_env: str = "OPENROUTER_API_KEY"

    @property
    def api_key(self) -> str:
        return os.getenv(self.api_key_env, "").strip()


class RerankerSettings(BaseModel):
    enabled: bool = False
    model: str = "BAAI/bge-reranker-base"


class VersionSettings(BaseModel):
    prompt_version: str = "v1.0"
    ontology_version: str = "v1.0"
    schema_version: str = "v1.0"
    chunker_version: str = "v1.0"
    extraction_version: str = "v1.0"


class ChunkingSettings(BaseModel):
    target_tokens: int = 700
    overlap_tokens: int = 100
    min_tokens: int = 100
    max_tokens: int = 900


class ExtractionSettings(BaseModel):
    confidence_floor: float = 0.5
    evidence_match_threshold: float = 0.85
    max_extraction_chunks: int = 800
    dry_run_sample_size: int = 20
    confirm_full_ingestion: bool = True
    prefilter_loss_target: float = 0.05


class ResolutionSettings(BaseModel):
    exact_match_threshold: float = 1.0
    embedding_similarity_threshold: float = 0.85
    review_band_lower: float = 0.70
    review_band_upper: float = 0.85


class RouterSettings(BaseModel):
    confidence_threshold: float = 0.75
    fallback_route: str = "hybrid"


class QuerySettings(BaseModel):
    default_top_k: int = 8
    max_top_k: int = 20
    max_question_length: int = 500
    graph_path_timeout_seconds: float = 5.0
    graph_path_hard_limit: int = 50
    context_token_budget: int = 4000
    runtime_support_check: bool = False


class SECSettings(BaseModel):
    user_agent_env: str = "SEC_USER_AGENT"
    rate_limit_per_second: float = 5.0
    raw_cache_dir: str = "data/raw"
    processed_dir: str = "data/processed"

    @property
    def user_agent(self) -> str:
        ua = os.getenv(self.user_agent_env, "KG_RAG_Research research_bot@example.com")
        return ua


class PostgresSettings(BaseModel):
    host_env: str = "POSTGRES_HOST"
    port_env: str = "POSTGRES_PORT"
    database_env: str = "POSTGRES_DB"
    user_env: str = "POSTGRES_USER"
    password_env: str = "POSTGRES_PASSWORD"
    pool_size: int = 10

    @property
    def host(self) -> str:
        return os.getenv(self.host_env) or os.getenv("DATABASE_POSTGRES_HOST") or "127.0.0.1"

    @property
    def port(self) -> int:
        return int(os.getenv(self.port_env) or os.getenv("DATABASE_POSTGRES_PORT") or "5432")

    @property
    def database(self) -> str:
        return os.getenv(self.database_env) or os.getenv("DATABASE_POSTGRES_DB") or "kgrag"

    @property
    def user(self) -> str:
        return os.getenv(self.user_env) or os.getenv("DATABASE_POSTGRES_USER") or "kgrag"

    @property
    def password(self) -> str:
        return os.getenv(self.password_env) or os.getenv("DATABASE_POSTGRES_PASSWORD") or ""

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class Neo4jSettings(BaseModel):
    uri_env: str = "NEO4J_URI"
    user_env: str = "NEO4J_USER"
    password_env: str = "NEO4J_PASSWORD"

    @property
    def uri(self) -> str:
        return os.getenv(self.uri_env) or os.getenv("DATABASE_NEO4J_URI") or "bolt://127.0.0.1:7687"

    @property
    def user(self) -> str:
        return os.getenv(self.user_env) or os.getenv("DATABASE_NEO4J_USER") or "neo4j"

    @property
    def password(self) -> str:
        return os.getenv(self.password_env) or os.getenv("DATABASE_NEO4J_PASSWORD") or ""


class DatabaseSettings(BaseModel):
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)


class StatisticsSettings(BaseModel):
    bootstrap_iterations: int = 2000
    random_seed: int = 42
    min_category_size_confirmatory: int = 15


class Settings(BaseModel):
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    system_one: SystemOneSettings = Field(default_factory=SystemOneSettings)
    reranker: RerankerSettings = Field(default_factory=RerankerSettings)
    versions: VersionSettings = Field(default_factory=VersionSettings)
    chunking: ChunkingSettings = Field(default_factory=ChunkingSettings)
    extraction: ExtractionSettings = Field(default_factory=ExtractionSettings)
    resolution: ResolutionSettings = Field(default_factory=ResolutionSettings)
    router: RouterSettings = Field(default_factory=RouterSettings)
    query: QuerySettings = Field(default_factory=QuerySettings)
    sec: SECSettings = Field(default_factory=SECSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    statistics: StatisticsSettings = Field(default_factory=StatisticsSettings)


def find_config_dir() -> Path:
    """Find config directory relative to current file or project root."""
    current = Path(__file__).resolve().parent
    for parent in [current, current.parent, current.parent.parent]:
        candidate = parent / "config"
        if candidate.exists() and (candidate / "settings.yaml").exists():
            return candidate
    return Path("config").resolve()


def load_yaml(file_path: Path) -> dict[str, Any]:
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    with open(file_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache
def get_settings() -> Settings:
    config_dir = find_config_dir()
    settings_file = config_dir / "settings.yaml"
    data = load_yaml(settings_file)

    # Environment variable overrides
    if "LLM_RUNTIME" in os.environ:
        data.setdefault("llm", {})["runtime"] = os.environ["LLM_RUNTIME"]
    if "LLM_MODEL" in os.environ:
        data.setdefault("llm", {})["model"] = os.environ["LLM_MODEL"]
    if "EMBEDDING_MODEL" in os.environ:
        data.setdefault("embedding", {})["model"] = os.environ["EMBEDDING_MODEL"]
    if "EMBEDDING_DIMENSION" in os.environ:
        data.setdefault("embedding", {})["dimension"] = int(os.environ["EMBEDDING_DIMENSION"])
    if "SYSTEM_ONE_MODEL" in os.environ:
        data.setdefault("system_one", {})["model"] = os.environ["SYSTEM_ONE_MODEL"]

    return Settings(**data)


@lru_cache
def get_ontology() -> dict[str, Any]:
    config_dir = find_config_dir()
    ontology_file = config_dir / "ontology.yaml"
    return load_yaml(ontology_file)


@lru_cache
def get_prefilter_config() -> dict[str, Any]:
    config_dir = find_config_dir()
    prefilter_file = config_dir / "prefilter.yaml"
    return load_yaml(prefilter_file)
