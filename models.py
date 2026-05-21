from datetime import datetime

from extensions import db


class Game(db.Model):
    __tablename__ = "games"

    game_id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    num_players = db.Column(db.Integer, nullable=False)
    winning_role = db.Column(db.String(20), nullable=True)
    secret_word = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)
    round_number = db.Column(db.Integer, default=1, nullable=False)
    phase = db.Column(db.String(20), default="clue", nullable=False)

    players = db.relationship("Player", backref="game", lazy=True, cascade="all, delete-orphan")
    rounds = db.relationship("Round", backref="game", lazy=True, cascade="all, delete-orphan")
    votes = db.relationship("Vote", backref="game", lazy=True, cascade="all, delete-orphan")


class Player(db.Model):
    __tablename__ = "players"

    player_id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.game_id"), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    color = db.Column(db.String(10), default="#ff0000")
    was_voted_out = db.Column(db.Boolean, default=False, nullable=False)
    is_bot = db.Column(db.Boolean, default=False, nullable=False)

    rounds = db.relationship("Round", backref="player", lazy=True)
    votes_cast = db.relationship(
        "Vote",
        foreign_keys="Vote.voter_id",
        backref="voter",
        lazy=True,
    )
    votes_received = db.relationship(
        "Vote",
        foreign_keys="Vote.target_id",
        backref="target",
        lazy=True,
    )


class Round(db.Model):
    __tablename__ = "rounds"

    round_id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.game_id"), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    clue_given = db.Column(db.String(100), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.player_id"), nullable=False)


class Vote(db.Model):
    __tablename__ = "votes"

    vote_id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.game_id"), nullable=False)
    round_id = db.Column(db.Integer, db.ForeignKey("rounds.round_id"), nullable=True)
    voter_id = db.Column(db.Integer, db.ForeignKey("players.player_id"), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey("players.player_id"), nullable=False)


class Word(db.Model):
    __tablename__ = "words"

    word_id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)
    category_id = db.Column(db.Integer, nullable=False)
    subcategory_id = db.Column(db.Integer, nullable=False)
    word_length = db.Column(db.Integer, nullable=False)
    commonality = db.Column(db.Float, nullable=False)
