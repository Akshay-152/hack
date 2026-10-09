"""Campus Event Management System — Flask backend entry point."""
from __future__ import annotations

import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

import db
from config import Config

FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend"))
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_class)
    app.config["UPLOAD_DIR"] = UPLOAD_DIR
    app.secret_key = app.config["SECRET_KEY"]
    app.permanent_session_lifetime = 60 * 60 * 24 * 14  # 2 weeks
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    db.init_db()

    from auth_service import seed_admin
    seed_admin()

    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGIN"]}},
         supports_credentials=True)

    from routes.ai import bp as ai_bp
    from routes.admin import bp as admin_bp
    from routes.auth_routes import bp as auth_bp
    from routes.events import bp as events_bp
    from routes.profile import bp as profile_bp
    from routes.recommendations import bp as recommendations_bp
    from routes.registrations import bp as registrations_bp
    from routes.suggestions import bp as suggestions_bp

    for blueprint in (auth_bp, events_bp, recommendations_bp,
                      registrations_bp, profile_bp, admin_bp,
                      suggestions_bp, ai_bp):
        app.register_blueprint(blueprint)

    @app.get("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(UPLOAD_DIR, filename)

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", database="sqlite", )

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify(error="not found"), 404

    @app.errorhandler(500)
    def server_error(_e):
        return jsonify(error="internal server error"), 500

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/<path:page>")
    def page(page):
        if page.startswith("api"):
            return jsonify(error="not found"), 404
        return send_from_directory(FRONTEND_DIR, page)

    return app


if __name__ == "__main__":
    create_app().run(debug=Config.DEBUG, port=5000)
