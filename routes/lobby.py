from flask import Blueprint, redirect, render_template, session, url_for

from models import Settings

lobby_bp = Blueprint("lobby", __name__)


@lobby_bp.route("/")
def index():
    session.pop("error", None)
    return render_template("index.html")
