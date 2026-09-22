#!/usr/bin/env python3
"""
Client MeteoHub (ItaliaMeteo / Cineca) — unica fonte meteo per Boletus Map.

Flusso:
  1. login → token
  2. POST /api/data (estrazione asincrona, ultimi N giorni, prodotti temp+pioggia)
  3. poll /api/requests fino a SUCCESS
  4. download JSON e cache locale
  5. lookup stazione più vicina a (lat, lon)

Credenziali (in ordine di priorità):
  - variabili d'ambiente METEOHUB_USER / METEOHUB_PASSWORD
  - file meteohub_credentials.json accanto a questo modulo
    {"username": "...", "password": "..."}
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any

import pandas as pd
import requests

BASE = "https://meteohub.agenziaitaliameteo.it"
CACHE_DIR = Path(__file__).resolve().parent / "meteohub_cache"
CACHE_DIR.mkdir(exist_ok=True)

# Reti osservative utili al Centro-Sud (e dintorni). Si possono estendere.
DATASETS_CENTRO_SUD = [
    "dpcn-molise",
    "dpcn-lazio",
    "dpcn-campania",
    "dpcn-marche",
    "dpcn-umbria",
    "dpcn-puglia",
    "dpcn-basilicata",
    "dpcn-calabria",
    "dpcn-sicilia",
    "dpcn-sardegna",
    "sir-toscana",
    "open-trentino",
    "dpcn-veneto",
    "dpcn-lombardia",
    "dpcn-piemonte",
    "dpcn-liguria",
    "dpcn-bolzanoboze",
    "arpafvg",
    "mnw",  # MeteoNetwork via MeteoHub
]

# Codici BUFR
PRODUCT_TEMP = "B12101"       # temperatura aria
PRODUCT_PRECIP = "B13011"     # precipitazione totale
PRODUCTS = [PRODUCT_TEMP, PRODUCT_PRECIP]

# Cache in-memory del token e del catalogo serie
_TOKEN: str | None = None
_TOKEN_TS: float = 0.0
_TOKEN_TTL = 50 * 60  # 50 minuti
_SERIES_CACHE: dict[str, pd.DataFrame] = {}
_STATIONS_CACHE: list[dict] | None = None
_LAST_REFRESH: float = 0.0
REFRESH_TTL = 6 * 3600  # ricarica dati ogni 6 ore


def _creds() -> tuple[str, str]:
    u = (os.environ.get("METEOHUB_USER") or "").strip()
    p = (os.environ.get("METEOHUB_PASSWORD") or "").strip()
    if u and p:
        return u, p
    path = Path(__file__).resolve().parent / "meteohub_credentials.json"
    if path.exists():
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            u = (d.get("username") or d.get("email") or d.get("user") or "").strip()
            p = (d.get("password") or d.get("pass") or "").strip()
            if u and p:
                return u, p
        except Exception:
            pass
    return "", ""


def login(force: bool = False) -> str:
    """Restituisce un Bearer token valido."""
    global _TOKEN, _TOKEN_TS
    now = time.time()
    if not force and _TOKEN and (now - _TOKEN_TS) < _TOKEN_TTL:
        return _TOKEN
    user, password = _creds()
    if not user or not password:
        raise RuntimeError(
            "Credenziali MeteoHub mancanti. Imposta METEOHUB_USER e METEOHUB_PASSWORD "
            "oppure crea meteohub_credentials.json con {\"username\": \"...\", \"password\": \"...\"}."
        )
    last_err = ""
    for payload in (
        {"username": user, "password": password},
        {"email": user, "password": password},
    ):
        r = requests.post(f"{BASE}/auth/login", json=payload, timeout=30)
        last_err = f"HTTP {r.status_code}: {r.text[:300]}"
        if r.status_code != 200:
            continue
        try:
            data = r.json()
        except Exception:
            data = r.text.strip().strip('"')
        # Il server può restituire il JWT come stringa JSON pura
        if isinstance(data, str) and data.count(".") >= 2:
            _TOKEN = data.strip().strip('"')
            _TOKEN_TS = now
            return _TOKEN
        if isinstance(data, dict):
            token = (
                data.get("token")
                or data.get("access_token")
                or data.get("Response")
                or (data.get("data") or {}).get("token")
                or (data.get("data") or {}).get("access_token")
            )
            if isinstance(token, str) and token:
                _TOKEN = token
                _TOKEN_TS = now
                return _TOKEN
    raise RuntimeError(f"Login MeteoHub fallito: {last_err}")


def _headers() -> dict:
    return {"Authorization": f"Bearer {login()}", "Content-Type": "application/json"}


def _iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:00.000000Z")


def _datasets_disponibili() -> list[str]:
    """Interroga il catalogo e tiene solo i dataset OBS presenti."""
    try:
        r = requests.get(f"{BASE}/api/datasets", timeout=30)
        r.raise_for_status()
        ids = {d.get("id") for d in r.json() if d.get("category") == "OBS"}
        return [d for d in DATASETS_CENTRO_SUD if d in ids] or [d for d in DATASETS_CENTRO_SUD]
    except Exception:
        return list(DATASETS_CENTRO_SUD)


def submit_extraction(days: int = 35, datasets: list[str] | None = None) -> str:
    """Invia richiesta di estrazione. Ritorna request_id."""
    now = datetime.now(timezone.utc)
    frm = now - timedelta(days=days)
    body = {
        "request_name": f"boletus_{now.strftime('%Y%m%d_%H%M')}",
        "reftime": {"from": _iso_utc(frm), "to": _iso_utc(now)},
        "dataset_names": datasets or _datasets_disponibili(),
        "filters": {
            "product": [{"code": c} for c in PRODUCTS],
        },
        "output_format": "json",
        "only_reliable": False,
    }
    r = requests.post(f"{BASE}/api/data", headers=_headers(), json=body, timeout=90)
    if r.status_code == 401:
        login(force=True)
        r = requests.post(f"{BASE}/api/data", headers=_headers(), json=body, timeout=90)
    # 202 Accepted = richiesta in coda (normale)
    if r.status_code not in (200, 201, 202):
        raise RuntimeError(f"Submit fallito HTTP {r.status_code}: {r.text[:500]}")
    data = r.json() if r.content else {}
    rid = data.get("request_id") or data.get("id")
    if not rid:
        raise RuntimeError(f"Risposta senza request_id: {json.dumps(data)[:500]}")
    return str(rid)


def wait_request(request_id: str, max_wait: int = 600) -> str:
    """Attende SUCCESS e restituisce il nome file di output."""
    waited = 0
    last_status = ""
    while waited < max_wait:
        r = requests.get(f"{BASE}/api/requests", headers=_headers(), timeout=30)
        if r.status_code == 401:
            login(force=True)
            r = requests.get(f"{BASE}/api/requests", headers=_headers(), timeout=30)
        r.raise_for_status()
        payload = r.json()
        items = payload if isinstance(payload, list) else (
            payload.get("requests") or payload.get("data") or payload.get("items") or []
        )
        mine = None
        for it in items:
            iid = it.get("request_id") if it.get("request_id") is not None else it.get("id")
            if str(iid) == str(request_id):
                mine = it
                break
        if mine:
            status = str(mine.get("status") or mine.get("state") or "").upper()
            if status != last_status:
                print(f"  MeteoHub richiesta {request_id}: {status} ({waited}s)")
                last_status = status
            if status == "SUCCESS":
                fname = (
                    mine.get("fileoutput")
                    or mine.get("filename")
                    or mine.get("output")
                    or mine.get("file_output")
                )
                if not fname:
                    raise RuntimeError(f"SUCCESS senza file: {json.dumps(mine)[:800]}")
                return str(fname)
            if status in ("FAILED", "ERROR", "FAILURE"):
                raise RuntimeError(f"Richiesta fallita: {json.dumps(mine)[:800]}")
        time.sleep(8)
        waited += 8
    raise TimeoutError(f"Timeout attesa richiesta {request_id} dopo {max_wait}s (ultimo stato: {last_status})")



def download_and_aggregate(filename: str) -> tuple[list[dict], dict[str, pd.DataFrame]]:
    """
    Scarica il JSONL in streaming e aggrega subito a giornaliero,
    senza tenere tutto il file in RAM.
    """
    r = requests.get(
        f"{BASE}/api/data/{filename}",
        headers=_headers(),
        timeout=300,
        stream=True,
    )
    if r.status_code == 401:
        login(force=True)
        r = requests.get(
            f"{BASE}/api/data/{filename}",
            headers=_headers(),
            timeout=300,
            stream=True,
        )
    r.raise_for_status()

    stations_map: dict[str, dict] = {}
    # sid -> date -> {precip_sum, t_vals}
    acc: dict[str, dict] = {}
    n_lines = 0

    for raw_line in r.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        n_lines += 1
        try:
            rec = json.loads(raw_line)
        except Exception:
            continue
        parsed = _extract_from_msg(rec)
        if not parsed:
            continue
        sid = parsed["id"]
        if sid not in stations_map:
            stations_map[sid] = {
                "id": sid,
                "nome": parsed["nome"],
                "lat": parsed["lat"],
                "lon": parsed["lon"],
                "quota": parsed["quota"],
                "network": parsed["network"],
            }
        day = parsed["dt"].astimezone(timezone.utc).date() if parsed["dt"].tzinfo else parsed["dt"].date()
        bucket = acc.setdefault(sid, {}).setdefault(day, {"precip": 0.0, "temps": []})
        if parsed["precip"] is not None:
            try:
                bucket["precip"] += float(parsed["precip"])
            except Exception:
                pass
        if parsed["temp"] is not None:
            try:
                bucket["temps"].append(float(parsed["temp"]))
            except Exception:
                pass

    series: dict[str, pd.DataFrame] = {}
    for sid, days in acc.items():
        rows = []
        for day, vals in sorted(days.items()):
            temps = vals["temps"]
            rows.append({
                "date": pd.Timestamp(day),
                "precip": vals["precip"],
                "t_max": max(temps) if temps else None,
                "t_min": min(temps) if temps else None,
                "t_med": (sum(temps) / len(temps)) if temps else None,
            })
        if rows:
            series[sid] = pd.DataFrame(rows)

    print(f"    streaming: {n_lines} righe → {len(stations_map)} stazioni")
    return list(stations_map.values()), series



def download_result(filename: str) -> str:
    r = requests.get(f"{BASE}/api/data/{filename}", headers=_headers(), timeout=120)
    if r.status_code == 401:
        login(force=True)
        r = requests.get(f"{BASE}/api/data/{filename}", headers=_headers(), timeout=120)
    r.raise_for_status()
    return r.text


def _parse_records(text: str) -> list[dict]:
    """JSON Lines (formato reale MeteoHub) o JSON array."""
    text = (text or "").strip()
    if not text:
        return []
    records: list[dict] = []
    # JSON Lines (una riga = un messaggio)
    if text[:1] == "{":
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    records.append(obj)
            except Exception:
                continue
        if records:
            return records
    try:
        data = json.loads(text)
    except Exception:
        return records
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("data", "records", "items", "results", "observations"):
            if isinstance(data.get(key), list):
                return [x for x in data[key] if isinstance(x, dict)]
        return [data]
    return records


def _extract_from_msg(rec: dict) -> dict | None:
    """
    Formato MeteoHub JSONL:
      network, date, data: [
        {vars: {B01019: {v: nome}, B05001: {v: lat}, B06001: {v: lon}, B07030: {v: quota}, ...}},
        {timerange: [...], vars: {B13011: {v: mm} or B12101: {v: temp}}}
      ]
    """
    data_blocks = rec.get("data") or []
    if not isinstance(data_blocks, list):
        return None

    nome = None
    lat = None
    lon = None
    quota = None
    network = rec.get("network")
    precip = None
    temp = None

    for block in data_blocks:
        if not isinstance(block, dict):
            continue
        vars_ = block.get("vars") or {}
        if not isinstance(vars_, dict):
            continue
        # metadata block
        if "B01019" in vars_:
            try:
                nome = str(vars_["B01019"].get("v"))
            except Exception:
                pass
        if "B05001" in vars_:
            try:
                lat = float(vars_["B05001"]["v"])
            except Exception:
                pass
        if "B06001" in vars_:
            try:
                lon = float(vars_["B06001"]["v"])
            except Exception:
                pass
        if "B07030" in vars_:
            try:
                quota = float(vars_["B07030"]["v"])
            except Exception:
                pass
        if "B01194" in vars_ and not network:
            try:
                network = str(vars_["B01194"]["v"])
            except Exception:
                pass
        # measurements
        if "B13011" in vars_:
            try:
                precip = float(vars_["B13011"]["v"])
            except Exception:
                pass
        if "B12101" in vars_:
            try:
                temp = float(vars_["B12101"]["v"])
                # BUFR temperatura spesso in Kelvin
                if temp > 200:
                    temp = temp - 273.15
            except Exception:
                pass

    if lat is None or lon is None:
        return None
    dt = None
    try:
        s = str(rec.get("date") or "").replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
    except Exception:
        return None

    # id stabile: network + nome o coordinate
    sid = f"{network or 'unk'}|{nome or f'{lat:.4f}_{lon:.4f}'}"
    return {
        "id": sid,
        "nome": nome or sid,
        "lat": lat,
        "lon": lon,
        "quota": quota,
        "network": network or "",
        "dt": dt,
        "precip": precip,
        "temp": temp,
    }


def records_to_frames(records: list[dict]) -> tuple[list[dict], dict[str, pd.DataFrame]]:
    """
    Costruisce:
      - lista stazioni {id, nome, lat, lon, quota, network}
      - dict id -> DataFrame giornaliero: date, precip, t_max, t_min, t_med
    Precipitazione: somma dei valori (tipicamente cumulati a 1 min → somma ≈ totale giorno).
    """
    stations_map: dict[str, dict] = {}
    buckets: dict[str, list[dict]] = {}

    for rec in records:
        parsed = _extract_from_msg(rec)
        if not parsed:
            continue
        sid = parsed["id"]
        if sid not in stations_map:
            stations_map[sid] = {
                "id": sid,
                "nome": parsed["nome"],
                "lat": parsed["lat"],
                "lon": parsed["lon"],
                "quota": parsed["quota"],
                "network": parsed["network"],
            }
        day = parsed["dt"].astimezone(timezone.utc).date() if parsed["dt"].tzinfo else parsed["dt"].date()
        buckets.setdefault(sid, []).append({
            "date": day,
            "precip": parsed["precip"],
            "temp": parsed["temp"],
        })

    series: dict[str, pd.DataFrame] = {}
    for sid, rows in buckets.items():
        if not rows:
            continue
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        g = df.groupby("date", as_index=False).agg(
            precip=("precip", "sum"),
            t_max=("temp", "max"),
            t_min=("temp", "min"),
            t_med=("temp", "mean"),
        )
        series[sid] = g.sort_values("date")

    stations = [s for s in stations_map.values() if s.get("lat") is not None and s.get("lon") is not None]
    return stations, series


def _cache_paths() -> tuple[Path, Path]:
    return CACHE_DIR / "stations.json", CACHE_DIR / "series.parquet"


def save_cache(stations: list[dict], series: dict[str, pd.DataFrame]) -> None:
    sp, qp = _cache_paths()
    sp.write_text(json.dumps(stations, ensure_ascii=False, indent=2), encoding="utf-8")
    # salva serie come un unico parquet con colonna station_id
    frames = []
    for sid, df in series.items():
        d = df.copy()
        d["station_id"] = sid
        frames.append(d)
    if frames:
        big = pd.concat(frames, ignore_index=True)
        try:
            big.to_parquet(qp, index=False)
        except Exception:
            # fallback csv compresso
            big.to_csv(CACHE_DIR / "series.csv.gz", index=False, compression="gzip")
    meta = {"ts": time.time(), "n_stations": len(stations), "n_series": len(series)}
    (CACHE_DIR / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def load_cache() -> tuple[list[dict], dict[str, pd.DataFrame]] | None:
    sp, qp = _cache_paths()
    meta_p = CACHE_DIR / "meta.json"
    if not sp.exists() or not meta_p.exists():
        return None
    try:
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        if time.time() - float(meta.get("ts") or 0) > REFRESH_TTL:
            return None  # scaduta
        stations = json.loads(sp.read_text(encoding="utf-8"))
        series: dict[str, pd.DataFrame] = {}
        if qp.exists():
            big = pd.read_parquet(qp)
        elif (CACHE_DIR / "series.csv.gz").exists():
            big = pd.read_csv(CACHE_DIR / "series.csv.gz")
        else:
            return None
        if "station_id" not in big.columns:
            return None
        big["date"] = pd.to_datetime(big["date"])
        for sid, g in big.groupby("station_id"):
            series[str(sid)] = g.drop(columns=["station_id"]).reset_index(drop=True)
        return stations, series
    except Exception:
        return None


def _merge_series(base: dict[str, pd.DataFrame], extra: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    out = dict(base)
    for sid, df in extra.items():
        if sid not in out:
            out[sid] = df
            continue
        combined = pd.concat([out[sid], df], ignore_index=True)
        combined["date"] = pd.to_datetime(combined["date"])
        # somma precip se stesso giorno da più chunk, max/min temp
        g = combined.groupby("date", as_index=False).agg(
            precip=("precip", "sum"),
            t_max=("t_max", "max"),
            t_min=("t_min", "min"),
            t_med=("t_med", "mean"),
        )
        out[sid] = g.sort_values("date")
    return out


def refresh_data(days: int = 35, force: bool = False) -> tuple[list[dict], dict[str, pd.DataFrame]]:
    """
    Aggiorna cache da MeteoHub se scaduta o force=True.
    Estrae per singolo dataset e finestre di 3 giorni, aggregando in streaming.
    """
    global _STATIONS_CACHE, _SERIES_CACHE, _LAST_REFRESH
    if not force:
        cached = load_cache()
        if cached is not None:
            _STATIONS_CACHE, _SERIES_CACHE = cached
            _LAST_REFRESH = time.time()
            return cached
        if _STATIONS_CACHE is not None and _SERIES_CACHE and (time.time() - _LAST_REFRESH) < REFRESH_TTL:
            return _STATIONS_CACHE, _SERIES_CACHE

    datasets = _datasets_disponibili()
    priority = [
        "dpcn-molise", "dpcn-lazio", "dpcn-campania", "dpcn-marche",
        "dpcn-umbria", "dpcn-puglia", "dpcn-basilicata", "dpcn-calabria",
        "sir-toscana", "mnw",
    ]
    ordered = [d for d in priority if d in datasets] + [d for d in datasets if d not in priority]

    all_stations: dict[str, dict] = {}
    all_series: dict[str, pd.DataFrame] = {}

    window = 3  # giorni per richiesta
    n_windows = max(1, (days + window - 1) // window)

    for ds in ordered:
        for w in range(n_windows):
            end_offset = w * window
            start_offset = min(days, (w + 1) * window)
            if start_offset <= end_offset:
                continue
            try:
                print(f"  MeteoHub: {ds} [{start_offset}-{end_offset}] gg…")
                now = datetime.now(timezone.utc)
                to_dt = now - timedelta(days=end_offset)
                from_dt = now - timedelta(days=start_offset)
                body = {
                    "request_name": f"boletus_{ds}_{w}",
                    "reftime": {"from": _iso_utc(from_dt), "to": _iso_utc(to_dt)},
                    "dataset_names": [ds],
                    "filters": {"product": [{"code": c} for c in PRODUCTS]},
                    "output_format": "json",
                    "only_reliable": False,
                }
                r = requests.post(f"{BASE}/api/data", headers=_headers(), json=body, timeout=90)
                if r.status_code == 401:
                    login(force=True)
                    r = requests.post(f"{BASE}/api/data", headers=_headers(), json=body, timeout=90)
                if r.status_code not in (200, 201, 202):
                    print(f"    skip HTTP {r.status_code}: {r.text[:180]}")
                    continue
                rid = str((r.json() or {}).get("request_id") or (r.json() or {}).get("id"))
                fname = wait_request(rid, max_wait=600)
                st, ser = download_and_aggregate(fname)
                for s in st:
                    all_stations[s["id"]] = s
                all_series = _merge_series(all_series, ser)
                # salva progresso parziale
                save_cache(list(all_stations.values()), all_series)
            except Exception as e:
                print(f"    errore {ds} w{w}: {e}")
                continue

    stations = list(all_stations.values())
    save_cache(stations, all_series)
    _STATIONS_CACHE = stations
    _SERIES_CACHE = all_series
    _LAST_REFRESH = time.time()
    return stations, all_series


def distanza_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * r * atan2(sqrt(a), sqrt(1 - a))


def stazioni_vicine(
    lat: float,
    lon: float,
    stations: list[dict] | None = None,
    quota: float | None = None,
    n: int = 5,
    max_km: float = 40.0,
    max_dq: float = 500.0,
) -> list[dict]:
    if stations is None:
        stations = _STATIONS_CACHE or []
        if not stations:
            cached = load_cache()
            if cached:
                stations = cached[0]
    out = []
    for s in stations:
        try:
            d = distanza_km(lat, lon, float(s["lat"]), float(s["lon"]))
        except Exception:
            continue
        if d > max_km:
            continue
        dq = None
        if quota is not None and s.get("quota") is not None:
            try:
                dq = abs(float(quota) - float(s["quota"]))
                if dq > max_dq:
                    continue
            except Exception:
                pass
        item = dict(s)
        item["distanza_km"] = round(d, 2)
        item["delta_quota"] = dq
        out.append(item)
    out.sort(key=lambda x: (x["distanza_km"], x.get("delta_quota") or 0))
    return out[:n]


def serie_stazione(station_id: str, series: dict[str, pd.DataFrame] | None = None) -> pd.DataFrame | None:
    if series is None:
        series = _SERIES_CACHE
        if not series:
            cached = load_cache()
            if cached:
                series = cached[1]
    if not series:
        return None
    df = series.get(str(station_id))
    if df is None or len(df) == 0:
        return None
    return df.copy()


def get_meteo_punto(
    lat: float,
    lon: float,
    days: int = 30,
    quota: float | None = None,
    max_km: float = 35.0,
    auto_refresh: bool = True,
) -> tuple[pd.DataFrame | None, dict]:
    """
    API principale per Boletus Map.
    Ritorna (df giornaliero ultimi `days`, info).
    info ha: fonte, stazione, distanza_km, quota_stazione, pioggia_stazione_30g, giorni_pluviometro
    """
    info: dict[str, Any] = {
        "fonte": "MeteoHub",
        "stazione": "n/d",
        "distanza_km": None,
        "quota_stazione": None,
        "pioggia_stazione_30g": None,
        "giorni_pluviometro": [],
        "network": None,
    }

    try:
        if auto_refresh:
            stations, series = refresh_data(days=max(days + 5, 35), force=False)
        else:
            cached = load_cache()
            if not cached:
                stations, series = refresh_data(days=max(days + 5, 35), force=True)
            else:
                stations, series = cached
    except Exception as e:
        info["fonte"] = f"MeteoHub errore: {e}"
        return None, info

    vicine = stazioni_vicine(lat, lon, stations, quota=quota, n=8, max_km=max_km)
    if not vicine:
        info["fonte"] = f"MeteoHub · nessuna stazione entro {max_km:.0f} km"
        return None, info

    # scegli la migliore: più giorni con pioggia valida, poi più vicina
    migliore = None
    miglior_df = None
    miglior_score = -1.0
    oggi = pd.Timestamp(datetime.now().date())
    taglio = oggi - pd.Timedelta(days=days)

    for s in vicine:
        df = serie_stazione(s["id"], series)
        if df is None or len(df) == 0:
            continue
        d = df.copy()
        d["date"] = pd.to_datetime(d["date"]).dt.normalize()
        d = d[(d["date"] >= taglio) & (d["date"] <= oggi)]
        if len(d) < 3:
            continue
        n_precip = int(pd.to_numeric(d["precip"], errors="coerce").notna().sum()) if "precip" in d.columns else 0
        n_temp = int(pd.to_numeric(d.get("t_max"), errors="coerce").notna().sum()) if "t_max" in d.columns else 0
        dist = float(s.get("distanza_km") or 99)
        score = n_precip * 3.0 + n_temp * 1.5 - dist * 0.8
        if score > miglior_score:
            miglior_score = score
            migliore = s
            miglior_df = d

    if migliore is None or miglior_df is None:
        # fallback: stazione più vicina anche se pochi dati
        s0 = vicine[0]
        df0 = serie_stazione(s0["id"], series)
        if df0 is None:
            info["fonte"] = f"MeteoHub · stazioni vicine senza serie ({vicine[0].get('nome')})"
            info["stazione"] = vicine[0].get("nome")
            info["distanza_km"] = vicine[0].get("distanza_km")
            return None, info
        d = df0.copy()
        d["date"] = pd.to_datetime(d["date"]).dt.normalize()
        d = d[(d["date"] >= taglio) & (d["date"] <= oggi)]
        migliore, miglior_df = s0, d

    mm = None
    if "precip" in miglior_df.columns:
        try:
            mm = round(float(pd.to_numeric(miglior_df["precip"], errors="coerce").sum(skipna=True)), 1)
        except Exception:
            mm = None

    giorni = []
    if "precip" in miglior_df.columns:
        for _, row in miglior_df.sort_values("date").iterrows():
            try:
                p = float(row["precip"]) if pd.notna(row["precip"]) else 0.0
            except Exception:
                continue
            if p >= 0.2:
                giorni.append(f"{pd.Timestamp(row['date']).date().isoformat()}: {p:.1f} mm")

    net = migliore.get("network") or ""
    info.update({
        "fonte": f"MeteoHub {net} · {migliore.get('nome')} a {migliore.get('distanza_km')} km".strip(),
        "stazione": f"{migliore.get('nome')} ({migliore.get('id')})",
        "distanza_km": migliore.get("distanza_km"),
        "quota_stazione": migliore.get("quota"),
        "pioggia_stazione_30g": mm,
        "giorni_pluviometro": giorni,
        "network": net,
    })
    return miglior_df.reset_index(drop=True), info


def ensure_cache(days: int = 35) -> dict:
    """Chiamata da UI/startup: forza o verifica cache. Ritorna summary."""
    stations, series = refresh_data(days=days, force=False)
    return {
        "ok": True,
        "n_stations": len(stations),
        "n_series": len(series),
        "cache_dir": str(CACHE_DIR),
    }
