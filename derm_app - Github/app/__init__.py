from flask import Flask

def create_app():
    app = Flask(__name__)
    app.secret_key = "dev-secret"  # change if needed

    from .routes.auth import auth_bp
    from .routes.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    return app
