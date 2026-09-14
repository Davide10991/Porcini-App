#!/usr/bin/env python3
"""Boletus Map — sito web senza Streamlit."""
from __future__ import annotations

import json
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import engine

app = Flask(__name__)
app.secret_key = "boletus-map-porcino-2026"
CACHE = {"risultati": []}


def login_required(fn):
    @wraps(fn)
    def wrap(*a, **k):
        if not session.get("ok"):
            return redirect(url_for("login"))
        return fn(*a, **k)

    return wrap


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


@app.route("/login", methods=["GET", "POST"])
def login():
    err = ""
    if request.method == "POST":
        pw = (request.form.get("password") or "").strip()
        if pw == engine.GUEST_PASS:
            session["ok"] = True
            return redirect(url_for("home"))
        err = "Password errata"
    return render_template("login.html", errore=err)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    return render_template(
        "index.html",
        n_punti=len(engine.PUNTI),
        regioni=sorted({p["regione"] for p in engine.PUNTI}),
    )


@app.route("/api/zone")
@login_required
def api_zone():
    q = (request.args.get("q") or "").strip().lower()
    out = []
    for p in engine.PUNTI:
        if q and q not in p["nome"].lower():
            continue
        out.append(p["nome"])
        if len(out) >= 20:
            break
    return jsonify(out)


@app.route("/api/progress")
@login_required
def api_progress():
    return jsonify(engine.CALC_PROGRESS)


@app.route("/api/calcola", methods=["POST"])
@login_required
def api_calcola():
    body = request.get_json(force=True, silent=True) or {}
    regioni = body.get("regioni") or [
        "Abruzzo",
        "Molise",
        "Lazio",
        "Campania",
        "Marche",
        "Umbria",
    ]
    tipi = body.get("tipi") or [
        "faggio",
        "castagno",
        "quercia",
        "leccio",
        "misto_carpino_quercia",
        "abete_bianco",
        "abete_rosso",
    ]
    qmin = int(body.get("qmin") or 0)
    qmax = int(body.get("qmax") or 1800)
    cerca = (body.get("cerca") or "").strip().lower()
    f_staz = bool(body.get("stazioni", True))
    f_radar = bool(body.get("radar", True))
    regole = {
        "pioggia_min": int(body.get("pioggia_min") or 40),
        "pioggia_max": int(body.get("pioggia_max") or 100),
    }
    punti = [
        p
        for p in engine.PUNTI
        if p["regione"] in regioni
        and p["tipo"] in tipi
        and qmin <= p["quota"] <= qmax
        and (cerca in p["nome"].lower() if cerca else True)
    ]
    engine.CALC_PROGRESS.update({"pct": 0, "text": f"Calcolo {len(punti)} zone…"})
    ris = engine.calcola_tutti(
        punti,
        regole,
        "",
        max_km_stazione=5.0,
        max_workers=4,
        usa_wc=True,
    )

    def zona_radar(r):
        fonte = str((r.get("meteo") or {}).get("fonte") or "").lower()
        return bool((r.get("meteo") or {}).get("stima_mappa")) or "mappe" in fonte or "realtime" in fonte

    view = [
        r
        for r in ris
        if (zona_radar(r) and f_radar) or ((not zona_radar(r)) and f_staz)
    ]
    CACHE["risultati"] = view
    engine.CALC_PROGRESS.update({"pct": 100, "text": "Fatto"})
    return jsonify(
        {
            "n": len(view),
            "n_alto": sum(1 for r in view if r.get("score", 0) >= 70),
            "n_medio": sum(1 for r in view if 50 <= r.get("score", 0) < 70),
            "zone": [_jsonable(r) for r in view],
        }
    )


@app.route("/api/csv")
@login_required
def api_csv():
    rows = CACHE.get("risultati") or []
    lines = [
        "zona,regione,tipo,quota,score,livello,pioggia_30g,stazione"
    ]
    for r in rows:
        d = r.get("dettaglio") or {}
        m = r.get("meteo") or {}
        lines.append(
            ",".join(
                str(x).replace(",", " ")
                for x in (
                    r.get("nome"),
                    r.get("regione"),
                    r.get("tipo"),
                    r.get("quota"),
                    round(float(r.get("score") or 0), 1),
                    r.get("livello"),
                    d.get("precip_totale_30g"),
                    m.get("stazione"),
                )
            )
        )
    nome = f"porcini_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        "\n".join(lines),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={nome}"},
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=False, threaded=True)
