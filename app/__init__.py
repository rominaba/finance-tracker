from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from sqlalchemy import text

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app(test_config=None):
    app = Flask(__name__)

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
