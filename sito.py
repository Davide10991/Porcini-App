#!/usr/bin/env python3
"""Boletus Map — sito web senza Streamlit."""
from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from functools import wraps
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash
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
ADMIN_USER = "Davide1099"
ADMIN_PASS = "Ciccione99"
CACHE_FILE = Path(__file__).resolve().parent / "ultimo_calcolo.json"
USERS_FILE = Path(__file__).resolve().parent / "utenti.json"
CACHE = {"risultati": []}


def _utenti():
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text())
        except Exception:
            return {}
    return {}


def _salva_utenti(d):
    USERS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2))


def _smtp_conf():
    p = Path(__file__).resolve().parent / "smtp.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {
        "host": os.environ.get("BOLETUS_SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.environ.get("BOLETUS_SMTP_PORT", "587")),
        "user": os.environ.get("BOLETUS_SMTP_USER", ""),
        "password": os.environ.get("BOLETUS_SMTP_PASS", ""),
        "from": os.environ.get("BOLETUS_SMTP_FROM", "") or os.environ.get("BOLETUS_SMTP_USER", ""),
    }


def _invia_registrazione(dest):
    cfg = _smtp_conf()
    if not cfg.get("user") or not cfg.get("password"):
        return False
    msg = MIMEText(
        "Ciao,\n\nla registrazione a Boletus Map è andata a buon fine.\n"
        f"Account: {dest}\n\nBuone cercate.\n",
        "plain",
        "utf-8",
    )
    msg["Subject"] = "Registrazione Boletus Map"
    msg["From"] = cfg.get("from") or cfg["user"]
    msg["To"] = dest
    with smtplib.SMTP(cfg["host"], int(cfg.get("port") or 587), timeout=20) as s:
        s.starttls()
        s.login(cfg["user"], cfg["password"])
        s.send_message(msg)
    return True


def _carica_cache():
    if CACHE["risultati"]:
        return
    if CACHE_FILE.exists():
        try:
            CACHE["risultati"] = json.loads(CACHE_FILE.read_text())
        except Exception:
            CACHE["risultati"] = []


def _salva_cache(rows):
    CACHE["risultati"] = rows
    try:
        CACHE_FILE.write_text(json.dumps(rows, ensure_ascii=False))
    except Exception:
        pass


_carica_cache()


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
        email = (request.form.get("email") or "").strip()
        pw = (request.form.get("password") or "").strip()
        email_l = email.lower()
        if email == ADMIN_USER and pw == ADMIN_PASS:
            session["ok"] = True
            session["email"] = ADMIN_USER
            session["ruolo"] = "admin"
            return redirect(url_for("home"))
        users = _utenti()
        rec = users.get(email_l)
        if rec and check_password_hash(rec.get("hash", ""), pw):
            session["ok"] = True
            session["email"] = email_l
            session["ruolo"] = "guest"
            return redirect(url_for("home"))
        err = "Email o password errati"
    return render_template("login.html", errore=err)


@app.route("/register", methods=["GET", "POST"])
def register():
    err = ""
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        pw = (request.form.get("password") or "").strip()
        pw2 = (request.form.get("password2") or "").strip()
        if "@" not in email or "." not in email.split("@")[-1]:
            err = "Email non valida"
        elif len(pw) < 6:
            err = "Password almeno 6 caratteri"
        elif pw != pw2:
            err = "Le password non coincidono"
        else:
            users = _utenti()
            if email in users:
                err = "Questa email è già registrata"
            else:
                users[email] = {
                    "hash": generate_password_hash(pw),
                    "quando": datetime.now().isoformat(timespec="seconds"),
                }
                _salva_utenti(users)
                try:
                    _invia_registrazione(email)
                except Exception:
                    pass
                session["ok"] = True
                session["email"] = email
                session["ruolo"] = "guest"
                return redirect(url_for("home"))
    return render_template("register.html", errore=err)


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
        ruolo=session.get("ruolo", "guest"),
        email=session.get("email", ""),
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
    regioni = body.get("regioni") or sorted({p["regione"] for p in engine.PUNTI})
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
        max_km_stazione=8.0,
        max_workers=3,
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
    view_j = [_jsonable(r) for r in view]
    _salva_cache(view_j)
    engine.CALC_PROGRESS.update({"pct": 100, "text": "Fatto"})
    return jsonify(
        {
            "n": len(view),
            "n_alto": sum(1 for r in view if r.get("score", 0) >= 70),
            "n_medio": sum(1 for r in view if 50 <= r.get("score", 0) < 70),
            "zone": view_j,
        }
    )


@app.route("/api/ultimo")
@login_required
def api_ultimo():
    _carica_cache()
    view = CACHE.get("risultati") or []
    return jsonify(
        {
            "n": len(view),
            "n_alto": sum(1 for r in view if float(r.get("score") or 0) >= 70),
            "n_medio": sum(1 for r in view if 50 <= float(r.get("score") or 0) < 70),
            "zone": view,
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
