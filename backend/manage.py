from flask_migrate import Migrate
from flask import Flask
from app import create_app, db
from config import DevelopmentConfig

app = create_app(DevelopmentConfig)
migrate = Migrate(app, db)

@app.cli.command()
def setup_db():
    """Setup database and create tables"""
    db.create_all()
    print("Database tables created!")

if __name__ == '__main__':
    app.run()