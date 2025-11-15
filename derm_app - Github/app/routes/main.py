from flask import Blueprint, session, render_template, request, redirect, url_for
from app.services.ai_client import ask_ai
from app.services.red_flags import check_red_flags

main_bp = Blueprint("main", __name__)

@main_bp.route("/", methods=["GET", "POST"])
def home():
    if not session.get("authenticated"):
        return redirect(url_for("auth.login"))

    if "conversation" not in session:
        session["conversation"] = []

    red_warning = None
    conversation = session["conversation"]

    if request.method == "POST":
        text = request.form["question"].strip()
        image_file = request.files.get("image")

        # Add the user's question
        user_content = text

        # If an image was attached, just note it in the conversation for now
        if image_file and image_file.filename:
            user_content += " [Image attached (not stored in this demo)]"

        conversation.append({"role": "user", "content": user_content})

        # Red flag detection based on text only
        red_warning = check_red_flags(text)

        # AI response
        answer = ask_ai(conversation, text)
        conversation.append({"role": "assistant", "content": answer})

        session["conversation"] = conversation

    return render_template("home.html",
                           conversation=conversation,
                           red_warning=red_warning)
