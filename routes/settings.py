from flask import Blueprint, redirect, render_template, request, url_for

from extensions import db
from models import Settings
from words import get_word_categories

settings_bp = Blueprint("settings", __name__)


def get_or_create_settings():
    s = db.session.get(Settings, 1)
    if not s:
        s = Settings(id=1)
        db.session.add(s)
        db.session.commit()
    return s


@settings_bp.route("/settings", methods=["GET"])
def settings_page():
    s = get_or_create_settings()
    categories = get_word_categories()
    tab = request.args.get("tab", "game")
    return render_template("settings.html", settings=s, categories=categories, active_tab=tab)


@settings_bp.route("/settings", methods=["POST"])
def save_settings():
    s = get_or_create_settings()
    tab = request.form.get("tab", "game")
    if tab == "app":
        s.dark_mode = request.form.get("dark_mode") == "on"
        s.font_size = int(request.form.get("font_size", 16))
        s.high_contrast = request.form.get("high_contrast") == "on"
    else:
        s.default_imposter_count = int(request.form.get("imposter_count", 1))
        s.default_jester_count = int(request.form.get("jester_count", 0))
        s.default_jester_info = request.form.get("jester_info", "nothing")
        s.default_category = request.form.get("category", "Animals")
        s.default_player_count = int(request.form.get("player_count", 6))
    db.session.commit()
    return redirect(url_for("settings.settings_page", tab=tab))
