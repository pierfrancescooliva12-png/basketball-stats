"""Genera i file del logo ASSIST in assets/logo (il disegno è in basket/logo.py).

    python assets/logo/nuovo_logo.py          # SVG
    python assets/logo/nuovo_logo.py --png    # anche i PNG del simbolo (serve Chromium)
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from basket.logo import CREMA, INK, scritta_svg, simbolo_svg  # noqa: E402


def main():
    (HERE / "assist-scritta.svg").write_text(scritta_svg(INK), encoding="utf-8")
    (HERE / "assist-scritta-chiara.svg").write_text(scritta_svg(CREMA), encoding="utf-8")
    (HERE / "assist-mark.svg").write_text(simbolo_svg(), encoding="utf-8")
    if "--png" in sys.argv:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
            for lato in (32, 128, 512):
                pg = b.new_page(viewport={"width": lato, "height": lato})
                pg.set_content(f'<body style="margin:0">{simbolo_svg(lato)}</body>')
                pg.screenshot(path=str(HERE / f"assist-mark-{lato}.png"), omit_background=True)
            b.close()
    print("Logo scritto in", HERE)


if __name__ == "__main__":
    main()
