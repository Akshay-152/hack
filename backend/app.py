"""Campus Event Recommendation Bot — Flask backend entry point."""
from __future__ import annotations

from flask import Flask, g, jsonify, send_from_directory
from flask_cors import CORS

from config import Config
from storage import get_store


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_class)
    app.store = get_store(app.config)

    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGIN"]}})

    from routes.auth_routes import bp as auth_bp
    from routes.events import bp as events_bp
    from routes.recommendations import bp as recommendations_bp
    from routes.registrations import bp as registrations_bp
    from routes.profile import bp as profile_bp
    from routes.admin import bp as admin_bp

    for blueprint in (auth_bp, events_bp, recommendations_bp,
                      registrations_bp, profile_bp, admin_bp):
        app.register_blueprint(blueprint)

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify(error="not found"), 404

    @app.errorhandler(500)
    def server_error(_e):
        return jsonify(error="internal server error"), 500

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", backend=app.config["DB_BACKEND"])

    # Serve the frontend from the same server (convenient for dev/demo).
    FRONTEND_DIR = "../frontend"

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
    create_app().run(debug=Config.DEBUG, port=int(Config.SECRET_KEY == "x" and 0 or 5000))
