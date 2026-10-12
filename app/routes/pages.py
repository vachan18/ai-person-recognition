"""HTML pages for Dashboard, Person Registration, and Profile Management."""

from flask import Blueprint, render_template

pages_bp = Blueprint("pages", __name__)


@pages_bp.get("/")
def dashboard():
    return render_template("dashboard.html", active="dashboard")


@pages_bp.get("/register")
def register_person():
    return render_template("register.html", active="register")


@pages_bp.get("/manage")
def manage_people():
    return render_template("manage.html", active="manage")
