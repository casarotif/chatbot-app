from flask import Flask
from app.config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # O cliente OpenAI será inicializado dinamicamente quando necessário
    # usando a configuração centralizada do Flask

    from app.routes import main
    app.register_blueprint(main)

    return app