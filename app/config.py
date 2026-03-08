import os

class Config:
    DB_USER = os.environ.get("DB_USER")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")
    DB_NAME = os.environ.get("DB_NAME")
    DB_HOST = os.environ.get("DB_HOST")
    DB_PORT = os.environ.get("DB_PORT")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    # Disable SQLAlchemy event system overhead because it is not needed here.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask secret
    SECRET_KEY = os.environ.get("SECRET_KEY")
    # Separate JWT secret so tokens can be rotated independently of Flask's secret.
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret")
    # Token expiry in minutes
    JWT_EXPIRATION_MINUTES = int(os.environ.get("JWT_EXPIRATION_MINUTES", "60"))