import atexit

from flask import Flask, render_template

from config import Config
from routes.api import bp as api_bp
from services.address_repository import AddressRepository
from services.bch_service import BchService
from services.blockchain_client import BlockchainInfoClient
from services.btc_service import BtcService
from services.database import init_db
from services.eth_service import EthService
from services.identity_service import IdentityService
from services.price_service import PriceService
from services.scraper_service import BlockchainComScraper
from services.tag_service import TagService


def create_app() -> Flask:
    app = Flask(__name__)

    # --- Base de données ---
    init_db(Config.DB_PATH)

    # --- Services ---
    client = BlockchainInfoClient()
    tag_service = TagService()
    repo = AddressRepository()

    scraper = None
    if Config.SCRAPER_ENABLED:
        scraper = BlockchainComScraper()
        atexit.register(scraper.close)

    identity = IdentityService(
        tag_service=tag_service,
        scraper=scraper,
    )

    app.extensions["services"] = {
        "btc": BtcService(client),
        "bch": BchService(client),
        "eth": EthService(client),
        "price": PriceService(),
        "tags": tag_service,
        "identity": identity,
        "repo": repo,
        "scraper": scraper,
    }

    app.register_blueprint(api_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
    )