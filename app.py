import os

from flask import Flask, g, render_template

from config import Config
from extensions import db, socketio
from models import GameEvent, Settings, Word
from routes.game import game_bp
from routes.lobby import lobby_bp
from routes.settings import settings_bp
from socketio_events import register_socketio_events
from words import seed_words_table


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    app.register_blueprint(lobby_bp)
    app.register_blueprint(game_bp)
    app.register_blueprint(settings_bp)

    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    register_socketio_events(socketio)

    with app.app_context():
        db.create_all()
        seed_words_table(db.session, Word)

    @app.before_request
    def load_settings():
        from routes.settings import get_or_create_settings
        g.settings = get_or_create_settings()

    @app.context_processor
    def inject_settings():
        s = getattr(g, 'settings', None)
        return {
            "dark_mode": s is not None and s.dark_mode,
            "font_size": s.font_size if s else 16,
            "high_contrast": s is not None and s.high_contrast,
        }

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403, message="Access denied."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, message="Page not found."), 404

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("error.html", code=500, message="Something went wrong."), 500

    return app, socketio


if __name__ == "__main__":
    flask_app, socketio_instance = create_app()
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    socketio_instance.run(flask_app, host=host, port=int(os.environ.get("PORT", 5001)), debug=flask_app.config["DEBUG"], allow_unsafe_werkzeug=True)
