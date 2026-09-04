# TrustBridge Configuration
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    # Application
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # Database
    database_url: str = "sqlite:///trustbridge.db"

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    # AI Provider (Backend-only)
    ai_provider: str = "openai"
    ai_api_key: Optional[str] = None
    ai_model: str = "gpt-4o-mini"
    ai_max_tokens: int = 2000
    ai_temperature: float = 0.3
    ai_timeout_seconds: int = 120
    ai_base_url: Optional[str] = None

    # ML Model
    ml_model_path: str = "models/isolation_forest_model.pkl"
    ml_scaler_path: str = "models/feature_scaler.pkl"
    ml_feature_cols_path: str = "models/feature_columns.pkl"
    ml_contamination: float = 0.01
    ml_n_estimators: int = 200
    ml_random_state: int = 42

    # Risk Engine
    fraud_rule_multiplier: float = 3.0
    trust_score_weight_payment_reliability: float = 0.40
    trust_score_weight_transaction_consistency: float = 0.35
    trust_score_weight_account_behaviour: float = 0.25
    risk_threshold_high: int = 80
    risk_threshold_moderate: int = 50

    # Payment Simulation
    default_currency: str = "INR"
    idempotency_key_prefix: str = "TB_"
    payment_timeout_seconds: int = 30

    # Frontend
    vite_api_base_url: str = "http://localhost:8000/api"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def ai_configured(self) -> bool:
        return bool(self.ai_api_key and self.ai_api_key != "YOUR_API_KEY_HERE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()