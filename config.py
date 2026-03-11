import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    secret_key: str
    flask_env: str
    cors_allowed_origins: str
    host: str
    port: int
    ssl_cert_file: str
    ssl_key_file: str
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str

    @property
    def cors_origins(self):
        if self.cors_allowed_origins.strip() == "*":
            return "*"
        return [item.strip() for item in self.cors_allowed_origins.split(",") if item.strip()]

    @property
    def cloudinary_configured(self) -> bool:
        return bool(self.cloudinary_cloud_name and self.cloudinary_api_key and self.cloudinary_api_secret)


def load_settings() -> Settings:
    return Settings(
        secret_key=os.getenv("SECRET_KEY", "super-secret-key-change-me-in-production"),
        flask_env=os.getenv("FLASK_ENV", "development"),
        cors_allowed_origins=os.getenv("CORS_ALLOWED_ORIGINS", "*"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 5000)),
        ssl_cert_file=os.getenv("SSL_CERT_FILE", ""),
        ssl_key_file=os.getenv("SSL_KEY_FILE", ""),
        db_host=os.getenv("DB_HOST", "localhost"),
        db_port=int(os.getenv("DB_PORT", "3306")),
        db_user=os.getenv("DB_USER", "root"),
        db_password=os.getenv("DB_PASSWORD", ""),
        db_name=os.getenv("DB_NAME", "upred_db"),
        cloudinary_cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", ""),
        cloudinary_api_key=os.getenv("CLOUDINARY_API_KEY", ""),
        cloudinary_api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
    )
