import logging

from flask import Flask, request
from prometheus_flask_exporter import PrometheusMetrics
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from sqlalchemy import text

logger = logging.getLogger(__name__)

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app(test_config=None):
    app = Flask(__name__)

    # Expose /metrics for Prometheus (HTTP counters, latency histogram, etc.)
    PrometheusMetrics(app, path="/metrics")

    if test_config is None:
        app.config.from_object("app.config.Config")
    else:
        app.config.update(test_config)

    CORS(
        app,
        resources={
            r"/*": {
                "origins": [
                    "http://localhost:3000",
                    "http://app.174.138.113.111.sslip.io",
                    "https://app.174.138.113.111.sslip.io" # in case we end up using HTTPS
                ]
            }
        },
    )

    # After every request handler, inspect the response and log if there's a msg or error
    @app.after_request
    def log_api_response(response):
        if not response.is_json:
            return response

        res_json = response.get_json(silent=True)
        if not isinstance(res_json, dict):
            return response

        message = res_json.get("message")
        error = res_json.get("error")
        if message is None and error is None:
            return response

        logger.info(f"API response method={request.method} path={request.path} status={response.status_code} message={message} error={error}")
        return response

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    from .routes import api_bp
    app.register_blueprint(api_bp)

    @app.get("/health")
    def health_check():
        return {"status": "ok", "message": "Finance backend is running."}, 200

    @app.get("/health/db")
    def health_check_db():
        """Readiness check: verifies the application can reach the database."""
        try:
            db.session.execute(text("SELECT 1"))
            return {"status": "ok", "message": "Database connection is healthy."}, 200
        except Exception:
            return {
                "status": "error",
                "message": "Database connection failed.",
            }, 503

    return app
