"""
Initialise la base SQLite (tables addresses + btc_tags).
Usage : python -m scripts.init_db
"""
from config import Config
from services.database import init_db

if __name__ == "__main__":
    init_db(Config.DB_PATH)
    print(f"Base initialisée : {Config.DB_PATH}")