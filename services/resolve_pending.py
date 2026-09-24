"""
Résout les noms des adresses en attente (jamais tentées).
Usage : python -m scripts.resolve_pending

Utile si vous voulez forcer la résolution sans passer par le front.
"""
from app import create_app
from services.address_repository import AddressRepository
from services.identity_service import IdentityService
from services.scraper_service import BlockchainComScraper
from services.tag_service import TagService
from config import Config


def main():
    app = create_app()
    with app.app_context():
        services = app.extensions["services"]
        repo = services["repo"]
        identity = services["identity"]

        pending = repo.list_pending(limit=50)
        print(f"{len(pending)} adresses en attente.")

        for item in pending:
            addr = item["address"]
            chain = item["chain"]
            print(f"→ {addr} ({chain})", end=" ", flush=True)
            try:
                result = identity.resolve(chain, addr)
                repo.set_name(addr, result["name"], result["source"])
                print(f"=> {result['name'] or '(aucun)'} [{result['source'] or '-'}]")
            except Exception as e:
                print(f"erreur : {e}")


if __name__ == "__main__":
    main()