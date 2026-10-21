"""Rassegna stampa Foggia e provincia -> Telegram.

Eseguito da GitHub Actions ogni 15 minuti: legge i feed in feeds.json,
tiene solo cronaca, politica, sport e ordine e sicurezza pubblica
(parole in argomenti.json), scarta i doppioni e invia le novità su Telegram.
Le notizie già inviate sono salvate in inviate.json.
"""
import calendar
import html
import json
import os
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urlparse

import feedparser
import requests

# ===== IMPOSTAZIONI =====
ORE_MASSIME = 3            # invia solo notizie delle ultime N ore
CATEGORIE_ATTIVE = ["sicurezza", "cronaca", "politica", "sport"]
PAUSA_TRA_MESSAGGI = 3     # secondi, per rispettare i limiti di Telegram
GIORNI_MEMORIA = 10        # per quanti giorni ricordare le notizie già inviate
# ========================

CARTELLA = os.path.dirname(os.path.abspath(__file__))
FILE_STATO = os.path.join(CARTELLA, "inviate.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
PAROLE_CHIAVE = re.compile(
    r"foggia|capitanata|foggian|gargano|tavoliere|monti dauni|manfredonia|cerignola|"
    r"san severo|lucera|vieste|san giovanni rotondo|monte sant'angelo|torremaggiore|"
    r"apricena|orta nova|san marco in lamis|san nicandro|peschici|mattinata|"
    r"rodi garganico|vico del gargano|lesina|tremiti|ascoli satriano|bovino|"
    r"zapponeta|stornara|carapelle|borgo mezzanone", re.I)


def carica(nome):
    with open(os.path.join(CARTELLA, nome), encoding="utf-8") as f:
        return json.load(f)


def regex_da(parole):
    parti = []
    for p in parole:
        if p.endswith("*"):
            parti.append(re.escape(p[:-1]))
        else:
            parti.append(re.escape(p) + r"(?!\w)")
    return re.compile(r"(?<!\w)(?:" + "|".join(parti) + ")", re.I | re.U)


CONF = carica("feeds.json")
ARG = carica("argomenti.json")
CATEGORIE = {c["id"]: c for c in ARG["categorie"]}
RX = {c["id"]: regex_da(c["parole"]) for c in ARG["categorie"]}
RX_ESCL = regex_da(ARG["esclusioni"])
DOMINI_SPORT = ARG["domini_sport"]


def classifica(titolo, testo, link, categorie_feed, host):
    tutto = " ".join([titolo, testo, " ".join(categorie_feed)])
    if RX_ESCL.search(titolo) and not RX["sicurezza"].search(titolo):
        return None
    percorso = urlparse(link).path.lower()
    if RX["sicurezza"].search(titolo):
        return "sicurezza"
    if any(host.endswith(d) for d in DOMINI_SPORT):
        return "sport"
    for cid in ("cronaca", "politica", "sport"):
        if RX[cid].search(titolo):
            return cid
    if re.search(r"/cronaca|/giudiziaria|/nera/", percorso):
        return "cronaca"
    if "/politica" in percorso:
        return "politica"
    if re.search(r"/sport|/calcio", percorso):
        return "sport"
    for cid in ("sicurezza", "cronaca", "politica", "sport"):
        if RX[cid].search(tutto):
            return cid
    return None


def chiave_di(titolo):
    t = unicodedata.normalize("NFD", titolo.lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", t)[:120]


def nome_fonte(host):
    fonti = CONF["fonti"]
    if host in fonti:
        return fonti[host]
    for dominio, nome in fonti.items():
        if host.endswith(dominio):
            return nome
    return host


def scarica(feed):
    try:
        r = requests.get(feed["url"], headers={"User-Agent": UA}, timeout=25)
        r.raise_for_status()
        return feed, feedparser.parse(r.content)
    except Exception as e:  # feed irraggiungibile: si salta
        print(f"  ! {feed['nome']}: {e}")
        return feed, None


def raccogli():
    limite = time.time() - ORE_MASSIME * 3600
    filtrati = CONF["domini_da_filtrare"]
    notizie, viste = [], set()
    with ThreadPoolExecutor(max_workers=12) as ex:
        risultati = list(ex.map(scarica, CONF["feeds"]))
    for feed, dati in risultati:
        if not dati:
            continue
        for e in dati.entries:
            titolo = (e.get("title") or "").strip()
            link = e.get("link") or ""
            if not titolo or not link:
                continue
            host = urlparse(link).hostname or ""
            host = host[4:] if host.startswith("www.") else host
            fonte = nome_fonte(host)
            if host == "news.google.com":
                if " - " in titolo:
                    titolo, fonte = titolo.rsplit(" - ", 1)
                else:
                    fonte = (e.get("source") or {}).get("title", "Google News")
            sommario = re.sub(r"<[^>]+>", " ", e.get("summary") or "")
            if any(host.endswith(d) for d in filtrati):
                if not PAROLE_CHIAVE.search(titolo + " " + sommario):
                    continue
            data_t = e.get("published_parsed") or e.get("updated_parsed")
            data = calendar.timegm(data_t) if data_t else time.time()
            if data < limite:
                continue
            categorie_feed = [t.get("term", "") for t in e.get("tags", [])]
            cat = classifica(titolo, sommario, link, categorie_feed, host)
            if cat not in CATEGORIE_ATTIVE:
                continue
            chiave = chiave_di(titolo)
            if not chiave or chiave in viste:
                continue
            viste.add(chiave)
            notizie.append({"fonte": fonte.strip(), "titolo": titolo.strip(),
                            "link": link, "data": data, "cat": cat, "chiave": chiave})
    notizie.sort(key=lambda n: n["data"])
    return notizie


def messaggio(n):
    c = CATEGORIE[n["cat"]]
    e = html.escape
    return (f"{c['etichetta']} · <b>{e(n['fonte'], quote=False)}</b>\n"
            f"<a href=\"{e(n['link'])}\">{e(n['titolo'], quote=False)}</a>\n{c['tag']}")


def invia(token, chat_id, testo):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for _ in range(3):
        r = requests.post(url, data={"chat_id": chat_id, "text": testo,
                                     "parse_mode": "HTML"}, timeout=20)
        if r.status_code == 429:  # troppi messaggi: Telegram dice quanto aspettare
            time.sleep(r.json().get("parameters", {}).get("retry_after", 10) + 1)
            continue
        return r.status_code, r.text
    return r.status_code, r.text


def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    prova = "--prova" in sys.argv  # stampa a schermo senza inviare
    if not prova and (not token or not chat_id):
        sys.exit("Mancano TELEGRAM_TOKEN e/o TELEGRAM_CHAT_ID nei Secrets del repository.")

    stato = {}
    if os.path.exists(FILE_STATO):
        with open(FILE_STATO, encoding="utf-8") as f:
            stato = json.load(f)
    soglia = time.time() - GIORNI_MEMORIA * 86400
    stato = {k: v for k, v in stato.items() if v >= soglia}

    nuove = [n for n in raccogli() if n["chiave"] not in stato]
    print(f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC - notizie nuove: {len(nuove)}")

    for n in nuove:
        testo = messaggio(n)
        if prova:
            print(testo, "\n")
            continue
        codice, risposta = invia(token, chat_id, testo)
        if codice != 200:
            print(f"  ! Telegram {codice}: {risposta[:300]}")
        errore_chat = codice in (401, 403, 404) or (
            codice == 400 and re.search(r"chat not found|not enough rights|bot was kicked|"
                                        r"have no rights|chat_id is empty", risposta, re.I))
        if errore_chat:
            sys.exit("Token o chat ID non validi, oppure il bot non è nella chat "
                     "o non può scriverci. Dettaglio di Telegram: " + risposta[:300])
        if codice in (200, 400):  # 400 su un singolo messaggio: non riprovarlo
            stato[n["chiave"]] = time.time()
        with open(FILE_STATO, "w", encoding="utf-8") as f:
            json.dump(stato, f)
        time.sleep(PAUSA_TRA_MESSAGGI)

    if not prova:
        with open(FILE_STATO, "w", encoding="utf-8") as f:
            json.dump(stato, f)


if __name__ == "__main__":
    main()
