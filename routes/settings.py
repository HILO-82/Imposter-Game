from flask import Blueprint, redirect, render_template, request, url_for

from extensions import db
from models import Settings
from words import get_word_categories

settings_bp = Blueprint("settings", __name__)


def get_or_create_settings():
    s = Settings.query.get(1)
    if not s:
        s = Settings(id=1)
        db.session.add(s)
        db.session.commit()
    return s


@settings_bp.route("/settings", methods=["GET"])
def settings_page():
    s = get_or_create_settings()
    categories = get_word_categories()
    return render_template("settings.html", settings=s, categories=categories)


@settings_bp.route("/settings", methods=["POST"])
def save_settings():
    s = get_or_create_settings()
    s.default_imposter_count = int(request.form.get("imposter_count", 1))
    s.default_jester_count = int(request.form.get("jester_count", 0))
    s.default_jester_info = request.form.get("jester_info", "nothing")
    s.default_category = request.form.get("category", "Animals")
    s.default_player_count = int(request.form.get("player_count", 6))
    db.session.commit()
    return redirect(url_for("lobby.index"))
