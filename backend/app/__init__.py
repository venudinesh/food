from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_socketio import SocketIO
from config import Config

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()
socketio = SocketIO(cors_allowed_origins="*")

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)

    # Import models to ensure they are registered with SQLAlchemy
    from app.models import models

    from app.routes import auth
    from app.routes import delivery
    from app.routes import telecast
    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(delivery.delivery_bp)
    app.register_blueprint(telecast.telecast_bp)

    # Initialize telecast service
    from app.services.live_telecast_service import LiveTelecastService, register_socket_events
    telecast_service = LiveTelecastService(socketio)
    app.telecast_service = telecast_service

    # Register Socket.IO events
    register_socket_events(socketio, telecast_service)

    return app