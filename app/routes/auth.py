from flask import Blueprint, render_template, request, redirect, url_for, session

auth_bp = Blueprint("auth", __name__)

DEMO_USER = {"email": "demo@example.com", "password": "password123"}
DEMO_2FA = "123456"

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (request.form["email"] == DEMO_USER["email"] and 
            request.form["password"] == DEMO_USER["password"]):
            session["pending"] = DEMO_USER["email"]
            return redirect(url_for("auth.verify_2fa"))
    return render_template("login.html")

@auth_bp.route("/verify-2fa", methods=["GET", "POST"])
def verify_2fa():
    if request.method == "POST":
        if request.form["code"] == DEMO_2FA:
            session["authenticated"] = True
            return redirect(url_for("main.home"))
    return render_template("verify_2fa.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))