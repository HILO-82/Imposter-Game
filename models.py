from datetime import datetime, timezone

from extensions import db


class Settings(db.Model):
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True, default=1)
    default_imposter_count = db.Column(db.Integer, default=1, nullable=False)
    default_jester_count = db.Column(db.Integer, default=0, nullable=False)
    default_jester_info = db.Column(db.String(20), default="nothing", nullable=False)
    default_category = db.Column(db.String(50), default="Animals", nullable=False)
    default_player_count = db.Column(db.Integer, default=6, nullable=False)
    dark_mode = db.Column(db.Boolean, default=False, nullable=False)
    font_size = db.Column(db.Integer, default=16, nullable=False)
    high_contrast = db.Column(db.Boolean, default=False, nullable=False)


class Game(db.Model):
    __tablename__ = "games"

    game_id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    num_players = db.Column(db.Integer, nullable=False)
    imposter_count = db.Column(db.Integer, default=1, nullable=False)
    jester_count = db.Column(db.Integer, default=0, nullable=False)
    jester_info = db.Column(db.String(20), default="nothing", nullable=False)
    winning_role = db.Column(db.String(20), nullable=True)
    secret_word = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="lobby", nullable=False)
    round_number = db.Column(db.Integer, default=1, nullable=False)
    phase = db.Column(db.String(20), default="lobby", nullable=False)
    current_player_index = db.Column(db.Integer, default=0, nullable=False)
    creator_player_id = db.Column(db.Integer, nullable=True)
    is_multi_device = db.Column(db.Boolean, default=False, nullable=False)
    host_token = db.Column(db.String(100), nullable=True, unique=True, index=True)

    players = db.relationship("Player", backref="game", lazy=True, cascade="all, delete-orphan")
    rounds = db.relationship("Round", backref="game", lazy=True, cascade="all, delete-orphan")
    votes = db.relationship("Vote", backref="game", lazy=True, cascade="all, delete-orphan")


class Player(db.Model):
    __tablename__ = "players"

    player_id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.game_id"), nullable=False)
    session_id = db.Column(db.String(100), nullable=True, index=True)
    player_token = db.Column(db.String(100), nullable=True, unique=True, index=True)
    name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    color = db.Column(db.String(10), default="#ff0000")
    was_voted_out = db.Column(db.Boolean, default=False, nullable=False)
    is_bot = db.Column(db.Boolean, default=False, nullable=False)
    is_connected = db.Column(db.Boolean, default=True, nullable=False)

    rounds = db.relationship("Round", backref="player", lazy=True)
    votes_cast = db.relationship("Vote", foreign_keys="Vote.voter_id", backref="voter", lazy=True)
    votes_received = db.relationship("Vote", foreign_keys="Vote.target_id", backref="target", lazy=True)


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
    round_number = db.Column(db.Integer, nullable=False)
    voter_id = db.Column(db.Integer, db.ForeignKey("players.player_id"), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey("players.player_id"), nullable=False)


class GameEvent(db.Model):
    __tablename__ = "game_events"

    event_id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.game_id"), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("players.player_id"), nullable=True)
    event_type = db.Column(db.String(50), nullable=False)  # e.g. "eliminated", "imposter_out"
    notes = db.Column(db.Text, nullable=True)

    game = db.relationship("Game", backref="events")
    player = db.relationship("Player", foreign_keys=[player_id])


class Word(db.Model):
    __tablename__ = "words"

    word_id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)
    category_id = db.Column(db.Integer, nullable=False)
    subcategory_id = db.Column(db.Integer, nullable=False)
    word_length = db.Column(db.Integer, nullable=False)
    commonality = db.Column(db.Float, nullable=False)
