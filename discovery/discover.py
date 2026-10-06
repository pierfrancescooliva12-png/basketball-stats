"""Ricognizione della fonte dati legapallacanestro.com.

Apre alcune pagine con un browser headless, registra tutte le richieste di
rete (in particolare XHR/fetch e risposte JSON) e salva HTML renderizzato,
elenco richieste e corpi JSON in discovery/output/. Una pagina al secondo
al massimo.
"""

import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

BASE = "https://www.legapallacanestro.com"
OUT = Path(__file__).parent / "output"

SEED_PAGES = [
    # Partite 2026/27 giocate (codici presi dal calendario JSON)
    BASE + "/wp/match/ita2_412/ita2/x2627",
    BASE + "/wp/match/ita2_412/ita2/x2627/play-by-play",
    BASE + "/wp/match/ita3_a_410/ita3_a/x2627",
    BASE + "/serie/1/calendario",
]
DOMINO = "https://lnpstat.domino.it/getstatisticsfiles"
# Chiamate dirette all'endpoint JSON per capire quali "task" esistono
PROBE_URLS = [
    DOMINO + "?task=schedule&year=x2627&league=ita2&round=1",
    DOMINO + "?task=schedule&year=x2627&league=ita3_b&round=1",
] + [
    DOMINO + f"?task={t}&year=x2627&league=ita2&game={g}"
    for t in ("boxscore", "game", "match", "stats", "pbp", "playbyplay")
    for g in ("ita2_412",)
] + [
    DOMINO + "?task=boxscore&year=x2627&league=ita2&gameid=ita2_412",
    DOMINO + "?task=boxscore&year=x2627&league=ita2&round=ita2_412",
]
JS_KEYWORDS = ("domino", "getstatistics", "boxscore")
LINK_PATTERN = re.compile(r'href="([^"#]*/(?:serie/\d+|wp/)[^"#]*)"', re.I)
MAX_EXTRA_PAGES = 0
MIN_INTERVAL = 1.0
MAX_BODY = 300_000


def slug(url: str) -> str:
    p = urlparse(url)
    s = (p.path + ("_" + p.query if p.query else "")).strip("/") or "home"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)[:120]


def visit(page, url, summary):
    requests = []

    def on_response(resp):
        req = resp.request
        ctype = resp.headers.get("content-type", "")
        entry = {
            "url": resp.url,
            "method": req.method,
            "type": req.resource_type,
            "status": resp.status,
            "content_type": ctype,
        }
        if req.resource_type == "script" and "legapallacanestro" in resp.url:
            try:
                js = resp.text()
                if any(k in js for k in JS_KEYWORDS):
                    (OUT / "js").mkdir(exist_ok=True)
                    (OUT / "js" / (slug(resp.url) + ".js")).write_text(js, encoding="utf-8")
            except Exception:  # noqa: BLE001
                pass
        if req.resource_type in ("xhr", "fetch") or "json" in ctype:
            try:
                body = resp.text()
                entry["body_len"] = len(body)
                entry["body"] = body[:MAX_BODY]
            except Exception as exc:  # noqa: BLE001
                entry["body_error"] = str(exc)
        requests.append(entry)

    page.on("response", on_response)
    status = None
    try:
        resp = page.goto(url, wait_until="networkidle", timeout=45_000)
        status = resp.status if resp else None
        page.wait_for_timeout(2_000)
        html = page.content()
    except Exception as exc:  # noqa: BLE001
        html = f"<!-- errore: {exc} -->"
    page.remove_listener("response", on_response)

    name = slug(url)
    (OUT / "html" / f"{name}.html").write_text(html, encoding="utf-8")
    interesting = [r for r in requests if "body" in r or "body_error" in r]
    for i, r in enumerate(interesting):
        (OUT / "json" / f"{name}__{i:02d}.txt").write_text(
            r["url"] + "\n\n" + r.get("body", r.get("body_error", "")),
            encoding="utf-8",
        )
    (OUT / "requests" / f"{name}.json").write_text(
        json.dumps([{k: v for k, v in r.items() if k != "body"} for r in requests],
                   indent=1, ensure_ascii=False),
        encoding="utf-8",
    )
    summary.append({
        "url": url,
        "status": status,
        "title": re.search(r"<title>(.*?)</title>", html, re.S).group(1).strip()
        if "<title>" in html else "",
        "n_requests": len(requests),
        "xhr_json": [r["url"] for r in interesting],
    })
    return html


def main():
    for sub in ("html", "json", "requests"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    summary = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"))
        last = 0.0
        queue = list(SEED_PAGES)
        seen = set()
        extra = 0
        while queue:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            wait = MIN_INTERVAL - (time.time() - last)
            if wait > 0:
                time.sleep(wait)
            last = time.time()
            print("->", url, flush=True)
            html = visit(page, url, summary)
            if url == BASE + "/":
                links = sorted({urljoin(BASE, m.group(1))
                                for m in LINK_PATTERN.finditer(html)})
                (OUT / "home_links.txt").write_text("\n".join(links), encoding="utf-8")
                for link in links:
                    if extra < MAX_EXTRA_PAGES and urlparse(link).netloc.endswith(
                            "legapallacanestro.com"):
                        queue.append(link)
                        extra += 1
        probes = []
        for url in PROBE_URLS:
            time.sleep(MIN_INTERVAL)
            print("probe", url, flush=True)
            try:
                r = page.request.get(url, headers={"Referer": BASE + "/"})
                body = r.text()
                probes.append({"url": url, "status": r.status,
                               "content_type": r.headers.get("content-type", ""),
                               "body_len": len(body), "head": body[:1500]})
                (OUT / "probe").mkdir(exist_ok=True)
                (OUT / "probe" / (re.sub(r"[^A-Za-z0-9]+", "_", url[len(DOMINO):]) + ".txt")
                 ).write_text(url + "\n\n" + body[:MAX_BODY], encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                probes.append({"url": url, "error": str(exc)})
        (OUT / "probes.json").write_text(
            json.dumps(probes, indent=1, ensure_ascii=False), encoding="utf-8")
        browser.close()
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
