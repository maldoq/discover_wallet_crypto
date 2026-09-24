"""
Scraper pour blockchain.com utilisant un thread dédié.

Playwright sync API est thread-bound : le browser doit être créé ET utilisé
dans le même thread. On utilise donc un worker thread dédié qui possède le
browser. Les autres threads communiquent via une queue et attendent un Event.

NOTE : on n'utilise JAMAIS wait_until="networkidle" sur blockchain.com.
La page charge en permanence des pubs, trackers et WebSockets, donc le
réseau ne se calme jamais. On attend domcontentloaded puis le sélecteur
cible explicitement.
"""

import atexit
import queue
import threading

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from config import Config


class BlockchainComScraper:
    BASE_URL = "https://www.blockchain.com/explorer/addresses/{chain}/{address}"

    # Sélecteurs candidats, testés dans l'ordre.
    NAME_SELECTORS = [
        "[data-testid='address-name']",
        "[data-testid='address-label']",
        "[class*='AddressName']",
        ".address-name",
        ".address-label",
        "h1",
    ]

    def __init__(self):
        self._task_queue: "queue.Queue" = queue.Queue()
        self._closed = False
        self._worker = threading.Thread(
            target=self._worker_loop,
            name="scraper-worker",
            daemon=True,
        )
        self._worker.start()
        atexit.register(self.close)

    # ------------------------------------------------------------------
    # API publique — appelable depuis n'importe quel thread
    # ------------------------------------------------------------------
    def fetch_name(self, chain: str, address: str) -> str | None:
        if self._closed:
            return None

        result = {"name": None, "error": None, "event": threading.Event()}
        self._task_queue.put((chain, address, result))

        # Timeout global (un peu supérieur au timeout Playwright)
        timeout_s = (Config.SCRAPER_TIMEOUT_MS / 1000.0) + 10.0
        if not result["event"].wait(timeout=timeout_s):
            return None

        if result["error"]:
            raise result["error"]
        return result["name"]

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._task_queue.put(None)

    # ------------------------------------------------------------------
    # Worker thread — possède le browser, exécute les tâches
    # ------------------------------------------------------------------
    def _worker_loop(self):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=Config.SCRAPER_HEADLESS,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
                try:
                    self._serve(browser)
                finally:
                    try:
                        browser.close()
                    except Exception:
                        pass
        except Exception:
            self._drain_queue_with_error()

    def _serve(self, browser):
        while True:
            task = self._task_queue.get()
            if task is None:
                break
            chain, address, result = task
            try:
                result["name"] = self._do_scrape(browser, chain, address)
            except Exception as exc:
                result["error"] = exc
            finally:
                result["event"].set()

    def _drain_queue_with_error(self):
        while True:
            try:
                task = self._task_queue.get_nowait()
            except queue.Empty:
                break
            if task is None:
                continue
            _, _, result = task
            result["error"] = RuntimeError("Scraper worker crashed")
            result["event"].set()

    # ------------------------------------------------------------------
    # Scraping à proprement parler (exécuté dans le worker)
    # ------------------------------------------------------------------
    def _do_scrape(self, browser, chain: str, address: str) -> str | None:
        url = self.BASE_URL.format(chain=chain, address=address)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 900},
            locale="fr-FR",
        )
        page = context.new_page()
        try:
            # On bloque les ressources non essentielles pour accélérer et
            # éviter que les trackers/pubs ne bloquent le chargement.
            page.route("**/*", self._route_filter)

            # --- Navigation : domcontentloaded uniquement, jamais networkidle
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=Config.SCRAPER_TIMEOUT_MS,
            )

            # --- Attente ciblée du sélecteur de nom
            # On attend que AU MOINS un des sélecteurs soit présent dans le DOM.
            # On met un timeout court par sélecteur : le premier qui apparaît
            # gagne.
            for selector in self.NAME_SELECTORS:
                try:
                    page.wait_for_selector(
                        selector,
                        state="attached",
                        timeout=5000,
                    )
                except PlaywrightTimeout:
                    continue

                # Laisse le framework (Next.js) injecter le contenu texte.
                # On attend que le premier nœud texte ne soit plus vide.
                try:
                    page.wait_for_function(
                        """(sel) => {
                            const el = document.querySelector(sel);
                            if (!el) return false;
                            const t = (el.textContent || '').trim();
                            return t.length > 0 && t.length < 120;
                        }""",
                        arg=selector,
                        timeout=3000,
                    )
                except PlaywrightTimeout:
                    pass  # on tentera quand même l'extraction

                # Extraction : on teste tous les éléments matchés, car
                # blockchain.com rend souvent DEUX <h1> (desktop + mobile).
                for el in page.query_selector_all(selector):
                    text = self._extract_name(el, address)
                    if text:
                        return text

            return None
        finally:
            try:
                page.close()
            except Exception:
                pass
            try:
                context.close()
            except Exception:
                pass

    @staticmethod
    def _route_filter(route):
        """
        Bloque les ressources inutiles : images, fonts, médias, pubs.
        Accélère fortement le chargement et évite les timeouts.
        """
        resource_type = route.request.resource_type
        blocked_types = {"image", "font", "media"}
        url = route.request.url

        # Bloque les domaines de pubs/trackers connus sur blockchain.com
        blocked_hosts = (
            "doubleclick.net",
            "googlesyndication.com",
            "google-analytics.com",
            "googletagmanager.com",
            "adx.ws",
            "sevioads",
            "sevio",
        )

        if resource_type in blocked_types:
            return route.abort()
        if any(h in url for h in blocked_hosts):
            return route.abort()
        return route.continue_()

    @staticmethod
    def _extract_name(el, address: str) -> str | None:
        """
        Récupère le nom depuis un élément.
        On lit uniquement le premier nœud texte car le <h1> contient
        un <div> pour le badge « vérifié » qui pollue inner_text().
        """
        try:
            text = el.evaluate(
                "el => (el.childNodes[0] && el.childNodes[0].textContent || '').trim()"
            )
        except Exception:
            text = ""
        if not text:
            text = (el.inner_text() or "").strip()

        # Nettoyage : on garde la première ligne
        text = text.split("\n")[0].strip()

        if not text or len(text) < 2 or len(text) > 120:
            return None
        if text.lower() == address.lower():
            return None
        if text.replace(" ", "") == address:
            return None
        if text.isupper() and len(text) <= 4:
            return None
        return text