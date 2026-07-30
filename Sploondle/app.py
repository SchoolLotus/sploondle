from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from datetime import datetime, date

import json
import os

#
# -----------------------------
# Flask Configuration
# -----------------------------
#

app = Flask(__name__)

app.secret_key = "change_this_secret_key"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///sploondle.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

#
# -----------------------------
# Database Models
# -----------------------------
#

class User(db.Model):

    user_id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )


class Weapon(db.Model):

    weapon_id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    weapon_class = db.Column(
        db.String(50),
        nullable=False
    )

    sub_weapon = db.Column(
        db.String(50),
        nullable=False
    )

    special_weapon = db.Column(
        db.String(50),
        nullable=False
    )


class Game(db.Model):

    game_id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.user_id"),
        nullable=False
    )

    answer_weapon_id = db.Column(
        db.Integer,
        db.ForeignKey("weapon.weapon_id"),
        nullable=False
    )

    game_date = db.Column(
        db.Date,
        nullable=False
    )

    completed = db.Column(
        db.Boolean,
        default=False
    )

    guesses = db.Column(
        db.Text,
        default="[]"
    )


#
# -----------------------------
# Context Processor
# -----------------------------
#

@app.context_processor
def inject_user():

    return {

        "logged_in": "user_id" in session

    }


#
# -----------------------------
# Load weapons.json
# -----------------------------
#

def populate_weapons():

    json_path = os.path.join(
        app.root_path,
        "weapons.json"
    )

    if not os.path.exists(json_path):

        print("ERROR: weapons.json not found.")

        return

    with open(json_path, "r", encoding="utf-8") as file:

        weapons = json.load(file)

    added = 0
    updated = 0

    for weapon_data in weapons:

        weapon = Weapon.query.filter_by(
            name=weapon_data["name"]
        ).first()

        if weapon is None:

            weapon = Weapon(
                name=weapon_data["name"],
                weapon_class=weapon_data["weapon_class"],
                sub_weapon=weapon_data["sub_weapon"],
                special_weapon=weapon_data["special_weapon"]
            )

            db.session.add(weapon)

            added += 1

        else:

            changed = False

            if weapon.weapon_class != weapon_data["weapon_class"]:

                weapon.weapon_class = weapon_data["weapon_class"]
                changed = True

            if weapon.sub_weapon != weapon_data["sub_weapon"]:

                weapon.sub_weapon = weapon_data["sub_weapon"]
                changed = True

            if weapon.special_weapon != weapon_data["special_weapon"]:

                weapon.special_weapon = weapon_data["special_weapon"]
                changed = True

            if changed:

                updated += 1

    db.session.commit()

    print(f"Weapons added: {added}")
    print(f"Weapons updated: {updated}")
    print(f"Total weapons in database: {Weapon.query.count()}")

#
# -----------------------------
# Weapon of the Day
# -----------------------------
#

def get_daily_weapon():

    weapons = Weapon.query.order_by(
        Weapon.weapon_id
    ).all()

    if len(weapons) == 0:

        return None

    today = date.today()

    index = today.toordinal() % len(weapons)

    return weapons[index]

#
# -----------------------------
# Compare Weapons
# -----------------------------
#

def compare_weapons(answer, guess):

    return {

        "name": guess.name,

        "weapon_class": guess.weapon_class,

        "sub_weapon": guess.sub_weapon,

        "special_weapon": guess.special_weapon,

        "weapon_correct":
            guess.weapon_id == answer.weapon_id,

        "class_correct":
            guess.weapon_class == answer.weapon_class,

        "sub_correct":
            guess.sub_weapon == answer.sub_weapon,

        "special_correct":
            guess.special_weapon == answer.special_weapon

    }


#
# -----------------------------
# Compare Guess
# -----------------------------
#

def compare_weapons(answer, guess):

    return {

        "name": guess.name,

        "class_correct":

            guess.weapon_class == answer.weapon_class,

        "sub_correct":

            guess.sub_weapon == answer.sub_weapon,

        "special_correct":

            guess.special_weapon == answer.special_weapon,

        "weapon_correct":

            guess.weapon_id == answer.weapon_id

    }


#
# -----------------------------
# Current Game
# -----------------------------
#

def get_current_game(user_id):

    today = date.today()

    game = Game.query.filter_by(

        user_id=user_id,

        game_date=today

    ).first()

    if game:

        return game

    answer = get_daily_weapon()

    game = Game(

        user_id=user_id,

        answer_weapon_id=answer.weapon_id,

        game_date=today,

        completed=False,

        guesses="[]"

    )

    db.session.add(game)

    db.session.commit()

    return game

#
# -----------------------------
# Home
# -----------------------------
#

@app.route("/")
def home():

    return render_template("home.html")


#
# -----------------------------
# Register
# -----------------------------
#

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if email == "" or password == "":

            flash("Please fill in all fields.")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():

            flash("That email is already registered.")
            return redirect(url_for("register"))

        username = email.split("@")[0]

        user = User(

            username=username,

            email=email,

            password_hash=generate_password_hash(password)

        )

        db.session.add(user)
        db.session.commit()

        flash("Account created successfully.")

        return redirect(url_for("login"))

    return render_template("register.html")


#
# -----------------------------
# Login
# -----------------------------
#

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):

            session["user_id"] = user.user_id

            return redirect(url_for("game"))

        flash("Invalid email or password.")

    return render_template("login.html")


#
# -----------------------------
# Logout
# -----------------------------
#

@app.route("/logout")
def logout():

    session.clear()

    flash("Logged out.")

    return redirect(url_for("home"))


#
# -----------------------------
# Autocomplete API
# -----------------------------
#

@app.route("/weapon_list")
def weapon_list():

    weapons = Weapon.query.order_by(Weapon.name).all()

    return jsonify([weapon.name for weapon in weapons])


#
# -----------------------------
# Game
# -----------------------------
#

@app.route("/game", methods=["GET", "POST"])
def game():

    if "user_id" not in session:

        return redirect(url_for("login"))

    game = get_current_game(session["user_id"])

    answer = Weapon.query.get(game.answer_weapon_id)

    guess_history = json.loads(game.guesses)

    results = []

    # Rebuild previous guesses
    for guess_name in guess_history:

        weapon = Weapon.query.filter_by(name=guess_name).first()

        if weapon:

            results.append(compare_weapons(answer, weapon))

    if request.method == "POST" and not game.completed:

        guess_name = request.form.get("guess", "").strip()

        guess = Weapon.query.filter_by(name=guess_name).first()

        if guess is None:

            flash("Weapon not found.")

        elif guess.name in guess_history:

            flash("You've already guessed that weapon.")

        else:

            guess_history.append(guess.name)

            game.guesses = json.dumps(guess_history)

            if guess.weapon_id == answer.weapon_id:

                game.completed = True

                flash("🎉 You guessed today's weapon!")

            db.session.commit()

            results.append(compare_weapons(answer, guess))

    return render_template(

        "game.html",

        guesses=results,

        completed=game.completed

    )


#
# -----------------------------
# New Game
# -----------------------------
#
# For testing only.
# Remove this route if you want only one
# global weapon per day.
#

@app.route("/reset")
def reset_game():

    if "user_id" not in session:

        return redirect(url_for("login"))

    today = date.today()

    game = Game.query.filter_by(

        user_id=session["user_id"],

        game_date=today

    ).first()

    if game:

        db.session.delete(game)

        db.session.commit()

    flash("Today's game has been reset.")

    return redirect(url_for("game"))


#
# -----------------------------
# Run App
# -----------------------------
#

if __name__ == "__main__":

    with app.app_context():

        db.create_all()

        populate_weapons()

        print("------------------------------------")
        print(f"Users   : {User.query.count()}")
        print(f"Weapons : {Weapon.query.count()}")
        print(f"Games   : {Game.query.count()}")
        print("------------------------------------")

    app.run(debug=True)