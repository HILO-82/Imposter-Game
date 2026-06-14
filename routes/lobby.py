from flask import Blueprint, render_template, session

from ml.insights import random_tip

lobby_bp = Blueprint("lobby", __name__)


@lobby_bp.route("/")
def index():
    session.pop("error", None)
    tip = random_tip()
    return render_template("index.html", tip=tip)
