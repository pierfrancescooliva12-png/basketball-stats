"""Verifica di loghi e foto sul sito della Lega: per ogni squadra della stagione se il logo
c'è, per ogni giocatore che ha giocato se c'è la foto. Serve a distinguere ciò che manca alla
fonte da un problema del sito ASSIST.

    python -m basket.verifica_media             # tutte le squadre e tutti i giocatori
    python -m basket.verifica_media --solo-loghi

Le richieste sono distanziate (il sito chiede di non sovraccaricarlo). Il riepilogo va anche
nel sommario dell'esecuzione su GitHub (GITHUB_STEP_SUMMARY)."""

import argparse
import os
import time

from . import brand
from .contesto import open_readonly
from .scheda_giocatori import _scarica, anagrafica, foto_url


def _prova(url: str) -> str:
    try:
        return "ok" if _scarica(url, 12.0) else "manca"
    except Exception as exc:              # noqa: BLE001
        return f"errore ({type(exc).__name__})"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verifica di loghi e foto sul sito della Lega")
    ap.add_argument("--solo-loghi", action="store_true")
    ap.add_argument("--pausa-loghi", type=float, default=3.0)
    ap.add_argument("--pausa-foto", type=float, default=0.4)
    args = ap.parse_args(argv)
    ctx = open_readonly()
    bs = ctx.bs
    squadre = bs.drop_duplicates("squadra_id")[["squadra_id", "squadra", "campionato_id"]] \
        .sort_values(["campionato_id", "squadra"])
    righe = ["## Loghi", "", "| Campionato | Squadra | id | Logo |", "|---|---|---|---|"]
    senza_logo = []
    for r in squadre.itertuples():
        esiti = [_prova(c.format(id=int(r.squadra_id))) for c in brand.CANDIDATI]
        esito = "ok" if "ok" in esiti else esiti[0]
        if esito != "ok":
            senza_logo.append(r.squadra)
        righe.append(f"| {r.campionato_id} | {r.squadra} | {r.squadra_id} | {esito} |")
        print(f"LOGO  {r.campionato_id:8s} {r.squadra:40s} {r.squadra_id:>9} {esito}")
        time.sleep(args.pausa_loghi)
    righe += ["", f"**Loghi trovati: {len(squadre) - len(senza_logo)} su {len(squadre)}**", ""]
    if not args.solo_loghi:
        ana = anagrafica(ctx.conn)
        pl = ctx.players[ctx.players["minuti"] > 0].sort_values(["squadra", "minuti"], ascending=[True, False])
        mancano, errori, per_squadra = [], [], {}
        for p in pl.itertuples():
            info = ana.loc[p.giocatore_id].to_dict() if not ana.empty and p.giocatore_id in ana.index else {}
            esito = _prova(foto_url(p.giocatore_id, info, ctx.stagione))
            tot, ok = per_squadra.get(p.squadra, (0, 0))
            per_squadra[p.squadra] = (tot + 1, ok + (esito == "ok"))
            if esito == "manca":
                mancano.append(f"{p.giocatore} ({p.squadra}, {p.minuti_pg:.0f}' a partita)")
            elif esito != "ok":
                errori.append(f"{p.giocatore} ({p.squadra}): {esito}")
            time.sleep(args.pausa_foto)
        n_ok = sum(ok for _, ok in per_squadra.values())
        righe += ["## Foto", "", f"**Foto trovate: {n_ok} su {len(pl)}** (giocatori con minuti in stagione)", "",
                  "| Squadra | Foto |", "|---|---|"]
        righe += [f"| {sq} | {ok} su {tot} |" for sq, (tot, ok) in sorted(per_squadra.items())]
        if mancano:
            righe += ["", "### Senza foto sul sito della Lega", ""] + [f"- {x}" for x in mancano]
        if errori:
            righe += ["", "### Non raggiungibili (errore di rete)", ""] + [f"- {x}" for x in errori]
        print(f"FOTO trovate {n_ok} su {len(pl)}; mancano {len(mancano)}; errori {len(errori)}")
        for sq, (tot, ok) in sorted(per_squadra.items()):
            print(f"FOTO  {sq:40s} {ok} su {tot}")
        for x in mancano:
            print("SENZA FOTO", x)
    testo = "\n".join(righe) + "\n"
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(testo)
    print(f"Loghi trovati: {len(squadre) - len(senza_logo)} su {len(squadre)}")
    for x in senza_logo:
        print("SENZA LOGO", x)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
