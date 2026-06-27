from functools import lru_cache
from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "EnterpriseMind"

    # 前端允许访问后端的来源，多个地址使用逗号分隔
    frontend_origins: str = (
        "http://127.0.0.1:5173,"
        "http://localhost:5173"
    )

    @property
    def frontend_origin_list(self) -> list[str]:
        """将逗号分隔的前端来源转换为列表。"""
        return [
            item.strip()
            for item in self.frontend_origins.split(",")
            if item.strip()
        ]

    database_url: str = (
        "postgresql+asyncpg://"
        "enterprisemind:enterprisemind"
        "@127.0.0.1:5432/enterprisemind"
    )
    readonly_database_url: str = (
        "postgresql+asyncpg://"
        "enterprisemind_reader:reader-local-password"
        "@127.0.0.1:5432/enterprisemind"
    )

    jwt_secret: str = "development-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30

    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_collection: str = "enterprise_knowledge_bge_m3_v1"
    embedding_dimensions: int = 1024
    ollama_embedding_model: str = "bge-m3"
    ollama_embedding_timeout_seconds: float = 60.0
    retrieval_minimum_score: float = 0.20
    retrieval_full_answer_score: float = 0.45
    retrieval_partial_answer_score: float = 0.20
    retrieval_minimum_hit_count: int = 1
    retrieval_rerank_candidates: int = 8
    retrieval_full_relevance_score: float = 0.72
    retrieval_full_coverage_score: float = 0.55
    retrieval_partial_relevance_score: float = 0.55
    retrieval_partial_vector_score: float = 0.15
    retrieval_final_top_k: int = 5

    memory_enabled: bool = True
    memory_collection: str = "enterprise_conversation_memory_v1"
    memory_top_k: int = 3
    memory_minimum_score: float = 0.25
    memory_summary_trigger_messages: int = 6
    memory_summary_recent_messages: int = 8
    memory_summary_max_chars: int = 1200

    redis_url: str = "redis://127.0.0.1:6379/0"
    rq_document_queue: str = "document_ingestion"
    rq_job_timeout_seconds: int = 300
    rq_result_ttl_seconds: int = 86400

    upload_directory: Path = Path("uploads")
    maximum_upload_bytes: int = 10 * 1024 * 1024

    evaluation_case_directory: Path = Path(
        "evaluation/cases"
    )
    evaluation_maximum_drop: float = 0.03
    evaluation_executor_mode: str = "orchestrator"
    evaluation_judge_enabled: bool = True
    evaluation_judge_minimum_score: float = 0.75
    evaluation_judge_fail_closed: bool = True
    evaluation_judge_model_sensitivity: str = "internal"
    evaluation_default_hr_username: str = "hr01"
    evaluation_default_it_username: str = "it01"
    evaluation_default_finance_username: str = "finance01"
    evaluation_default_employee_username: str = "employee01"
    evaluation_default_admin_username: str = "admin"
    intent_router_mode: str = "rule"
    tool_manager_enabled: bool = False
    tool_default_timeout_ms: int = 3000
    tool_default_cache_ttl_seconds: int = 30
    tool_circuit_failure_threshold: int = 3
    tool_circuit_recovery_seconds: int = 30
    composite_agent_enabled: bool = False
    monitor_enabled: bool = False
    benchmark_output_dir: Path = Path("evaluation/reports")
    benchmark_judge_enabled: bool = True
    benchmark_judge_minimum_score: float = 0.75

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_seconds: float = 120.0

    external_model_base_url: str = (
        "https://api.example.com/v1"
    )
    external_model_api_key: str = ""
    external_model_name: str = "external-chat-model"
    external_model_timeout_seconds: float = 30.0

    allow_external_for_internal: bool = False
    sql_max_rows: int = 200
    sql_timeout_seconds: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
