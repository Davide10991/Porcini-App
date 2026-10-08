#!/usr/bin/env python3
"""Boletus Map — sito web senza Streamlit."""
from __future__ import annotations

import json
import os
import random
import secrets
import string
import smtplib
from datetime import datetime, timedelta
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
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
ADMIN_USER = "Davide1099"  # login admin classico (username)
ADMIN_PASS = "Ciccione99"
# email con privilegi admin (login con password account o ADMIN_PASS)
ADMIN_APPROVE_KEY = "BoletusApprove1099"  # consente approvazione dal link email
ADMIN_EMAILS = {
    "davidemenna3@gmail.com",
    "boletusmap@gmail.com",
    "davide1099",
}
ADMIN_NOTIFY_EMAIL = "boletusmap@gmail.com"
PAYPAL_DONATE = "https://paypal.me/Davide751/10"
CODES_FILE = Path(__file__).resolve().parent / "invite_codes.json"
REQUESTS_FILE = Path(__file__).resolve().parent / "invite_requests.json"
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




def _is_admin_email(email):
    e = (email or "").strip().lower()
    if not e:
        return False
    if e in {x.lower() for x in ADMIN_EMAILS}:
        return True
    if e == (ADMIN_USER or "").strip().lower():
        return True
    return False


def _nuovo_captcha():
    """Domanda semplice anti-bot (somma), salvata in sessione."""
    a = random.randint(2, 12)
    b = random.randint(1, 9)
    session["captcha_sum"] = a + b
    return f"{a} + {b}"


def _verifica_captcha(risposta):
    try:
        atteso = session.pop("captcha_sum", None)
        if atteso is None:
            return False
        return int(str(risposta).strip()) == int(atteso)
    except Exception:
        session.pop("captcha_sum", None)
        return False


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




def _carica_codici():
    if not CODES_FILE.exists():
        return {}
    try:
        data = json.loads(CODES_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _salva_codici(d):
    CODES_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def _carica_richieste():
    if not REQUESTS_FILE.exists():
        return {}
    try:
        data = json.loads(REQUESTS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _salva_richieste(d):
    REQUESTS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def _genera_codice_unico():
    alphabet = string.ascii_uppercase + string.digits
    codici = _carica_codici()
    for _ in range(30):
        code = "BM-" + "".join(secrets.choice(alphabet) for _ in range(8))
        if code not in codici:
            return code
    return "BM-" + secrets.token_hex(5).upper()


def _consuma_codice(codice, email):
    """Valida e segna il codice come usato. Ritorna (ok, errore)."""
    codice = (codice or "").strip()
    codici = _carica_codici()
    rec = codici.get(codice)
    if not rec:
        return False, "Codice invito non valido o già usato"
    if rec.get("stato") == "usato":
        return False, "Questo codice è già stato utilizzato"
    # se il codice era riservato a una email, deve coincidere
    riservato = (rec.get("email") or "").strip().lower()
    if riservato and riservato != (email or "").strip().lower():
        return False, "Questo codice è riservato a un altro indirizzo email"
    rec["stato"] = "usato"
    rec["usato_da"] = email
    rec["usato_il"] = _ora_roma().isoformat(timespec="seconds")
    codici[codice] = rec
    _salva_codici(codici)
    return True, ""



def _logo_path():
    return Path(__file__).resolve().parent / "static" / "logo.png"


def _invia_mail(dest, oggetto, corpo_testo, corpo_html=None):
    """Invia email testo+HTML con logo inline se presente."""
    cfg = _smtp_conf()
    if not cfg.get("user") or not cfg.get("password"):
        return False
    mittente = cfg.get("from") or cfg["user"]
    logo = _logo_path()
    if corpo_html and logo.exists():
        msg = MIMEMultipart("related")
        msg["Subject"] = oggetto
        msg["From"] = mittente
        msg["To"] = dest
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(corpo_testo, "plain", "utf-8"))
        alt.attach(MIMEText(corpo_html, "html", "utf-8"))
        msg.attach(alt)
        with open(logo, "rb") as f:
            img = MIMEImage(f.read(), _subtype="png")
        img.add_header("Content-ID", "<boletus_logo>")
        img.add_header("Content-Disposition", "inline", filename="logo.png")
        msg.attach(img)
    else:
        msg = MIMEText(corpo_testo, "plain", "utf-8")
        msg["Subject"] = oggetto
        msg["From"] = mittente
        msg["To"] = dest
    with smtplib.SMTP(cfg["host"], int(cfg.get("port") or 587), timeout=20) as s:
        s.starttls()
        s.login(cfg["user"], cfg["password"])
        s.send_message(msg)
    return True


def _html_mail(titolo, paragrafi, footer="Buone cercate,<br>Il team Boletus Map"):
    body = "".join(f"<p style=\"margin:0 0 12px;line-height:1.5\">{p}</p>" for p in paragrafi)
    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#1a1008;font-family:Segoe UI,Helvetica,Arial,sans-serif">
  <div style="max-width:520px;margin:24px auto;padding:28px 24px;background:#2a1a10;border:1px solid #c4783a;border-radius:16px;color:#f3e6d4">
    <div style="text-align:center;margin-bottom:18px">
      <img src="cid:boletus_logo" alt="Boletus Map" width="72" height="72"
           style="border-radius:50%;border:2px solid #c4783a;display:inline-block">
      <div style="margin-top:10px;font-size:22px;font-weight:700;color:#c4783a">Boletus Map</div>
    </div>
    <h2 style="margin:0 0 14px;font-size:18px;color:#f3e6d4">{titolo}</h2>
    {body}
    <p style="margin:20px 0 0;opacity:.9;line-height:1.5">{footer}</p>
  </div>
</body></html>"""


def _invia_codice_a_utente(email, codice):
    testo = (
        f"Ciao,\n\n"
        f"grazie per la donazione a supporto di Boletus Map.\n\n"
        f"Il tuo codice invito monouso è:\n\n"
        f"    {codice}\n\n"
        f"Registrati su Boletus Map inserendo questo codice.\n"
        f"Il codice funziona una sola volta e solo per: {email}\n\n"
        f"Buone cercate,\n"
        f"Il team Boletus Map\n"
    )
    html = _html_mail(
        "Il tuo codice invito",
        [
            "Grazie per la donazione a supporto di <b>Boletus Map</b>.",
            f"Il tuo <b>codice invito monouso</b> è:",
            f"<div style=\"text-align:center;font-size:22px;letter-spacing:.08em;padding:14px;"
            f"margin:8px 0;background:#1a1008;border-radius:10px;border:1px solid #c4783a\">"
            f"<b>{codice}</b></div>",
            f"Registrati inserendo questo codice. Vale <b>una sola volta</b> e solo per: <b>{email}</b>.",
        ],
    )
    return _invia_mail(email, "Il tuo codice invito Boletus Map", testo, html)


def _invia_richiesta_codice(email_richiedente, tx_id=""):
    """Salva richiesta + avvisa admin. Il codice si invia solo dopo approvazione (donazione)."""
    cfg = _smtp_conf()
    email_richiedente = (email_richiedente or "").strip().lower()
    token = secrets.token_urlsafe(16)
    reqs = _carica_richieste()
    reqs[token] = {
        "email": email_richiedente,
        "tx_id": (tx_id or "").strip(),
        "quando": _ora_roma().isoformat(timespec="seconds"),
        "ip": getattr(request, "remote_addr", None),
        "stato": "in_attesa",
    }
    _salva_richieste(reqs)
    if not cfg.get("user") or not cfg.get("password"):
        return True
    dest = ADMIN_NOTIFY_EMAIL or (cfg.get("from") or cfg.get("user"))
    quando = _ora_roma().strftime("%d/%m/%Y %H:%M")
    base = (request.url_root or "").rstrip("/")
    link = f"{base}/admin/approva-codice?token={token}&key={ADMIN_APPROVE_KEY}"
    corpo = (
        "Richiesta codice invito — Boletus Map\n\n"
        f"Data/ora: {quando}\n"
        f"Email: {email_richiedente}\n"
        f"ID pagamento PayPal (se indicato): {tx_id or '(non indicato)'}\n"
        f"IP: {request.remote_addr or '?'}\n\n"
        "Verifica la donazione (≥ 10 €) su PayPal,\n"
        "poi approva e invia il codice monouso con questo link:\n\n"
        f"{link}\n"
    )
    html = _html_mail(
        "Richiesta codice invito",
        [
            f"<b>Data/ora:</b> {quando}",
            f"<b>Email:</b> {email_richiedente}",
            f"<b>ID PayPal:</b> {tx_id or '(non indicato)'}",
            f"<b>IP:</b> {request.remote_addr or '?'}",
            "Verifica la donazione (≥ 10 €), poi approva dal link:",
            f'<a href="{link}" style="color:#c4783a;word-break:break-all">{link}</a>',
        ],
        footer="Boletus Map — pannello admin",
    )
    try:
        _invia_mail(dest, f"Richiesta codice (donazione) — {email_richiedente}", corpo, html)
    except Exception:
        pass
    return True


def _invia_registrazione(dest):
    testo = (
        f"Ciao,\n\n"
        f"benvenuto su Boletus Map.\n\n"
        f"La tua registrazione è andata a buon fine.\n\n"
        f"Email account: {dest}\n\n"
        f"Puoi consultare la mappa delle zone a porcini, lo stato delle buttate\n"
        f"e cercare boschi o punti sulla mappa.\n\n"
        f"Accedi con questa email e la password scelta in registrazione.\n\n"
        f"Se non sei stato tu a registrarti, ignora questo messaggio.\n\n"
        f"Buone cercate,\n"
        f"Il team Boletus Map\n"
    )
    html = _html_mail(
        "Benvenuto su Boletus Map",
        [
            "La tua registrazione è andata a <b>buon fine</b>.",
            f"<b>Account:</b> {dest}",
            "Puoi consultare la mappa delle zone a porcini in Italia, vedere lo stato delle buttate "
            "e cercare boschi o punti sulla mappa.",
            "Accedi con questa email e la password scelta in fase di registrazione.",
            "Se non sei stato tu a registrarti, ignora pure questo messaggio.",
        ],
    )
    return _invia_mail(dest, "Benvenuto su Boletus Map — registrazione confermata", testo, html)



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


def _safe_next():
    """Redirect post-login sicuro (solo path interni)."""
    nxt = (request.args.get("next") or request.form.get("next") or "").strip()
    if nxt.startswith("/") and not nxt.startswith("//"):
        return nxt
    return None


def login_required(fn):
    @wraps(fn)
    def wrap(*a, **k):
        if not session.get("ok"):
            nxt = request.full_path if request.query_string else request.path
            if nxt.endswith("?"):
                nxt = nxt[:-1]
            return redirect(url_for("login", next=nxt))
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
        if not _verifica_captcha(request.form.get("captcha")):
            err = "Verifica anti-bot non corretta. Riprova."
        else:
            email = (request.form.get("email") or "").strip()
            pw = (request.form.get("password") or "").strip()
            email_l = email.lower()
            users = _utenti()
            rec = users.get(email_l)
            # 1) username admin classico
            if email == ADMIN_USER and pw == ADMIN_PASS:
                session["ok"] = True
                session["email"] = ADMIN_USER
                session["ruolo"] = "admin"
                return redirect(_safe_next() or url_for("home"))
            # 2) email admin (davidemenna3@gmail.com, ecc.)
            if _is_admin_email(email_l):
                ok_pw = (pw == ADMIN_PASS)
                if not ok_pw and rec:
                    ok_pw = check_password_hash(rec.get("hash", ""), pw)
                if ok_pw:
                    session["ok"] = True
                    session["email"] = email_l
                    session["ruolo"] = "admin"
                    return redirect(_safe_next() or url_for("home"))
            # 3) utente normale
            if rec and check_password_hash(rec.get("hash", ""), pw):
                session["ok"] = True
                session["email"] = email_l
                session["ruolo"] = "admin" if _is_admin_email(email_l) else "guest"
                return redirect(_safe_next() or url_for("home"))
            err = "Email o password errati"
    domanda = _nuovo_captcha()
    return render_template(
        "login.html",
        errore=err,
        captcha_domanda=domanda,
        next_url=(request.args.get("next") or request.form.get("next") or ""),
    )



@app.route("/register/richiedi-codice", methods=["POST"])
def richiedi_codice():
    email = (request.form.get("email") or "").strip().lower()
    tx_id = (request.form.get("tx_id") or "").strip()
    donato = (request.form.get("donato") or "") in ("1", "true", "on", "yes")
    if not email or "@" not in email:
        return jsonify(ok=False, errore="Inserisci prima la tua email")
    if not donato:
        return jsonify(ok=False, errore="Conferma di aver donato almeno 10 € via PayPal")
    try:
        _invia_richiesta_codice(email, tx_id=tx_id)
        return jsonify(
            ok=True,
            messaggio="Richiesta inviata. Dopo la verifica della donazione riceverai il codice invito via email.",
        )
    except Exception:
        return jsonify(ok=False, errore="Impossibile inviare la richiesta. Riprova più tardi.")



@app.route("/admin/codici")
@login_required
def admin_codici():
    if session.get("ruolo") != "admin" and not _is_admin_email(session.get("email")):
        return "Solo amministratore", 403
    session["ruolo"] = "admin"
    reqs = _carica_richieste()
    pending = [(tok, r) for tok, r in reqs.items() if r.get("stato") == "in_attesa"]
    pending.sort(key=lambda x: x[1].get("quando") or "", reverse=True)
    rows = []
    for tok, r in pending:
        rows.append(
            f"<tr><td>{r.get('quando','')}</td><td>{r.get('email','')}</td>"
            f"<td>{r.get('tx_id') or '—'}</td>"
            f"<td><a style='color:#c4783a' href='/admin/approva-codice?token={tok}&key={ADMIN_APPROVE_KEY}'>Approva e invia codice</a></td></tr>"
        )
    body = "".join(rows) or "<tr><td colspan=4>Nessuna richiesta in attesa</td></tr>"
    return (
        "<html><body style='font-family:system-ui;background:#1a1008;color:#f3e6d4;padding:24px'>"
        "<h1>Boletus Map — Codici invito</h1>"
        "<p>Richieste in attesa (dopo donazione PayPal ≥ 10 €). Clicca Approva per generare e inviare il codice monouso.</p>"
        "<table border='1' cellpadding='8' style='border-collapse:collapse;width:100%;max-width:900px'>"
        "<tr><th>Quando</th><th>Email</th><th>ID PayPal</th><th>Azione</th></tr>"
        + body +
        "</table>"
        "<p style='margin-top:20px'><a href='/' style='color:#c4783a'>← Mappa</a></p>"
        "</body></html>"
    )


@app.route("/admin/approva-codice")
def admin_approva_codice():
    token = (request.args.get("token") or "").strip()
    key = (request.args.get("key") or "").strip()
    # accesso: admin loggato OPPURE chiave segreta nel link email
    is_admin = session.get("ok") and (
        session.get("ruolo") == "admin" or _is_admin_email(session.get("email"))
    )
    key_ok = bool(ADMIN_APPROVE_KEY) and key == ADMIN_APPROVE_KEY
    if not is_admin and not key_ok:
        # manda al login e poi torna qui
        nxt = request.full_path
        if nxt.endswith("?"):
            nxt = nxt[:-1]
        return redirect(url_for("login", next=nxt))
    if is_admin:
        session["ruolo"] = "admin"
    if not token:
        return "Token mancante. Usa /admin/codici", 400
    reqs = _carica_richieste()
    rec = reqs.get(token)
    if not rec:
        return (
            "<html><body style='font-family:sans-serif;background:#1a1008;color:#f3e6d4;padding:40px'>"
            "<h2>Richiesta non trovata</h2>"
            "<p>Token sconosciuto. Controlla di aver aperto il link completo dalla mail.</p>"
            "<p><a href='/admin/codici' style='color:#c4783a'>Vai all'elenco richieste</a></p>"
            "</body></html>"
        ), 404
    if rec.get("stato") != "in_attesa":
        cod = rec.get("codice") or "?"
        return (
            f"<html><body style='font-family:sans-serif;background:#1a1008;color:#f3e6d4;padding:40px'>"
            f"<h2>Già gestita</h2>"
            f"<p>Questa richiesta è già stata approvata.</p>"
            f"<p>Codice: <b>{cod}</b> → {rec.get('email')}</p>"
            f"<p><a href='/admin/codici' style='color:#c4783a'>Elenco richieste</a></p>"
            f"</body></html>"
        )
    email = (rec.get("email") or "").strip().lower()
    if not email:
        return "Email mancante", 400
    codice = _genera_codice_unico()
    codici = _carica_codici()
    codici[codice] = {
        "email": email,
        "stato": "libero",
        "creato": _ora_roma().isoformat(timespec="seconds"),
        "token_richiesta": token,
    }
    _salva_codici(codici)
    rec["stato"] = "approvata"
    rec["codice"] = codice
    reqs[token] = rec
    _salva_richieste(reqs)
    try:
        _invia_codice_a_utente(email, codice)
        mail_ok = "sì"
    except Exception as e:
        mail_ok = f"no ({e})"
    return (
        f"<html><body style='font-family:sans-serif;background:#1a1008;color:#f3e6d4;padding:40px'>"
        f"<h2>Codice approvato</h2>"
        f"<p>Email: <b>{email}</b></p>"
        f"<p>Codice monouso: <b>{codice}</b></p>"
        f"<p>Email inviata all'utente: {mail_ok}</p>"
        f"<p><a href='/' style='color:#c4783a'>Torna alla mappa</a></p>"
        f"</body></html>"
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    err = ""
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        pw = (request.form.get("password") or "").strip()
        pw2 = (request.form.get("password2") or "").strip()
        codice = (request.form.get("codice") or "").strip()
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
                ok_c, err_c = _consuma_codice(codice, email)
                if not ok_c:
                    err = err_c
                else:
                    users[email] = {
                        "hash": generate_password_hash(pw),
                        "quando": datetime.now().isoformat(timespec="seconds"),
                        "codice_usato": codice,
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
    return render_template("register.html", errore=err, ok_richiesta="", paypal_url=PAYPAL_DONATE, captcha_domanda=_nuovo_captcha())


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    # promuovi admin se email in lista
    if _is_admin_email(session.get("email")):
        session["ruolo"] = "admin"
    ruolo = session.get("ruolo", "guest")
    richieste = []
    if ruolo == "admin" or _is_admin_email(session.get("email")):
        reqs = _carica_richieste()
        for tok, r in reqs.items():
            if r.get("stato") == "in_attesa":
                richieste.append({
                    "token": tok,
                    "email": r.get("email") or "",
                    "quando": r.get("quando") or "",
                    "tx_id": r.get("tx_id") or "",
                })
        richieste.sort(key=lambda x: x.get("quando") or "", reverse=True)
    boschi = [
        {
            "nome": p.get("nome"),
            "lat": p.get("lat"),
            "lon": p.get("lon"),
            "regione": p.get("regione"),
            "quota": p.get("quota"),
            "tipo": p.get("tipo"),
        }
        for p in engine.PUNTI
    ]
    return render_template(
        "index.html",
        n_punti=len(engine.PUNTI),
        regioni=sorted({p["regione"] for p in engine.PUNTI}),
        ruolo=ruolo,
        email=session.get("email", ""),
        boschi_json=boschi,
        richieste_codici=richieste,
        approve_key=ADMIN_APPROVE_KEY if ruolo == "admin" else "",
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
