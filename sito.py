#!/usr/bin/env python3
"""Boletus Map — sito web senza Streamlit."""
from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
from email.mime.text import MIMEText
from functools import wraps
import threading
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
INVITE_CODE = "BoletusMap1099"  # obbligatorio per registrarsi
CACHE_FILE = Path(__file__).resolve().parent / "ultimo_calcolo.json"
USERS_FILE = Path(__file__).resolve().parent / "utenti.json"
CACHE = {"risultati": [], "aggiornato": None}


def _ora_roma():
    """Ora italiana (Europe/Rome), non UTC del server."""
    try:
        if ZoneInfo is not None:
            return datetime.now(ZoneInfo("Europe/Rome"))
    except Exception:
        pass
    return datetime.utcnow() + timedelta(hours=2)

CALC_JOBS = {}  # sid -> {running, result, error, started_at}
_JOBS_LOCK = threading.Lock()


def _sid():
    """Id sessione stabile per non far bloccare un utente dall'altro."""
    try:
        from flask import session as _s
        if not _s.get("_jid"):
            import uuid
            _s["_jid"] = uuid.uuid4().hex
        return str(_s.get("_jid") or _s.get("email") or "anon")
    except Exception:
        return "anon"


def _job(sid=None):
    sid = sid or _sid()
    with _JOBS_LOCK:
        if sid not in CALC_JOBS:
            CALC_JOBS[sid] = {
                "running": False,
                "result": None,
                "error": None,
                "started_at": None,
            }
        return CALC_JOBS[sid]



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
    if CACHE.get("risultati"):
        return
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text())
            if isinstance(data, dict) and "zone" in data:
                CACHE["risultati"] = data.get("zone") or []
                CACHE["aggiornato"] = data.get("aggiornato")
            elif isinstance(data, list):
                CACHE["risultati"] = data
                try:
                    CACHE["aggiornato"] = (datetime.fromtimestamp(CACHE_FILE.stat().st_mtime) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")
                except Exception:
                    CACHE["aggiornato"] = None
            else:
                CACHE["risultati"] = []
        except Exception:
            CACHE["risultati"] = []


def _salva_cache(rows):
    CACHE["risultati"] = rows
    CACHE["aggiornato"] = _ora_roma().strftime("%Y-%m-%dT%H:%M:%S")
    try:
        payload = {"aggiornato": CACHE["aggiornato"], "zone": rows}
        CACHE_FILE.write_text(json.dumps(payload, ensure_ascii=False))
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
        codice = (request.form.get("codice") or "").strip()
        if codice != INVITE_CODE:
            err = "Codice di invito non valido"
        elif "@" not in email or "." not in email.split("@")[-1]:
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
        if q and q not in (p.get("nome") or "").lower() and q not in (p.get("regione") or "").lower():
            continue
        out.append({
            "nome": p.get("nome"),
            "lat": p.get("lat"),
            "lon": p.get("lon"),
            "regione": p.get("regione"),
            "quota": p.get("quota"),
            "tipo": p.get("tipo"),
        })
        if len(out) >= 25:
            break
    return jsonify(out)


@app.route("/api/progress")
@login_required
def api_progress():
    return jsonify(engine.CALC_PROGRESS)


@app.route("/api/punto", methods=["POST"])
@login_required
def api_punto():
    body = request.get_json(force=True, silent=True) or {}
    try:
        lat = float(body.get("lat"))
        lon = float(body.get("lon"))
    except Exception:
        return jsonify({"ok": False, "errore": "coordinate"}), 400
    tipo = (body.get("tipo") or "").strip()
    try:
        quota = int(body.get("quota") or 0)
    except Exception:
        quota = 0
    vicino = engine.punto_piu_vicino(lat, lon, 6.0)
    if vicino:
        if not tipo or tipo == "faggio":
            tipo = vicino.get("tipo") or tipo
        if not quota:
            quota = int(vicino.get("quota") or 0)
        nome = body.get("nome") or vicino.get("nome")
        regione = body.get("regione") or vicino.get("regione") or "Italia"
    else:
        nome = body.get("nome") or f"Punto {lat:.3f},{lon:.3f}"
        regione = body.get("regione") or "Italia"
        if not quota:
            quota = 800
        tipo = engine.classifica_bosco(nome, quota, regione, lat, tipo)
    if not tipo:
        tipo = engine.classifica_bosco(nome, quota, regione, lat, None)
    p = {
        "nome": nome,
        "lat": lat,
        "lon": lon,
        "tipo": tipo,
        "quota": quota or 800,
        "regione": regione,
    }
    regole = {
        "pioggia_min": int(body.get("pioggia_min") or 40),
        "pioggia_max": int(body.get("pioggia_max") or 100),
    }
    r = engine.analizza_punto(p, regole, "", 5.0, "", None, None, True)
    return jsonify({"ok": True, "zona": r})


@app.route("/api/calcola/reset", methods=["POST"])
@login_required
def api_calcola_reset():
    """Sblocca solo il calcolo di QUESTA sessione (non tocca gli altri utenti)."""
    j = _job()
    j["running"] = False
    j["started_at"] = None
    j["error"] = None
    engine.CALC_PROGRESS.update({"pct": 0, "text": "Pronto"})
    return jsonify({"ok": True, "text": "Calcolo sbloccato"})


@app.route("/api/calcola", methods=["POST"])
@login_required
def api_calcola():
    """Calcolo in background *per sessione*: due utenti possono calcolare insieme."""
    body = request.get_json(force=True, silent=True) or {}
    # Ogni click = nuovo calcolo: interrompe quello precedente della stessa sessione
    j = _job()
    j["running"] = True
    j["result"] = None
    j["error"] = None
    j["started_at"] = datetime.now().isoformat(timespec="seconds")
    j["token"] = (j.get("token") or 0) + 1
    mio_token = j["token"]

    regioni = body.get("regioni") or sorted({p["regione"] for p in engine.PUNTI})
    tipi = body.get("tipi") or [
        "faggio", "castagno", "quercia", "leccio",
        "misto_carpino_quercia", "abete_bianco", "abete_rosso",
    ]
    qmin = int(body.get("qmin") or 0)
    qmax = int(body.get("qmax") or 1800)
    cerca = (body.get("cerca") or "").strip().lower()
    regole = {
        "pioggia_min": int(body.get("pioggia_min") or 40),
        "pioggia_max": int(body.get("pioggia_max") or 100),
    }
    punti = [
        p for p in engine.PUNTI
        if p["regione"] in regioni
        and p["tipo"] in tipi
        and qmin <= p["quota"] <= qmax
        and (cerca in p["nome"].lower() if cerca else True)
    ]
    engine.CALC_PROGRESS.update({"pct": 1, "text": f"Avvio calcolo di {len(punti)} zone…"})
    sid = _sid()

    def _lavoro():
        job = _job(sid)
        try:
            ris = engine.calcola_tutti(
                punti, regole, "",
                max_km_stazione=5.0,
                max_workers=2,
                usa_wc=True,
            )
            # se nel frattempo l'utente ha rilanciato, scarta questo risultato
            if job.get("token") != mio_token:
                return
            view = list(ris)
            view_j = [_jsonable(r) for r in view]
            _salva_cache(view_j)
            engine.CALC_PROGRESS.update({"pct": 100, "text": "Fatto"})
            job["result"] = {
                "ok": True,
                "aggiornato": CACHE.get("aggiornato"),
                "n": len(view),
                "n_alto": sum(1 for r in view if r.get("score", 0) >= 70),
                "n_medio": sum(1 for r in view if 50 <= r.get("score", 0) < 70),
                "zone": view_j,
            }
        except Exception as e:
            if job.get("token") != mio_token:
                return
            job["error"] = str(e)
            engine.CALC_PROGRESS.update({"pct": 0, "text": f"Errore: {e}"})
            job["result"] = {"ok": False, "errore": str(e), "zone": []}
        finally:
            if job.get("token") == mio_token:
                job["running"] = False
                job["started_at"] = None

    threading.Thread(target=_lavoro, daemon=True).start()
    return jsonify({"ok": True, "started": True, "n_punti": len(punti)})


@app.route("/api/calcola/stato")
@login_required
def api_calcola_stato():
    j = _job()
    running = bool(j.get("running"))
    prog = dict(engine.CALC_PROGRESS or {})
    if running:
        return jsonify({
            "done": False,
            "running": True,
            "pct": prog.get("pct") or 0,
            "text": prog.get("text") or "",
        })
    result = j.get("result")
    if result is not None:
        out = dict(result)
        out["done"] = True
        out["running"] = False
        return jsonify(out)
    return jsonify({
        "done": False,
        "running": False,
        "pct": prog.get("pct") or 0,
        "text": prog.get("text") or "Nessun calcolo",
    })


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
            "aggiornato": CACHE.get("aggiornato"),
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




@app.route("/api/meteohub/status")
@login_required
def api_meteohub_status():
    """Stato cache e credenziali MeteoHub (senza esporre la password)."""
    user, pwd = engine.meteohub._creds()
    cached = engine.meteohub.load_cache()
    meta = {}
    meta_p = engine.meteohub.CACHE_DIR / "meta.json"
    if meta_p.exists():
        try:
            import json as _json
            meta = _json.loads(meta_p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return jsonify({
        "credenziali": bool(user and pwd),
        "user": (user[:2] + "***" + user[-4:]) if user and len(user) > 6 else (user or ""),
        "cache": bool(cached),
        "n_stations": len(cached[0]) if cached else 0,
        "n_series": len(cached[1]) if cached else 0,
        "meta": meta,
    })


@app.route("/api/meteohub/refresh", methods=["POST"])
@login_required
def api_meteohub_refresh():
    """Forza il download di una nuova estrazione MeteoHub (può richiedere 1–5 min)."""
    try:
        stations, series = engine.meteohub.refresh_data(days=35, force=True)
        return jsonify({"ok": True, "n_stations": len(stations), "n_series": len(series)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=False, threaded=True)
