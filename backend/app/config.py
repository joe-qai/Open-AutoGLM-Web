"""Configuration settings for the LOCKIN Agent Platform."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8005
    
    # Model settings
    model_api_url: str = "http://localhost:8000/v1"
    model_name: str = "lockin-phone-9b"
    api_key: str = "EMPTY"
    
    # Agent settings
    max_steps: int = 100
    default_lang: str = "cn"
    default_format: str = "pseudo"
    
    # Device settings
    default_device_type: str = "adb"
    
    # Database settings
    database_url: str = "./app.db"
    
    # Screenshot settings
    screenshot_dir: str = "./screenshots"
    
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PHONE_AGENT_", protected_namespaces=('settings_',))


settings = Settings()
