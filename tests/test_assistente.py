"""Sintesi del report con l'AI: controllo dei numeri, ripiego automatico, cache."""

import json
from types import SimpleNamespace as NS

from basket import assistente as A

FATTI = {
    "squadra": "Basket Test", "record": "3-1", "posizione_in_classifica": 2, "partite_giocate": 4,
    "in_una_frase": ["attacco tra i più efficienti"],
    "profilo": [{"voce": "Rimbalzi offensivi %", "valore": 35.2, "media_campionato": 28.6, "posizione": "3/20"}],
    "giocatori": [{"nome": "Rossi", "punti": 18.5, "minuti": 30.1, "rimbalzi": 4.0, "assist": 3.2,
                   "triple_segnate": 2.8, "triple_tentate": 4.8, "pct_da_3": 56}],
    "consigli": {"In difesa · contro il loro attacco": [
        "Forti a rimbalzo offensivo (35,2% dei tiri sbagliati, 3° su 20): tagliafuori su ogni tiro"],
        "In attacco · contro la loro difesa": ["Concedono molto da 3 (40,6%, 6° su 20): cercare i tiratori"]},
}


class _Client:
    def __init__(self, risposta, stop="end_turn"):
        self.risposta, self.stop, self.chiamate = risposta, stop, 0
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **kw):
        self.chiamate += 1
        assert kw["model"] == A.MODELLO and kw["output_config"]["format"]["type"] == "json_schema"
        assert "Rossi" in kw["messages"][0]["content"]
        return NS(stop_reason=self.stop, content=[NS(type="text", text=json.dumps(self.risposta))])


def _risposta(**over):
    r = {"sintesi": "Squadra da rimbalzo: 35,2% dei loro errori ripresi (3° su 20).",
         "identita": ["Rimbalzo offensivo", "Tiro da 3"],
         "da_ricordare": ["Tagliafuori su ogni tiro", "Rossi tira 4,8 triple a partita"],
         "in_difesa": ["Tagliafuori anche degli esterni (35,2%, 3° su 20)",
                       "Raddoppiare sul post basso (concedono 61,3 punti in area)"],   # numero inventato
         "in_attacco": ["Cercare i tiratori dopo lo scarico (40,6%)"],
         "giocatori": [{"nome": "Rossi", "chi_e": "18,5 punti a partita",
                        "come_fermarlo": "chiudergli le triple (56% da 3)"},
                       {"nome": "Inventato", "chi_e": "", "come_fermarlo": ""}],
         "attenzione": "Solo 4 partite giocate."}
    r.update(over)
    return r


def test_numeri_controllati_sui_fatti(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "CACHE_DIR", tmp_path)
    c = _Client(_risposta())
    s = A.scrivi(FATTI, client=c)
    assert s["fonte"] == "ai"
    assert len(s["in_difesa"]) == 1 and "61,3" not in " ".join(s["in_difesa"])    # frase scartata
    assert [g["nome"] for g in s["giocatori"]] == ["Rossi"]                          # nome inventato scartato
    assert "35,2" in s["sintesi"] and s["attenzione"]
    # seconda volta dalla cache, senza chiamare il modello
    assert A.scrivi(FATTI, client=c) == s and c.chiamate == 1


def test_ripiego_automatico(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "CACHE_DIR", tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    s = A.scrivi(FATTI)
    assert s["fonte"] == "automatica" and s["in_difesa"] and s["giocatori"][0]["nome"] == "Rossi"
    assert s["da_ricordare"][0] == "Tagliafuori su ogni tiro"
    rifiuto = A.scrivi(FATTI, client=_Client(_risposta(), stop="refusal"))
    assert rifiuto["fonte"] == "automatica"
    # tutto scartato in una sezione: si riprende quella automatica
    vuota = A.scrivi(FATTI, client=_Client(_risposta(in_attacco=["Concedono 77,7 punti"])))
    assert vuota["in_attacco"] == A.automatica(FATTI)["in_attacco"]


def test_verifica():
    ok = A.numeri_ammessi(FATTI)
    assert A.verifica("35,2% e 3° su 20, 56%", ok) and A.verifica("35%", ok)
    assert not A.verifica("concedono 61,3 punti", ok)
