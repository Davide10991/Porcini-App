#!/usr/bin/env python3
"""
Test rapido dell'API MeteoHub (ItaliaMeteo/Cineca).
Fa login, invia una richiesta di estrazione breve (json), aspetta il
risultato e stampa i primi record cosi' vediamo la struttura del dato.

Uso:
    pip install requests
    python meteohub_test.py

Inserisci email e password quando richiesto (non vengono salvate).
"""
import getpass
import json
import time

import requests

BASE = "https://meteohub.agenziaitaliameteo.it"

DATASETS = [
    "arpafvg", "dpcn-lombardia", "dpcn-umbria", "dpcn-sicilia",
    "dpcn-veneto", "dpcn-piemonte", "dpcn-liguria", "open-trentino",
    "dpcn-campania", "dpcn-bolzanoboze", "dpcn-basilicata", "dpcn-molise",
    "dpcn-calabria", "dpcn-marche", "dpcn-sardegna", "dpcn-lazio",
    "dpcn-puglia", "sir-toscana",
]

# Codici BUFR: B12101 = temperatura, B13011 = precipitazione totale
PRODUCTS = ["B12101", "B13011"]


def _try_login(payload):
    r = requests.post(f"{BASE}/auth/login", json=payload, timeout=30)
    print(f"  tentativo con chiavi {list(payload.keys())} -> status {r.status_code}")
    if r.status_code != 200:
        print("  risposta server:", r.text[:500])
        return None
    data = r.json()
    token = data.get("token") or data.get("access_token") or data.get("Response") or data
    if isinstance(token, dict):
        # magari il token e' annidato, es. {"Response": "..."} o simili: stampa tutto
        print("  risposta completa (struttura inattesa):", json.dumps(data, indent=2)[:1000])
        return None
    return token


def login(email, password):
    print("Provo login...")
    for payload in (
        {"username": email, "password": password},
        {"email": email, "password": password},
    ):
        token = _try_login(payload)
        if token:
            return token
    raise SystemExit("\nLogin fallito con entrambe le varianti. Copia il messaggio sopra e mandalo a Claude.")


def submit_request(token, minutes_back=60):
    headers = {"Authorization": f"Bearer {token}"}
    now = time.gmtime()
    to_iso = time.strftime("%Y-%m-%dT%H:%M:00.000000Z", now)
    frm = time.gmtime(time.time() - minutes_back * 60)
    from_iso = time.strftime("%Y-%m-%dT%H:%M:00.000000Z", frm)

    body = {
        "request_name": "boletus_test",
        "reftime": {"from": from_iso, "to": to_iso},
        "dataset_names": DATASETS,
        "filters": {
            "product": [{"code": c} for c in PRODUCTS],
        },
        "output_format": "json",
        "only_reliable": False,
    }
    print("Invio richiesta:", json.dumps(body, indent=2))
    r = requests.post(f"{BASE}/api/data", headers=headers, json=body, timeout=60)
    print("Status:", r.status_code)
    print(r.text[:2000])
    r.raise_for_status()
    return r.json()


def poll_and_show(token, request_id, filename=None, max_wait=180):
    headers = {"Authorization": f"Bearer {token}"}
    waited = 0
    while waited < max_wait:
        r = requests.get(f"{BASE}/api/requests", headers=headers, timeout=30)
        r.raise_for_status()
        reqs = r.json()
        items = reqs if isinstance(reqs, list) else reqs.get("requests") or reqs.get("data") or []
        mine = None
        for it in items:
            if it.get("request_id") == request_id or it.get("id") == request_id:
                mine = it
                break
        if mine:
            status = mine.get("status") or mine.get("state")
            print("Stato:", status)
            if status and status.upper() == "SUCCESS":
                fname = mine.get("fileoutput") or mine.get("filename")
                if not fname:
                    print("Trovato SUCCESS ma senza nome file, risposta completa:")
                    print(json.dumps(mine, indent=2))
                    return
                dl = requests.get(f"{BASE}/api/data/{fname}", headers=headers, timeout=60)
                dl.raise_for_status()
                text = dl.text
                print("\n--- PRIME RIGHE DEL FILE SCARICATO ---\n")
                print(text[:3000])
                with open("meteohub_sample.json", "w", encoding="utf-8") as f:
                    f.write(text)
                print("\nSalvato per intero in meteohub_sample.json")
                return
            if status and status.upper() == "FAILED":
                print("Richiesta fallita:", json.dumps(mine, indent=2))
                return
        time.sleep(5)
        waited += 5
    print("Timeout: la richiesta e' ancora in corso, riprova a controllare tra poco su /api/requests")


def main():
    email = input("Email MeteoHub: ").strip()
    password = getpass.getpass("Password MeteoHub: ")
    token = login(email, password)
    print("Login ok.")
    resp = submit_request(token, minutes_back=60)
    request_id = resp.get("request_id") or resp.get("id")
    print("Request ID:", request_id)
    if request_id:
        poll_and_show(token, request_id)


if __name__ == "__main__":
    main()
