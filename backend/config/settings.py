"""Phase 4-5: Central settings with TRADING_MODE and security guards."""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradingMode(str, Enum):
    PAPER = "PAPER"
    TESTNET = "TESTNET"
    LIVE = "LIVE"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Phase 4
    trading_mode: TradingMode = Field(default=TradingMode.PAPER, alias="TRADING_MODE")

    # Phase 5 - credentials (never logged)
    arcus_api_key: str = Field(default="", alias="ARCUS_API_KEY")
    arcus_api_secret: str = Field(default="", alias="ARCUS_API_SECRET")
    arcus_account_address: str = Field(default="", alias="ARCUS_ACCOUNT_ADDRESS")
    arcus_account_index: int = Field(default=0, alias="ARCUS_ACCOUNT_INDEX")

    # Endpoints (official docs)
    arcus_rest_url: str = Field(default="https://api.arcus.xyz", alias="ARCUS_REST_URL")
    arcus_ws_url: str = Field(default="wss://ws.arcus.xyz", alias="ARCUS_WS_URL")
    arcus_testnet_rest_url: str = Field(
        default="https://testnet-api.arcus.xyz", alias="ARCUS_TESTNET_REST_URL"
    )
    arcus_testnet_ws_url: str = Field(
        default="wss://testnet-ws.arcus.xyz", alias="ARCUS_TESTNET_WS_URL"
    )

    # Strategy / risk (Phases 9-16, 19)
    market: str = Field(default="BTC-PERP", alias="MARKET")
    order_size: float = Field(default=0.001, alias="ORDER_SIZE")
    max_order_size: float = Field(default=0.01, alias="MAX_ORDER_SIZE")
    bid_spread_bps: float = Field(default=10.0, alias="BID_SPREAD_BPS")
    ask_spread_bps: float = Field(default=10.0, alias="ASK_SPREAD_BPS")
    quote_refresh_interval_ms: int = Field(default=1000, alias="QUOTE_REFRESH_INTERVAL_MS")
    max_inventory: float = Field(default=0.05, alias="MAX_INVENTORY")
    max_exposure: float = Field(default=5000.0, alias="MAX_EXPOSURE")
    max_daily_loss: float = Field(default=500.0, alias="MAX_DAILY_LOSS")
    max_open_orders: int = Field(default=2, alias="MAX_OPEN_ORDERS")
    max_order_age_sec: int = Field(default=30, alias="MAX_ORDER_AGE_SEC")
    min_expected_profit: float = Field(default=0.1, alias="MIN_EXPECTED_PROFIT")
    min_expected_edge_bps: float = Field(default=2.0, alias="MIN_EXPECTED_EDGE_BPS")
    inventory_skew_factor: float = Field(default=0.5, alias="INVENTORY_SKEW_FACTOR")
    maker_fee_bps: float = Field(default=0.0, alias="MAKER_FEE_BPS")
    dead_mans_switch_timeout_sec: int = Field(
        default=30, alias="DEAD_MANS_SWITCH_TIMEOUT_SEC"
    )

    # Backend
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    database_url: str = Field(default="sqlite+aiosqlite:///./arcus_maker.db", alias="DATABASE_URL")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", alias="LOG_LEVEL"
    )

    @field_validator("trading_mode", mode="before")
    @classmethod
    def _coerce_mode(cls, v: object) -> object:
        if isinstance(v, str):
            return v.upper()
        return v

    @property
    def is_live(self) -> bool:
        return self.trading_mode == TradingMode.LIVE

    @property
    def is_paper(self) -> bool:
        return self.trading_mode == TradingMode.PAPER

    @property
    def active_rest_url(self) -> str:
        if self.trading_mode == TradingMode.TESTNET:
            return self.arcus_testnet_rest_url
        return self.arcus_rest_url

    @property
    def active_ws_url(self) -> str:
        if self.trading_mode == TradingMode.TESTNET:
            return self.arcus_testnet_ws_url
        return self.arcus_ws_url

    def has_credentials(self) -> bool:
        return bool(self.arcus_api_key and self.arcus_api_secret and self.arcus_account_address)


settings = Settings()
