#!/usr/bin/env python3
"""Calcolo di tutte le zone. Lo lancia il cron, una volta al giorno."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import engine

try:
    ROMA = timezone(timedelta(hours=2))
except Exception:
    ROMA = timezone.utc


def _jsonable(obj):
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(x) for x in obj]
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:
            pass
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


def main():
    punti = list(engine.PUNTI)
    regole = {"pioggia_min": 40, "pioggia_max": 100}
    print(f"avvio {len(punti)} zone", flush=True)
    ris = engine.calcola_tutti(punti, regole, "", max_km_stazione=5.0, max_workers=6, usa_wc=True)
    rows = [_jsonable(r) for r in ris]
    quando = datetime.now(ROMA).strftime("%Y-%m-%dT%H:%M:%S")
    out = Path(__file__).resolve().parent / "ultimo_calcolo.json"
    out.write_text(json.dumps({"aggiornato": quando, "zone": rows}, ensure_ascii=False), encoding="utf-8")
    print(f"salvate {len(rows)} zone alle {quando}", flush=True)
    try:
        import sito
        salv = {}
        sf = Path(__file__).resolve().parent / "zone_salvate.json"
        if sf.exists():
            salv = json.loads(sf.read_text(encoding="utf-8"))
        by_nome = {r.get("nome"): r for r in rows}
        for email, nomi in salv.items():
            aperte = []
            for n in nomi:
                r = by_nome.get(n) or {}
                fase = str(((r.get("dettaglio") or {}).get("stato_buttata")) or "")
                if fase.upper() in ("IN CORSO", "INCROCIO"):
                    aperte.append(n)
            if aperte:
                sito._invia_mail(
                    email,
                    "Boletus Map: zone in buttata",
                    "Queste zone salvate sono in buttata: " + ", ".join(aperte) + "\n\nBuona cerca,\nBoletus Map",
                )
    except Exception as e:
        print("avviso zone:", e, flush=True)


if __name__ == "__main__":
    main()
