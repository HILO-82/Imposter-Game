import os

from flask import Flask, render_template

from config import Config
from extensions import db
from models import Word
from routes.game import game_bp
from routes.lobby import lobby_bp
from words import seed_words_table


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    app.register_blueprint(lobby_bp)
    app.register_blueprint(game_bp)

    with app.app_context():
        db.create_all()
        seed_words_table(db.session, Word)
        from ml.train_models import main as train_models

        model_dir = os.path.join(app.root_path, "knn_model.pkl")
        if not os.path.exists(model_dir):
            train_models()

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403, message="Access denied."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, message="Page not found."), 404

    @app.errorhandler(500)
    def server_error(_e):
        # Do not expose stack traces to users (DAST requirement)
        return render_template("error.html", code=500, message="Something went wrong."), 500

    return app


app = create_app()

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    app.run(host=host, port=int(os.environ.get("PORT", 5000)), debug=app.config["DEBUG"])
