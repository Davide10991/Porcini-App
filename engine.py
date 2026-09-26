# Motore Boletus Map — senza Streamlit
import pandas as pd
import requests
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
TZ_ROMA = ZoneInfo("Europe/Rome")
from math import radians, sin, cos, sqrt, atan2, exp
import io
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from functools import lru_cache
import time

try:
    from meteostat import Stations, Daily
    METEOSTAT_OK = True
except Exception:
    METEOSTAT_OK = False

import meteohub

GUEST_PASS = "Porcino1"
CALC_PROGRESS = {"pct": 0, "text": ""}

class _SS(dict):
    def setdefault(self, *a, **k):
        return dict.setdefault(self, *a, **k)

class _Bar:
    def progress(self, *a, **k):
        try:
            if a:
                CALC_PROGRESS["pct"] = int(float(a[0]) * 100) if float(a[0]) <= 1 else int(a[0])
            if k.get("text"):
                CALC_PROGRESS["text"] = k["text"]
        except Exception:
            pass

class _St:
    session_state = _SS()
    secrets = {}
    def cache_data(self, ttl=None, **k):
        def deco(fn):
            return lru_cache(maxsize=512)(fn)
        return deco
    def progress(self, *a, **k):
        b = _Bar()
        b.progress(*a, **k)
        return b

st = _St()

def _sfondo_url(nome):
    return ""

PUNTI = [
    # ===================== ABRUZZO =====================
    {"nome": "Gran Sasso - Campo Imperatore", "lat": 42.450, "lon": 13.550, "tipo": "faggio", "quota": 1600, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Pietracamela", "lat": 42.510, "lon": 13.555, "tipo": "faggio", "quota": 1500, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Prati di Tivo", "lat": 42.505, "lon": 13.570, "tipo": "faggio", "quota": 1450, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Castelli", "lat": 42.488, "lon": 13.712, "tipo": "faggio", "quota": 1200, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Santo Stefano di Sessanio", "lat": 42.343, "lon": 13.644, "tipo": "faggio", "quota": 1250, "regione": "Abruzzo"},
    {"nome": "Majella - Blockhaus", "lat": 42.140, "lon": 14.110, "tipo": "faggio", "quota": 1700, "regione": "Abruzzo"},
    {"nome": "Majella - Passolanciano", "lat": 42.170, "lon": 14.120, "tipo": "faggio", "quota": 1300, "regione": "Abruzzo"},
    {"nome": "Majella - Caramanico Terme", "lat": 42.156, "lon": 14.005, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Majella - Pacentro", "lat": 42.050, "lon": 13.995, "tipo": "faggio", "quota": 1200, "regione": "Abruzzo"},
    {"nome": "Majella - Palena", "lat": 41.984, "lon": 14.137, "tipo": "faggio", "quota": 1300, "regione": "Abruzzo"},
    {"nome": "Majella - Pescocostanzo", "lat": 41.887, "lon": 14.066, "tipo": "faggio", "quota": 1400, "regione": "Abruzzo"},
    {"nome": "Majella - Rivisondoli", "lat": 41.871, "lon": 14.070, "tipo": "faggio", "quota": 1350, "regione": "Abruzzo"},
    {"nome": "Sirente-Velino - Ovindoli", "lat": 42.137, "lon": 13.527, "tipo": "faggio", "quota": 1450, "regione": "Abruzzo"},
    {"nome": "Sirente-Velino - Rocca di Mezzo", "lat": 42.206, "lon": 13.519, "tipo": "faggio", "quota": 1320, "regione": "Abruzzo"},
    {"nome": "Sirente-Velino - Celano", "lat": 42.085, "lon": 13.540, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Monti della Laga - Campotosto", "lat": 42.560, "lon": 13.330, "tipo": "faggio", "quota": 1400, "regione": "Abruzzo"},
    {"nome": "Monti della Laga - Amatrice lato Abruzzo", "lat": 42.630, "lon": 13.350, "tipo": "faggio", "quota": 1300, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Pescasseroli", "lat": 41.808, "lon": 13.789, "tipo": "faggio", "quota": 1200, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Opi", "lat": 41.780, "lon": 13.830, "tipo": "faggio", "quota": 1250, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Villetta Barrea", "lat": 41.776, "lon": 13.939, "tipo": "faggio", "quota": 1000, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Civitella Alfedena", "lat": 41.765, "lon": 13.943, "tipo": "faggio", "quota": 1120, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Scanno", "lat": 41.904, "lon": 13.879, "tipo": "faggio", "quota": 1050, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Villalago", "lat": 41.935, "lon": 13.836, "tipo": "faggio", "quota": 930, "regione": "Abruzzo"},
    {"nome": "Monti Marsicani - Gioia dei Marsi", "lat": 41.955, "lon": 13.690, "tipo": "faggio", "quota": 1000, "regione": "Abruzzo"},
    {"nome": "Altopiano delle Cinquemiglia", "lat": 41.870, "lon": 14.050, "tipo": "faggio", "quota": 1250, "regione": "Abruzzo"},
    {"nome": "Bosco di Sant'Antonio - Pescocostanzo", "lat": 41.900, "lon": 14.050, "tipo": "faggio", "quota": 1300, "regione": "Abruzzo"},
    {"nome": "Monti Pizzi - Castel del Giudice lato Abruzzo", "lat": 41.860, "lon": 14.230, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Alto Sangro - Roccaraso", "lat": 41.850, "lon": 14.078, "tipo": "faggio", "quota": 1250, "regione": "Abruzzo"},
    {"nome": "Alto Sangro - Pescocostanzo faggete", "lat": 41.895, "lon": 14.080, "tipo": "faggio", "quota": 1400, "regione": "Abruzzo"},
    {"nome": "Chieti collinare - Guardiagrele", "lat": 42.190, "lon": 14.220, "tipo": "quercia", "quota": 600, "regione": "Abruzzo"},
    {"nome": "Teramo collinare - Cermignano", "lat": 42.590, "lon": 13.800, "tipo": "quercia", "quota": 550, "regione": "Abruzzo"},
    {"nome": "Monti Frentani - Palombaro", "lat": 42.125, "lon": 14.230, "tipo": "castagno", "quota": 700, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Assergi / Fonte Cerreto", "lat": 42.410, "lon": 13.508, "tipo": "faggio", "quota": 1300, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Isola del Gran Sasso", "lat": 42.503, "lon": 13.655, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Farindola", "lat": 42.443, "lon": 13.822, "tipo": "faggio", "quota": 1200, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Castel del Monte", "lat": 42.365, "lon": 13.726, "tipo": "faggio", "quota": 1350, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Calascio", "lat": 42.327, "lon": 13.697, "tipo": "faggio", "quota": 1200, "regione": "Abruzzo"},
    {"nome": "Campo Felice - Lucoli", "lat": 42.257, "lon": 13.394, "tipo": "faggio", "quota": 1400, "regione": "Abruzzo"},
    {"nome": "Sirente - Rocca di Cambio", "lat": 42.236, "lon": 13.488, "tipo": "faggio", "quota": 1400, "regione": "Abruzzo"},
    {"nome": "Sirente - Secinaro", "lat": 42.153, "lon": 13.681, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Sirente - Gagliano Aterno", "lat": 42.125, "lon": 13.700, "tipo": "faggio", "quota": 1000, "regione": "Abruzzo"},
    {"nome": "Velino - Magliano de' Marsi", "lat": 42.092, "lon": 13.364, "tipo": "faggio", "quota": 1000, "regione": "Abruzzo"},
    {"nome": "Monti della Laga - Cortino", "lat": 42.622, "lon": 13.508, "tipo": "faggio", "quota": 1200, "regione": "Abruzzo"},
    {"nome": "Monti della Laga - Rocca Santa Maria", "lat": 42.687, "lon": 13.528, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Monti della Laga - Valle Castellana", "lat": 42.736, "lon": 13.497, "tipo": "faggio", "quota": 1000, "regione": "Abruzzo"},
    {"nome": "Monti della Laga - Crognaleto", "lat": 42.588, "lon": 13.489, "tipo": "faggio", "quota": 1150, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Barrea", "lat": 41.756, "lon": 13.993, "tipo": "faggio", "quota": 1060, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Alfedena", "lat": 41.737, "lon": 14.035, "tipo": "faggio", "quota": 900, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Scontrone", "lat": 41.747, "lon": 14.039, "tipo": "faggio", "quota": 850, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Bisegna", "lat": 41.921, "lon": 13.758, "tipo": "faggio", "quota": 1200, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Ortona dei Marsi", "lat": 41.997, "lon": 13.728, "tipo": "faggio", "quota": 1050, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Villavallelonga", "lat": 41.867, "lon": 13.621, "tipo": "faggio", "quota": 1000, "regione": "Abruzzo"},
    {"nome": "Parco d'Abruzzo - Collelongo", "lat": 41.887, "lon": 13.585, "tipo": "faggio", "quota": 950, "regione": "Abruzzo"},
    {"nome": "Val Fondillo / Camosciara", "lat": 41.767, "lon": 13.852, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Passo Godi", "lat": 41.850, "lon": 13.920, "tipo": "faggio", "quota": 1550, "regione": "Abruzzo"},
    {"nome": "Monte Greco - Castel di Sangro", "lat": 41.784, "lon": 14.107, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Alto Sangro - Pescocostanzo / Aremogna", "lat": 41.830, "lon": 14.050, "tipo": "faggio", "quota": 1500, "regione": "Abruzzo"},
    {"nome": "Majella - Pretoro", "lat": 42.220, "lon": 14.143, "tipo": "faggio", "quota": 900, "regione": "Abruzzo"},
    {"nome": "Majella - Pennapiedimonte", "lat": 42.155, "lon": 14.194, "tipo": "faggio", "quota": 850, "regione": "Abruzzo"},
    {"nome": "Majella - Fara San Martino", "lat": 42.090, "lon": 14.205, "tipo": "faggio", "quota": 900, "regione": "Abruzzo"},
    {"nome": "Majella - Lama dei Peligni", "lat": 42.043, "lon": 14.187, "tipo": "faggio", "quota": 700, "regione": "Abruzzo"},
    {"nome": "Majella - Lettopalena", "lat": 41.983, "lon": 14.157, "tipo": "faggio", "quota": 700, "regione": "Abruzzo"},
    {"nome": "Majella - Roccamorice", "lat": 42.213, "lon": 14.028, "tipo": "faggio", "quota": 550, "regione": "Abruzzo"},
    {"nome": "Majella - Abbateggio", "lat": 42.224, "lon": 14.013, "tipo": "quercia", "quota": 500, "regione": "Abruzzo"},
    {"nome": "Morrone - Pacentro / Sulmona", "lat": 42.051, "lon": 13.948, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Morrone - Popoli", "lat": 42.174, "lon": 13.832, "tipo": "quercia", "quota": 500, "regione": "Abruzzo"},
    {"nome": "Monti Pizzi - Gamberale", "lat": 41.904, "lon": 14.208, "tipo": "faggio", "quota": 1350, "regione": "Abruzzo"},
    {"nome": "Monti Pizzi - Pizzoferrato", "lat": 41.919, "lon": 14.236, "tipo": "faggio", "quota": 1250, "regione": "Abruzzo"},
    {"nome": "Monti Pizzi - Quadri", "lat": 41.924, "lon": 14.288, "tipo": "faggio", "quota": 900, "regione": "Abruzzo"},
    {"nome": "Alto Vastese - Castiglione Messer Marino", "lat": 41.868, "lon": 14.452, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Alto Vastese - Schiavi d'Abruzzo", "lat": 41.815, "lon": 14.485, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Frentani - Roccascalegna", "lat": 42.062, "lon": 14.308, "tipo": "quercia", "quota": 550, "regione": "Abruzzo"},
    {"nome": "Frentani - Gessopalena", "lat": 42.055, "lon": 14.273, "tipo": "castagno", "quota": 650, "regione": "Abruzzo"},
    {"nome": "Frentani - Torricella Peligna", "lat": 42.025, "lon": 14.259, "tipo": "castagno", "quota": 750, "regione": "Abruzzo"},
    # Val di Sangro / Costa dei Trabocchi / Vastese (macrozona Atessa-Gissi-Vasto)
    {"nome": "Lecceta di Torino di Sangro", "lat": 42.227, "lon": 14.548, "tipo": "leccio", "quota": 80, "regione": "Abruzzo"},
    {"nome": "Boschi ripariali Fiume Osento", "lat": 42.167, "lon": 14.531, "tipo": "quercia", "quota": 80, "regione": "Abruzzo"},
    {"nome": "Bosco di Don Venanzio - Pollutri", "lat": 42.138, "lon": 14.615, "tipo": "quercia", "quota": 30, "regione": "Abruzzo"},
    {"nome": "Punta Aderci - foce Sinello", "lat": 42.175, "lon": 14.678, "tipo": "quercia", "quota": 25, "regione": "Abruzzo"},
    {"nome": "Bosco di Mozzagrogna / Sangro", "lat": 42.164, "lon": 14.448, "tipo": "quercia", "quota": 120, "regione": "Abruzzo"},
    {"nome": "Atessa - Fontecampana / Vallaspra", "lat": 42.070, "lon": 14.430, "tipo": "quercia", "quota": 400, "regione": "Abruzzo"},
    {"nome": "Monte Pallano - crinale", "lat": 42.038, "lon": 14.405, "tipo": "faggio", "quota": 950, "regione": "Abruzzo"},
    {"nome": "Monte Pallano - Lecceta Isca d'Archi", "lat": 42.090, "lon": 14.380, "tipo": "leccio", "quota": 450, "regione": "Abruzzo"},
    {"nome": "Tornareccio - cerrete Pallano", "lat": 42.030, "lon": 14.420, "tipo": "quercia", "quota": 600, "regione": "Abruzzo"},
    {"nome": "Bomba - versante Pallano", "lat": 42.033, "lon": 14.367, "tipo": "quercia", "quota": 450, "regione": "Abruzzo"},
    {"nome": "Archi - Isca d'Archi", "lat": 42.090, "lon": 14.381, "tipo": "quercia", "quota": 440, "regione": "Abruzzo"},
    {"nome": "Gissi - colline cerrete", "lat": 42.020, "lon": 14.548, "tipo": "quercia", "quota": 480, "regione": "Abruzzo"},
    {"nome": "Monte Sorbo - Carpineto Sinello", "lat": 41.990, "lon": 14.520, "tipo": "quercia", "quota": 700, "regione": "Abruzzo"},
    {"nome": "Carpineto Sinello - Colle S. Giovanni", "lat": 41.965, "lon": 14.534, "tipo": "castagno", "quota": 850, "regione": "Abruzzo"},
    {"nome": "Carunchio - Bosco Carunchino", "lat": 41.910, "lon": 14.530, "tipo": "quercia", "quota": 700, "regione": "Abruzzo"},
    {"nome": "Palmoli - Fiume Treste", "lat": 41.940, "lon": 14.580, "tipo": "quercia", "quota": 650, "regione": "Abruzzo"},
    {"nome": "San Buono - Frentani", "lat": 41.981, "lon": 14.571, "tipo": "quercia", "quota": 480, "regione": "Abruzzo"},
    {"nome": "Casoli - Lecceta Colleforeste", "lat": 42.120, "lon": 14.290, "tipo": "leccio", "quota": 350, "regione": "Abruzzo"},
    {"nome": "Fossacesia - collina Trabocchi", "lat": 42.250, "lon": 14.450, "tipo": "quercia", "quota": 80, "regione": "Abruzzo"},
    {"nome": "Casalbordino - collina Osento", "lat": 42.150, "lon": 14.590, "tipo": "quercia", "quota": 200, "regione": "Abruzzo"},
    {"nome": "Scerni - querceti", "lat": 42.110, "lon": 14.570, "tipo": "quercia", "quota": 250, "regione": "Abruzzo"},
    {"nome": "Paglieta - boschi Sangro", "lat": 42.160, "lon": 14.430, "tipo": "quercia", "quota": 200, "regione": "Abruzzo"},
    {"nome": "Cupello - hinterland Vasto", "lat": 42.050, "lon": 14.620, "tipo": "quercia", "quota": 220, "regione": "Abruzzo"},
    {"nome": "Villalfonsina - Osento", "lat": 42.160, "lon": 14.570, "tipo": "quercia", "quota": 150, "regione": "Abruzzo"},
    {"nome": "Lanciano - colline boschive", "lat": 42.218, "lon": 14.390, "tipo": "quercia", "quota": 280, "regione": "Abruzzo"},
    {"nome": "Vasto - collina Penna", "lat": 42.110, "lon": 14.708, "tipo": "quercia", "quota": 140, "regione": "Abruzzo"},
    {"nome": "Casalanguida - colline", "lat": 42.039, "lon": 14.488, "tipo": "quercia", "quota": 520, "regione": "Abruzzo"},
    {"nome": "Furci - Frentani", "lat": 41.950, "lon": 14.580, "tipo": "quercia", "quota": 550, "regione": "Abruzzo"},
    {"nome": "Montazzoli - Alto Vastese", "lat": 41.983, "lon": 14.450, "tipo": "castagno", "quota": 850, "regione": "Abruzzo"},
    {"nome": "Rosello - Abetina", "lat": 41.858, "lon": 14.350, "tipo": "faggio", "quota": 950, "regione": "Abruzzo"},
    {"nome": "Lentella - colline Trigno", "lat": 41.997, "lon": 14.677, "tipo": "quercia", "quota": 400, "regione": "Abruzzo"},
    {"nome": "Colline Vestine - Penne", "lat": 42.455, "lon": 13.930, "tipo": "quercia", "quota": 450, "regione": "Abruzzo"},
    {"nome": "Carsoli - Oricola / Pereto", "lat": 42.049, "lon": 13.039, "tipo": "faggio", "quota": 900, "regione": "Abruzzo"},
    {"nome": "Tagliacozzo - Cappadocia", "lat": 42.008, "lon": 13.280, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Marsica - Cocullo", "lat": 42.033, "lon": 13.775, "tipo": "faggio", "quota": 900, "regione": "Abruzzo"},
    {"nome": "Teramo collinare - Civitella del Tronto", "lat": 42.773, "lon": 13.675, "tipo": "quercia", "quota": 550, "regione": "Abruzzo"},
    {"nome": "Teramo collinare - Campli", "lat": 42.726, "lon": 13.686, "tipo": "quercia", "quota": 500, "regione": "Abruzzo"},

    # ===================== MOLISE =====================
    {"nome": "Capracotta - faggete", "lat": 41.834, "lon": 14.265, "tipo": "faggio", "quota": 1420, "regione": "Molise"},
    {"nome": "Pescopennataro - Abeti Soprani", "lat": 41.861, "lon": 14.294, "tipo": "faggio", "quota": 1450, "regione": "Molise"},
    {"nome": "Vastogirardi - Bosco Pennataro", "lat": 41.749, "lon": 14.197, "tipo": "faggio", "quota": 1100, "regione": "Molise"},
    {"nome": "Collemeluccio - Selvapiana", "lat": 41.718, "lon": 14.350, "tipo": "faggio", "quota": 900, "regione": "Molise"},
    {"nome": "Montedimezzo", "lat": 41.775, "lon": 14.261, "tipo": "faggio", "quota": 1000, "regione": "Molise"},
    {"nome": "Agnone - Alto Molise", "lat": 41.810, "lon": 14.379, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Carovilli", "lat": 41.714, "lon": 14.296, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Frosolone - Montagnola", "lat": 41.601, "lon": 14.449, "tipo": "faggio", "quota": 1100, "regione": "Molise"},
    {"nome": "Mainarde - Castel San Vincenzo", "lat": 41.656, "lon": 14.061, "tipo": "faggio", "quota": 1200, "regione": "Molise"},
    {"nome": "Pizzone - Mainarde", "lat": 41.667, "lon": 14.034, "tipo": "faggio", "quota": 1300, "regione": "Molise"},
    {"nome": "Rocchetta a Volturno", "lat": 41.629, "lon": 14.091, "tipo": "faggio", "quota": 900, "regione": "Molise"},
    {"nome": "Cerro al Volturno", "lat": 41.657, "lon": 14.102, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "Bojano - versante Matese", "lat": 41.485, "lon": 14.473, "tipo": "faggio", "quota": 900, "regione": "Molise"},
    {"nome": "Guardiaregia - Matese", "lat": 41.436, "lon": 14.504, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "San Massimo - Matese", "lat": 41.490, "lon": 14.410, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Cantalupo nel Sannio", "lat": 41.523, "lon": 14.394, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Campitello Matese", "lat": 41.463, "lon": 14.394, "tipo": "faggio", "quota": 1450, "regione": "Molise"},
    {"nome": "Monte Miletto", "lat": 41.452, "lon": 14.350, "tipo": "faggio", "quota": 1700, "regione": "Molise"},
    {"nome": "Roccamandolfi - Matese", "lat": 41.493, "lon": 14.351, "tipo": "faggio", "quota": 1400, "regione": "Molise"},
    {"nome": "Pietrabbondante", "lat": 41.748, "lon": 14.385, "tipo": "castagno", "quota": 800, "regione": "Molise"},
    {"nome": "San Pietro Avellana", "lat": 41.792, "lon": 14.183, "tipo": "faggio", "quota": 960, "regione": "Molise"},
    {"nome": "Castel del Giudice", "lat": 41.856, "lon": 14.232, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "Isernia - Pineta e colline", "lat": 41.594, "lon": 14.231, "tipo": "quercia", "quota": 450, "regione": "Molise"},
    {"nome": "Campobasso - colline boschive", "lat": 41.560, "lon": 14.660, "tipo": "quercia", "quota": 600, "regione": "Molise"},
    {"nome": "Capracotta - Prato Gentile", "lat": 41.850, "lon": 14.280, "tipo": "faggio", "quota": 1600, "regione": "Molise"},
    {"nome": "Monte Capraro", "lat": 41.820, "lon": 14.250, "tipo": "faggio", "quota": 1700, "regione": "Molise"},
    {"nome": "Monte Campo", "lat": 41.800, "lon": 14.310, "tipo": "faggio", "quota": 1740, "regione": "Molise"},
    {"nome": "Pescolanciano", "lat": 41.679, "lon": 14.248, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "Roccasicura", "lat": 41.697, "lon": 14.236, "tipo": "faggio", "quota": 750, "regione": "Molise"},
    {"nome": "Rionero Sannitico", "lat": 41.713, "lon": 14.140, "tipo": "faggio", "quota": 1050, "regione": "Molise"},
    {"nome": "Forlì del Sannio", "lat": 41.695, "lon": 14.180, "tipo": "faggio", "quota": 600, "regione": "Molise"},
    {"nome": "Acquaviva d'Isernia", "lat": 41.673, "lon": 14.148, "tipo": "faggio", "quota": 750, "regione": "Molise"},
    {"nome": "Sessano del Molise", "lat": 41.639, "lon": 14.328, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "Chiauci", "lat": 41.677, "lon": 14.385, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Civitanova del Sannio", "lat": 41.667, "lon": 14.393, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Bagnoli del Trigno", "lat": 41.703, "lon": 14.451, "tipo": "castagno", "quota": 750, "regione": "Molise"},
    {"nome": "Salcito", "lat": 41.726, "lon": 14.511, "tipo": "castagno", "quota": 700, "regione": "Molise"},
    {"nome": "Trivento", "lat": 41.776, "lon": 14.546, "tipo": "quercia", "quota": 600, "regione": "Molise"},
    {"nome": "Poggio Sannita", "lat": 41.779, "lon": 14.584, "tipo": "castagno", "quota": 700, "regione": "Molise"},
    {"nome": "Belmonte del Sannio", "lat": 41.824, "lon": 14.423, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Castelverrino", "lat": 41.766, "lon": 14.397, "tipo": "castagno", "quota": 700, "regione": "Molise"},
    {"nome": "Longano", "lat": 41.522, "lon": 14.247, "tipo": "faggio", "quota": 700, "regione": "Molise"},
    {"nome": "Castelpizzuto", "lat": 41.519, "lon": 14.292, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Santa Maria del Molise", "lat": 41.553, "lon": 14.367, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Macchiagodena", "lat": 41.560, "lon": 14.409, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Sant'Elena Sannita", "lat": 41.575, "lon": 14.472, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "Duronia", "lat": 41.659, "lon": 14.460, "tipo": "faggio", "quota": 900, "regione": "Molise"},
    {"nome": "Torella del Sannio", "lat": 41.640, "lon": 14.521, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Casalciprano", "lat": 41.580, "lon": 14.529, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Spinete", "lat": 41.544, "lon": 14.488, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    {"nome": "San Polo Matese", "lat": 41.460, "lon": 14.495, "tipo": "faggio", "quota": 750, "regione": "Molise"},
    {"nome": "Campochiaro", "lat": 41.448, "lon": 14.507, "tipo": "faggio", "quota": 750, "regione": "Molise"},
    {"nome": "Sepino", "lat": 41.408, "lon": 14.617, "tipo": "faggio", "quota": 700, "regione": "Molise"},
    {"nome": "Sassinoro", "lat": 41.375, "lon": 14.665, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Cercemaggiore", "lat": 41.461, "lon": 14.724, "tipo": "castagno", "quota": 800, "regione": "Molise"},
    {"nome": "Riccia", "lat": 41.483, "lon": 14.836, "tipo": "castagno", "quota": 700, "regione": "Molise"},
    {"nome": "Campolieto", "lat": 41.633, "lon": 14.767, "tipo": "castagno", "quota": 700, "regione": "Molise"},
    {"nome": "Castropignano", "lat": 41.619, "lon": 14.559, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Filignano", "lat": 41.545, "lon": 14.057, "tipo": "faggio", "quota": 650, "regione": "Molise"},
    {"nome": "Scapoli", "lat": 41.615, "lon": 14.059, "tipo": "faggio", "quota": 650, "regione": "Molise"},
    {"nome": "Colli a Volturno", "lat": 41.599, "lon": 14.103, "tipo": "quercia", "quota": 450, "regione": "Molise"},
    {"nome": "Montaquila", "lat": 41.562, "lon": 14.119, "tipo": "quercia", "quota": 450, "regione": "Molise"},
    {"nome": "Venafro - monti", "lat": 41.483, "lon": 14.045, "tipo": "quercia", "quota": 500, "regione": "Molise"},
    {"nome": "Conca Casale", "lat": 41.496, "lon": 14.007, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Miranda", "lat": 41.643, "lon": 14.247, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Pesche", "lat": 41.617, "lon": 14.278, "tipo": "castagno", "quota": 650, "regione": "Molise"},
    # Boschi interni Molise mancanti (Alto Molise, Montagnola, Biferno, Fortore)
    {"nome": "Pesche - Monte Totila", "lat": 41.630, "lon": 14.300, "tipo": "faggio", "quota": 950, "regione": "Molise"},
    {"nome": "Collemeluccio - abetine", "lat": 41.705, "lon": 14.347, "tipo": "abete_bianco", "quota": 950, "regione": "Molise"},
    {"nome": "Selvapiana - Castiglione La Cocozza", "lat": 41.730, "lon": 14.320, "tipo": "faggio", "quota": 1000, "regione": "Molise"},
    {"nome": "Monte Miglio - Pennataro", "lat": 41.770, "lon": 14.210, "tipo": "faggio", "quota": 1200, "regione": "Molise"},
    {"nome": "Monte Cavallerizzo", "lat": 41.760, "lon": 14.230, "tipo": "faggio", "quota": 1150, "regione": "Molise"},
    {"nome": "Monte Castelbarone", "lat": 41.845, "lon": 14.250, "tipo": "faggio", "quota": 1300, "regione": "Molise"},
    {"nome": "Sorgenti del Verde - Pescopennataro", "lat": 41.855, "lon": 14.270, "tipo": "abete_bianco", "quota": 1400, "regione": "Molise"},
    {"nome": "Isola della Fonte della Luna", "lat": 41.790, "lon": 14.220, "tipo": "faggio", "quota": 1100, "regione": "Molise"},
    {"nome": "Bosco Vallazzuna", "lat": 41.780, "lon": 14.300, "tipo": "faggio", "quota": 950, "regione": "Molise"},
    {"nome": "Pescolanciano - cerrete MaB", "lat": 41.680, "lon": 14.248, "tipo": "quercia", "quota": 800, "regione": "Molise"},
    {"nome": "Cerreto sul Volturno", "lat": 41.659, "lon": 14.102, "tipo": "quercia", "quota": 600, "regione": "Molise"},
    {"nome": "Montagnola Molisana - Frosolone est", "lat": 41.590, "lon": 14.480, "tipo": "faggio", "quota": 1200, "regione": "Molise"},
    {"nome": "Montagnola - Civitanova / Chiauci", "lat": 41.660, "lon": 14.400, "tipo": "faggio", "quota": 900, "regione": "Molise"},
    {"nome": "Roccavivara - faggete interne", "lat": 41.833, "lon": 14.598, "tipo": "faggio", "quota": 750, "regione": "Molise"},
    {"nome": "Castelmauro - colline interne", "lat": 41.830, "lon": 14.711, "tipo": "quercia", "quota": 700, "regione": "Molise"},
    {"nome": "Montefalcone nel Sannio - Selva", "lat": 41.755, "lon": 14.638, "tipo": "quercia", "quota": 750, "regione": "Molise"},
    {"nome": "Monte Mauro - Selva di Montefalcone", "lat": 41.740, "lon": 14.620, "tipo": "quercia", "quota": 800, "regione": "Molise"},
    {"nome": "Bosco Cerreto - Molise interno", "lat": 41.620, "lon": 14.700, "tipo": "quercia", "quota": 650, "regione": "Molise"},
    {"nome": "Bosco Ficarola", "lat": 41.640, "lon": 14.740, "tipo": "quercia", "quota": 600, "regione": "Molise"},
    {"nome": "Bosco Difesa - Ripabottoni", "lat": 41.688, "lon": 14.809, "tipo": "quercia", "quota": 650, "regione": "Molise"},
    {"nome": "Boschi di Castellino e Morrone", "lat": 41.650, "lon": 14.770, "tipo": "quercia", "quota": 600, "regione": "Molise"},
    {"nome": "Morrone del Sannio", "lat": 41.712, "lon": 14.776, "tipo": "quercia", "quota": 650, "regione": "Molise"},
    {"nome": "Castellino del Biferno", "lat": 41.702, "lon": 14.732, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Lucito", "lat": 41.632, "lon": 14.687, "tipo": "quercia", "quota": 500, "regione": "Molise"},
    {"nome": "Petrella Tifernina", "lat": 41.692, "lon": 14.697, "tipo": "quercia", "quota": 450, "regione": "Molise"},
    {"nome": "Limosano", "lat": 41.676, "lon": 14.623, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Civitacampomarano", "lat": 41.780, "lon": 14.689, "tipo": "quercia", "quota": 500, "regione": "Molise"},
    {"nome": "Oratino", "lat": 41.586, "lon": 14.584, "tipo": "quercia", "quota": 500, "regione": "Molise"},
    {"nome": "Busso", "lat": 41.558, "lon": 14.561, "tipo": "quercia", "quota": 650, "regione": "Molise"},
    {"nome": "Baranello", "lat": 41.526, "lon": 14.560, "tipo": "castagno", "quota": 640, "regione": "Molise"},
    {"nome": "Vinchiaturo - Sella / Monte Vairano", "lat": 41.493, "lon": 14.592, "tipo": "quercia", "quota": 650, "regione": "Molise"},
    {"nome": "San Giuliano del Sannio", "lat": 41.456, "lon": 14.641, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Guardiaregia - Oasi WWF", "lat": 41.436, "lon": 14.543, "tipo": "faggio", "quota": 900, "regione": "Molise"},
    {"nome": "Casacalenda - boschi Fortore", "lat": 41.738, "lon": 14.847, "tipo": "quercia", "quota": 650, "regione": "Molise"},
    {"nome": "Bonefro", "lat": 41.705, "lon": 14.933, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Sant'Elia a Pianisi", "lat": 41.622, "lon": 14.875, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Ripabottoni", "lat": 41.688, "lon": 14.809, "tipo": "quercia", "quota": 620, "regione": "Molise"},
    {"nome": "Colletorto", "lat": 41.662, "lon": 14.968, "tipo": "quercia", "quota": 500, "regione": "Molise"},
    {"nome": "San Giovanni in Galdo", "lat": 41.590, "lon": 14.750, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Toro", "lat": 41.573, "lon": 14.762, "tipo": "quercia", "quota": 500, "regione": "Molise"},
    {"nome": "Jelsi", "lat": 41.518, "lon": 14.798, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Gildone", "lat": 41.508, "lon": 14.740, "tipo": "quercia", "quota": 550, "regione": "Molise"},
    {"nome": "Ferrazzano", "lat": 41.530, "lon": 14.672, "tipo": "quercia", "quota": 700, "regione": "Molise"},
    {"nome": "Mirabello Sannitico", "lat": 41.515, "lon": 14.673, "tipo": "quercia", "quota": 600, "regione": "Molise"},
    {"nome": "Campodipietra", "lat": 41.557, "lon": 14.743, "tipo": "quercia", "quota": 500, "regione": "Molise"},
    {"nome": "Cantalupo nel Sannio - faggete", "lat": 41.523, "lon": 14.394, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Valle Porcina - Vandra", "lat": 41.620, "lon": 14.080, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "Monte Sammucro - Corno", "lat": 41.590, "lon": 13.980, "tipo": "faggio", "quota": 1100, "regione": "Molise"},
    {"nome": "Monte Cesima", "lat": 41.520, "lon": 13.990, "tipo": "faggio", "quota": 1000, "regione": "Molise"},

    # ===================== LAZIO =====================
    {"nome": "Terminillo", "lat": 42.473, "lon": 12.997, "tipo": "faggio", "quota": 1500, "regione": "Lazio"},
    {"nome": "Terminillo - Pian de Valli", "lat": 42.466, "lon": 12.987, "tipo": "faggio", "quota": 1600, "regione": "Lazio"},
    {"nome": "Monti della Laga - Amatrice", "lat": 42.628, "lon": 13.290, "tipo": "faggio", "quota": 1300, "regione": "Lazio"},
    {"nome": "Monti della Laga - Accumoli", "lat": 42.694, "lon": 13.247, "tipo": "faggio", "quota": 1200, "regione": "Lazio"},
    {"nome": "Monti Reatini - Leonessa", "lat": 42.569, "lon": 12.960, "tipo": "faggio", "quota": 1100, "regione": "Lazio"},
    {"nome": "Monti Reatini - Cittareale", "lat": 42.617, "lon": 13.158, "tipo": "faggio", "quota": 1000, "regione": "Lazio"},
    {"nome": "Simbruini - Vallepietra", "lat": 41.926, "lon": 13.231, "tipo": "faggio", "quota": 1200, "regione": "Lazio"},
    {"nome": "Simbruini - Subiaco", "lat": 41.925, "lon": 13.093, "tipo": "faggio", "quota": 900, "regione": "Lazio"},
    {"nome": "Simbruini - Camerata Nuova", "lat": 42.018, "lon": 13.106, "tipo": "faggio", "quota": 1100, "regione": "Lazio"},
    {"nome": "Simbruini - Filettino", "lat": 41.883, "lon": 13.325, "tipo": "faggio", "quota": 1100, "regione": "Lazio"},
    {"nome": "Ernici - Guarcino", "lat": 41.799, "lon": 13.314, "tipo": "faggio", "quota": 1000, "regione": "Lazio"},
    {"nome": "Ernici - Fiuggi boschi", "lat": 41.797, "lon": 13.220, "tipo": "faggio", "quota": 800, "regione": "Lazio"},
    {"nome": "Monti Lucretili - Licenza", "lat": 42.074, "lon": 12.900, "tipo": "castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Monti Lucretili - Palombara", "lat": 42.068, "lon": 12.768, "tipo": "quercia", "quota": 600, "regione": "Lazio"},
    {"nome": "Monti Prenestini - Capranica Prenestina", "lat": 41.863, "lon": 13.001, "tipo": "castagno", "quota": 850, "regione": "Lazio"},
    {"nome": "Castelli Romani - Nemi / Velletri", "lat": 41.718, "lon": 12.714, "tipo": "quercia", "quota": 600, "regione": "Lazio"},
    {"nome": "Castelli Romani - Monte Cavo", "lat": 41.750, "lon": 12.717, "tipo": "castagno", "quota": 750, "regione": "Lazio"},
    {"nome": "Monti Lepini - Carpineto Romano", "lat": 41.605, "lon": 13.085, "tipo": "faggio", "quota": 900, "regione": "Lazio"},
    {"nome": "Monti Lepini - Norma", "lat": 41.585, "lon": 12.972, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Monti Ausoni - Sonnino", "lat": 41.414, "lon": 13.244, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Monti Aurunci - Maranola", "lat": 41.290, "lon": 13.627, "tipo": "castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Monti Aurunci - Itri boschi", "lat": 41.290, "lon": 13.530, "tipo": "quercia", "quota": 450, "regione": "Lazio"},
    {"nome": "Cimini - Soriano nel Cimino", "lat": 42.418, "lon": 12.234, "tipo": "castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Cimini - Viterbo faggete", "lat": 42.400, "lon": 12.180, "tipo": "faggio", "quota": 800, "regione": "Lazio"},
    {"nome": "Monte Amiata laziale / Alto Lazio", "lat": 42.700, "lon": 11.850, "tipo": "faggio", "quota": 900, "regione": "Lazio"},
    {"nome": "Monti della Tolfa", "lat": 42.150, "lon": 11.950, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Monti Sabini - Poggio Moiano", "lat": 42.200, "lon": 12.880, "tipo": "quercia", "quota": 600, "regione": "Lazio"},
    {"nome": "Sabina - Tarano / San Polo", "lat": 42.357, "lon": 12.597, "tipo": "quercia", "quota": 280, "regione": "Lazio"},
    {"nome": "Sabina - Montebuono", "lat": 42.368, "lon": 12.594, "tipo": "quercia", "quota": 300, "regione": "Lazio"},
    {"nome": "Sabina - Collevecchio boschi", "lat": 42.333, "lon": 12.553, "tipo": "quercia", "quota": 250, "regione": "Lazio"},
    {"nome": "Sabina - Torri in Sabina", "lat": 42.353, "lon": 12.638, "tipo": "quercia", "quota": 400, "regione": "Lazio"},
    {"nome": "Sabina - Casperia / Roccantica", "lat": 42.330, "lon": 12.672, "tipo": "castagno", "quota": 500, "regione": "Lazio"},
    {"nome": "Sabina - Cottanello", "lat": 42.406, "lon": 12.685, "tipo": "quercia", "quota": 550, "regione": "Lazio"},
    {"nome": "Sabina - Magliano Sabina", "lat": 42.361, "lon": 12.483, "tipo": "quercia", "quota": 220, "regione": "Lazio"},
    {"nome": "Sabina - Stimigliano / Selci", "lat": 42.300, "lon": 12.563, "tipo": "quercia", "quota": 220, "regione": "Lazio"},
    {"nome": "Sabina - Poggio Mirteto", "lat": 42.268, "lon": 12.688, "tipo": "quercia", "quota": 350, "regione": "Lazio"},
    {"nome": "Sabina - Montopoli di Sabina", "lat": 42.247, "lon": 12.692, "tipo": "quercia", "quota": 300, "regione": "Lazio"},
    {"nome": "Sabina - Fara in Sabina / Farfa", "lat": 42.209, "lon": 12.718, "tipo": "quercia", "quota": 250, "regione": "Lazio"},
    {"nome": "Sabina - Poggio Catino", "lat": 42.293, "lon": 12.698, "tipo": "castagno", "quota": 450, "regione": "Lazio"},
    {"nome": "Sabina - Toffia", "lat": 42.215, "lon": 12.755, "tipo": "quercia", "quota": 280, "regione": "Lazio"},
    {"nome": "Riserva Tevere-Farfa - Nazzano", "lat": 42.229, "lon": 12.611, "tipo": "quercia", "quota": 80, "regione": "Lazio"},
    {"nome": "Monte Soratte - Sant'Oreste", "lat": 42.233, "lon": 12.525, "tipo": "quercia", "quota": 400, "regione": "Lazio"},
    {"nome": "Sabina - Vacone / Configni", "lat": 42.385, "lon": 12.645, "tipo": "quercia", "quota": 450, "regione": "Lazio"},
    {"nome": "Sabina - Greccio boschi", "lat": 42.455, "lon": 12.755, "tipo": "quercia", "quota": 550, "regione": "Lazio"},
    {"nome": "Sabina - Contigliano", "lat": 42.411, "lon": 12.766, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Parco dei Monti Simbruini - Cervara", "lat": 41.988, "lon": 13.067, "tipo": "faggio", "quota": 1050, "regione": "Lazio"},
    {"nome": "Terminillo - Micigliano", "lat": 42.452, "lon": 13.053, "tipo": "faggio", "quota": 900, "regione": "Lazio"},
    {"nome": "Terminillo - Posta", "lat": 42.525, "lon": 13.097, "tipo": "faggio", "quota": 700, "regione": "Lazio"},
    {"nome": "Monti Reatini - Antrodoco", "lat": 42.416, "lon": 13.079, "tipo": "faggio", "quota": 750, "regione": "Lazio"},
    {"nome": "Monti Reatini - Morro Reatino", "lat": 42.449, "lon": 12.834, "tipo": "castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Monti Reatini - Rivodutri", "lat": 42.517, "lon": 12.856, "tipo": "quercia", "quota": 550, "regione": "Lazio"},
    {"nome": "Salto-Cicolano - Fiamignano", "lat": 42.268, "lon": 13.126, "tipo": "faggio", "quota": 1000, "regione": "Lazio"},
    {"nome": "Salto-Cicolano - Pescorocchiano", "lat": 42.207, "lon": 13.146, "tipo": "faggio", "quota": 850, "regione": "Lazio"},
    {"nome": "Salto-Cicolano - Petrella Salto", "lat": 42.296, "lon": 13.068, "tipo": "faggio", "quota": 800, "regione": "Lazio"},
    {"nome": "Salto-Cicolano - Varco Sabino", "lat": 42.240, "lon": 13.019, "tipo": "faggio", "quota": 750, "regione": "Lazio"},
    {"nome": "Sabina - Orvinio", "lat": 42.133, "lon": 12.993, "tipo": "castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Sabina - Collalto Sabino", "lat": 42.226, "lon": 13.049, "tipo": "faggio", "quota": 950, "regione": "Lazio"},
    {"nome": "Sabina - Turania", "lat": 42.139, "lon": 13.008, "tipo": "castagno", "quota": 750, "regione": "Lazio"},
    {"nome": "Lucretili - Percile", "lat": 42.095, "lon": 12.905, "tipo": "quercia", "quota": 600, "regione": "Lazio"},
    {"nome": "Lucretili - Orvinio / Pozzaglia", "lat": 42.170, "lon": 12.964, "tipo": "castagno", "quota": 750, "regione": "Lazio"},
    {"nome": "Lucretili - Monte Gennaro", "lat": 42.055, "lon": 12.833, "tipo": "castagno", "quota": 1000, "regione": "Lazio"},
    {"nome": "Lucretili - Monteflavio", "lat": 42.109, "lon": 12.831, "tipo": "castagno", "quota": 850, "regione": "Lazio"},
    {"nome": "Simbruini - Monte Livata", "lat": 41.950, "lon": 13.120, "tipo": "faggio", "quota": 1400, "regione": "Lazio"},
    {"nome": "Simbruini - Jenne", "lat": 41.889, "lon": 13.169, "tipo": "faggio", "quota": 850, "regione": "Lazio"},
    {"nome": "Simbruini - Trevi nel Lazio", "lat": 41.863, "lon": 13.253, "tipo": "faggio", "quota": 800, "regione": "Lazio"},
    {"nome": "Simbruini - Altipiani di Arcinazzo", "lat": 41.879, "lon": 13.114, "tipo": "faggio", "quota": 850, "regione": "Lazio"},
    {"nome": "Simbruini - Rocca di Botte", "lat": 42.026, "lon": 13.068, "tipo": "faggio", "quota": 750, "regione": "Lazio"},
    {"nome": "Ernici - Collepardo", "lat": 41.765, "lon": 13.368, "tipo": "faggio", "quota": 800, "regione": "Lazio"},
    {"nome": "Ernici - Vico nel Lazio", "lat": 41.777, "lon": 13.341, "tipo": "faggio", "quota": 700, "regione": "Lazio"},
    {"nome": "Ernici - Veroli", "lat": 41.691, "lon": 13.418, "tipo": "quercia", "quota": 600, "regione": "Lazio"},
    {"nome": "Ernici - Alatri", "lat": 41.726, "lon": 13.342, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Valle di Comino - San Donato", "lat": 41.708, "lon": 13.813, "tipo": "faggio", "quota": 750, "regione": "Lazio"},
    {"nome": "Valle di Comino - Settefrati", "lat": 41.670, "lon": 13.851, "tipo": "faggio", "quota": 800, "regione": "Lazio"},
    {"nome": "Valle di Comino - Picinisco", "lat": 41.647, "lon": 13.868, "tipo": "faggio", "quota": 750, "regione": "Lazio"},
    {"nome": "Valle di Comino - Villa Latina", "lat": 41.615, "lon": 13.836, "tipo": "faggio", "quota": 600, "regione": "Lazio"},
    {"nome": "Valle di Comino - Atina", "lat": 41.620, "lon": 13.802, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Valle di Comino - Alvito", "lat": 41.690, "lon": 13.744, "tipo": "faggio", "quota": 500, "regione": "Lazio"},
    {"nome": "Valle di Comino - Pescosolido", "lat": 41.749, "lon": 13.657, "tipo": "faggio", "quota": 550, "regione": "Lazio"},
    {"nome": "Valle di Comino - Campoli Appennino", "lat": 41.736, "lon": 13.683, "tipo": "faggio", "quota": 650, "regione": "Lazio"},
    {"nome": "Mainarde laziali - Vallerotonda", "lat": 41.551, "lon": 13.911, "tipo": "faggio", "quota": 700, "regione": "Lazio"},
    {"nome": "Mainarde laziali - San Biagio Saracinisco", "lat": 41.613, "lon": 13.932, "tipo": "faggio", "quota": 850, "regione": "Lazio"},
    {"nome": "Cassinate - Terelle", "lat": 41.552, "lon": 13.778, "tipo": "faggio", "quota": 900, "regione": "Lazio"},
    {"nome": "Prenestini - Capranica / Piglio", "lat": 41.828, "lon": 13.144, "tipo": "castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Lepini - Segni", "lat": 41.690, "lon": 13.016, "tipo": "castagno", "quota": 650, "regione": "Lazio"},
    {"nome": "Lepini - Montelanico", "lat": 41.651, "lon": 13.040, "tipo": "faggio", "quota": 700, "regione": "Lazio"},
    {"nome": "Lepini - Bassiano", "lat": 41.549, "lon": 13.088, "tipo": "faggio", "quota": 550, "regione": "Lazio"},
    {"nome": "Lepini - Sezze / Sermoneta", "lat": 41.498, "lon": 13.060, "tipo": "quercia", "quota": 250, "regione": "Lazio"},
    {"nome": "Ausoni - Priverno", "lat": 41.472, "lon": 13.181, "tipo": "quercia", "quota": 150, "regione": "Lazio"},
    {"nome": "Ausoni - Prossedi / Roccagorga", "lat": 41.500, "lon": 13.236, "tipo": "quercia", "quota": 300, "regione": "Lazio"},
    {"nome": "Ausoni - Lenola", "lat": 41.339, "lon": 13.359, "tipo": "quercia", "quota": 450, "regione": "Lazio"},
    {"nome": "Ausoni - Campodimele", "lat": 41.388, "lon": 13.386, "tipo": "castagno", "quota": 650, "regione": "Lazio"},
    {"nome": "Aurunci - Spigno Saturnia", "lat": 41.297, "lon": 13.735, "tipo": "quercia", "quota": 200, "regione": "Lazio"},
    {"nome": "Aurunci - Esperia", "lat": 41.385, "lon": 13.685, "tipo": "quercia", "quota": 350, "regione": "Lazio"},
    {"nome": "Cimini - Caprarola", "lat": 42.327, "lon": 12.237, "tipo": "castagno", "quota": 650, "regione": "Lazio"},
    {"nome": "Cimini - Canepina", "lat": 42.383, "lon": 12.223, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Cimini - Ronciglione", "lat": 42.289, "lon": 12.197, "tipo": "quercia", "quota": 450, "regione": "Lazio"},
    {"nome": "Cimini - Monte Cimino", "lat": 42.408, "lon": 12.203, "tipo": "faggio", "quota": 1000, "regione": "Lazio"},
    {"nome": "Alto Lazio - Acquapendente", "lat": 42.744, "lon": 11.865, "tipo": "quercia", "quota": 400, "regione": "Lazio"},
    {"nome": "Alto Lazio - San Lorenzo Nuovo", "lat": 42.687, "lon": 11.907, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Selva del Lamone - Farnese", "lat": 42.549, "lon": 11.726, "tipo": "quercia", "quota": 350, "regione": "Lazio"},
    {"nome": "Tolfa - Allumiere", "lat": 42.157, "lon": 11.904, "tipo": "quercia", "quota": 500, "regione": "Lazio"},
    {"nome": "Bracciano - Manziana / Oriolo", "lat": 42.130, "lon": 12.127, "tipo": "quercia", "quota": 400, "regione": "Lazio"},
    {"nome": "Veio - Sacrofano / Formello", "lat": 42.106, "lon": 12.345, "tipo": "quercia", "quota": 250, "regione": "Lazio"},
    {"nome": "Castelli Romani - Rocca di Papa", "lat": 41.766, "lon": 12.710, "tipo": "castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Castelli Romani - Tuscolo / Monte Porzio", "lat": 41.807, "lon": 12.716, "tipo": "quercia", "quota": 600, "regione": "Lazio"},

    # ===================== CAMPANIA =====================
    {"nome": "Matese - Piedimonte alto", "lat": 41.355, "lon": 14.371, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Lago del Matese", "lat": 41.410, "lon": 14.400, "tipo": "faggio", "quota": 1010, "regione": "Campania"},
    {"nome": "San Gregorio Matese", "lat": 41.385, "lon": 14.380, "tipo": "faggio", "quota": 1100, "regione": "Campania"},
    {"nome": "Gallo Matese", "lat": 41.465, "lon": 14.225, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Letino", "lat": 41.450, "lon": 14.250, "tipo": "faggio", "quota": 1000, "regione": "Campania"},
    {"nome": "Cusano Mutri - Mutria", "lat": 41.330, "lon": 14.520, "tipo": "faggio", "quota": 1200, "regione": "Campania"},
    {"nome": "Cusano Mutri - Piano Melaina", "lat": 41.345, "lon": 14.505, "tipo": "faggio", "quota": 1100, "regione": "Campania"},
    {"nome": "Bocca della Selva", "lat": 41.408, "lon": 14.355, "tipo": "faggio", "quota": 1400, "regione": "Campania"},
    {"nome": "Piedimonte Matese - boschi", "lat": 41.357, "lon": 14.373, "tipo": "faggio", "quota": 700, "regione": "Campania"},
    {"nome": "Castello del Matese - faggete", "lat": 41.375, "lon": 14.390, "tipo": "faggio", "quota": 1050, "regione": "Campania"},
    {"nome": "San Potito Sannitico", "lat": 41.338, "lon": 14.392, "tipo": "faggio", "quota": 550, "regione": "Campania"},
    {"nome": "Gioia Sannitica - Matese", "lat": 41.300, "lon": 14.347, "tipo": "quercia", "quota": 500, "regione": "Campania"},
    {"nome": "Alife - piede Matese", "lat": 41.326, "lon": 14.334, "tipo": "quercia", "quota": 200, "regione": "Campania"},
    {"nome": "Capriati a Volturno", "lat": 41.468, "lon": 14.146, "tipo": "faggio", "quota": 450, "regione": "Campania"},
    {"nome": "Fontegreca", "lat": 41.462, "lon": 14.184, "tipo": "faggio", "quota": 850, "regione": "Campania"},
    {"nome": "Prata Sannita", "lat": 41.433, "lon": 14.203, "tipo": "faggio", "quota": 370, "regione": "Campania"},
    {"nome": "Valle Agricola", "lat": 41.425, "lon": 14.255, "tipo": "faggio", "quota": 700, "regione": "Campania"},
    {"nome": "Gallo Matese - lago", "lat": 41.466, "lon": 14.225, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Letino - lago", "lat": 41.453, "lon": 14.255, "tipo": "faggio", "quota": 1000, "regione": "Campania"},
    {"nome": "Roccamonfina - cratere", "lat": 41.295, "lon": 13.982, "tipo": "castagno", "quota": 850, "regione": "Campania"},
    {"nome": "Roccamonfina - Monte Santa Croce", "lat": 41.305, "lon": 13.968, "tipo": "castagno", "quota": 1000, "regione": "Campania"},
    {"nome": "Roccamonfina - castagneti", "lat": 41.288, "lon": 13.995, "tipo": "castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Conca della Campania", "lat": 41.332, "lon": 13.991, "tipo": "quercia", "quota": 520, "regione": "Campania"},
    {"nome": "Galluccio - Roccamonfina", "lat": 41.352, "lon": 13.954, "tipo": "quercia", "quota": 550, "regione": "Campania"},
    {"nome": "Tora e Piccilli", "lat": 41.337, "lon": 14.025, "tipo": "quercia", "quota": 500, "regione": "Campania"},
    {"nome": "Marzano Appio", "lat": 41.318, "lon": 14.045, "tipo": "quercia", "quota": 480, "regione": "Campania"},
    {"nome": "Teano - colline boschive", "lat": 41.251, "lon": 14.067, "tipo": "quercia", "quota": 280, "regione": "Campania"},
    {"nome": "Sessa Aurunca - versante Roccamonfina", "lat": 41.255, "lon": 13.955, "tipo": "quercia", "quota": 400, "regione": "Campania"},
    {"nome": "Mignano Monte Lungo", "lat": 41.405, "lon": 13.985, "tipo": "quercia", "quota": 180, "regione": "Campania"},
    {"nome": "Presenzano", "lat": 41.374, "lon": 14.088, "tipo": "quercia", "quota": 220, "regione": "Campania"},
    {"nome": "San Pietro Infine", "lat": 41.447, "lon": 13.960, "tipo": "quercia", "quota": 180, "regione": "Campania"},
    {"nome": "Pietraroja", "lat": 41.347, "lon": 14.550, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Castello del Matese", "lat": 41.368, "lon": 14.378, "tipo": "faggio", "quota": 800, "regione": "Campania"},
    {"nome": "Taburno - Camposauro", "lat": 41.100, "lon": 14.600, "tipo": "castagno", "quota": 900, "regione": "Campania"},
    {"nome": "Partenio - Montevergine", "lat": 40.936, "lon": 14.727, "tipo": "faggio", "quota": 1200, "regione": "Campania"},
    {"nome": "Partenio - Avella", "lat": 40.960, "lon": 14.600, "tipo": "castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Picentini - Montella", "lat": 40.844, "lon": 15.018, "tipo": "faggio", "quota": 1100, "regione": "Campania"},
    {"nome": "Picentini - Bagnoli Irpino", "lat": 40.833, "lon": 15.072, "tipo": "faggio", "quota": 1200, "regione": "Campania"},
    {"nome": "Picentini - Laceno", "lat": 40.800, "lon": 15.100, "tipo": "faggio", "quota": 1100, "regione": "Campania"},
    {"nome": "Picentini - Serino", "lat": 40.795, "lon": 14.872, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Terminio - Cervialto", "lat": 40.830, "lon": 15.030, "tipo": "faggio", "quota": 1400, "regione": "Campania"},
    {"nome": "Alburni - Sicignano", "lat": 40.560, "lon": 15.305, "tipo": "faggio", "quota": 1000, "regione": "Campania"},
    {"nome": "Alburni - Ottati", "lat": 40.463, "lon": 15.321, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Cilento - Corleto Monforte", "lat": 40.437, "lon": 15.380, "tipo": "faggio", "quota": 850, "regione": "Campania"},
    {"nome": "Cilento - Piaggine", "lat": 40.345, "lon": 15.378, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Cilento - Rofrano", "lat": 40.212, "lon": 15.428, "tipo": "quercia", "quota": 500, "regione": "Campania"},
    {"nome": "Cilento - Monte Cervati", "lat": 40.285, "lon": 15.410, "tipo": "faggio", "quota": 1400, "regione": "Campania"},
    {"nome": "Cilento - Sanza", "lat": 40.244, "lon": 15.553, "tipo": "quercia", "quota": 550, "regione": "Campania"},
    {"nome": "Monti Lattari - Agerola", "lat": 40.638, "lon": 14.539, "tipo": "castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Monti Lattari - Pimonte", "lat": 40.675, "lon": 14.510, "tipo": "quercia", "quota": 500, "regione": "Campania"},
    {"nome": "Monte Faito", "lat": 40.650, "lon": 14.500, "tipo": "castagno", "quota": 1100, "regione": "Campania"},
    {"nome": "Sannio - Morcone", "lat": 41.344, "lon": 14.667, "tipo": "castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Irpinia - Trevico", "lat": 41.048, "lon": 15.233, "tipo": "faggio", "quota": 1000, "regione": "Campania"},
    {"nome": "Irpinia - Bagnoli / Laceno basso", "lat": 40.820, "lon": 15.080, "tipo": "castagno", "quota": 800, "regione": "Campania"},
    {"nome": "Matese - Faicchio", "lat": 41.278, "lon": 14.478, "tipo": "quercia", "quota": 200, "regione": "Campania"},
    {"nome": "Matese - Cerreto Sannita", "lat": 41.284, "lon": 14.557, "tipo": "quercia", "quota": 300, "regione": "Campania"},
    {"nome": "Matese - Pontelandolfo", "lat": 41.292, "lon": 14.689, "tipo": "quercia", "quota": 500, "regione": "Campania"},
    {"nome": "Fortore - San Bartolomeo in Galdo", "lat": 41.416, "lon": 15.017, "tipo": "quercia", "quota": 600, "regione": "Campania"},
    {"nome": "Fortore - Baselice", "lat": 41.394, "lon": 14.974, "tipo": "quercia", "quota": 500, "regione": "Campania"},
    {"nome": "Fortore - Circello", "lat": 41.355, "lon": 14.809, "tipo": "castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Fortore - Colle Sannita", "lat": 41.373, "lon": 14.833, "tipo": "castagno", "quota": 750, "regione": "Campania"},
    {"nome": "Irpinia - Ariano Irpino", "lat": 41.153, "lon": 15.088, "tipo": "castagno", "quota": 800, "regione": "Campania"},
    {"nome": "Irpinia - Greci", "lat": 41.191, "lon": 15.169, "tipo": "castagno", "quota": 800, "regione": "Campania"},
    {"nome": "Irpinia - Savignano Irpino", "lat": 41.227, "lon": 15.179, "tipo": "castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Irpinia - Zungoli", "lat": 41.126, "lon": 15.202, "tipo": "castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Irpinia - Bisaccia", "lat": 41.013, "lon": 15.375, "tipo": "castagno", "quota": 850, "regione": "Campania"},
    {"nome": "Irpinia - Andretta", "lat": 40.937, "lon": 15.325, "tipo": "faggio", "quota": 850, "regione": "Campania"},
    {"nome": "Irpinia - Calitri", "lat": 40.921, "lon": 15.436, "tipo": "quercia", "quota": 600, "regione": "Campania"},
    {"nome": "Irpinia - Lioni", "lat": 40.878, "lon": 15.188, "tipo": "faggio", "quota": 550, "regione": "Campania"},
    {"nome": "Irpinia - Teora", "lat": 40.852, "lon": 15.253, "tipo": "faggio", "quota": 650, "regione": "Campania"},
    {"nome": "Irpinia - Caposele", "lat": 40.815, "lon": 15.223, "tipo": "faggio", "quota": 450, "regione": "Campania"},
    {"nome": "Irpinia - Calabritto", "lat": 40.783, "lon": 15.223, "tipo": "faggio", "quota": 500, "regione": "Campania"},
    {"nome": "Irpinia - Senerchia", "lat": 40.741, "lon": 15.204, "tipo": "faggio", "quota": 600, "regione": "Campania"},
    {"nome": "Picentini - Nusco", "lat": 40.887, "lon": 15.087, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Picentini - Cassano Irpino", "lat": 40.870, "lon": 15.026, "tipo": "faggio", "quota": 500, "regione": "Campania"},
    {"nome": "Picentini - Volturara Irpina", "lat": 40.883, "lon": 14.918, "tipo": "faggio", "quota": 650, "regione": "Campania"},
    {"nome": "Picentini - Acerno", "lat": 40.737, "lon": 15.056, "tipo": "faggio", "quota": 750, "regione": "Campania"},
    {"nome": "Picentini - Giffoni Valle Piana", "lat": 40.718, "lon": 14.942, "tipo": "quercia", "quota": 250, "regione": "Campania"},
    {"nome": "Partenio - Summonte", "lat": 40.947, "lon": 14.775, "tipo": "faggio", "quota": 750, "regione": "Campania"},
    {"nome": "Partenio - Ospedaletto d'Alpinolo", "lat": 40.939, "lon": 14.746, "tipo": "faggio", "quota": 700, "regione": "Campania"},
    {"nome": "Partenio - Mercogliano", "lat": 40.920, "lon": 14.743, "tipo": "quercia", "quota": 400, "regione": "Campania"},
    {"nome": "Partenio - Baiano", "lat": 40.952, "lon": 14.617, "tipo": "quercia", "quota": 200, "regione": "Campania"},
    {"nome": "Taburno - Vitulano", "lat": 41.117, "lon": 14.658, "tipo": "quercia", "quota": 450, "regione": "Campania"},
    {"nome": "Taburno - Foglianise", "lat": 41.161, "lon": 14.671, "tipo": "quercia", "quota": 350, "regione": "Campania"},
    {"nome": "Taburno - Cautano", "lat": 41.150, "lon": 14.644, "tipo": "quercia", "quota": 400, "regione": "Campania"},
    {"nome": "Alburni - Petina", "lat": 40.532, "lon": 15.347, "tipo": "faggio", "quota": 650, "regione": "Campania"},
    {"nome": "Alburni - Sant'Angelo a Fasanella", "lat": 40.456, "lon": 15.341, "tipo": "faggio", "quota": 550, "regione": "Campania"},
    {"nome": "Alburni - Castelcivita", "lat": 40.495, "lon": 15.234, "tipo": "quercia", "quota": 450, "regione": "Campania"},
    {"nome": "Alburni - Sicignano / Postiglione", "lat": 40.559, "lon": 15.232, "tipo": "faggio", "quota": 600, "regione": "Campania"},
    {"nome": "Cilento - Valle dell'Angelo", "lat": 40.344, "lon": 15.366, "tipo": "faggio", "quota": 600, "regione": "Campania"},
    {"nome": "Cilento - Laurino", "lat": 40.339, "lon": 15.339, "tipo": "faggio", "quota": 500, "regione": "Campania"},
    {"nome": "Cilento - Roscigno", "lat": 40.400, "lon": 15.346, "tipo": "faggio", "quota": 550, "regione": "Campania"},
    {"nome": "Cilento - Sacco", "lat": 40.377, "lon": 15.379, "tipo": "faggio", "quota": 600, "regione": "Campania"},
    {"nome": "Cilento - Novi Velia", "lat": 40.224, "lon": 15.286, "tipo": "faggio", "quota": 650, "regione": "Campania"},
    {"nome": "Cilento - Vallo della Lucania", "lat": 40.230, "lon": 15.266, "tipo": "quercia", "quota": 400, "regione": "Campania"},
    {"nome": "Cilento - Montano Antilia", "lat": 40.163, "lon": 15.366, "tipo": "castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Cilento - Cuccaro Vetere", "lat": 40.164, "lon": 15.321, "tipo": "castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Cilento - Monte Stella", "lat": 40.233, "lon": 15.140, "tipo": "castagno", "quota": 900, "regione": "Campania"},
    {"nome": "Cilento - Stio", "lat": 40.310, "lon": 15.252, "tipo": "castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Cilento - Magliano Vetere", "lat": 40.346, "lon": 15.236, "tipo": "castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Cilento - Monte Soprano / Trentinara", "lat": 40.400, "lon": 15.115, "tipo": "quercia", "quota": 550, "regione": "Campania"},
    {"nome": "Cilento - San Giovanni a Piro", "lat": 40.051, "lon": 15.453, "tipo": "quercia", "quota": 450, "regione": "Campania"},
    {"nome": "Cilento - Roccagloriosa", "lat": 40.106, "lon": 15.429, "tipo": "quercia", "quota": 450, "regione": "Campania"},
    {"nome": "Vallo di Diano - Teggiano", "lat": 40.379, "lon": 15.540, "tipo": "quercia", "quota": 600, "regione": "Campania"},
    {"nome": "Vallo di Diano - Sassano", "lat": 40.340, "lon": 15.566, "tipo": "quercia", "quota": 500, "regione": "Campania"},
    {"nome": "Vallo di Diano - Monte San Giacomo", "lat": 40.344, "lon": 15.535, "tipo": "faggio", "quota": 700, "regione": "Campania"},
    {"nome": "Vallo di Diano - Padula", "lat": 40.337, "lon": 15.656, "tipo": "castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Vallo di Diano - Montesano sulla Marcellana", "lat": 40.276, "lon": 15.705, "tipo": "faggio", "quota": 850, "regione": "Campania"},
    {"nome": "Vallo di Diano - Casalbuono", "lat": 40.214, "lon": 15.686, "tipo": "castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Vallo di Diano - Sala Consilina", "lat": 40.399, "lon": 15.596, "tipo": "quercia", "quota": 550, "regione": "Campania"},
    {"nome": "Tanagro - Atena Lucana", "lat": 40.455, "lon": 15.557, "tipo": "castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Tanagro - Auletta / Pertosa", "lat": 40.561, "lon": 15.394, "tipo": "quercia", "quota": 300, "regione": "Campania"},
    {"nome": "Alto Sele - Colliano", "lat": 40.726, "lon": 15.289, "tipo": "quercia", "quota": 600, "regione": "Campania"},
    {"nome": "Alto Sele - Valva", "lat": 40.739, "lon": 15.270, "tipo": "quercia", "quota": 500, "regione": "Campania"},
    {"nome": "Alto Sele - Laviano", "lat": 40.786, "lon": 15.310, "tipo": "faggio", "quota": 500, "regione": "Campania"},
    {"nome": "Monti Lattari - Tramonti", "lat": 40.695, "lon": 14.640, "tipo": "quercia", "quota": 400, "regione": "Campania"},
    {"nome": "Monti Lattari - Scala / Ravello", "lat": 40.653, "lon": 14.608, "tipo": "quercia", "quota": 400, "regione": "Campania"},
    {"nome": "Monti Lattari - Gragnano / Lettere", "lat": 40.689, "lon": 14.515, "tipo": "quercia", "quota": 350, "regione": "Campania"},
    {"nome": "Monti Lattari - Vico Equense", "lat": 40.661, "lon": 14.427, "tipo": "quercia", "quota": 400, "regione": "Campania"},
    {"nome": "Abetina di Rosello", "lat": 41.901, "lon": 14.349, "tipo": "abete_bianco", "quota": 1000, "regione": "Abruzzo"},
    {"nome": "Laga - Bosco della Martese / Ceppo", "lat": 42.700, "lon": 13.480, "tipo": "abete_bianco", "quota": 1300, "regione": "Abruzzo"},
    {"nome": "Laga - Cortino / Altovia", "lat": 42.627, "lon": 13.507, "tipo": "abete_bianco", "quota": 1200, "regione": "Abruzzo"},
    {"nome": "Laga - Monte Pelone", "lat": 42.735, "lon": 13.460, "tipo": "abete_bianco", "quota": 1400, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Piana dell'Abete / Segadacqua", "lat": 42.548, "lon": 13.478, "tipo": "abete_bianco", "quota": 1300, "regione": "Abruzzo"},
    {"nome": "Gran Sasso - Fonte Vetica abeti", "lat": 42.448, "lon": 13.575, "tipo": "abete_rosso", "quota": 1600, "regione": "Abruzzo"},
    {"nome": "PNALM - Selva di Ornano", "lat": 41.790, "lon": 13.820, "tipo": "abete_bianco", "quota": 1400, "regione": "Abruzzo"},
    {"nome": "Alto Sangro - Aremogna abeti", "lat": 41.808, "lon": 14.045, "tipo": "abete_rosso", "quota": 1500, "regione": "Abruzzo"},
    {"nome": "Abeti Soprani - Pescopennataro", "lat": 41.878, "lon": 14.294, "tipo": "abete_bianco", "quota": 1200, "regione": "Molise"},
    {"nome": "Sant'Angelo del Pesco - abetine", "lat": 41.889, "lon": 14.255, "tipo": "abete_bianco", "quota": 1100, "regione": "Molise"},
    {"nome": "Capracotta - abete bianco", "lat": 41.833, "lon": 14.266, "tipo": "abete_bianco", "quota": 1400, "regione": "Molise"},
    {"nome": "Terminillo - rimboschimenti abete", "lat": 42.473, "lon": 12.997, "tipo": "abete_rosso", "quota": 1600, "regione": "Lazio"},
    {"nome": "Monti della Duchessa - conifere", "lat": 42.180, "lon": 13.330, "tipo": "abete_rosso", "quota": 1500, "regione": "Lazio"},
    {"nome": "Matese - rimboschimenti abete", "lat": 41.460, "lon": 14.380, "tipo": "abete_rosso", "quota": 1400, "regione": "Campania"},
    # Marche
    {"nome": "Sibillini - Ussita", "lat": 42.944, "lon": 13.166, "tipo": "faggio", "quota": 1200, "regione": "Marche"},
    {"nome": "Sibillini - Visso", "lat": 42.931, "lon": 13.088, "tipo": "faggio", "quota": 1100, "regione": "Marche"},
    {"nome": "Sibillini - Castelsantangelo sul Nera", "lat": 42.895, "lon": 13.153, "tipo": "faggio", "quota": 1300, "regione": "Marche"},
    {"nome": "Sibillini - Bolognola", "lat": 42.993, "lon": 13.228, "tipo": "faggio", "quota": 1400, "regione": "Marche"},
    {"nome": "Sibillini - Fiastra / Lago", "lat": 43.037, "lon": 13.169, "tipo": "faggio", "quota": 900, "regione": "Marche"},
    {"nome": "Sibillini - Sarnano", "lat": 43.035, "lon": 13.237, "tipo": "faggio", "quota": 850, "regione": "Marche"},
    {"nome": "Sibillini - Amandola", "lat": 42.980, "lon": 13.353, "tipo": "faggio", "quota": 900, "regione": "Marche"},
    {"nome": "Sibillini - Montefortino", "lat": 42.943, "lon": 13.340, "tipo": "faggio", "quota": 1100, "regione": "Marche"},
    {"nome": "Sibillini - Montemonaco", "lat": 42.898, "lon": 13.330, "tipo": "faggio", "quota": 1200, "regione": "Marche"},
    {"nome": "Sibillini - Montegallo", "lat": 42.842, "lon": 13.332, "tipo": "faggio", "quota": 1100, "regione": "Marche"},
    {"nome": "Laga Marche - Arquata del Tronto", "lat": 42.773, "lon": 13.296, "tipo": "faggio", "quota": 1200, "regione": "Marche"},
    {"nome": "Laga Marche - Acquasanta Terme", "lat": 42.770, "lon": 13.410, "tipo": "faggio", "quota": 900, "regione": "Marche"},
    {"nome": "Monte Ceresa - Montegallo / Rocca", "lat": 42.855, "lon": 13.370, "tipo": "faggio", "quota": 1000, "regione": "Marche"},
    {"nome": "Monte Catria - Frontone", "lat": 43.520, "lon": 12.738, "tipo": "faggio", "quota": 1100, "regione": "Marche"},
    {"nome": "Monte Catria - Cantiano", "lat": 43.451, "lon": 12.628, "tipo": "faggio", "quota": 900, "regione": "Marche"},
    {"nome": "Monte Nerone - Piobbico", "lat": 43.588, "lon": 12.510, "tipo": "faggio", "quota": 1000, "regione": "Marche"},
    {"nome": "Monte Nerone - Apecchio", "lat": 43.559, "lon": 12.418, "tipo": "faggio", "quota": 900, "regione": "Marche"},
    {"nome": "Monte Cucco Marche - Scheggia Passo", "lat": 43.404, "lon": 12.666, "tipo": "faggio", "quota": 800, "regione": "Marche"},
    {"nome": "Montefeltro - Carpegna", "lat": 43.781, "lon": 12.333, "tipo": "faggio", "quota": 900, "regione": "Marche"},
    {"nome": "Montefeltro - Pennabilli", "lat": 43.817, "lon": 12.262, "tipo": "faggio", "quota": 800, "regione": "Marche"},
    {"nome": "Alpe della Luna - Borgo Pace", "lat": 43.648, "lon": 12.293, "tipo": "faggio", "quota": 900, "regione": "Marche"},
    {"nome": "Alpe della Luna - Mercatello sul Metauro", "lat": 43.647, "lon": 12.336, "tipo": "faggio", "quota": 850, "regione": "Marche"},
    {"nome": "Furlo - Acqualagna", "lat": 43.627, "lon": 12.675, "tipo": "quercia", "quota": 350, "regione": "Marche"},
    {"nome": "Monte San Vicino - Apiro", "lat": 43.393, "lon": 13.131, "tipo": "faggio", "quota": 800, "regione": "Marche"},
    {"nome": "Monte San Vicino - Cingoli", "lat": 43.374, "lon": 13.216, "tipo": "quercia", "quota": 600, "regione": "Marche"},
    {"nome": "Genga / Frasassi", "lat": 43.430, "lon": 12.935, "tipo": "quercia", "quota": 400, "regione": "Marche"},
    {"nome": "Fabriano - boschi Giano", "lat": 43.336, "lon": 12.904, "tipo": "castagno", "quota": 500, "regione": "Marche"},
    {"nome": "Sassoferrato - Montelago", "lat": 43.436, "lon": 12.834, "tipo": "faggio", "quota": 700, "regione": "Marche"},
    {"nome": "Camerino - castagneti", "lat": 43.136, "lon": 13.068, "tipo": "castagno", "quota": 650, "regione": "Marche"},
    {"nome": "Muccia - Valle del Chienti", "lat": 43.082, "lon": 13.043, "tipo": "castagno", "quota": 550, "regione": "Marche"},
    {"nome": "Pievebovigliana / Val di Fiastra", "lat": 43.123, "lon": 13.125, "tipo": "castagno", "quota": 550, "regione": "Marche"},
    {"nome": "Sarnano - castagneti", "lat": 43.035, "lon": 13.251, "tipo": "castagno", "quota": 700, "regione": "Marche"},
    {"nome": "Cagli - Monte Petrano", "lat": 43.547, "lon": 12.647, "tipo": "faggio", "quota": 900, "regione": "Marche"},
    {"nome": "Serra Sant'Abbondio - Catria", "lat": 43.488, "lon": 12.771, "tipo": "faggio", "quota": 750, "regione": "Marche"},
    {"nome": "Pergola - colline cesane", "lat": 43.562, "lon": 12.837, "tipo": "quercia", "quota": 350, "regione": "Marche"},
    {"nome": "Urbino - Cesane", "lat": 43.726, "lon": 12.636, "tipo": "quercia", "quota": 450, "regione": "Marche"},
    {"nome": "Monte Conero - Sirolo", "lat": 43.522, "lon": 13.601, "tipo": "leccio", "quota": 350, "regione": "Marche"},
    {"nome": "Filottrano - colline", "lat": 43.438, "lon": 13.351, "tipo": "quercia", "quota": 250, "regione": "Marche"},
    {"nome": "Cingoli - querceti", "lat": 43.359, "lon": 13.208, "tipo": "quercia", "quota": 450, "regione": "Marche"},
    {"nome": "San Ginesio - colline", "lat": 43.107, "lon": 13.321, "tipo": "quercia", "quota": 600, "regione": "Marche"},
    {"nome": "Amandola - castagneti", "lat": 42.980, "lon": 13.353, "tipo": "castagno", "quota": 700, "regione": "Marche"},
    {"nome": "Sibillini - Pintura di Bolognola abeti", "lat": 42.995, "lon": 13.215, "tipo": "abete_bianco", "quota": 1450, "regione": "Marche"},
    {"nome": "Catria - versante abetine", "lat": 43.462, "lon": 12.705, "tipo": "abete_bianco", "quota": 1300, "regione": "Marche"},
    # Umbria
    {"nome": "Sibillini Umbria - Norcia", "lat": 42.793, "lon": 13.094, "tipo": "faggio", "quota": 1100, "regione": "Umbria"},
    {"nome": "Sibillini Umbria - Castelluccio", "lat": 42.829, "lon": 13.207, "tipo": "faggio", "quota": 1450, "regione": "Umbria"},
    {"nome": "Valnerina - Preci", "lat": 42.880, "lon": 13.037, "tipo": "faggio", "quota": 900, "regione": "Umbria"},
    {"nome": "Valnerina - Cerreto di Spoleto", "lat": 42.822, "lon": 12.917, "tipo": "faggio", "quota": 800, "regione": "Umbria"},
    {"nome": "Valnerina - Sellano", "lat": 42.888, "lon": 12.923, "tipo": "faggio", "quota": 750, "regione": "Umbria"},
    {"nome": "Valnerina - Cascia", "lat": 42.718, "lon": 13.013, "tipo": "faggio", "quota": 900, "regione": "Umbria"},
    {"nome": "Monteleone di Spoleto", "lat": 42.651, "lon": 12.952, "tipo": "faggio", "quota": 950, "regione": "Umbria"},
    {"nome": "Monte Cucco - Sigillo", "lat": 43.331, "lon": 12.742, "tipo": "faggio", "quota": 900, "regione": "Umbria"},
    {"nome": "Monte Cucco - Costacciaro", "lat": 43.359, "lon": 12.712, "tipo": "faggio", "quota": 850, "regione": "Umbria"},
    {"nome": "Monte Cucco - Scheggia", "lat": 43.404, "lon": 12.666, "tipo": "faggio", "quota": 700, "regione": "Umbria"},
    {"nome": "Gubbio - Monte Ingino", "lat": 43.355, "lon": 12.578, "tipo": "faggio", "quota": 700, "regione": "Umbria"},
    {"nome": "Gubbio - castagneti", "lat": 43.351, "lon": 12.573, "tipo": "castagno", "quota": 550, "regione": "Umbria"},
    {"nome": "Pietralunga - Foresta", "lat": 43.437, "lon": 12.435, "tipo": "faggio", "quota": 650, "regione": "Umbria"},
    {"nome": "Città di Castello - Alpe della Luna", "lat": 43.540, "lon": 12.240, "tipo": "faggio", "quota": 800, "regione": "Umbria"},
    {"nome": "San Giustino - Monte Santa Maria", "lat": 43.547, "lon": 12.175, "tipo": "faggio", "quota": 700, "regione": "Umbria"},
    {"nome": "Umbertide - colline Tevere", "lat": 43.306, "lon": 12.328, "tipo": "quercia", "quota": 350, "regione": "Umbria"},
    {"nome": "Monte Tezio - Perugia", "lat": 43.198, "lon": 12.347, "tipo": "quercia", "quota": 650, "regione": "Umbria"},
    {"nome": "Monte Subasio - Assisi", "lat": 43.074, "lon": 12.651, "tipo": "faggio", "quota": 900, "regione": "Umbria"},
    {"nome": "Monte Subasio - Spello", "lat": 43.000, "lon": 12.672, "tipo": "quercia", "quota": 450, "regione": "Umbria"},
    {"nome": "Colfiorito - Foligno", "lat": 43.027, "lon": 12.890, "tipo": "faggio", "quota": 800, "regione": "Umbria"},
    {"nome": "Nocera Umbra - Monte Pennino", "lat": 43.115, "lon": 12.854, "tipo": "faggio", "quota": 900, "regione": "Umbria"},
    {"nome": "Nocera Umbra - castagneti", "lat": 43.114, "lon": 12.786, "tipo": "castagno", "quota": 550, "regione": "Umbria"},
    {"nome": "Spoleto - Monteluco", "lat": 42.724, "lon": 12.748, "tipo": "faggio", "quota": 750, "regione": "Umbria"},
    {"nome": "Monti Martani - Massa Martana", "lat": 42.777, "lon": 12.525, "tipo": "quercia", "quota": 600, "regione": "Umbria"},
    {"nome": "Monte Peglia - San Venanzo", "lat": 42.869, "lon": 12.268, "tipo": "quercia", "quota": 650, "regione": "Umbria"},
    {"nome": "Orvieto - selva Querce", "lat": 42.718, "lon": 12.110, "tipo": "quercia", "quota": 350, "regione": "Umbria"},
    {"nome": "Piegaro - boschi Nestore", "lat": 42.966, "lon": 12.085, "tipo": "quercia", "quota": 400, "regione": "Umbria"},
    {"nome": "Trasimeno - Castiglione del Lago", "lat": 43.127, "lon": 12.045, "tipo": "quercia", "quota": 300, "regione": "Umbria"},
    {"nome": "Trasimeno - Magione / Montecolognola", "lat": 43.143, "lon": 12.203, "tipo": "quercia", "quota": 350, "regione": "Umbria"},
    {"nome": "Amerini - Amelia", "lat": 42.553, "lon": 12.416, "tipo": "quercia", "quota": 400, "regione": "Umbria"},
    {"nome": "Narni - boschi Serra", "lat": 42.519, "lon": 12.515, "tipo": "quercia", "quota": 350, "regione": "Umbria"},
    {"nome": "Terni - Monte Torre Maggiore", "lat": 42.620, "lon": 12.580, "tipo": "faggio", "quota": 900, "regione": "Umbria"},
    {"nome": "Ferentillo - Valnerina bassa", "lat": 42.621, "lon": 12.791, "tipo": "castagno", "quota": 400, "regione": "Umbria"},
    {"nome": "Scheggino - Valnerina", "lat": 42.712, "lon": 12.830, "tipo": "castagno", "quota": 450, "regione": "Umbria"},
    {"nome": "Cascia - castagneti", "lat": 42.717, "lon": 13.013, "tipo": "castagno", "quota": 700, "regione": "Umbria"},
    {"nome": "Norcia - Piano di Santa Scolastica", "lat": 42.793, "lon": 13.094, "tipo": "castagno", "quota": 650, "regione": "Umbria"},
    {"nome": "Valnerina - abetine Cerreto", "lat": 42.822, "lon": 12.917, "tipo": "abete_bianco", "quota": 1000, "regione": "Umbria"},
    {"nome": "Monte Cucco - abetine Pian delle Macinare", "lat": 43.350, "lon": 12.740, "tipo": "abete_bianco", "quota": 1100, "regione": "Umbria"},
    {"nome": "Frentani - misto carpino Gessopalena", "lat": 42.055, "lon": 14.273, "tipo": "misto_carpino_quercia", "quota": 650, "regione": "Abruzzo"},
    {"nome": "Vastese - misto carpino Carpineto", "lat": 41.965, "lon": 14.534, "tipo": "misto_carpino_quercia", "quota": 700, "regione": "Abruzzo"},
    {"nome": "Cerreto sul Volturno - misto", "lat": 41.659, "lon": 14.102, "tipo": "misto_carpino_quercia", "quota": 600, "regione": "Molise"},
    {"nome": "Pescolanciano - cerrete miste", "lat": 41.680, "lon": 14.248, "tipo": "misto_carpino_quercia", "quota": 800, "regione": "Molise"},
    {"nome": "Simbruini - misto carpino Subiaco", "lat": 41.925, "lon": 13.110, "tipo": "misto_carpino_quercia", "quota": 600, "regione": "Lazio"},
    {"nome": "Cimini - misto Viterbo", "lat": 42.408, "lon": 12.180, "tipo": "misto_carpino_quercia", "quota": 550, "regione": "Lazio"},
    {"nome": "Roccamonfina - lecceta", "lat": 41.297, "lon": 13.972, "tipo": "leccio", "quota": 400, "regione": "Campania"},
    {"nome": "Matese basso - misto Alife", "lat": 41.326, "lon": 14.334, "tipo": "misto_carpino_quercia", "quota": 250, "regione": "Campania"},
    {"nome": "Furlo - misto carpino", "lat": 43.627, "lon": 12.675, "tipo": "misto_carpino_quercia", "quota": 400, "regione": "Marche"},
    {"nome": "Genga / Frasassi - lecceta", "lat": 43.430, "lon": 12.935, "tipo": "leccio", "quota": 400, "regione": "Marche"},
    {"nome": "Amerini - misto Amelia", "lat": 42.553, "lon": 12.416, "tipo": "misto_carpino_quercia", "quota": 400, "regione": "Umbria"},
    {"nome": "Orvieto - lecceta", "lat": 42.718, "lon": 12.110, "tipo": "leccio", "quota": 350, "regione": "Umbria"},
    {"nome": "Casentino - Camaldoli", "lat": 43.813, "lon": 11.821, "tipo": "faggio", "quota": 1100, "regione": "Toscana"},
    {"nome": "Casentino - Badia Prataglia", "lat": 43.792, "lon": 11.883, "tipo": "faggio", "quota": 850, "regione": "Toscana"},
    {"nome": "Pratomagno - Consuma", "lat": 43.748, "lon": 11.585, "tipo": "faggio", "quota": 1000, "regione": "Toscana"},
    {"nome": "Abetone - Libro Aperto", "lat": 44.145, "lon": 10.665, "tipo": "faggio", "quota": 1400, "regione": "Toscana"},
    {"nome": "Abetone - abetine", "lat": 44.146, "lon": 10.665, "tipo": "abete_bianco", "quota": 1350, "regione": "Toscana"},
    {"nome": "Amiata - Abbadia San Salvatore", "lat": 42.881, "lon": 11.678, "tipo": "faggio", "quota": 1100, "regione": "Toscana"},
    {"nome": "Amiata - castagneti", "lat": 42.870, "lon": 11.620, "tipo": "castagno", "quota": 800, "regione": "Toscana"},
    {"nome": "Mugello - Passo della Futa", "lat": 44.098, "lon": 11.270, "tipo": "faggio", "quota": 900, "regione": "Toscana"},
    {"nome": "Apuane - Arni", "lat": 44.064, "lon": 10.250, "tipo": "faggio", "quota": 1100, "regione": "Toscana"},
    {"nome": "Colline Metallifere - Massa Marittima", "lat": 43.050, "lon": 10.890, "tipo": "leccio", "quota": 400, "regione": "Toscana"},
    {"nome": "Cimone - Sestola", "lat": 44.230, "lon": 10.770, "tipo": "faggio", "quota": 1400, "regione": "Emilia-Romagna"},
    {"nome": "Piandelagotti", "lat": 44.236, "lon": 10.532, "tipo": "faggio", "quota": 1200, "regione": "Emilia-Romagna"},
    {"nome": "Cerreto Laghi", "lat": 44.283, "lon": 10.240, "tipo": "faggio", "quota": 1350, "regione": "Emilia-Romagna"},
    {"nome": "Val Taro - Bedonia", "lat": 44.508, "lon": 9.629, "tipo": "castagno", "quota": 550, "regione": "Emilia-Romagna"},
    {"nome": "Corniglio - Parco Appennino", "lat": 44.475, "lon": 10.090, "tipo": "faggio", "quota": 900, "regione": "Emilia-Romagna"},
    {"nome": "Foreste Casentinesi - Campigna", "lat": 43.873, "lon": 11.747, "tipo": "faggio", "quota": 1100, "regione": "Emilia-Romagna"},
    {"nome": "Aveto - Rezzoaglio", "lat": 44.526, "lon": 9.389, "tipo": "faggio", "quota": 750, "regione": "Liguria"},
    {"nome": "Antola - Torriglia", "lat": 44.520, "lon": 9.158, "tipo": "faggio", "quota": 800, "regione": "Liguria"},
    {"nome": "Beigua - Sassello", "lat": 44.480, "lon": 8.490, "tipo": "faggio", "quota": 900, "regione": "Liguria"},
    {"nome": "Val di Vara - Zignago", "lat": 44.277, "lon": 9.745, "tipo": "castagno", "quota": 650, "regione": "Liguria"},
    {"nome": "Alpi Marittime - Entracque", "lat": 44.241, "lon": 7.400, "tipo": "faggio", "quota": 1100, "regione": "Piemonte"},
    {"nome": "Cuneese - Chiusa Pesio", "lat": 44.326, "lon": 7.675, "tipo": "faggio", "quota": 900, "regione": "Piemonte"},
    {"nome": "Val di Susa - Bardonecchia boschi", "lat": 45.078, "lon": 6.703, "tipo": "abete_rosso", "quota": 1400, "regione": "Piemonte"},
    {"nome": "Biellese - Oropa", "lat": 45.628, "lon": 7.978, "tipo": "faggio", "quota": 1200, "regione": "Piemonte"},
    {"nome": "Verbano - Val Grande", "lat": 46.050, "lon": 8.460, "tipo": "faggio", "quota": 1000, "regione": "Piemonte"},
    {"nome": "Langhe alte - Mombarcaro", "lat": 44.365, "lon": 8.078, "tipo": "castagno", "quota": 800, "regione": "Piemonte"},
    {"nome": "Orobie - Valbondione", "lat": 46.038, "lon": 10.012, "tipo": "faggio", "quota": 1100, "regione": "Lombardia"},
    {"nome": "Valsassina - Introbio", "lat": 45.973, "lon": 9.452, "tipo": "faggio", "quota": 900, "regione": "Lombardia"},
    {"nome": "Valcamonica - Ponte di Legno boschi", "lat": 46.260, "lon": 10.510, "tipo": "abete_rosso", "quota": 1500, "regione": "Lombardia"},
    {"nome": "Valtellina - Chiesa Valmalenco", "lat": 46.265, "lon": 9.849, "tipo": "abete_rosso", "quota": 1400, "regione": "Lombardia"},
    {"nome": "Cansiglio - Fregona", "lat": 46.047, "lon": 12.338, "tipo": "faggio", "quota": 1000, "regione": "Veneto"},
    {"nome": "Altopiano Asiago", "lat": 45.876, "lon": 11.509, "tipo": "faggio", "quota": 1050, "regione": "Veneto"},
    {"nome": "Lessini - Bosco Chiesanuova", "lat": 45.622, "lon": 11.032, "tipo": "faggio", "quota": 1200, "regione": "Veneto"},
    {"nome": "Cadore - Auronzo boschi", "lat": 46.552, "lon": 12.443, "tipo": "abete_rosso", "quota": 1200, "regione": "Veneto"},
    {"nome": "Tarvisio - Fusine", "lat": 46.495, "lon": 13.674, "tipo": "abete_rosso", "quota": 900, "regione": "Friuli-Venezia Giulia"},
    {"nome": "Carnia - Forni di Sopra", "lat": 46.420, "lon": 12.583, "tipo": "abete_rosso", "quota": 1100, "regione": "Friuli-Venezia Giulia"},
    {"nome": "Cansiglio est - Caneva", "lat": 46.010, "lon": 12.450, "tipo": "faggio", "quota": 950, "regione": "Friuli-Venezia Giulia"},
    {"nome": "Paneveggio", "lat": 46.309, "lon": 11.748, "tipo": "abete_rosso", "quota": 1500, "regione": "Trentino-Alto Adige"},
    {"nome": "Val di Fiemme - Cavalese boschi", "lat": 46.291, "lon": 11.459, "tipo": "abete_rosso", "quota": 1200, "regione": "Trentino-Alto Adige"},
    {"nome": "Adamello - versante TN", "lat": 46.220, "lon": 10.630, "tipo": "abete_rosso", "quota": 1400, "regione": "Trentino-Alto Adige"},
    {"nome": "Val Pusteria - Tesido", "lat": 46.775, "lon": 12.207, "tipo": "abete_rosso", "quota": 1300, "regione": "Trentino-Alto Adige"},
    {"nome": "Cogne - Valnontey", "lat": 45.609, "lon": 7.344, "tipo": "abete_rosso", "quota": 1700, "regione": "Valle d'Aosta"},
    {"nome": "Valpelline", "lat": 45.825, "lon": 7.326, "tipo": "abete_rosso", "quota": 1400, "regione": "Valle d'Aosta"},
    {"nome": "Gargano - Foresta Umbra", "lat": 41.810, "lon": 16.000, "tipo": "faggio", "quota": 800, "regione": "Puglia"},
    {"nome": "Subappennino Dauno - Faeto", "lat": 41.325, "lon": 15.160, "tipo": "faggio", "quota": 750, "regione": "Puglia"},
    {"nome": "Alta Murgia - Minervino", "lat": 41.123, "lon": 16.078, "tipo": "leccio", "quota": 500, "regione": "Puglia"},
    {"nome": "Vulture - Melfi boschi", "lat": 40.996, "lon": 15.652, "tipo": "castagno", "quota": 700, "regione": "Basilicata"},
    {"nome": "Pollino - Terranova", "lat": 39.977, "lon": 16.204, "tipo": "faggio", "quota": 1400, "regione": "Basilicata"},
    {"nome": "Abetina Reale Lucana", "lat": 40.150, "lon": 15.850, "tipo": "abete_bianco", "quota": 1300, "regione": "Basilicata"},
    {"nome": "Sila Grande - Lorica", "lat": 39.382, "lon": 16.535, "tipo": "faggio", "quota": 1350, "regione": "Calabria"},
    {"nome": "Sila - Camigliatello", "lat": 39.340, "lon": 16.440, "tipo": "faggio", "quota": 1300, "regione": "Calabria"},
    {"nome": "Sila - abetine", "lat": 39.350, "lon": 16.500, "tipo": "abete_bianco", "quota": 1400, "regione": "Calabria"},
    {"nome": "Aspromonte - Gambarie", "lat": 38.170, "lon": 15.830, "tipo": "faggio", "quota": 1300, "regione": "Calabria"},
    {"nome": "Pollino calabro - Civita", "lat": 39.837, "lon": 16.313, "tipo": "faggio", "quota": 900, "regione": "Calabria"},
    {"nome": "Nebrodi - Cesarò", "lat": 37.845, "lon": 14.713, "tipo": "faggio", "quota": 1200, "regione": "Sicilia"},
    {"nome": "Etna - Piano Provenzana", "lat": 37.797, "lon": 15.039, "tipo": "faggio", "quota": 1800, "regione": "Sicilia"},
    {"nome": "Madonie - Piano Battaglia", "lat": 37.877, "lon": 14.013, "tipo": "faggio", "quota": 1600, "regione": "Sicilia"},
    {"nome": "Gennargentu - Fonni", "lat": 40.119, "lon": 9.254, "tipo": "leccio", "quota": 1000, "regione": "Sardegna"},
    {"nome": "Limbara - Tempio Pausania", "lat": 40.900, "lon": 9.210, "tipo": "leccio", "quota": 550, "regione": "Sardegna"},
    {"nome": "Sette Fratelli - Sinnai", "lat": 39.250, "lon": 9.400, "tipo": "leccio", "quota": 600, "regione": "Sardegna"},
    {"nome": "Vallombrosa", "lat": 43.732, "lon": 11.558, "tipo": "abete_bianco", "quota": 950, "regione": "Toscana"},
    {"nome": "Orecchiella - San Romano", "lat": 44.200, "lon": 10.270, "tipo": "faggio", "quota": 1200, "regione": "Toscana"},
    {"nome": "Falterona - Castagno d'Andrea", "lat": 43.860, "lon": 11.650, "tipo": "faggio", "quota": 1100, "regione": "Toscana"},
    {"nome": "Corno alle Scale", "lat": 44.129, "lon": 10.831, "tipo": "faggio", "quota": 1500, "regione": "Emilia-Romagna"},
    {"nome": "Monte Cimone - Fanano", "lat": 44.212, "lon": 10.797, "tipo": "faggio", "quota": 1300, "regione": "Emilia-Romagna"},
    {"nome": "Penna - Santo Stefano d'Aveto", "lat": 44.551, "lon": 9.451, "tipo": "faggio", "quota": 1000, "regione": "Liguria"},
    {"nome": "Alta Val Tanaro - Ormea", "lat": 44.147, "lon": 7.920, "tipo": "faggio", "quota": 900, "regione": "Piemonte"},
    {"nome": "Valle Pesio - Certosa", "lat": 44.244, "lon": 7.663, "tipo": "faggio", "quota": 1100, "regione": "Piemonte"},
    {"nome": "Val Brembana - Foppolo", "lat": 46.046, "lon": 9.691, "tipo": "abete_rosso", "quota": 1600, "regione": "Lombardia"},
    {"nome": "Val Trompia - Collio", "lat": 45.810, "lon": 10.335, "tipo": "faggio", "quota": 900, "regione": "Lombardia"},
    {"nome": "Val di Fassa - Canazei boschi", "lat": 46.477, "lon": 11.770, "tipo": "abete_rosso", "quota": 1500, "regione": "Trentino-Alto Adige"},
    {"nome": "Alpe Cimbra - Folgaria", "lat": 45.916, "lon": 11.172, "tipo": "abete_rosso", "quota": 1300, "regione": "Trentino-Alto Adige"},
    {"nome": "Comelico - Santo Stefano", "lat": 46.557, "lon": 12.549, "tipo": "abete_rosso", "quota": 1200, "regione": "Veneto"},
    {"nome": "Sappada boschi", "lat": 46.566, "lon": 12.684, "tipo": "abete_rosso", "quota": 1250, "regione": "Friuli-Venezia Giulia"},
    {"nome": "Gran Paradiso - Rhêmes", "lat": 45.670, "lon": 7.150, "tipo": "abete_rosso", "quota": 1600, "regione": "Valle d'Aosta"},
    {"nome": "Sila Piccola - Taverna", "lat": 39.022, "lon": 16.583, "tipo": "faggio", "quota": 1200, "regione": "Calabria"},
    {"nome": "Serre - Serra San Bruno", "lat": 38.574, "lon": 16.326, "tipo": "abete_bianco", "quota": 1000, "regione": "Calabria"},
    {"nome": "Pollino - Rotonda", "lat": 39.952, "lon": 16.039, "tipo": "faggio", "quota": 900, "regione": "Basilicata"},
    {"nome": "Umbra - Vico del Gargano", "lat": 41.900, "lon": 15.960, "tipo": "faggio", "quota": 600, "regione": "Puglia"},
    {"nome": "Etna - Ragabo", "lat": 37.810, "lon": 15.056, "tipo": "faggio", "quota": 1400, "regione": "Sicilia"},
    {"nome": "Nebrodi - Portella Femmina Morta", "lat": 37.890, "lon": 14.650, "tipo": "faggio", "quota": 1500, "regione": "Sicilia"},
    {"nome": "Mugello - Passo del Giogo", "lat": 44.050, "lon": 11.380, "tipo": "faggio", "quota": 880, "regione": "Toscana"},
    {"nome": "Pratomagno - Anciolina", "lat": 43.645, "lon": 11.680, "tipo": "castagno", "quota": 800, "regione": "Toscana"},
    {"nome": "Apuane - Campocatino", "lat": 44.040, "lon": 10.230, "tipo": "faggio", "quota": 1100, "regione": "Toscana"},
    {"nome": "Amiata - Seggiano", "lat": 42.929, "lon": 11.557, "tipo": "castagno", "quota": 700, "regione": "Toscana"},
    {"nome": "Casentino - La Verna", "lat": 43.707, "lon": 11.931, "tipo": "faggio", "quota": 1120, "regione": "Toscana"},
    {"nome": "Abetone - Cutigliano", "lat": 44.100, "lon": 10.756, "tipo": "faggio", "quota": 900, "regione": "Toscana"},
    {"nome": "Lago Santo Modenese", "lat": 44.220, "lon": 10.590, "tipo": "faggio", "quota": 1500, "regione": "Emilia-Romagna"},
    {"nome": "Febbio - Villa Minozzo", "lat": 44.300, "lon": 10.430, "tipo": "faggio", "quota": 1200, "regione": "Emilia-Romagna"},
    {"nome": "Cerreto - Collagna", "lat": 44.347, "lon": 10.273, "tipo": "faggio", "quota": 900, "regione": "Emilia-Romagna"},
    {"nome": "Val d'Aveto - Rezzoaglio alto", "lat": 44.540, "lon": 9.400, "tipo": "faggio", "quota": 900, "regione": "Liguria"},
    {"nome": "Monte Beigua - Pra", "lat": 44.433, "lon": 8.563, "tipo": "faggio", "quota": 1100, "regione": "Liguria"},
    {"nome": "Valbrevenna", "lat": 44.563, "lon": 9.102, "tipo": "castagno", "quota": 550, "regione": "Liguria"},
    {"nome": "Val Maira - Acceglio", "lat": 44.475, "lon": 6.990, "tipo": "faggio", "quota": 1200, "regione": "Piemonte"},
    {"nome": "Val Varaita - Sampeyre", "lat": 44.579, "lon": 7.187, "tipo": "faggio", "quota": 1000, "regione": "Piemonte"},
    {"nome": "Biellese - Piedicavallo", "lat": 45.690, "lon": 7.946, "tipo": "faggio", "quota": 1050, "regione": "Piemonte"},
    {"nome": "Ossola - Formazza", "lat": 46.377, "lon": 8.425, "tipo": "abete_rosso", "quota": 1300, "regione": "Piemonte"},
    {"nome": "Val Masino", "lat": 46.215, "lon": 9.576, "tipo": "faggio", "quota": 900, "regione": "Lombardia"},
    {"nome": "Valtellina - Aprica", "lat": 46.154, "lon": 10.151, "tipo": "abete_rosso", "quota": 1200, "regione": "Lombardia"},
    {"nome": "Valle Camonica - Edolo", "lat": 46.178, "lon": 10.333, "tipo": "abete_rosso", "quota": 700, "regione": "Lombardia"},
    {"nome": "Adamello - Ponte di Legno TN", "lat": 46.210, "lon": 10.640, "tipo": "abete_rosso", "quota": 1600, "regione": "Trentino-Alto Adige"},
    {"nome": "Val di Non - Ruffre", "lat": 46.455, "lon": 11.060, "tipo": "abete_rosso", "quota": 1200, "regione": "Trentino-Alto Adige"},
    {"nome": "Tesino - Castello Tesino", "lat": 46.063, "lon": 11.633, "tipo": "abete_rosso", "quota": 900, "regione": "Trentino-Alto Adige"},
    {"nome": "Altopiano di Asiago - Gallio", "lat": 45.890, "lon": 11.557, "tipo": "faggio", "quota": 1100, "regione": "Veneto"},
    {"nome": "Cansiglio - Pian Cansiglio", "lat": 46.064, "lon": 12.410, "tipo": "faggio", "quota": 1000, "regione": "Veneto"},
    {"nome": "Lessinia - San Giorgio", "lat": 45.658, "lon": 11.000, "tipo": "faggio", "quota": 1400, "regione": "Veneto"},
    {"nome": "Tarvisio - Val Saisera", "lat": 46.510, "lon": 13.480, "tipo": "abete_rosso", "quota": 800, "regione": "Friuli-Venezia Giulia"},
    {"nome": "Forni Avoltri", "lat": 46.587, "lon": 12.776, "tipo": "abete_rosso", "quota": 900, "regione": "Friuli-Venezia Giulia"},
    {"nome": "Valsavarenche", "lat": 45.590, "lon": 7.210, "tipo": "abete_rosso", "quota": 1600, "regione": "Valle d'Aosta"},
    {"nome": "Sila Grande - Lorica est", "lat": 39.390, "lon": 16.550, "tipo": "faggio", "quota": 1400, "regione": "Calabria"},
    {"nome": "Aspromonte - Montalto", "lat": 38.155, "lon": 15.921, "tipo": "faggio", "quota": 1700, "regione": "Calabria"},
    {"nome": "Pollino - Colle Impiso", "lat": 39.905, "lon": 16.185, "tipo": "faggio", "quota": 1550, "regione": "Basilicata"},
    {"nome": "Gargano - Monte Sant'Angelo boschi", "lat": 41.706, "lon": 15.955, "tipo": "leccio", "quota": 800, "regione": "Puglia"},
    {"nome": "Etna nord - Linguaglossa", "lat": 37.843, "lon": 15.142, "tipo": "faggio", "quota": 1100, "regione": "Sicilia"},
    {"nome": "Gennargentu - Arzana", "lat": 39.917, "lon": 9.528, "tipo": "leccio", "quota": 700, "regione": "Sardegna"},
    {"nome": "Supramonte - Orgosolo", "lat": 40.205, "lon": 9.352, "tipo": "leccio", "quota": 700, "regione": "Sardegna"},
]


def classifica_bosco(nome="", quota=800, regione="", lat=42.0, tipo_hint=None):
    """Albero del bosco da quota, nome e regione — non lasciare tutto faggio."""
    n = (nome or "").lower()
    q = int(quota or 800)
    r = regione or ""
    if "lecc" in n:
        return "leccio"
    if "castagn" in n:
        return "castagno"
    if any(k in n for k in ("querc", "cerret", "roverel", "farnet")):
        return "quercia"
    if "carpino" in n:
        return "misto_carpino_quercia"
    if any(k in n for k in ("abete rosso", "pecceta", "peccia", "peccio")):
        return "abete_rosso"
    if any(k in n for k in ("abete bianco", "abetina")):
        return "abete_bianco"
    if any(k in n for k in ("cansiglio", "casentin", "camaldol", "vallombros", "foresta umbra", "umbra -")):
        return "faggio"
    alpino = r in ("Valle d'Aosta", "Trentino-Alto Adige") or (
        r in ("Piemonte", "Lombardia", "Friuli-Venezia Giulia") and float(lat or 0) >= 45.5
    ) or any(k in n for k in ("dolomit", "adamello", "ortles", "formazza", "tarvis", "saisera", "valtellina"))
    if alpino:
        if q >= 1200:
            return "abete_rosso"
        if q >= 900:
            return "abete_bianco"
        if q >= 600:
            return "faggio"
        return "castagno"
    if r == "Sardegna":
        return "leccio" if q < 1000 else "faggio"
    if r == "Sicilia" and q < 1000:
        return "leccio"
    if r == "Puglia" and q < 550:
        return "leccio"
    if q < 320:
        return "leccio" if float(lat or 42) < 42.3 else "quercia"
    if q < 620:
        if r in ("Campania", "Calabria", "Toscana"):
            return "castagno"
        return "quercia"
    if q < 880:
        if r in ("Campania", "Calabria", "Toscana", "Lazio"):
            return "castagno"
        return "misto_carpino_quercia"
    if q < 1050:
        return "faggio" if any(
            k in n for k in (
                "gran sasso", "majella", "matese", "sibillin", "terminillo",
                "sirente", "velino", "parco", "fagget", "blockhaus", "laga",
            )
        ) else "castagno"
    return "faggio"


for _p in PUNTI:
    _p["tipo"] = classifica_bosco(
        _p.get("nome"), _p.get("quota"), _p.get("regione"), _p.get("lat"), _p.get("tipo")
    )


def punto_piu_vicino(lat, lon, max_km=6.0):
    migliore = None
    for z in PUNTI:
        d = distanza_km(lat, lon, z["lat"], z["lon"])
        if d <= max_km and (migliore is None or d < migliore[0]):
            migliore = (d, z)
    return None if migliore is None else migliore[1]


# Stazioni ufficiali (WMO / Aeronautica / aeroporti) nelle 4 regioni e dintorni
STAZIONI = [
    {"id": "16214", "nome": "L'Aquila Preturo", "lat": 42.38, "lon": 13.31},
    {"id": "16219", "nome": "Campo Imperatore", "lat": 42.44, "lon": 13.56},
    {"id": "16220", "nome": "Pescara", "lat": 42.43, "lon": 14.18},
    {"id": "16230", "nome": "Pescara Aeroporto", "lat": 42.43, "lon": 14.18},
    {"id": "16232", "nome": "Termoli", "lat": 42.00, "lon": 15.00},
    {"id": "16224", "nome": "Campobasso", "lat": 41.57, "lon": 14.65},
    {"id": "16252", "nome": "Isernia", "lat": 41.59, "lon": 14.23},
    {"id": "16253", "nome": "Capracotta", "lat": 41.83, "lon": 14.26},
    {"id": "16261", "nome": "Grazzanise (CE)", "lat": 41.06, "lon": 14.08},
    {"id": "16289", "nome": "Napoli Capodichino", "lat": 40.88, "lon": 14.29},
    {"id": "16310", "nome": "Salerno Pontecagnano", "lat": 40.62, "lon": 14.91},
    {"id": "16312", "nome": "Trevico", "lat": 41.05, "lon": 15.23},
    {"id": "16320", "nome": "Capo Palinuro", "lat": 40.03, "lon": 15.28},
    {"id": "16239", "nome": "Roma Ciampino", "lat": 41.80, "lon": 12.59},
    {"id": "16242", "nome": "Roma Fiumicino", "lat": 41.80, "lon": 12.23},
    {"id": "16234", "nome": "Viterbo", "lat": 42.43, "lon": 12.06},
    {"id": "16221", "nome": "Rieti", "lat": 42.43, "lon": 12.86},
    {"id": "16206", "nome": "Terminillo", "lat": 42.47, "lon": 12.98},
    {"id": "16235", "nome": "Monte Terminillo Osservatorio", "lat": 42.47, "lon": 12.99},
    {"id": "16294", "nome": "Capo Palinuro / Cilento", "lat": 40.03, "lon": 15.28},
    {"id": "16258", "nome": "Latina", "lat": 41.55, "lon": 12.90},
    {"id": "16244", "nome": "Pratica di Mare", "lat": 41.65, "lon": 12.45},
    {"id": "16280", "nome": "Frosinone", "lat": 41.64, "lon": 13.30},
    {"id": "16191", "nome": "Ancona Falconara", "lat": 43.62, "lon": 13.36},
    {"id": "16190", "nome": "Frontone", "lat": 43.52, "lon": 12.73},
    {"id": "16181", "nome": "Perugia Sant'Egidio", "lat": 43.10, "lon": 12.50},
    {"id": "16179", "nome": "Terminillo / Leonessa confine", "lat": 42.47, "lon": 12.99},
]



MN_PREC_PALETTE = [
    ((216, 227, 255), 0.1),
    ((186, 204, 255), 0.5),
    ((151, 185, 255), 1.0),
    ((136, 160, 255), 2.0),
    ((113, 127, 249), 5.0),
    ((39, 111, 253), 10.0),
    ((13, 139, 188), 15.0),
    ((0, 160, 100), 18.0),
    ((13, 183, 98), 20.0),
    ((0, 176, 95), 22.0),
    ((11, 180, 95), 22.0),
    ((40, 200, 60), 28.0),
    ((65, 231, 35), 30.0),
    ((63, 229, 33), 32.0),
    ((100, 240, 20), 35.0),
    ((132, 255, 13), 40.0),
    ((130, 253, 11), 42.0),
    ((155, 255, 25), 48.0),
    ((175, 255, 35), 50.0),
    ((168, 254, 22), 52.0),
    ((174, 252, 33), 55.0),
    ((200, 255, 40), 58.0),
    ((221, 255, 43), 60.0),
    ((219, 252, 40), 62.0),
    ((217, 254, 31), 65.0),
    ((240, 250, 30), 70.0),
    ((255, 237, 13), 80.0),
    ((255, 220, 13), 90.0),
    ((255, 193, 13), 100.0),
    ((255, 156, 13), 120.0),
    ((255, 112, 13), 150.0),
    ((248, 34, 13), 200.0),
    ((135, 13, 13), 250.0),
]

# scale tipiche mappe daily MN (approssimate sulla legenda)
MN_TMIN_PALETTE = [
    ((40, 0, 80), -8), ((20, 40, 180), -2), ((40, 120, 230), 4),
    ((80, 200, 220), 8), ((160, 230, 140), 12), ((230, 230, 80), 16),
    ((250, 160, 40), 20), ((240, 60, 30), 24), ((160, 20, 20), 28),
]
MN_TMAX_PALETTE = [
    ((40, 0, 80), 0), ((20, 40, 180), 8), ((40, 120, 230), 14),
    ((80, 200, 220), 18), ((160, 230, 140), 22), ((230, 230, 80), 26),
    ((250, 160, 40), 30), ((240, 60, 30), 34), ((160, 20, 20), 38),
]
MN_WIND_PALETTE = [
    ((230, 230, 230), 2), ((180, 220, 255), 8), ((80, 180, 120), 15),
    ((200, 220, 60), 25), ((250, 160, 40), 40), ((230, 40, 30), 60),
    ((120, 0, 80), 80),
]


def _mn_png_xy(lat, lon, w=1026, h=1252):
    x = 50 + (float(lon) - 6.2) / (18.8 - 6.2) * 900
    y = 70 + (47.2 - float(lat)) / (47.2 - 36.5) * 1090
    return int(max(0, min(w - 1, x))), int(max(0, min(h - 1, y)))


def _mn_e_mare_o_bordo(rgb):
    r, g, b = rgb[:3]
    if r < 28 and g < 28 and b < 28:
        return True
    if r > 245 and g > 245 and b > 245:
        return True
    # azzurro mare MN
    if b >= 230 and g >= 190 and r <= 200:
        return True
    return False


def _mn_e_terra_asciutta(rgb):
    r, g, b = rgb[:3]
    chroma = max(r, g, b) - min(r, g, b)
    if chroma < 52:
        return True
    # beige rilievo senza pioggia
    if r > 170 and g > 160 and b > 150 and abs(r - g) < 28 and b <= g + 8:
        return True
    return False


def _mn_rgb_to_scala(rgb, palette, neutro=True):
    r, g, b = rgb[:3]
    if neutro and _mn_e_terra_asciutta(rgb):
        return None
    best, bd = None, 1e9
    for (pr, pg, pb), val in palette:
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if d < bd:
            bd, best = d, val
    if bd > 2800:
        return None
    return float(best)


def _mn_rgb_to_mm(rgb):
    if _mn_e_mare_o_bordo(rgb) or _mn_e_terra_asciutta(rgb):
        return 0.0
    v = _mn_rgb_to_scala(rgb, MN_PREC_PALETTE, neutro=False)
    return 0.0 if v is None else v


def _mn_get_px(buf, w, h, x, y):
    i = (y * w + x) * 3
    return (buf[i], buf[i + 1], buf[i + 2])


def _mn_sample(lat, lon, giorno, variabile, decoder):
    """Campiona il pixel sulla mappa MN.

    Per la pioggia: nel raggio locale prende il *massimo* tra i pixel terra
    (le mappe interpolate hanno nuclei colorati; un solo pixel può sottostimare).
    """
    pack = _mn_mappa_px(giorno, variabile)
    if not pack:
        return None
    try:
        w, h, buf = pack
        x0, y0 = _mn_png_xy(lat, lon, w, h)
        if variabile != "prec":
            candidati = [(0, 0)]
            for rad in range(1, 8):
                for dx in range(-rad, rad + 1):
                    candidati.append((dx, -rad))
                    candidati.append((dx, rad))
                for dy in range(-rad + 1, rad):
                    candidati.append((-rad, dy))
                    candidati.append((rad, dy))
            for dx, dy in candidati:
                x = max(0, min(w - 1, x0 + dx))
                y = max(0, min(h - 1, y0 + dy))
                rgb = _mn_get_px(buf, w, h, x, y)
                if _mn_e_mare_o_bordo(rgb):
                    continue
                v = decoder(rgb)
                if v is not None:
                    return v
            return None

        # PRECIP: max locale (raggio ~18 px ≈ 15-25 km sulla PNG Italia)
        # le mappe interpolate hanno nuclei spostati di qualche pixel rispetto al geopunto
        valori = []
        for dy in range(-18, 19):
            for dx in range(-18, 19):
                if dx * dx + dy * dy > 324:
                    continue
                x = max(0, min(w - 1, x0 + dx))
                y = max(0, min(h - 1, y0 + dy))
                rgb = _mn_get_px(buf, w, h, x, y)
                if _mn_e_mare_o_bordo(rgb):
                    continue
                if _mn_e_terra_asciutta(rgb):
                    valori.append(0.0)
                    continue
                v = decoder(rgb)
                if v is not None:
                    valori.append(float(v))
        if not valori:
            return 0.0
        # usa il massimo locale (nucleo temporale sulla mappa)
        return max(valori)
    except Exception:
        return None


_MAPPE_DIR = Path(__file__).resolve().parent / "cache_mappe"


@st.cache_data(ttl=21600)
def _mn_mappa_px(giorno, variabile="prec"):
    """Scarica e decodifica UNA volta la PNG del giorno (disco + RAM)."""
    d = str(giorno)
    _MAPPE_DIR.mkdir(exist_ok=True)
    fp = _MAPPE_DIR / f"{d}_{variabile}.bin"
    if fp.exists() and fp.stat().st_size > 1000:
        try:
            raw = fp.read_bytes()
            w = int.from_bytes(raw[:4], "big")
            h = int.from_bytes(raw[4:8], "big")
            return (w, h, raw[8:])
        except Exception:
            pass
    url = (
        "https://cdn1.meteonetwork.it/models/malawi/wnetwork/mappe_daily/"
        f"{d}/{d}_{variabile}_italia.png"
    )
    try:
        r = None
        for _t in range(3):
            try:
                r = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200 and len(r.content) >= 10000:
                    break
            except Exception:
                r = None
                time.sleep(0.4)
        if r is None or r.status_code != 200 or len(r.content) < 10000:
            return None
        from PIL import Image
        import io
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
        buf = im.tobytes()
        try:
            fp.write_bytes(im.size[0].to_bytes(4, "big") + im.size[1].to_bytes(4, "big") + buf)
        except Exception:
            pass
        return (im.size[0], im.size[1], buf)
    except Exception:
        return None


def mn_prec_da_mappa(lat, lon, giorno):
    return _mn_sample(lat, lon, giorno, "prec", _mn_rgb_to_mm)


def mn_preload_mappe(giorni=30):
    oggi = datetime.now().date()
    fatti = 0
    def _one(i):
        g = (oggi - timedelta(days=i)).isoformat()
        _mn_mappa_px(g, "prec")
        _mn_mappa_px(g, "temp_min")
        _mn_mappa_px(g, "temp_max")
        _mn_mappa_px(g, "wind")
    with ThreadPoolExecutor(max_workers=4) as ex:
        for _ in ex.map(_one, range(giorni)):
            fatti += 1
            CALC_PROGRESS.update({"pct": max(1, int(fatti * 12 / giorni)), "text": f"Mappe MN {fatti}/{giorni}"})


def dpc_pioggia_punto(lat, lon):
    """Cumulata DPC ultime 24h (rete pluviometri ufficiali + interpolazione)."""
    headers = {
        "Origin": "https://radar.protezionecivile.it",
        "Referer": "https://radar.protezionecivile.it/",
        "User-Agent": "Mozilla/5.0",
    }
    try:
        last = requests.get(
            "https://radar-api.protezionecivile.it/findLastProductByType",
            params={"type": "CUM24", "origin": "https://radar.protezionecivile.it"},
            headers=headers,
            timeout=10,
        )
        js = last.json() if last.status_code == 200 else {}
        prods = js.get("lastProducts") or []
        ts = prods[0].get("time") if prods else None
    except Exception:
        ts = None
    mm = None
    try:
        pad = 0.04
        url = (
            "https://radar-geowebcache.protezionecivile.it/service/wms"
            "?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetFeatureInfo"
            "&LAYERS=radar:srt24&QUERY_LAYERS=radar:srt24"
            "&INFO_FORMAT=application/json&SRS=EPSG:4326"
            f"&BBOX={lon-pad},{lat-pad},{lon+pad},{lat+pad}"
            "&WIDTH=11&HEIGHT=11&X=5&Y=5"
        )
        r = requests.get(url, headers=headers, timeout=12)
        data = r.json() if r.status_code == 200 else {}
        feats = data.get("features") or []
        if feats:
            props = feats[0].get("properties") or {}
            for k, v in props.items():
                try:
                    mm = float(v)
                    break
                except Exception:
                    continue
    except Exception:
        mm = None
    return {"mm_24h": mm, "ts": ts, "fonte": "DPC CUM24 / SRT24"}


@lru_cache(maxsize=20000)
def _dpc_giorno_mm(lat_r, lon_r, giorno_iso, ora_utc):
    """Valore CUM24 (radar tarato sui pluviometri, dato reale non modellato) per un punto/giorno.
    Cache per (lat arrotondata, lon arrotondata, giorno, ora): la cella radar è ~1km,
    quindi punti vicini nello stesso giorno riusano la stessa chiamata."""
    headers = {
        "Origin": "https://radar.protezionecivile.it",
        "Referer": "https://radar.protezionecivile.it/",
        "User-Agent": "Mozilla/5.0",
    }
    pad = 0.045
    time_param = f"{giorno_iso}T{ora_utc}.000Z"
    url = (
        "https://radar-geowebcache.protezionecivile.it/service/wms"
        "?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetFeatureInfo"
        "&LAYERS=radar:cum24&QUERY_LAYERS=radar:cum24"
        "&INFO_FORMAT=application/json&SRS=EPSG:4326"
        f"&BBOX={lon_r - pad},{lat_r - pad},{lon_r + pad},{lat_r + pad}"
        "&WIDTH=11&HEIGHT=11&X=5&Y=5"
        f"&TIME={time_param}"
    )
    try:
        r = requests.get(url, headers=headers, timeout=12)
        if r.status_code != 200 or not r.content:
            return None
        data = r.json()
        feats = data.get("features") or []
        if not feats:
            return None
        props = feats[0].get("properties") or {}
        for v in props.values():
            try:
                return float(v)
            except Exception:
                continue
    except Exception:
        return None
    return None


def dpc_serie_giorni(lat, lon, giorni=30, max_workers=5):
    """Serie storica di pioggia REALE (radar Protezione Civile tarato sui pluviometri,
    prodotto CUM24) per un punto, ultimi N giorni. Copertura nazionale (Sicilia/Calabria
    incluse), a differenza dei modelli meteo che a Sud/sulle isole degradano o non arrivano.
    Ritorna None se la copertura radar sul punto non è buona (troppi buchi o pixel piatto,
    es. fuori portata/mare/margine)."""
    lat_r, lon_r = round(float(lat), 2), round(float(lon), 2)
    oggi = datetime.now(TZ_ROMA).date()

    def _uno(i):
        g = oggi - timedelta(days=i)
        iso = g.isoformat()
        mm = _dpc_giorno_mm(lat_r, lon_r, iso, "06:00:00")
        if mm is None:
            mm = _dpc_giorno_mm(lat_r, lon_r, iso, "00:00:00")
        return g, mm

    rows = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for g, mm in ex.map(_uno, range(int(giorni))):
            if mm is not None:
                rows.append({"date": pd.Timestamp(g), "precip": round(max(float(mm), 0.0), 1)})
    if len(rows) < max(15, int(giorni * 0.5)):
        return None
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    vals = df["precip"].round(1)
    vc = vals.value_counts()
    # stesso mm quasi tutti i giorni = cella radar non valida (mare/bordo/buco copertura)
    if len(vc) and (vc.iloc[0] / len(vals)) >= 0.7:
        return None
    return df


def mn_pioggia_mappa(lat, lon, raggio=15):
    """Legge le PNG mappe giornaliere MN (scala colori) sul punto, ultimi 30 giorni."""
    oggi = datetime.now().date()
    rows = []

    def _giorno(i):
        g = oggi - timedelta(days=i)
        iso = g.isoformat()
        mm = mn_prec_da_mappa(lat, lon, iso)
        if mm is None:
            return None
        tmin = _mn_sample(lat, lon, iso, "temp_min", lambda rgb: _mn_rgb_to_scala(rgb, MN_TMIN_PALETTE))
        tmax = _mn_sample(lat, lon, iso, "temp_max", lambda rgb: _mn_rgb_to_scala(rgb, MN_TMAX_PALETTE))
        vento = _mn_sample(lat, lon, iso, "wind", lambda rgb: _mn_rgb_to_scala(rgb, MN_WIND_PALETTE))
        return {
            "date": pd.Timestamp(g),
            "precip": round(float(mm or 0), 1),
            "t_min": None if tmin is None else round(float(tmin), 1),
            "t_max": None if tmax is None else round(float(tmax), 1),
            "vento_max": None if vento is None else round(float(vento), 1),
        }

    try:
        with ThreadPoolExecutor(max_workers=6) as ex:
            for rec in ex.map(_giorno, range(30)):
                if rec is not None:
                    rows.append(rec)
    except Exception:
        for i in range(30):
            rec = _giorno(i)
            if rec is not None:
                rows.append(rec)
    if not rows:
        return None
    df = pd.DataFrame(rows).sort_values("date")
    try:
        vals = pd.to_numeric(df["precip"], errors="coerce").fillna(0).round(1)
        if len(vals) >= 8:
            vc = vals.value_counts()
            top, ntop = float(vc.index[0]), int(vc.iloc[0])
            # stesso mm tutti i giorni = pixel sbagliato (mare/legenda)
            if top > 0 and ntop / len(vals) >= 0.55:
                return None
            tot_chk = float(vals.sum())
            if tot_chk > 280 and vals.nunique() <= 4:
                return None
    except Exception:
        pass
    tot = round(float(df["precip"].sum()), 1)
    oggi_ts = pd.Timestamp(oggi)
    oggi_mm = float(df.loc[df["date"] == oggi_ts, "precip"].iloc[0]) if (df["date"] == oggi_ts).any() else 0.0
    return {"df": df, "oggi_mm": oggi_mm, "mese_mm": tot, "n": len(rows)}


def _ultimi_30g(df):
    """Ogni aggiornamento: tengo solo gli ultimi 30 giorni."""
    if df is None or len(df) == 0 or "date" not in getattr(df, "columns", []):
        return df
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date"])
    if not len(d):
        return d
    oggi = pd.Timestamp(datetime.now().date())
    taglio = oggi - pd.Timedelta(days=30)
    d = d[(d["date"] >= taglio) & (d["date"] <= oggi)]
    return d.sort_values("date")


def distanza_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * atan2(sqrt(a), sqrt(1 - a))


def mn_login(email, password):
    """Ritorna (token, errore). Una sola chiamata: il login ha limite stretto (429)."""
    if not email or not password:
        return None, "Inserisci email e password di myMeteoNetwork."
    try:
        r = requests.post(
            "https://api.meteonetwork.it/v3/login",
            data={
                "email": email,
                "username": email,
                "user": email,
                "password": password,
            },
            headers={"User-Agent": "PorciniPredictor/1.0 (uso personale)"},
            timeout=20,
        )
    except Exception as e:
        return None, f"Rete: {e}"
    if r.status_code == 429:
        return None, (
            "Troppe richieste a MeteoNetwork (HTTP 429). "
            "Non riprovare subito: aspetta almeno 30–60 minuti. "
            "Poi usa il pulsante «Collega MeteoNetwork» una volta sola, oppure incolla un token già salvato."
        )
    if r.status_code != 200:
        return None, f"Login API non riuscito. HTTP {r.status_code}: {r.text[:240]}"
    try:
        js = r.json()
    except Exception:
        return None, f"Risposta login non valida: {r.text[:200]}"
    data = js.get("data") if isinstance(js.get("data"), dict) else {}
    token = js.get("access_token") or js.get("token") or data.get("token") or data.get("access_token")
    if token:
        return str(token), None
    return None, f"Nessun token nella risposta: {r.text[:240]}"


def _parse_stazioni_mn(js):
    if isinstance(js, dict):
        js = js.get("data") or js.get("stations") or js.get("items") or []
    if not isinstance(js, list):
        return []
    out = []
    for s in js:
        if not isinstance(s, dict):
            continue
        try:
            lat = float(s.get("latitude") or s.get("lat"))
            lon = float(s.get("longitude") or s.get("lon"))
            code = s.get("station_code") or s.get("code") or s.get("id")
            nome = s.get("name") or s.get("place") or s.get("area") or code
            regione = s.get("region_name") or s.get("region") or ""
            quota_s = s.get("altitude") or s.get("elevation") or s.get("alt")
            try:
                quota_s = float(quota_s) if quota_s not in (None, "") else None
            except Exception:
                quota_s = None
            if code and lat and lon:
                out.append({
                    "code": str(code),
                    "nome": str(nome),
                    "lat": lat,
                    "lon": lon,
                    "regione": str(regione),
                    "quota": quota_s,
                })
        except Exception:
            continue
    return out


@st.cache_data(ttl=3600)
def mn_elenco_stazioni(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "PorciniPredictor/1.0 (uso personale)",
    }
    tentativi = [
        ("https://api.meteonetwork.it/v3/stations", {"country": "IT"}),
        ("https://api.meteonetwork.it/v3/stations", {"region": "Molise"}),
        ("https://api.meteonetwork.it/v3/stations", {"region": "Abruzzo"}),
        ("https://api.meteonetwork.it/v3/stations", {"region": "Lazio"}),
        ("https://api.meteonetwork.it/v3/stations", {"region": "Campania"}),
        ("https://api.meteonetwork.it/v3/stations", {"region": "Marche"}),
        ("https://api.meteonetwork.it/v3/stations", {"region": "Umbria"}),
        ("https://api.meteonetwork.it/v3/data-realtime", {"country": "IT", "region": "Molise"}),
    ]
    ultimo = "nessuna risposta"
    trovate = []
    seen = set()
    for url, params in tentativi:
        try:
            r = requests.get(url, headers=headers, params=params, timeout=30)
        except Exception as e:
            ultimo = str(e)
            continue
        ultimo = f"HTTP {r.status_code}: {r.text[:180]}"
        if r.status_code != 200:
            continue
        try:
            js = r.json()
        except Exception:
            continue
        for s in _parse_stazioni_mn(js):
            if s["code"] not in seen:
                seen.add(s["code"])
                trovate.append(s)
        if trovate:
            return trovate
    # memorizza il motivo per la sidebar (cache-friendly: lo mettiamo in un dict fittizio no)
    st.session_state["mn_elenco_errore"] = ultimo
    return []


@st.cache_data(ttl=1800)
def _path_codici_salvati():
    return Path(__file__).resolve().parent / "mn_codici_utente.txt"


def carica_codici_salvati():
    out = []
    seen = set()
    path = _path_codici_salvati()
    if path.exists():
        try:
            for p in path.read_text(encoding="utf-8").replace(";", ",").split(","):
                c = p.strip().lower()
                if c and c not in seen:
                    seen.add(c)
                    out.append(c)
        except Exception:
            pass
    for c in (st.session_state.get("mn_codici_lista") or []):
        c = str(c).strip().lower()
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def salva_codici_utente(lista):
    puliti = []
    seen = set()
    for c in lista:
        c = str(c).strip().lower()
        if c and c not in seen:
            seen.add(c)
            puliti.append(c)
    st.session_state["mn_codici_lista"] = puliti
    try:
        _path_codici_salvati().write_text(", ".join(puliti), encoding="utf-8")
    except Exception:
        pass
    return puliti


def mn_stazioni_da_codici(token, codici):
    """STANDARD: /stations/{code} (singola) + realtime. Poche chiamate, mai in parallelo."""
    if not token or not codici:
        return []
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "PorciniPredictor/1.0 (uso personale)",
    }
    out = []
    for raw in str(codici).replace(";", ",").split(","):
        code = raw.strip().split("/")[-1].split("?")[0].strip().lower()
        if not code:
            continue
        row = None
        for url in (
            f"https://api.meteonetwork.it/v3/stations/{code}",
            f"https://api.meteonetwork.it/v3/data-realtime/{code}",
        ):
            try:
                r = requests.get(url, headers=headers, timeout=20)
                if r.status_code != 200:
                    continue
                js = r.json()
                cand = js[0] if isinstance(js, list) and js else js
                if isinstance(cand, dict):
                    row = cand
                    break
            except Exception:
                continue
        if not row:
            continue
        lat = row.get("latitude") or row.get("lat")
        lon = row.get("longitude") or row.get("lon")
        if lat is None or lon is None:
            continue
        quota_s = row.get("altitude") or row.get("elevation")
        try:
            quota_s = float(quota_s) if quota_s not in (None, "") else None
        except Exception:
            quota_s = None
        out.append({
            "code": str(row.get("station_code") or code),
            "nome": str(
                row.get("name") or row.get("place_name") or row.get("place") or row.get("area") or code
            ),
            "lat": float(lat),
            "lon": float(lon),
            "regione": str(row.get("region") or row.get("region_name") or ""),
            "quota": quota_s,
        })
    return out


def punteggio_vicinanza(dist_km, d_quota, max_dist=45):
    """Più basso è meglio. 0–2 km meglio di 2–5; quota simile conta."""
    if dist_km is None or dist_km > max_dist:
        return 9999
    dq = abs(d_quota) if d_quota is not None else 250
    if dist_km <= 2.0:
        base = dist_km
    elif dist_km <= 5.0:
        base = 4.0 + (dist_km - 2.0) * 2.5
    else:
        base = 20.0 + dist_km
    return base + dq / 40.0


def mn_stazioni_vicine(lat, lon, stazioni, quota=None, n=5, max_km=40):
    if not stazioni:
        return []
    ranked = []
    for s in stazioni:
        d = distanza_km(lat, lon, s["lat"], s["lon"])
        if d > max_km:
            continue
        q_st = s.get("quota") or s.get("altitude")
        dq = (quota - q_st) if (quota is not None and q_st not in (None, "")) else None
        ranked.append((punteggio_vicinanza(d, dq, max_km), d, s))
    ranked.sort(key=lambda x: x[0])
    out = []
    for _, d, s in ranked[:n]:
        s2 = dict(s)
        s2["distanza_km"] = round(d, 1)
        out.append(s2)
    return out


def mn_stazione_vicina(lat, lon, stazioni, quota=None):
    vicine = mn_stazioni_vicine(lat, lon, stazioni, quota=quota, n=1)
    if not vicine:
        return None, None
    return vicine[0], vicine[0]["distanza_km"]


def _mn_rows_to_df(righe):
    records = []
    for row in righe:
        if not isinstance(row, dict):
            continue
        rain = row.get("daily_rain")
        if rain is None:
            rain = row.get("rain") or row.get("precipitation") or row.get("prec")
        tmax = row.get("current_tmax") or row.get("tmax") or row.get("temperature")
        tmin = row.get("current_tmin") or row.get("tmin")
        tmed = row.get("current_tmed") or row.get("tmed") or row.get("temperature")
        data = (
            row.get("observation_date")
            or row.get("date")
            or row.get("observation_time_local")
            or row.get("day")
            or ""
        )
        try:
            precip = float(rain) if rain not in (None, "") else 0.0
        except Exception:
            precip = 0.0
        records.append({
            "date": str(data)[:10],
            "precip": precip,
            "t_max": float(tmax) if tmax not in (None, "") else None,
            "t_min": float(tmin) if tmin not in (None, "") else None,
            "t_mean": float(tmed) if tmed not in (None, "") else None,
        })
    if not records:
        return None
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).drop_duplicates("date").sort_values("date")
    return df.fillna(0)


def _path_giorni_salvati():
    return Path(__file__).resolve().parent / "mn_giorni_utente.json"


# Agosto 2026 Bagnolo Amatrice (laz201) da tabella FM / pluviometro
SEED_LAZ201_AGO2026 = {
    "2026-08-01": 0.0, "2026-08-02": 0.0, "2026-08-03": 0.0, "2026-08-04": 0.51,
    "2026-08-05": 0.0, "2026-08-06": 0.0, "2026-08-07": 0.0, "2026-08-08": 0.0,
    "2026-08-09": 0.0, "2026-08-10": 0.0, "2026-08-11": 1.52, "2026-08-12": 0.0,
    "2026-08-13": 0.0, "2026-08-14": 0.0, "2026-08-15": 0.0, "2026-08-16": 4.06,
    "2026-08-17": 2.03, "2026-08-18": 0.0, "2026-08-19": 0.0, "2026-08-20": 0.0,
    "2026-08-21": 6.60, "2026-08-22": 0.0, "2026-08-23": 0.0, "2026-08-24": 0.0,
    "2026-08-25": 3.30, "2026-08-26": 0.0, "2026-08-27": 0.0, "2026-08-28": 4.32,
    "2026-08-29": 0.25, "2026-08-30": 0.0, "2026-08-31": 0.0,
}


def _carica_giorni_file():
    """Carica sempre da disco (Flask non ha session Streamlit persistente)."""
    store = st.session_state.setdefault("mn_giorni", {})
    path = _path_giorni_salvati()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data:
                # merge: file ha priorità sui giorni presenti
                store.update(data)
                st.session_state["mn_giorni"] = store
                st.session_state["mn_giorni_file_ok"] = True
        except Exception:
            pass
    if not st.session_state.get("seed_laz201_ok"):
        for giorno, mm in SEED_LAZ201_AGO2026.items():
            chiave = f"laz201|{giorno}"
            if chiave not in store:
                store[chiave] = {"date": giorno, "precip": mm}
        st.session_state["mn_giorni"] = store
        st.session_state["seed_laz201_ok"] = True
    return store


def _salva_giorni_file():
    """Archivio rotante: tengo 31 giorni, cancello tutto ciò che è più vecchio di un mese."""
    try:
        store = dict(st.session_state.get("mn_giorni") or {})
        limite = (datetime.now().date() - timedelta(days=30)).isoformat()
        pulito = {}
        for k, v in store.items():
            d = ""
            if isinstance(v, dict):
                d = str(v.get("date") or "")[:10]
            if not d and "|" in str(k):
                d = str(k).rsplit("|", 1)[-1][:10]
            if d >= limite:
                pulito[k] = v
        st.session_state["mn_giorni"] = pulito
        _path_giorni_salvati().write_text(
            json.dumps(pulito, ensure_ascii=False),
            encoding="utf-8",
        )
        _push_giorni_github(pulito)
    except Exception:
        pass


def _push_giorni_github(store):
    """Se nei Secrets c'è GITHUB_TOKEN, aggiorna mn_giorni_utente.json sul repo."""
    try:
        last = float(st.session_state.get("mn_push_ts") or 0)
        if time.time() - last < 90:
            return
        tok = ""
        repo = ""
        branch = "main"
        try:
            tok = str(st.secrets.get("GITHUB_TOKEN") or "")
            repo = str(st.secrets.get("GITHUB_REPO") or "")
            branch = str(st.secrets.get("GITHUB_BRANCH") or "main")
        except Exception:
            pass
        tok = tok or str(__import__("os").environ.get("GITHUB_TOKEN") or "")
        repo = repo or str(__import__("os").environ.get("GITHUB_REPO") or "")
        if not tok or not repo or "/" not in repo:
            st.session_state["mn_push_err"] = "manca GITHUB_TOKEN o GITHUB_REPO nei Secrets"
            return
        path = "mn_giorni_utente.json"
        api = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {
            "Authorization": f"Bearer {tok}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "PorciniPredictor",
        }
        sha = None
        r = requests.get(api, headers=headers, params={"ref": branch}, timeout=20)
        if r.status_code == 200:
            sha = (r.json() or {}).get("sha")
        body = {
            "message": f"archivio piogge {datetime.now().date().isoformat()}",
            "content": base64.b64encode(
                json.dumps(store, ensure_ascii=False).encode("utf-8")
            ).decode("ascii"),
            "branch": branch,
        }
        if sha:
            body["sha"] = sha
        p = requests.put(api, headers=headers, json=body, timeout=25)
        if p.status_code in (200, 201):
            st.session_state["mn_push_ts"] = time.time()
            st.session_state["mn_push_ok"] = True
            st.session_state["mn_push_err"] = ""
        else:
            st.session_state["mn_push_ok"] = False
            st.session_state["mn_push_err"] = f"GitHub HTTP {p.status_code}"
    except Exception as e:
        st.session_state["mn_push_ok"] = False
        st.session_state["mn_push_err"] = str(e)[:80]


def mn_giorno_pluviometro(token, code, giorno):
    """Un giorno. Successi in sessione e su file; i 429 non si cachano."""
    store = _carica_giorni_file()
    key = f"{code}|{giorno}"
    if key in store:
        return {"ok": True, "status": 200, "row": store[key]}
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "PorciniPredictor/1.0 (uso personale)",
    }
    r = requests.get(
        f"https://api.meteonetwork.it/v3/data-daily/{code}",
        headers=headers,
        params={"observation_date": giorno},
        timeout=15,
    )
    if r.status_code != 200:
        return {"ok": False, "status": r.status_code, "row": None}
    js = r.json()
    row = js[0] if isinstance(js, list) and js else js
    if isinstance(row, dict):
        store[key] = row
        st.session_state["mn_giorni"] = store
        _salva_giorni_file()
        return {"ok": True, "status": 200, "row": row}
    return {"ok": False, "status": r.status_code, "row": None}


def mn_serie_giornaliera(token, code, days=30, nuovi_per_volta=4):
    """Fino a 30 giorni. Ogni Calcola scarica al massimo 4 giorni nuovi."""
    if not token or not code:
        return None, 0, days
    oggi = datetime.now().date()
    righe = []
    nuovi = 0
    store = _carica_giorni_file()
    for i in range(min(int(days), 30)):
        d = (oggi - timedelta(days=i)).isoformat()
        key = f"{code}|{d}"
        if key in store:
            righe.append(store[key])
            continue
        if nuovi >= nuovi_per_volta:
            continue
        pack = mn_giorno_pluviometro(token, code, d)
        if pack.get("status") == 429:
            break
        if pack.get("ok") and pack.get("row"):
            righe.append(pack["row"])
            store[key] = pack["row"]
        nuovi += 1
    st.session_state["mn_giorni"] = store
    _salva_giorni_file()
    return _mn_rows_to_df(righe), len(righe), days


@st.cache_data(ttl=1800)
def mn_dati_stazione(token, code, days=30):
    """Una o poche chiamate per stazione. Niente 30 GET: quello genera 429 e poi sparisce MN."""
    headers = {"Authorization": f"Bearer {token}"}
    oggi = datetime.now().date()
    start = (oggi - timedelta(days=min(days, 16))).isoformat()
    end = oggi.isoformat()

    for url, params in [
        (f"https://api.meteonetwork.it/v3/data-daily/{code}", {"start": start, "end": end}),
        (f"https://api.meteonetwork.it/v3/daily/{code}", {"from": start, "to": end}),
    ]:
        try:
            r = requests.get(url, headers=headers, params=params, timeout=20)
            if r.status_code != 200:
                continue
            js = r.json()
            if isinstance(js, dict):
                js = js.get("data") or js.get("values") or js.get("daily") or []
            if isinstance(js, list) and js:
                df = _mn_rows_to_df(js)
                if df is not None and len(df) >= 3:
                    return df
        except Exception:
            continue

    try:
        r = requests.get(
            f"https://api.meteonetwork.it/v3/data-realtime/{code}",
            headers=headers,
            timeout=20,
        )
        if r.status_code == 200:
            js = r.json()
            row = js[0] if isinstance(js, list) and js else js
            if isinstance(row, dict):
                return _mn_rows_to_df([row])
    except Exception:
        pass
    return None


def _stazione_attiva(daily_end, max_giorni_fermo=120):
    """Una stazione Meteostat senza dati recenti (daily_end vecchio) non va scelta
    come 'più vicina': darebbe un archivio vuoto e forzerebbe comunque il fallback."""
    de = str(daily_end or "").strip()
    if not de:
        return True  # nessuna data di fine indicata: la si considera attiva
    try:
        d = datetime.fromisoformat(de[:10]).date()
    except Exception:
        return True
    return (datetime.now().date() - d).days <= max_giorni_fermo


@st.cache_data(ttl=86400)
def catalogo_stazioni_ufficiali():
    """Stazioni Meteostat del Centro-Sud + elenco hardcoded (WMO/aeroporti)."""
    out = []
    seen = set()
    path = Path(__file__).resolve().parent / "stazioni_it.json"
    if path.exists():
        try:
            for s in json.loads(path.read_text()):
                sid = str(s.get("id"))
                if not sid:
                    continue
                seen.add(sid)
                if not _stazione_attiva(s.get("daily_end")):
                    continue
                out.append({
                    "id": sid,
                    "nome": s.get("nome") or sid,
                    "lat": float(s["lat"]),
                    "lon": float(s["lon"]),
                    "quota": s.get("quota"),
                    "daily_end": s.get("daily_end"),
                })
        except Exception:
            pass
    for s in STAZIONI:
        sid = str(s["id"])
        if sid in seen:
            continue
        out.append({
            "id": sid,
            "nome": s["nome"],
            "lat": s["lat"],
            "lon": s["lon"],
            "quota": None,
            "daily_end": None,
        })
    return out


def stazioni_ufficiali_vicine(lat, lon, quota=None, n=4, max_km=35):
    ranked = []
    for s in catalogo_stazioni_ufficiali():
        d = distanza_km(lat, lon, s["lat"], s["lon"])
        if d > max_km:
            continue
        dq = (quota - s["quota"]) if (quota is not None and s.get("quota") is not None) else None
        ranked.append((punteggio_vicinanza(d, dq, max_km), d, s))
    ranked.sort(key=lambda x: x[0])
    res = []
    for _, d, s in ranked[:n]:
        s2 = dict(s)
        s2["distanza_km"] = round(d, 1)
        res.append(s2)
    return res


def stazione_piu_vicina(lat, lon, quota=None):
    vicine = stazioni_ufficiali_vicine(lat, lon, quota=quota, n=1, max_km=80)
    if not vicine:
        return None, None
    return vicine[0], vicine[0]["distanza_km"]


@st.cache_data(ttl=3600)
def get_stazione_dati(station_id, days=30):
    year = datetime.now().year
    frames = []
    for y in (year - 1, year):
        url = f"https://data.meteostat.net/daily/{y}/{station_id}.csv.gz"
        try:
            r = requests.get(url, timeout=20)
            if r.status_code != 200:
                continue
            raw = gzip.decompress(r.content)
            dfy = pd.read_csv(io.BytesIO(raw))
            frames.append(dfy)
        except Exception:
            continue
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    if "date" not in df.columns:
        return None
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    fine = datetime.now()
    inizio = fine - timedelta(days=days)
    df = df[(df["date"] >= inizio) & (df["date"] <= fine)].copy()
    if len(df) < 8:
        return None
    prcp = pd.to_numeric(df.get("prcp"), errors="coerce")
    # se la colonna pioggia è quasi tutta vuota la stazione non è utile per i porcini
    if prcp.notna().sum() < 8:
        return None
    # NON mettere 0 sui buchi: uno 0 finto abbassa i mm rispetto alla stazione vera
    out = pd.DataFrame({
        "date": df["date"],
        "precip": prcp,
        "t_max": pd.to_numeric(df.get("tmax"), errors="coerce"),
        "t_min": pd.to_numeric(df.get("tmin"), errors="coerce"),
        "t_mean": pd.to_numeric(df.get("tavg"), errors="coerce"),
    })
    return out


def riepilogo_vento(df, giorni=10):
    """Vento persistente secca il letto: fattore 1 = ok, verso 0 = nascite azzerate."""
    vuoto = {
        "vento_medio_10g": None,
        "vento_max_10g": None,
        "giorni_oltre_20": 0,
        "giorni_oltre_30": 0,
        "giorni_consecutivi_venti": 0,
        "fattore_vento": 1.0,
        "nota_vento": "Vento non disponibile",
        "picchi_vento": [],
        "picco_max_data": None,
        "picco_max_kmh": None,
    }
    if df is None or "vento_max" not in getattr(df, "columns", []):
        return vuoto
    coda = df.tail(giorni).copy()
    v = pd.to_numeric(coda["vento_max"], errors="coerce").fillna(0)
    if v.isna().all() or float(v.max()) == 0 and float(v.mean()) == 0:
        # potrebbe essere tutto zero vero, trattiamo comunque
        pass
    giorni_20 = int((v >= 20).sum())
    giorni_30 = int((v >= 30).sum())
    streak = 0
    for val in reversed(list(v)):
        if val >= 20:
            streak += 1
        else:
            break
    media = float(v.mean())
    vmax = float(v.max())
    # stress: persistenza + intensità (esponenziale come richiesto)
    stress = giorni_20 * 0.12 + giorni_30 * 0.32 + max(0, streak - 1) * 0.22
    if media >= 28:
        stress += 0.7
    elif media >= 22:
        stress += 0.35
    fattore = float(max(0.03, min(1.0, exp(-stress))))
    if giorni_30 >= 4 and streak >= 3:
        fattore = min(fattore, 0.12)
    if fattore >= 0.85:
        nota = "Vento debole, umidità del suolo tenuta"
    elif fattore >= 0.5:
        nota = "Vento fresco persistente: il letto si sta asciugando"
    elif fattore >= 0.2:
        nota = "Vento forte e ripetuto: nascite fortemente ridotte"
    else:
        nota = "Vento persistente >20–30 km/h: umidità quasi azzerata"
    picchi = []
    picco_data = None
    picco_kmh = None
    try:
        serie = df.copy()
        serie["date"] = pd.to_datetime(serie["date"], errors="coerce")
        serie["vento_max"] = pd.to_numeric(serie["vento_max"], errors="coerce")
        serie = serie.dropna(subset=["date", "vento_max"])
        taglio = pd.Timestamp(datetime.now().date()) - pd.Timedelta(days=30)
        serie = serie[serie["date"] >= taglio]
        forti = serie[serie["vento_max"] >= 20].sort_values("date")
        for _, rr in forti.iterrows():
            picchi.append(
                f"{pd.to_datetime(rr['date']).date()}: {float(rr['vento_max']):.1f} km/h"
            )
        if len(serie):
            top = serie.loc[serie["vento_max"].idxmax()]
            picco_data = pd.to_datetime(top["date"]).date().isoformat()
            picco_kmh = round(float(top["vento_max"]), 1)
    except Exception:
        pass
    return {
        "vento_medio_10g": round(media, 1),
        "vento_max_10g": round(vmax, 1),
        "giorni_oltre_20": giorni_20,
        "giorni_oltre_30": giorni_30,
        "giorni_consecutivi_venti": streak,
        "fattore_vento": round(fattore, 3),
        "nota_vento": nota,
        "picchi_vento": picchi,
        "picco_max_data": picco_data,
        "picco_max_kmh": picco_kmh,
    }


def _dir_cardinale(gradi):
    try:
        g = float(gradi) % 360
    except Exception:
        return None
    nomi = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    return nomi[int((g + 22.5) // 45) % 8]


@st.cache_data(ttl=3600)
def get_vento_direzione_om(lat, lon):
    """Direzione prevalente 10 gg. L'archivio MN mensile non ha i gradi."""
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": round(float(lat), 3),
                "longitude": round(float(lon), 3),
                "past_days": 10,
                "forecast_days": 1,
                "daily": "wind_direction_10m_dominant",
                "timezone": "Europe/Rome",
            },
            timeout=12,
        )
        if r.status_code != 200:
            return None
        vals = (r.json().get("daily") or {}).get("wind_direction_10m_dominant") or []
        nums = [float(x) for x in vals if x is not None]
        if not nums:
            return None
        import math
        rad = [math.radians(x) for x in nums]
        x = sum(math.sin(a) for a in rad) / len(rad)
        y = sum(math.cos(a) for a in rad) / len(rad)
        ang = (math.degrees(math.atan2(x, y)) + 360) % 360
        return _dir_cardinale(ang)
    except Exception:
        return None


@st.cache_data(ttl=3600)
def get_temperature_om(lat, lon, days=30):
    """Solo temperature, non la pioggia."""
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": round(float(lat), 3),
                "longitude": round(float(lon), 3),
                "past_days": min(int(days), 92),
                "forecast_days": 1,
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "Europe/Rome",
            },
            timeout=12,
        )
        if r.status_code != 200:
            return None
        d = r.json().get("daily") or {}
        if not d.get("time"):
            return None
        return pd.DataFrame({
            "date": pd.to_datetime(d["time"]).normalize(),
            "t_max": d.get("temperature_2m_max"),
            "t_min": d.get("temperature_2m_min"),
        })
    except Exception:
        return None


@st.cache_data(ttl=3600)
def get_umidita_media(lat, lon):
    """Umidità relativa media 10 giorni (Open-Meteo). MN pubblico spesso non la manda."""
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": round(float(lat), 3),
                "longitude": round(float(lon), 3),
                "past_days": 10,
                "forecast_days": 1,
                "daily": "relative_humidity_2m_mean",
                "timezone": "Europe/Rome",
            },
            timeout=12,
        )
        if r.status_code != 200:
            return None
        vals = (r.json().get("daily") or {}).get("relative_humidity_2m_mean") or []
        nums = [float(x) for x in vals if x is not None]
        if not nums:
            return None
        return round(sum(nums) / len(nums), 1)
    except Exception:
        return None


@st.cache_data(ttl=3600)
def get_openmeteo_bundle(lat, lon, days=30):
    """Storico + previsione + suolo. Pioggia da ICON-2I (2 km) se disponibile."""
    oggi = pd.Timestamp(datetime.now().date())
    start = (datetime.now().date() - timedelta(days=days)).isoformat()
    end = datetime.now().date().isoformat()

    storico = None
    # storico ad alta risoluzione sul modello italiano
    try:
        r = requests.get(
            "https://historical-forecast-api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": start,
                "end_date": end,
                "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min,temperature_2m_mean,wind_speed_10m_max",
                "models": "italia_meteo_arpae_icon_2i",
                "timezone": "Europe/Rome",
            },
            timeout=25,
        )
        if r.status_code == 200:
            data = r.json()
            if "daily" in data:
                storico = pd.DataFrame({
                    "date": pd.to_datetime(data["daily"]["time"]),
                    "precip": data["daily"]["precipitation_sum"],
                    "t_max": data["daily"]["temperature_2m_max"],
                    "t_min": data["daily"]["temperature_2m_min"],
                    "t_mean": data["daily"]["temperature_2m_mean"],
                    "vento_max": data["daily"].get("wind_speed_10m_max") or 0,
                }).fillna(0)
    except Exception:
        storico = None

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "past_days": min(days, 92),
        "forecast_days": 7,
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min,temperature_2m_mean,wind_speed_10m_max",
        "hourly": "soil_moisture_7_to_28cm",
        "timezone": "Europe/Rome",
        "models": "italia_meteo_arpae_icon_2i",
    }
    try:
        r = requests.get(url, params=params, timeout=25)
        if r.status_code != 200:
            params.pop("models", None)
            r = requests.get(url, params=params, timeout=25)
        r.raise_for_status()
        data = r.json()
    except Exception:
        data = {}

    daily = None
    if "daily" in data:
        daily = pd.DataFrame({
            "date": pd.to_datetime(data["daily"]["time"]),
            "precip": data["daily"]["precipitation_sum"],
            "t_max": data["daily"]["temperature_2m_max"],
            "t_min": data["daily"]["temperature_2m_min"],
            "t_mean": data["daily"]["temperature_2m_mean"],
            "vento_max": data["daily"].get("wind_speed_10m_max") or 0,
        }).fillna(0)

    if storico is None and daily is not None:
        storico = daily[daily["date"] <= oggi].tail(days)
    elif storico is not None and daily is not None and "vento_max" in daily.columns:
        # allinea il vento del modello anche se la pioggia viene da altrove
        if "vento_max" not in storico.columns:
            storico = storico.merge(daily[["date", "vento_max"]], on="date", how="left")
    forecast = daily[daily["date"] > oggi].head(7) if daily is not None else None

    soil = None
    if data.get("hourly") and data["hourly"].get("soil_moisture_7_to_28cm"):
        soil_vals = [v for v in data["hourly"]["soil_moisture_7_to_28cm"] if v is not None]
        if soil_vals:
            soil = round(sum(soil_vals[-72:]) / max(1, len(soil_vals[-72:])), 3)
    vento = riepilogo_vento(storico if storico is not None else daily)
    return storico, forecast, soil, vento


def get_openmeteo_data(lat, lon, days=30):
    storico, *_ = get_openmeteo_bundle(lat, lon, days)
    return storico


def _info_stazione(s, fonte):
    return {
        "fonte": fonte,
        "stazione": s.get("nome") or s.get("code") or "n/d",
        "distanza_km": s.get("distanza_km"),
        "quota_stazione": s.get("quota"),
        "codice": s.get("code") or s.get("id"),
        "pioggia_modello_30g": None,
        "pioggia_stazione_30g": None,
    }


def _tabella_bosco(df):
    if df is None or len(df) == 0:
        return ""
    cols = list(df.columns)

    def _esc(v):
        s = "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    th = "".join(f"<th>{_esc(c)}</th>" for c in cols)
    body = []
    for _, rr in df.iterrows():
        body.append("<tr>" + "".join(f"<td>{_esc(rr[c])}</td>" for c in cols) + "</tr>")
    return (
        '<div class="bmap-table"><table><thead><tr>'
        + th
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


_WC_SESS = None

def _wc_session():
    global _WC_SESS
    if _WC_SESS is not None:
        return _WC_SESS
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://app.weathercloud.net/map",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json,text/javascript,*/*",
    })
    try:
        s.get("https://app.weathercloud.net/", timeout=8)
    except Exception:
        pass
    _WC_SESS = s
    return s


def _wc_id(code):
    code = str(code).strip()
    if not code:
        return ""
    if code.isdigit():
        return code
    try:
        return str(int(code, 36))
    except Exception:
        return code


def _wc_catalogo_file():
    path = Path(__file__).resolve().parent / "weathercloud_centro.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


@st.cache_data(ttl=21600)
def wc_catalogo():
    """Stazioni WeatherCloud Centro-Sud. File locale subito, live se risponde."""
    locale = _wc_catalogo_file()
    s = _wc_session()
    try:
        r = s.get("https://app.weathercloud.net/map/bgdevices", timeout=20)
        txt = r.text or ""
        js = r.json() if txt.lstrip()[:1] == "{" else None
        devs = (js or {}).get("devices") or []
    except Exception:
        devs = []
    if not devs:
        return locale
    out = []
    for d in devs:
        if not isinstance(d, (list, tuple)) or len(d) < 4:
            continue
        try:
            lat, lon = float(d[2]), float(d[3])
        except Exception:
            continue
        if not (36.5 <= lat <= 47.2 and 6.5 <= lon <= 18.6):
            continue
        code = str(d[0])
        out.append({
            "code": code,
            "id": _wc_id(code),
            "nome": str(d[1]),
            "lat": lat,
            "lon": lon,
            "online": d[4] == 2 if len(d) > 4 else True,
        })
    if len(out) < 50:
        return locale or out
    return out


@st.cache_data(ttl=3600)
def _wc_evolution(device_id, variable):
    s = _wc_session()
    did = _wc_id(device_id)
    try:
        r = s.post(
            "https://app.weathercloud.net/device/evolution",
            data={"device": did, "variable": str(variable), "period": "month"},
            timeout=(4, 10),
        )
        return ((r.json() or {}).get("data") or {}).get("values") or {}
    except Exception:
        return {}


@st.cache_data(ttl=90)
def wc_mese_mm(device_id):
    """Solo mm WC (801), per confrontare in fretta."""
    vals = _wc_evolution(device_id, "801")
    recs = []
    for ts, payload in (vals or {}).items():
        try:
            dt = datetime.fromtimestamp(int(ts), tz=TZ_ROMA).date()
            stats = ((payload or {}).get("801") or {}).get("stats") or {}
            mm = stats.get("total")
            if mm is None:
                mm = stats.get("sum") or 0
            recs.append({"date": pd.Timestamp(dt), "precip": float(mm or 0)})
        except Exception:
            continue
    if not recs:
        store = _carica_giorni_file()
        did = str(_wc_id(device_id))
        oggi = datetime.now().date()
        for i in range(40):
            d = oggi - timedelta(days=i)
            old = store.get(f"wc:{did}|{d.isoformat()}") or {}
            if old:
                recs.append({"date": pd.Timestamp(d), "precip": float(old.get("precip") or 0)})
    if not recs:
        return None
    return pd.DataFrame(recs).sort_values("date")


@st.cache_data(ttl=90)
def wc_mese_pioggia(device_id):
    """Mese WC: mm (801) + T (101) + vento raffica (541/521, m/s → km/h). Date = sito WC."""
    vals_r = _wc_evolution(device_id, "801")
    vals_t = _wc_evolution(device_id, "101")
    vals_v = _wc_evolution(device_id, "541")
    by_day = {}
    for ts, payload in (vals_r or {}).items():
        try:
            dt = datetime.fromtimestamp(int(ts), tz=TZ_ROMA).date()
            stats = ((payload or {}).get("801") or {}).get("stats") or {}
            mm = stats.get("total")
            if mm is None:
                mm = stats.get("sum") or 0
            by_day[dt] = {"date": pd.Timestamp(dt), "precip": float(mm or 0)}
        except Exception:
            continue
    for ts, payload in (vals_t or {}).items():
        try:
            dt = datetime.fromtimestamp(int(ts), tz=TZ_ROMA).date()
            stats = ((payload or {}).get("101") or {}).get("stats") or {}
            rec = by_day.setdefault(dt, {"date": pd.Timestamp(dt), "precip": 0.0})
            if stats.get("max") is not None:
                rec["t_max"] = float(stats["max"])
            if stats.get("min") is not None:
                rec["t_min"] = float(stats["min"])
            if stats.get("sum") is not None and stats.get("samples"):
                rec["t_med"] = round(float(stats["sum"]) / float(stats["samples"]), 1)
        except Exception:
            continue
    for ts, payload in (vals_v or {}).items():
        try:
            dt = datetime.fromtimestamp(int(ts), tz=TZ_ROMA).date()
            rec = by_day.setdefault(dt, {"date": pd.Timestamp(dt), "precip": 0.0})
            payload = payload or {}
            raffica = ((payload.get("521") or {}).get("stats") or {}).get("max")
            medio = ((payload.get("541") or {}).get("stats") or {}).get("max")
            ms = raffica if raffica is not None else medio
            if ms is not None:
                rec["vento_max"] = round(float(ms) * 3.6, 1)
        except Exception:
            continue
    store = _carica_giorni_file()
    did = str(_wc_id(device_id))
    for dt, rec in list(by_day.items()):
        key = f"wc:{did}|{dt.isoformat()}"
        packed = {"date": dt.isoformat(), "precip": float(rec.get("precip") or 0)}
        for k in ("t_max", "t_min", "t_med", "vento_max"):
            if rec.get(k) is not None:
                packed[k] = rec[k]
        store[key] = packed
    oggi = datetime.now().date()
    inizio_api = min(by_day.keys()) if by_day else oggi
    for i in range(40):
        d = oggi - timedelta(days=i)
        key = f"wc:{did}|{d.isoformat()}"
        if d >= inizio_api or key not in store:
            continue
        old = store.get(key) or {}
        rec = {"date": pd.Timestamp(d), "precip": float(old.get("precip") or 0)}
        for k in ("t_max", "t_min", "t_med", "vento_max"):
            if old.get(k) is not None:
                rec[k] = float(old[k])
        by_day[d] = rec
    st.session_state["mn_giorni"] = store
    try:
        _salva_giorni_file()
    except Exception:
        pass
    if not by_day:
        for i in range(40):
            d = oggi - timedelta(days=i)
            key = f"wc:{did}|{d.isoformat()}"
            old = store.get(key) or {}
            if not old:
                continue
            rec = {"date": pd.Timestamp(d), "precip": float(old.get("precip") or 0)}
            for k in ("t_max", "t_min", "t_med", "vento_max"):
                if old.get(k) is not None:
                    rec[k] = float(old[k])
            by_day[d] = rec
    if not by_day:
        return None
    df = pd.DataFrame(list(by_day.values()))
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    taglio = pd.Timestamp(oggi) - pd.Timedelta(days=30)
    df = df[df["date"] >= taglio]
    return df.sort_values("date")


def _mn_catalogo_file():
    p = Path(__file__).resolve().parent / "mn_centro.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


@st.cache_data(ttl=3600)
def mn_catalogo_pubblico():
    """Elenco dalla pagina pubblica /it/stations-list. Niente token."""
    sess = requests.Session()
    sess.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    rows = []
    try:
        page = sess.get("https://www.meteonetwork.eu/it/stations-list", timeout=30)
        m = re.search(r'csrf-token" content="([^"]+)"', page.text or "")
        csrf = m.group(1) if m else ""
        r = sess.post(
            "https://www.meteonetwork.eu/it/get-elenco-stazioni-tabella",
            headers={
                "X-CSRF-TOKEN": csrf,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.meteonetwork.eu/it/stations-list",
                "Accept": "application/json",
            },
            timeout=15,
        )
        rows = (r.json() or {}).get("stations") or []
    except Exception:
        rows = []
    if not rows:
        return _mn_catalogo_file()
    out = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 7:
            continue
        if str(row[5] or "").upper() != "IT":
            continue
        try:
            lat, lon = float(row[1]), float(row[2])
        except Exception:
            continue
        if not (39.5 <= lat <= 43.5 and 12.0 <= lon <= 16.5):
            continue
        oggi = None
        try:
            if len(row) > 20 and row[20] not in (None, ""):
                oggi = float(row[20])
        except Exception:
            oggi = None
        mese = None
        try:
            if len(row) > 22 and row[22] not in (None, ""):
                mese = float(row[22])
        except Exception:
            mese = None
        nome = str(row[3] or row[4] or row[0])
        citta = str(row[4] or "")
        if citta and citta.lower() not in nome.lower():
            nome = f"{citta} - {nome}"
        out.append({
            "code": str(row[0]),
            "nome": nome,
            "lat": lat,
            "lon": lon,
            "oggi_mm": oggi,
            "mese_mm": mese,
        })
    if len(out) < 50:
        locale = _mn_catalogo_file()
        if locale:
            return locale
    return out


@st.cache_data(ttl=3600)
def fm_pdf_mese(slug, quale="precedente"):
    """PDF mese corrente/precedente del Semaforo Funghimagazine."""
    if not slug:
        return None
    v = datetime.now().strftime("%Y%m%d%H00")
    url = (
        f"https://funghimagazine.it/wp-content/uploads/pdf_stazioni/"
        f"storico_{quale}/{slug}.pdf?v={v}"
    )
    try:
        r = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://funghimagazine.it/lazio-semaforo-dei-funghi/",
                "Accept": "application/pdf,*/*",
            },
            timeout=25,
        )
        if r.status_code != 200 or not (r.content or b"").startswith(b"%PDF"):
            return None
        from pypdf import PdfReader
        import io
        text = ""
        reader = PdfReader(io.BytesIO(r.content))
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
    except Exception:
        return None
    records = []
    for m in re.finditer(
        r"(20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]20\d{2})\s+(-?\d+[.,]?\d*)",
        text,
    ):
        ds, vs = m.group(1), m.group(2).replace(",", ".")
        try:
            mm = float(vs)
        except Exception:
            continue
        dt = None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(ds, fmt)
                break
            except Exception:
                continue
        if dt:
            records.append({"date": pd.Timestamp(dt.date()), "precip": mm})
    if not records:
        return None
    return pd.DataFrame(records).drop_duplicates("date").sort_values("date")


FM_LOCALITA = {
    "Abruzzo": [
        "gran sasso", "campo imperatore", "majella", "popoli", "fara san martino",
        "atessa", "ofena", "ovindoli", "roccaraso", "sulmona", "pescasseroli",
        "scanno", "castel di sangro", "pacentro", "caramanico", "pietracamela",
        "prati di tivo", "blockhaus", "passolanciano",
        "vasto", "gissi", "casalbordino", "torino di sangro", "fossacesia",
        "lanciano", "carunchio", "carpineto", "pollutri", "pallano", "scerni",
    ],
    "Campania": [
        "matese", "piedimonte", "cusano", "irpinia", "cilento", "sarno",
        "calitri", "sapri", "amalfi", "montella", "bagnoli", "laceno",
        "serino", "roccamonfina", "teano", "avellino", "benevento",
        "picentini", "terminio", "alburni",
    ],
    "Molise": [
        "capracotta", "agnone", "matese", "montedimezzo", "collemeluccio",
        "pescopennataro", "frosolone", "guardiaregia", "isernia", "campobasso",
        "mainarde", "trivento", "roccavivara", "vinchiaturo",
    ],
    "Lazio": [
        "terminillo", "leonessa", "cimini", "soratte", "simbruini", "subiaco",
        "ernici", "fiuggi", "lepini", "aurunci", "ausoni", "rieti",
        "viterbo", "frosinone", "cassino", "sora", "alatri", "filettino",
    ],
    "Marche": [
        "sibillini", "ussita", "visso", "sarnano", "amandola", "montemonaco",
        "arquata", "acquasanta", "catria", "nerone", "carpegna", "camerino",
        "fabriano", "cingoli", "conero", "fiastra", "bolognola", "frontone",
    ],
    "Umbria": [
        "norcia", "castelluccio", "valnerina", "cascia", "cucco", "gubbio",
        "subasio", "colfiorito", "spoleto", "orvieto", "trasimeno", "amelia",
        "nocera umbra", "pietralunga", "cerreto", "preci", "terni",
    ],
}

CAPUT_FRIGORIS = {
    "valle castellana": "TE080",
    "rocca santa maria": "TE106",
    "ceppo": "TE106",
}

# stazioni CF Abruzzo con coordinate (descrizione.php + paesi)
CF_STAZIONI = [
    {"id": "AQ081", "nome": "Campo Imperatore Giardino Botanico", "lat": 42.4438, "lon": 13.5583},
    {"id": "AQ010", "nome": "Campo Felice", "lat": 42.2124, "lon": 13.4575},
    {"id": "AQ071", "nome": "Rocca di Cambio", "lat": 42.2367, "lon": 13.4890},
    {"id": "AQ059", "nome": "Ovindoli", "lat": 42.1390, "lon": 13.5230},
    {"id": "AQ024", "nome": "Rocca di Mezzo Rovere", "lat": 42.1634, "lon": 13.5180},
    {"id": "AQ023", "nome": "Fonteavignone", "lat": 42.2000, "lon": 13.5100},
    {"id": "AQ014", "nome": "Pescasseroli", "lat": 41.8080, "lon": 13.7890},
    {"id": "AQ012", "nome": "Rifugio Fioretti", "lat": 42.4550, "lon": 13.5550},
    {"id": "AQ021", "nome": "Piani di Pezza", "lat": 42.1750, "lon": 13.4600},
    {"id": "AQ020", "nome": "Altopiano delle Cinque Miglia", "lat": 41.8700, "lon": 14.0500},
    {"id": "AQ030", "nome": "Monte Genzana", "lat": 41.9510, "lon": 13.8840},
    {"id": "AQ035", "nome": "Scanno Pineta", "lat": 41.9040, "lon": 13.8790},
    {"id": "AQ124", "nome": "Villetta Barrea", "lat": 41.7760, "lon": 13.9230},
    {"id": "AQ015", "nome": "Rifugio Montecristo", "lat": 41.8600, "lon": 13.9800},
    {"id": "AQ077", "nome": "Capestrano", "lat": 42.2680, "lon": 13.7670},
    {"id": "TE080", "nome": "Valle Castellana", "lat": 42.7350, "lon": 13.4970},
    {"id": "TE106", "nome": "Il Ceppo", "lat": 42.6650, "lon": 13.4780},
    {"id": "TE013", "nome": "Rifugio Franchetti", "lat": 42.4700, "lon": 13.5650},
    {"id": "TE127", "nome": "Poggio Umbricchio", "lat": 42.5800, "lon": 13.5200},
    {"id": "CH003", "nome": "Guardiagrele", "lat": 42.1900, "lon": 14.2210},
    {"id": "PE111", "nome": "Farindola", "lat": 42.4430, "lon": 13.8220},
    {"id": "PE079", "nome": "Popoli", "lat": 42.1740, "lon": 13.8320},
    {"id": "PE078", "nome": "Bussi sul Tirino", "lat": 42.2130, "lon": 13.8250},
]


def cf_stazione_vicina(lat, lon, max_km=5.0):
    migliore = None
    for s in CF_STAZIONI:
        d = distanza_km(lat, lon, s["lat"], s["lon"])
        if d <= max_km and (migliore is None or d < migliore["distanza_km"]):
            migliore = {**s, "distanza_km": round(d, 1)}
    return migliore


@st.cache_data(ttl=1800)
def cf_scheda(station_id):
    """Pioggia giornaliera / mensile / annuale da caputfrigoris.it."""
    try:
        r = requests.get(
            f"https://www.caputfrigoris.it/station.php?id={station_id}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=25,
        )
        t = r.text or ""
    except Exception:
        return None
    idx = t.find("Pioggia")
    blocco = t[idx: idx + 900] if idx >= 0 else ""
    nums = re.findall(r"(\d+(?:\.\d+)?)\s*mm", blocco, flags=re.I)
    oggi = mese = anno = None
    try:
        if len(nums) >= 1:
            oggi = float(nums[0])
        if len(nums) >= 2:
            mese = float(nums[1])
        if len(nums) >= 3:
            anno = float(nums[2])
    except Exception:
        return None
    nome = station_id
    m = re.search(r"<title>([^<]+)", t, flags=re.I)
    if m:
        nome = m.group(1).split("-")[0].replace("Stazione:", "").strip() or station_id
    t_max = t_min = t_med = vento = None
    try:
        mmax = re.search(r"Max[^\d]{0,40}(\d+(?:[.,]\d+)?)\s*°C", t, flags=re.I)
        mmin = re.search(r"Min[^\d]{0,40}(\d+(?:[.,]\d+)?)\s*°C", t, flags=re.I)
        if mmax:
            t_max = float(mmax.group(1).replace(",", "."))
        if mmin:
            t_min = float(mmin.group(1).replace(",", "."))
        if t_max is not None and t_min is not None:
            t_med = round((t_max + t_min) / 2, 1)
    except Exception:
        pass
    try:
        mv = re.search(r"(\d+(?:[.,]\d+)?)\s*km/h", t, flags=re.I)
        if mv:
            vento = float(mv.group(1).replace(",", "."))
    except Exception:
        pass
    return {
        "id": station_id, "nome": nome,
        "oggi_mm": oggi, "mese_mm": mese, "anno_mm": anno,
        "t_max": t_max, "t_min": t_min, "t_med": t_med, "vento_max": vento,
    }


@st.cache_data(ttl=3600)
def mn_archivio_pubblico(code, mesi=2):
    """Giorni dalla pagina /archive della stazione. Niente token."""
    if not code:
        return None
    sess = requests.Session()
    sess.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    try:
        scheda = sess.get(
            f"https://www.meteonetwork.eu/it/weather-station/{code}",
            timeout=25,
        )
        page = sess.get(scheda.url.rstrip("/") + "/archive", timeout=25)
        m = re.search(r'csrf-token" content="([^"]+)"', page.text or "")
        csrf = m.group(1) if m else ""
        referer = page.url
    except Exception:
        return None
    oggi = datetime.now().date()
    records = []
    for back in range(int(mesi)):
        d0 = (oggi.replace(day=1) - timedelta(days=32 * back)).replace(day=1)
        try:
            r = sess.post(
                "https://www.meteonetwork.eu/it/update-month-riepilogue",
                headers={
                    "X-CSRF-TOKEN": csrf,
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": referer,
                },
                data={"anno": d0.year, "mese": d0.month, "code": code},
                timeout=25,
            )
            js = r.json()
            rows = js.get("data") if isinstance(js, dict) else None
        except Exception:
            rows = None
        if not rows:
            continue
        for row in rows:
            try:
                g = int(str(row.get("giorno") or "0"))
                raw = row.get("rain")
                txt = str(raw).strip().lower() if raw is not None else ""
                if raw in (None, "") or txt in ("---", "--", "-", "nan", "none", "null"):
                    rain = float("nan")
                else:
                    rain = float(str(raw).replace(",", "."))
                dt = datetime(d0.year, d0.month, g)
            except Exception:
                continue
            rec = {"date": pd.Timestamp(dt.date()), "precip": rain}
            for src, dst in (("tmax", "t_max"), ("tmin", "t_min"), ("tmed", "t_med"), ("wmax", "vento_max")):
                raw_t = row.get(src)
                ttxt = str(raw_t).strip().lower() if raw_t is not None else ""
                if raw_t in (None, "") or ttxt in ("---", "--", "-", "nan", "none", "null"):
                    continue
                try:
                    rec[dst] = float(str(raw_t).replace(",", "."))
                except Exception:
                    pass
            # giorno morto: niente pioggia vera e niente temperature
            if pd.isna(rec.get("precip")) and rec.get("t_max") is None:
                continue
            records.append(rec)
    store = _carica_giorni_file()
    for rec in records:
        d = pd.to_datetime(rec["date"]).date().isoformat()
        key = f"{code}|{d}"
        try:
            rain = float(rec.get("precip"))
            if pd.isna(rain):
                continue
        except Exception:
            continue
        old = store.get(key) or {}
        if not isinstance(old, dict):
            old = {"precip": old, "date": d}
        old_rain = None
        try:
            old_rain = float(old.get("precip") or 0)
        except Exception:
            old_rain = None
        if old_rain is not None and rain <= 0 and old_rain > 0:
            rec["precip"] = old_rain
        tmax = rec.get("t_max")
        if rain > 0.15 or (tmax is not None and 5 <= float(tmax) <= 45):
            packed = {"precip": float(rain), "date": d}
            for k in ("t_max", "t_min", "t_med", "vento_max"):
                if rec.get(k) is not None:
                    packed[k] = rec[k]
            store[key] = packed
    # NON reimportare zeri dallo store: i --- diventavano 0 mm e la stazione sembrava viva
    st.session_state["mn_giorni"] = store
    _salva_giorni_file()
    if not records:
        return None
    return pd.DataFrame(records).drop_duplicates("date").sort_values("date")


@st.cache_data(ttl=900)
def mn_interpolato(token, lat, lon):
    """Griglia MN 2.5 km (stesso dato delle mappe realtime). Serve token STANDARD."""
    if not token:
        return None
    try:
        r = requests.get(
            "https://api.meteonetwork.it/v3/interpolated-realtime",
            headers={"Authorization": f"Bearer {token}", "User-Agent": "PorciniPredictor/1.0"},
            params={"lat": lat, "lon": lon},
            timeout=20,
        )
        if r.status_code != 200:
            return None
        js = r.json()
        row = js[0] if isinstance(js, list) and js else js
        return row if isinstance(row, dict) else None
    except Exception:
        return None


@st.cache_data(ttl=900)
def wc_oggi(device_id):
    s = _wc_session()
    did = _wc_id(device_id)
    try:
        r = s.get(
            "https://app.weathercloud.net/device/values",
            params={"code": did},
            timeout=20,
        )
        js = r.json()
        if not isinstance(js, dict) or "rain" not in js and "temp" not in js:
            return None
        return js
    except Exception:
        return None


WU_WEB_KEY = "53b89abc03d14d7ab89abc03d1dd7ab6"


def wu_vicine(lat, lon):
    try:
        url = (
            "https://api.weather.com/v3/location/near"
            f"?geocode={lat:.4f},{lon:.4f}&product=pws&format=json&apiKey={WU_WEB_KEY}"
        )
        r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
        loc = (r.json() or {}).get("location") or {}
        ids = loc.get("stationId") or []
        out = []
        for i, sid in enumerate(ids):
            try:
                out.append({
                    "code": sid,
                    "nome": (loc.get("stationName") or [sid])[i],
                    "lat": float((loc.get("latitude") or [0])[i]),
                    "lon": float((loc.get("longitude") or [0])[i]),
                    "distanza_km": float((loc.get("distanceKm") or [99])[i]),
                    "qc": (loc.get("qcStatus") or [0])[i],
                })
            except Exception:
                continue
        return out
    except Exception:
        return []


def _wu_precip(metric, obs=None):
    """precipTotal 0.0 è un valore vero: non usare `or` che lo butta via."""
    m = metric or {}
    if m.get("precipTotal") is not None:
        try:
            return max(0.0, float(m.get("precipTotal")))
        except Exception:
            pass
    imp = (obs or {}).get("imperial") or {}
    if imp.get("precipTotal") not in (None, 0, 0.0):
        try:
            return max(0.0, float(imp.get("precipTotal")) * 25.4)
        except Exception:
            pass
    return 0.0


def wu_mese(station_id, days=30):
    sid = str(station_id or "").strip()
    if not sid:
        return None
    oggi = datetime.now().date()
    start = (oggi - timedelta(days=days)).strftime("%Y%m%d")
    end = oggi.strftime("%Y%m%d")
    url = (
        "https://api.weather.com/v2/pws/history/daily"
        f"?stationId={sid}&format=json&units=m&startDate={start}&endDate={end}"
        f"&apiKey={WU_WEB_KEY}&numericPrecision=decimal"
    )
    try:
        r = requests.get(url, timeout=18, headers={"User-Agent": "Mozilla/5.0"})
        obs = (r.json() or {}).get("observations") or []
        recs = []
        for o in obs:
            try:
                d = str(o.get("obsTimeLocal") or o.get("obsTimeUtc") or "")[:10]
                m = o.get("metric") or {}
                v = (
                    m.get("windgustHigh")
                    or m.get("windspeedHigh")
                    or o.get("windgustHigh")
                    or o.get("windspeedHigh")
                    or 0
                )
                try:
                    v = float(v or 0)
                except Exception:
                    v = 0.0
                recs.append({
                    "date": pd.Timestamp(d),
                    "precip": _wu_precip(m, o),
                    "t_max": float(m.get("tempHigh") or 0),
                    "t_min": float(m.get("tempLow") or 0),
                    "t_mean": float(m.get("tempAvg") or 0),
                    "vento_max": v,
                })
            except Exception:
                continue
        if not recs:
            return None
        dfw = pd.DataFrame(recs).sort_values("date")
        try:
            vv = pd.to_numeric(dfw["vento_max"], errors="coerce").fillna(0)
            nz = vv[vv > 0]
            # WU a volte dà m/s: se la mediana è bassa, porto in km/h
            if len(nz) and float(nz.median()) <= 12:
                dfw["vento_max"] = (vv * 3.6).round(1)
        except Exception:
            pass
        return dfw
    except Exception:
        return None


def _pluvio_morto(df):
    """Pluviometro spento o assente: quasi solo zeri."""
    if df is None or "precip" not in getattr(df, "columns", []) or len(df) < 8:
        return True
    p = pd.to_numeric(df["precip"], errors="coerce").fillna(0)
    umidi = int((p >= 0.4).sum())
    tot = float(p.sum())
    # 30 giorni a 0/tracce = niente secchio, non "non ha piovuto"
    if tot < 5.0 and umidi < 2:
        return True
    if umidi == 0:
        return True
    return False


def _mappa_smentisce_stazione(df, lat, lon):
    """Se la stazione ha giorni umidi che sulla mappa MN sul bosco non ci sono, è da scartare."""
    if df is None or "precip" not in getattr(df, "columns", []):
        return None
    mappa = mn_pioggia_mappa(lat, lon, 15) or {}
    mdf = mappa.get("df")
    mm_m = mappa.get("mese_mm")
    if mdf is None or mm_m is None:
        return None
    st = df.copy()
    st["date"] = pd.to_datetime(st["date"], errors="coerce").dt.normalize()
    mp = mdf.copy()
    mp["date"] = pd.to_datetime(mp["date"], errors="coerce").dt.normalize()
    j = st.merge(mp[["date", "precip"]].rename(columns={"precip": "mm_mappa"}), on="date", how="left")
    j["precip"] = pd.to_numeric(j["precip"], errors="coerce").fillna(0)
    j["mm_mappa"] = pd.to_numeric(j["mm_mappa"], errors="coerce").fillna(0)
    umidi = j[j["precip"] >= 4]
    if len(umidi) == 0:
        return None
    ghost = umidi[umidi["mm_mappa"] <= 1.0]
    ghost_mm = float(ghost["precip"].sum()) if len(ghost) else 0.0
    mm_st = float(j["precip"].sum())
    smentita = False
    if len(ghost) >= 3 or (len(ghost) >= 2 and ghost_mm >= 16):
        smentita = True
    if mm_st >= 22 and float(mm_m) < max(10.0, mm_st * 0.30):
        smentita = True
    if not smentita:
        return None
    return mappa



# ---- Wunderground (stesso accesso della tabella web / wundermap, senza key utente) ----
_WU_KEY_CACHE = {"key": None, "ts": 0}

def _wu_api_key():
    """Chiave pubblica usata dal sito WU (dashboard/table)."""
    import time as _t
    now = _t.time()
    if _WU_KEY_CACHE["key"] and now - _WU_KEY_CACHE["ts"] < 3600:
        return _WU_KEY_CACHE["key"]
    try:
        r = requests.get(
            "https://www.wunderground.com/wundermap",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        m = re.search(r'"API_KEY":"([^"]+)"', r.text or "")
        if m:
            _WU_KEY_CACHE["key"] = m.group(1)
            _WU_KEY_CACHE["ts"] = now
            return _WU_KEY_CACHE["key"]
    except Exception:
        pass
    # fallback: chiave client nota (può ruotare)
    return "f6d2efe5720d47ea92efe5720df7eaa8"


def wu_stazioni_vicine(lat, lon, max_km=5.0, limit=15):
    """PWS Wunderground vicino al punto (wundermap / location near)."""
    key = _wu_api_key()
    try:
        r = requests.get(
            "https://api.weather.com/v3/location/near",
            params={
                "geocode": f"{float(lat)},{float(lon)}",
                "product": "pws",
                "format": "json",
                "apiKey": key,
            },
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.wunderground.com/wundermap",
            },
            timeout=20,
        )
        if r.status_code != 200:
            return []
        loc = (r.json() or {}).get("location") or {}
        ids = loc.get("stationId") or []
        names = loc.get("stationName") or []
        lats = loc.get("latitude") or []
        lons = loc.get("longitude") or []
        dists = loc.get("distanceKm") or []
        out = []
        for i, sid in enumerate(ids):
            try:
                la = float(lats[i]) if i < len(lats) else None
                lo = float(lons[i]) if i < len(lons) else None
                d = float(dists[i]) if i < len(dists) else (
                    distanza_km(lat, lon, la, lo) if la is not None and lo is not None else 999
                )
            except Exception:
                continue
            if d > float(max_km):
                continue
            out.append({
                "id": str(sid),
                "nome": str(names[i]) if i < len(names) else str(sid),
                "lat": la,
                "lon": lo,
                "distanza_km": round(d, 2),
            })
        out.sort(key=lambda x: x["distanza_km"])
        return out[:limit]
    except Exception:
        return []


def wu_serie_giornaliera(station_id, days=30):
    """Serie daily dalla stessa API della tabella /dashboard/pws/.../table/.../daily."""
    key = _wu_api_key()
    end = datetime.now().date()
    start = end - timedelta(days=int(days or 30))
    try:
        r = requests.get(
            "https://api.weather.com/v2/pws/history/daily",
            params={
                "stationId": station_id,
                "format": "json",
                "units": "m",
                "startDate": start.strftime("%Y%m%d"),
                "endDate": end.strftime("%Y%m%d"),
                "apiKey": key,
            },
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": f"https://www.wunderground.com/dashboard/pws/{station_id}/table",
                "Accept": "application/json",
            },
            timeout=25,
        )
        if r.status_code != 200:
            return None
        obs = (r.json() or {}).get("observations") or []
        recs = []
        for o in obs:
            try:
                metric = o.get("metric") or {}
                day = str(o.get("obsTimeLocal") or "")[:10]
                if not day:
                    continue
                precip = metric.get("precipTotal")
                if precip is None:
                    precip = 0.0
                recs.append({
                    "date": pd.Timestamp(day),
                    "precip": float(precip or 0),
                    "t_max": metric.get("tempHigh"),
                    "t_min": metric.get("tempLow"),
                    "t_mean": metric.get("tempAvg"),
                    "vento_max": (
                        float(metric.get("windgustHigh") or 0)
                        if metric.get("windgustHigh") is not None
                        else (
                            float(metric.get("windspeedHigh") or 0)
                            if metric.get("windspeedHigh") is not None
                            else None
                        )
                    ),
                })
            except Exception:
                continue
        if len(recs) < 5:
            return None
        return pd.DataFrame(recs).drop_duplicates("date").sort_values("date")
    except Exception:
        return None


def get_weather_data(lat, lon, days=30, mn_token="", quota=None, max_km_stazione=5, mn_codici="", stazioni_mn=None, serie_mn=None, usa_wc=True, nome_zona="", regione=""):
    """Stazioni affidabili entro 5 km (tutte le regioni), poi mappa MN se scoperto.

    Ordine:
      1) Caput Frigoris / MeteoNetwork / WeatherCloud / Wunderground entro max_km (default 5)
      2) Scarta pluviometri morti (quasi solo zeri)
      3) Se nessuna stazione valida → mappa giornaliera MeteoNetwork sul punto
    """
    forecast = None
    soil = None
    vento = riepilogo_vento(None)
    lat = float(lat)
    lon = float(lon)
    days = int(days or 30)
    max_km = float(max_km_stazione if max_km_stazione is not None else 5)
    if max_km <= 0:
        max_km = 5.0
    # utente: non oltre 5 km per stazioni "vicine"
    max_km = min(max_km, 5.0)
    quota_f = float(quota) if quota is not None else None

    candidati = []  # list of dict: score, df, info

    def _info_base(fonte, stazione, dist, q_st, df):
        mm = None
        giorni = []
        if df is not None and len(df) and "precip" in df.columns:
            p = pd.to_numeric(df["precip"], errors="coerce").fillna(0)
            mm = round(float(p.sum()), 1)
            tmp = df.copy()
            tmp["_p"] = pd.to_numeric(tmp["precip"], errors="coerce").fillna(0)
            tmp = tmp[tmp["_p"] >= 0.2].sort_values("date")
            for _, row in tmp.iterrows():
                try:
                    d = str(row.get("date"))[:10]
                    giorni.append(f"{d}: {float(row['_p']):.1f} mm")
                except Exception:
                    pass
            # se non ci sono giorni umidi ma totale > 0, segnala
            if not giorni and mm and mm >= 0.2:
                giorni.append(f"totale 30g: {mm} mm")
        return {
            "fonte": fonte,
            "stazione": stazione or "n/d",
            "distanza_km": round(dist, 2) if dist is not None else None,
            "quota_stazione": q_st,
            "pioggia_stazione_30g": mm,
            "giorni_pluviometro": giorni[-20:],
            "stima_mappa": False,
        }

    def _score_df(df, dist_km):
        if df is None or len(df) < 5 or "precip" not in df.columns:
            return -1
        if _pluvio_morto(df):
            return -1
        p = pd.to_numeric(df["precip"], errors="coerce").fillna(0)
        tot = float(p.sum())
        umidi = int((p >= 0.4).sum())
        # preferisci più giorni, più pioggia reale, distanza minore
        return umidi * 3.0 + min(tot, 120) * 0.15 + max(0, 5.0 - float(dist_km or 5)) * 2.0

    # ---- 1) Caput Frigoris (tutte le regioni dove c'è stazione in CF_STAZIONI) ----
    try:
        cf = cf_stazione_vicina(lat, lon, max_km=max_km)
        if cf:
            scheda = cf_scheda(cf["id"]) or {}
            mese_mm = scheda.get("mese_mm")
            # costruisci serie grezza: se abbiamo solo mese, distribuisci in modo neutro
            # meglio usare store locale se presente
            store = {}
            try:
                store = _carica_giorni_file() or {}
            except Exception:
                store = {}
            recs = []
            oggi = datetime.now().date()
            for i in range(days):
                d = oggi - timedelta(days=i)
                key = f"cf:{cf['id']}|{d.isoformat()}"
                old = store.get(key) or {}
                if old:
                    recs.append({
                        "date": pd.Timestamp(d),
                        "precip": float(old.get("precip") or 0),
                        "t_max": old.get("t_max"),
                        "t_min": old.get("t_min"),
                        "t_mean": old.get("t_med") or old.get("t_mean"),
                    })
            if not recs and mese_mm is not None and float(mese_mm) >= 0:
                # un solo valore mensile noto: metti il totale sull'ultimo giorno del mese
                # e 0 altrove (meglio del nulla; analizza_punto usa la somma)
                for i in range(days):
                    d = oggi - timedelta(days=i)
                    mm = float(mese_mm) if i == 0 else 0.0
                    recs.append({
                        "date": pd.Timestamp(d),
                        "precip": mm,
                        "t_max": scheda.get("t_max"),
                        "t_min": scheda.get("t_min"),
                        "t_mean": scheda.get("t_med"),
                    })
            if recs:
                df_cf = pd.DataFrame(recs).sort_values("date")
                # se solo totale mensile sul giorno 0, non usare _pluvio_morto (umidi=1)
                sc = _score_df(df_cf, cf["distanza_km"])
                if sc < 0 and mese_mm is not None and float(mese_mm) >= 8:
                    sc = 8.0 + min(float(mese_mm), 100) * 0.1
                if sc >= 0:
                    candidati.append({
                        "score": sc + 5.0,  # leggero bonus CF (rete curata)
                        "df": df_cf,
                        "info": _info_base(
                            f"Caput Frigoris · {cf.get('nome')}",
                            cf.get("nome"),
                            cf.get("distanza_km"),
                            None,
                            df_cf,
                        ),
                    })
    except Exception:
        pass

    # ---- 2) MeteoNetwork da archivio locale (tutte le regioni nel catalogo) ----
    try:
        if stazioni_mn is None:
            try:
                stazioni_mn = mn_catalogo_pubblico() or []
            except Exception:
                stazioni_mn = []
            try:
                path = Path(__file__).resolve().parent / "mn_centro.json"
                if path.exists():
                    cat = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(cat, dict):
                        cat = cat.get("stations") or cat.get("data") or list(cat.values())
                    if isinstance(cat, list) and cat:
                        stazioni_mn = cat
            except Exception:
                pass
        vicine = mn_stazioni_vicine(lat, lon, stazioni_mn or [], quota=quota_f, n=8, max_km=max_km)
        store = {}
        try:
            store = _carica_giorni_file() or {}
        except Exception:
            store = {}
        oggi = datetime.now().date()
        for stz in vicine:
            code = str(stz.get("code") or stz.get("id") or "")
            if not code:
                continue
            recs = []
            for i in range(days):
                d = oggi - timedelta(days=i)
                old = store.get(f"{code}|{d.isoformat()}") or {}
                if not old:
                    continue
                recs.append({
                    "date": pd.Timestamp(d),
                    "precip": float(old.get("precip") or 0),
                    "t_max": old.get("t_max"),
                    "t_min": old.get("t_min"),
                    "t_mean": old.get("t_med") or old.get("t_mean"),
                    "vento_max": old.get("vento_max"),
                })
            if len(recs) < 8:
                continue
            df_mn = pd.DataFrame(recs).drop_duplicates("date").sort_values("date")
            sc = _score_df(df_mn, stz.get("distanza_km"))
            if sc < 0:
                continue
            candidati.append({
                "score": sc,
                "df": df_mn,
                "info": _info_base(
                    f"MeteoNetwork · {stz.get('nome') or code}",
                    stz.get("nome") or code,
                    stz.get("distanza_km"),
                    stz.get("quota") or stz.get("altitude"),
                    df_mn,
                ),
            })
    except Exception:
        pass

    # ---- 3) WeatherCloud (catalogo centro-sud, tutte le zone coperte) ----
    if usa_wc:
        try:
            cat_wc = wc_catalogo() or []
            ranked = []
            for s in cat_wc:
                try:
                    d = distanza_km(lat, lon, float(s["lat"]), float(s["lon"]))
                except Exception:
                    continue
                if d > max_km:
                    continue
                ranked.append((d, s))
            ranked.sort(key=lambda x: x[0])
            for d, s in ranked[:6]:
                did = s.get("id") or s.get("code")
                if not did:
                    continue
                try:
                    df_wc = wc_mese_pioggia(did)
                except Exception:
                    df_wc = None
                if df_wc is None or len(df_wc) < 5:
                    try:
                        df_wc = wc_mese_mm(did)
                    except Exception:
                        df_wc = None
                if df_wc is None or len(df_wc) < 5:
                    continue
                sc = _score_df(df_wc, d)
                if sc < 0:
                    continue
                candidati.append({
                    "score": sc,
                    "df": df_wc,
                    "info": _info_base(
                        f"WeatherCloud · {s.get('nome') or did}",
                        s.get("nome") or str(did),
                        d,
                        None,
                        df_wc,
                    ),
                })
        except Exception:
            pass

    # ---- 4) Wunderground (tabella dashboard PWS, come wundermap / FM) ----
    try:
        wu_near = wu_stazioni_vicine(lat, lon, max_km=max_km, limit=12)
        for s in wu_near:
            try:
                df_wu = wu_serie_giornaliera(s["id"], days=days)
            except Exception:
                df_wu = None
            if df_wu is None or len(df_wu) < 5:
                continue
            sc = _score_df(df_wu, s.get("distanza_km"))
            if sc < 0:
                continue
            candidati.append({
                "score": sc + 5.0,  # bonus WU (fonte principale FunghiMagazine)
                "df": df_wu,
                "info": _info_base(
                    f"Wunderground · {s.get('nome')} ({s.get('id')})",
                    f"{s.get('nome')} [{s.get('id')}]",
                    s.get("distanza_km"),
                    None,
                    df_wu,
                ),
            })
    except Exception:
        pass

    # ---- 4b) PDF Semaforo FunghiMagazine (stazioni WU processate da FM) ----
    try:
        reg = (regione or "").strip()
        nome_z = (nome_zona or "").lower()
        candidati_slug = []
        for rname, slugs in (FM_LOCALITA or {}).items():
            if reg and rname.lower() not in reg.lower() and reg.lower() not in rname.lower():
                # se regione non combacia, valuta comunque match per nome
                pass
            for slug in slugs:
                if slug in nome_z or any(p in nome_z for p in slug.split() if len(p) > 4):
                    candidati_slug.append(slug)
        # match generici utili
        for token, slug in [
            ("capracotta", "capracotta"), ("pescasseroli", "pescasseroli"),
            ("roccaraso", "roccaraso"), ("agnone", "agnone"),
            ("sangro", "castel-di-sangro"), ("matese", "piedimonte-matese"),
            ("ovindoli", "ovindoli"), ("scanno", "scanno"),
        ]:
            if token in nome_z:
                candidati_slug.append(slug)
        seen = set()
        for slug in candidati_slug:
            if slug in seen:
                continue
            seen.add(slug)
            df_fm = None
            for quale in ("corrente", "precedente"):
                try:
                    df_fm = fm_pdf_mese(slug, quale=quale)
                except Exception:
                    df_fm = None
                if df_fm is not None and len(df_fm) >= 5:
                    break
            if df_fm is None or len(df_fm) < 5:
                continue
            sc = _score_df(df_fm, 2.0)
            if sc < 0:
                continue
            candidati.append({
                "score": sc + 6.0,  # bonus forte: stazioni curate FM (WU verificate)
                "df": df_fm,
                "info": _info_base(
                    f"FunghiMagazine/WU · {slug}",
                    slug,
                    0.0,
                    None,
                    df_fm,
                ),
            })
    except Exception:
        pass

    # ---- scegli la migliore stazione ----
    candidati = [c for c in candidati if c.get("score", -1) >= 0 and c.get("df") is not None]
    candidati.sort(key=lambda x: -x["score"])

    df = None
    info = None
    if candidati:
        best = candidati[0]
        df = best["df"]
        info = best["info"]
        # se la mappa MN smentisce la stazione, scarta e prova la successiva
        try:
            sm = _mappa_smentisce_stazione(df, lat, lon)
            if sm is not None and len(candidati) > 1:
                best = candidati[1]
                df = best["df"]
                info = best["info"]
            elif sm is not None and sm.get("df") is not None:
                df = sm["df"]
                info = {
                    "fonte": "Mappa MeteoNetwork (stazione smentita)",
                    "stazione": "pixel mappa",
                    "distanza_km": 0,
                    "quota_stazione": None,
                    "pioggia_stazione_30g": sm.get("mese_mm"),
                    "giorni_pluviometro": [],
                    "stima_mappa": True,
                }
        except Exception:
            pass

    # ---- 5) Zone scoperte: mappa giornaliera MeteoNetwork (poi DPC/ICON) ----
    if df is None or _pluvio_morto(df):
        try:
            mappa = mn_pioggia_mappa(lat, lon, 15) or {}
            mdf = mappa.get("df")
            mm_m = float(mappa.get("mese_mm") or 0) if mappa else 0
            if mdf is not None and len(mdf) >= 5:
                df = mdf.copy()
                giorni = []
                tmp = df.copy()
                tmp["_p"] = pd.to_numeric(tmp["precip"], errors="coerce").fillna(0)
                for _, row in tmp[tmp["_p"] >= 0.2].sort_values("date").iterrows():
                    giorni.append(f"{str(row.get('date'))[:10]}: {float(row['_p']):.1f} mm")
                info = {
                    "fonte": "Mappa giornaliera MeteoNetwork",
                    "stazione": "pixel mappa MN",
                    "distanza_km": 0,
                    "quota_stazione": None,
                    "pioggia_stazione_30g": round(mm_m, 1),
                    "giorni_pluviometro": giorni[-20:],
                    "stima_mappa": True,
                }
        except Exception:
            pass
        if df is None or _pluvio_morto(df):
            try:
                dpc = dpc_serie_giorni(lat, lon, giorni=min(days, 20))
                if dpc is not None and len(dpc) >= 8 and not _pluvio_morto(dpc):
                    df = dpc.copy()
                    p = pd.to_numeric(df["precip"], errors="coerce").fillna(0)
                    giorni = []
                    for _, row in df.iterrows():
                        try:
                            if float(row.get("precip") or 0) >= 0.2:
                                giorni.append(f"{str(row.get('date'))[:10]}: {float(row['precip']):.1f} mm")
                        except Exception:
                            pass
                    info = {
                        "fonte": "Radar DPC (cumulata pluviometri)",
                        "stazione": "cella radar DPC",
                        "distanza_km": 0,
                        "quota_stazione": None,
                        "pioggia_stazione_30g": round(float(p.sum()), 1),
                        "giorni_pluviometro": giorni[-20:],
                        "stima_mappa": True,
                    }
            except Exception:
                pass

    if info is None:
        info = {
            "fonte": "nessuna stazione ≤5 km né mappa MN",
            "stazione": "n/d",
            "distanza_km": None,
            "quota_stazione": None,
            "pioggia_stazione_30g": None,
            "giorni_pluviometro": [],
            "stima_mappa": False,
        }

    if df is not None and len(df) and "precip" in df.columns:
        vento = riepilogo_vento(df)
    return df, info, forecast, soil, vento



def specie_porcini(tipo_bosco, quota=1000, t_max_media=20.0, mese=None):
    """4 specie da FunghiMagazine: albero + quota + mese + caldo."""
    if mese is None:
        mese = datetime.now().month
    tipo = (tipo_bosco or "").lower()
    q = float(quota or 1000)
    t = float(t_max_media or 20)

    # alberi: chi può uscire in quel bosco (articolo FM)
    base = {
        "faggio": ["estatino", "edulis", "pinicola"],
        "castagno": ["estatino", "edulis", "pinicola", "aereus"],
        "quercia": ["estatino", "aereus", "edulis"],
        "leccio": ["aereus", "estatino", "edulis"],
        "misto_carpino_quercia": ["estatino", "aereus", "edulis"],
        "abete_bianco": ["pinicola", "edulis", "estatino"],
        "abete_rosso": ["pinicola", "edulis"],
    }
    possibili = list(base.get(tipo, ["estatino", "edulis"]))
    # Centro-Sud: aereus su quercia/castagno, non in faggeta
    if tipo in ("quercia", "leccio", "misto_carpino_quercia") and t < 18:
        if "pinicola" not in possibili:
            possibili.append("pinicola")

    # stagione
    if mese in (3, 4, 5):
        stagione = {"estatino": 3, "pinicola": 3, "aereus": 1, "edulis": 1}
    elif mese in (6, 7, 8):
        stagione = {"aereus": 3, "estatino": 3, "edulis": 1, "pinicola": 1}
    elif mese == 9:
        stagione = {"estatino": 3, "edulis": 2, "aereus": 2, "pinicola": 2}
    elif mese in (10, 11):
        stagione = {"edulis": 3, "pinicola": 3, "estatino": 1, "aereus": 1}
    else:
        stagione = {"edulis": 2, "pinicola": 2, "estatino": 0, "aereus": 0}

    # clima: estatino/aereus amano il caldo; edulis/pinicola il fresco
    clima = {"estatino": 0, "aereus": 0, "edulis": 0, "pinicola": 0}
    if t >= 26:
        clima["aereus"] += 2
        clima["estatino"] += 2
        clima["edulis"] -= 1
        clima["pinicola"] -= 2
    elif t >= 22:
        clima["estatino"] += 2
        clima["aereus"] += 1
    elif 16 <= t <= 22:
        clima["edulis"] += 2
        clima["pinicola"] += 1
        clima["estatino"] += 1
    else:
        clima["pinicola"] += 2
        clima["edulis"] += 1
        clima["aereus"] -= 2
        clima["estatino"] -= 1
    if q >= 1200 and mese in (6, 7, 8, 9):
        clima["estatino"] += 2
        clima["edulis"] += 1
        clima["pinicola"] += 1
    elif q >= 1400:
        clima["pinicola"] += 2
        clima["edulis"] += 1
        clima["aereus"] -= 1
    elif q <= 600:
        clima["aereus"] += 1
        if mese in (6, 7, 8):
            clima["estatino"] -= 1
        else:
            clima["estatino"] += 1
        clima["pinicola"] -= 1

    nomi = {
        "estatino": "Estatino (B. reticulatus)",
        "aereus": "Nero / bronzino (B. aereus)",
        "edulis": "Chiaro tardivo (B. edulis)",
        "pinicola": "Pinicola (B. pinophilus)",
    }
    out = []
    for sp in possibili:
        punti = stagione.get(sp, 0) + clima.get(sp, 0)
        if punti >= 4:
            stato = "probabile"
        elif punti >= 2:
            stato = "possibile"
        else:
            stato = "fuori stagione"
        out.append({"id": sp, "nome": nomi[sp], "stato": stato, "punti": punti})
    out.sort(key=lambda x: -x["punti"])
    return out


def _soglia_spugnata(t_max_media=20.0, siccita=False):
    """Più caldo e più siccità prima, più mm servono. Base ~40 mm."""
    t = float(t_max_media or 20)
    soglia = 40.0
    if t >= 28:
        soglia = 58.0
    elif t >= 25:
        soglia = 50.0
    elif t >= 22:
        soglia = 44.0
    elif t <= 16:
        soglia = 34.0
    if siccita:
        soglia += 10.0
    return soglia


def _mm_efficaci(mm):
    """Pioggia moderata penetra; i diluvi scivolano."""
    mm = float(mm or 0)
    if mm <= 0:
        return 0.0
    if 3 <= mm <= 18:
        return mm
    if mm > 18:
        return 18.0 + (mm - 18.0) * 0.45
    return mm * 0.8


def giorni_attesa_bosco(tipo_bosco, t_max_media=20.0):
    """Faggio ~14 gg, castagno ~12, quercia ~10. Il caldo accorcia un filo."""
    t = tipo_bosco or "faggio"
    if t in ("faggio", "abete_bianco", "abete_rosso"):
        g = 14
    elif t == "castagno":
        g = 12
    else:
        g = 10
    tm = float(t_max_media or 20)
    if tm >= 26:
        g = max(8, g - 2)
    elif tm <= 16:
        g += 2
    return g


def trova_buttate(df, giorni_attesa, t_max_media=20.0, fattore_v=1.0, tipo_bosco="faggio", quota=1000, soil=None):
    """Spugnata ~40 mm (più se caldo/siccità), meglio distribuita.
    Nascite dopo 14/12/10 gg. Durata media 2 settimane, non un mese."""
    if df is None or len(df) == 0 or "precip" not in df.columns:
        return []
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"]).dt.normalize()
    d["precip"] = pd.to_numeric(d["precip"], errors="coerce").fillna(0)
    d = d.sort_values("date")
    eventi = []
    acc = 0.0
    acc_eff = 0.0
    n_gg = 0
    start = None
    last = None
    giorni_cluster = []
    for _, row in d.iterrows():
        mm = float(row["precip"])
        giorno = row["date"]
        if mm >= 1.5:
            if start is None:
                start = giorno
                acc = mm
                acc_eff = _mm_efficaci(mm)
                n_gg = 1
                giorni_cluster = [mm]
            elif last is not None and (giorno - last).days <= 4:
                # già una spugnata e 2+ giorni di pausa: nuova onda, non un unico blocco
                if acc_eff >= 38 and (giorno - last).days >= 2:
                    eventi.append((last or start, acc, acc_eff, n_gg, start))
                    start = giorno
                    acc = mm
                    acc_eff = _mm_efficaci(mm)
                    n_gg = 1
                    giorni_cluster = [mm]
                else:
                    acc += mm
                    acc_eff += _mm_efficaci(mm)
                    n_gg += 1
                    giorni_cluster.append(mm)
            else:
                eventi.append((last or start, acc, acc_eff, n_gg, start))
                start = giorno
                acc = mm
                acc_eff = _mm_efficaci(mm)
                n_gg = 1
                giorni_cluster = [mm]
            last = giorno
        elif start is not None and last is not None and (giorno - last).days > 4:
            eventi.append((last, acc, acc_eff, n_gg, start))
            start, acc, acc_eff, n_gg, last = None, 0.0, 0.0, 0, None
            giorni_cluster = []
    if start is not None:
        eventi.append((last or start, acc, acc_eff, n_gg, start))

    oggi = pd.Timestamp(datetime.now().date())
    out = []
    for data_evt, mm, mm_eff, n_gg, data_start in eventi:
        prec_prima = d[(d["date"] < pd.Timestamp(data_start)) & (d["date"] >= pd.Timestamp(data_start) - pd.Timedelta(days=12))]
        siccita = True
        if len(prec_prima):
            siccita = float(prec_prima["precip"].sum()) < 8
        soglia = _soglia_spugnata(t_max_media, siccita)
        terreno_umido = False
        if out:
            prev_pioggia = pd.to_datetime(out[-1]["data_pioggia"])
            if (pd.Timestamp(data_start) - prev_pioggia).days <= 22:
                terreno_umido = True
        ottimale = (16 <= float(t_max_media or 20) <= 24) and float(fattore_v or 1) >= 0.7
        if terreno_umido:
            soglia *= 0.52 if ottimale else 0.62
        if mm_eff < soglia and mm < soglia:
            continue
        # durata: media 14 gg. Tanta acqua ben distribuita: fino a 17-18, mai un mese
        durata = 14
        if mm_eff >= 70 and n_gg >= 4:
            durata = 17
        elif mm_eff >= 50 and n_gg >= 3:
            durata = 15
        elif mm_eff < soglia + 5:
            durata = 12
        if tipo_bosco in ("faggio", "abete_bianco", "abete_rosso"):
            durata += 1
        if quota and quota >= 1200:
            durata += 1
        if t_max_media >= 27:
            durata = round(durata * 0.72)
        elif t_max_media >= 24:
            durata = round(durata * 0.88)
        if fattore_v < 0.45:
            durata = round(durata * 0.65)
        elif fattore_v < 0.7:
            durata = round(durata * 0.82)
        if soil is not None:
            try:
                s = float(soil)
                if s < 0.18:
                    durata = round(durata * 0.75)
                elif 0.22 <= s <= 0.38:
                    durata = min(18, durata + 1)
            except Exception:
                pass
        durata = int(max(8, min(18, durata)))
        attesa = int(giorni_attesa)
        if terreno_umido and ottimale:
            attesa = max(7, attesa - 3)
        elif terreno_umido:
            attesa = max(8, attesa - 1)
        inizio = pd.Timestamp(data_evt) + pd.Timedelta(days=attesa)
        fine = inizio + pd.Timedelta(days=durata)
        dopo = d[d["date"] >= pd.Timestamp(data_evt)]
        ultima_umida = None
        if len(dopo):
            umide = dopo[dopo["precip"] >= 4]
            if len(umide):
                ultima_umida = pd.to_datetime(umide["date"].max()).normalize()
        if ultima_umida is not None and int((oggi - ultima_umida).days) >= 12:
            fine = min(fine, ultima_umida + pd.Timedelta(days=12))
        attiva = bool(inizio.normalize() <= oggi <= fine.normalize())
        if ultima_umida is not None and (oggi - ultima_umida).days >= 12:
            attiva = False
        incrocio = False
        if out:
            p = out[-1]
            if pd.to_datetime(p["inizio"]) <= fine and pd.to_datetime(p["fine"]) >= inizio:
                incrocio = True
                p["incrocio"] = True
        out.append({
            "pioggia_mm": round(float(mm), 1),
            "pioggia_efficace": round(float(mm_eff), 1),
            "giorni_pioggia": int(n_gg),
            "soglia_mm": round(soglia, 0),
            "data_pioggia": pd.Timestamp(data_evt).date().isoformat(),
            "inizio": inizio.date().isoformat(),
            "fine": fine.date().isoformat(),
            "attiva": attiva,
            "incrocio": incrocio,
            "onda": len(out) + 1,
            "in_attesa": bool(inizio.normalize() > oggi),
            "giorni_alla_nascita": int((inizio.normalize() - oggi).days) if inizio.normalize() > oggi else 0,
            "giorni_dal_inizio": int((oggi - inizio.normalize()).days) + 1 if attiva else 0,
            "giorni_alla_fine": int((fine.normalize() - oggi).days) if attiva else None,
        })
    return out


def stato_buttata(buttate, precip_totale=0, giorni_attesa=13):
    """Fase chiara: in attesa / in corso / finita / serve acqua."""
    oggi = pd.Timestamp(datetime.now().date())
    vuoto = {
        "fase": "SERVE ACQUA",
        "testo": (
            f"Buttata non partita. Servono circa 40 mm (di più se fa caldo o c'era siccità), "
            f"meglio in più giorni moderati, poi {giorni_attesa} giorni di attesa."
        ),
    }
    if not buttate:
        if float(precip_totale or 0) < 20:
            return vuoto
        return {
            "fase": "ACQUA DEBOLE",
            "testo": (
                f"Pioggia in 30g {float(precip_totale):.0f} mm, ma non una spugnata da ~40 mm "
                "distribuita. Serve altra acqua per far partire una buttata."
            ),
        }
    attive = [b for b in buttate if b.get("attiva")]
    future = [b for b in buttate if b.get("in_attesa") or pd.to_datetime(b["inizio"]) > oggi]
    if attive:
        def _riga(b):
            return (
                f"{b['pioggia_mm']} mm il {b['data_pioggia']} → "
                f"{b['inizio']}–{b['fine']}"
            )
        if len(attive) >= 2 or (attive and future):
            pezzi = [_riga(b) for b in attive]
            extra = ""
            if future:
                n = future[0]
                extra = (
                    f" Seconda onda in arrivo dal {n['inizio']} "
                    f"(ancora {n.get('giorni_alla_nascita', '?')} gg, pioggia {n['pioggia_mm']} mm il {n['data_pioggia']})."
                )
            return {
                "fase": "INCROCIO",
                "testo": (
                    "Buttate INCROCIATE: una nuova si sovrappone alla prima "
                    "(ripioggia durante la buttata, terreno già umido). "
                    + " · ".join(pezzi) + extra
                ),
            }
        b = attive[-1]
        restano = b.get("giorni_alla_fine")
        giorno = b.get("giorni_dal_inizio") or 1
        return {
            "fase": "IN CORSO",
            "testo": (
                f"Buttata INIZIATA il {b['inizio']} — oggi è il giorno {giorno}. "
                f"Resta aperta fino al {b['fine']}"
                + (f" ({restano} giorni)" if restano is not None else "")
                + f". Innescata da {b['pioggia_mm']} mm il {b['data_pioggia']}. "
                "Se ripiove abbastanza con temperature ok, può incrociarsi una seconda."
            ),
        }
    if future:
        b = future[0]
        manca = b.get("giorni_alla_nascita")
        if manca is None:
            manca = int((pd.to_datetime(b["inizio"]) - oggi).days)
        return {
            "fase": "IN ATTESA",
            "testo": (
                f"La buttata NON è ancora nata. Pioggia buona {b['pioggia_mm']} mm il {b['data_pioggia']}. "
                f"Attendi ancora {manca} giorni — nascite previste dal {b['inizio']} al {b['fine']}."
            ),
        }
    b = buttate[-1]
    return {
        "fase": "FINITA",
        "testo": (
            f"Buttata FINITA il {b['fine']} (era partita il {b['inizio']} "
            f"dopo {b['pioggia_mm']} mm il {b['data_pioggia']}). "
            "Serve una nuova spugnata per farne riniziare un'altra."
        ),
    }


def _completa_vento(df, lat, lon, vento=None):
    """Vento da stazione (WU/MN); se manca, mappe MN; ultimo il modello."""
    def _ok(v):
        return v and v.get("vento_max_10g") not in (None, 0) and v.get("nota_vento") != "Vento non disponibile"

    if df is not None and "vento_max" in getattr(df, "columns", []):
        try:
            vv = pd.to_numeric(df["vento_max"], errors="coerce").fillna(0)
            if float(vv.max()) > 0:
                v0 = riepilogo_vento(df)
                if _ok(v0):
                    return df, v0
        except Exception:
            pass
    # mappe MN vento sul bosco
    try:
        mappa = mn_pioggia_mappa(lat, lon, 15) or {}
        mdf = mappa.get("df")
        if mdf is not None and "vento_max" in mdf.columns:
            if df is None or len(df) == 0:
                df = mdf
            else:
                df = df.copy()
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                m2 = mdf.copy()
                m2["date"] = pd.to_datetime(m2["date"], errors="coerce")
                if "vento_max" in df.columns:
                    df = df.drop(columns=["vento_max"])
                df = df.merge(m2[["date", "vento_max"]], on="date", how="left")
            v0 = riepilogo_vento(df)
            if _ok(v0):
                return df, v0
    except Exception:
        pass
    try:
        _st, _fc, _so, vento_om = get_openmeteo_bundle(lat, lon, 30)
        if df is not None and _st is not None and "vento_max" in _st.columns:
            df = df.copy()
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            _st = _st.copy()
            _st["date"] = pd.to_datetime(_st["date"], errors="coerce")
            if "vento_max" in df.columns:
                df = df.drop(columns=["vento_max"])
            df = df.merge(_st[["date", "vento_max"]], on="date", how="left")
            v0 = riepilogo_vento(df)
            if _ok(v0):
                return df, v0
        if _ok(vento_om):
            return df, vento_om
    except Exception:
        pass
    return df, vento or riepilogo_vento(df if df is not None and "vento_max" in getattr(df, "columns", []) else None)


def finestra_uscita(giorni_dalla_pioggia, giorni_attesa, forecast):
    """Stima i prossimi giorni utili in base al ritardo dalla spugnata e alla previsione."""
    if giorni_dalla_pioggia is None or giorni_dalla_pioggia >= 99:
        return "Attendi una buona pioggia (≥30 mm cumulati)"

    inizio = giorni_attesa - 3
    fine = giorni_attesa + 5
    oggi_offset = giorni_dalla_pioggia

    if inizio <= oggi_offset <= fine:
        stato = "Finestra aperta adesso"
    elif oggi_offset < inizio:
        manca = inizio - oggi_offset
        stato = f"Ancora presto — prova tra {manca}–{manca + 4} giorni"
    else:
        stato = "Finestra in chiusura / già passata"

    pioggia_prevista = 0.0
    if forecast is not None and len(forecast):
        pioggia_prevista = float(forecast["precip"].sum())
        if pioggia_prevista >= 20:
            stato += f" · in arrivo ~{pioggia_prevista:.0f} mm (nuova spugnata)"
    return stato


def calcola_punteggio(df, tipo_bosco, regole, quota=1000, soil=None, forecast=None, vento=None):
    df = _ultimi_30g(df)
    if df is None or len(df) < 5:
        return 0, "Dati insufficienti", {}

    precip_totale = float(df["precip"].sum())
    giorni_con_pioggia = int((df["precip"] > 1).sum())
    def _media(col, fallback):
        if df is None or col not in df.columns:
            return fallback, None
        v = float(pd.to_numeric(df[col], errors="coerce").mean())
        if pd.isna(v):
            return fallback, None
        return v, round(v, 1)

    t_max_media, t_max_view = _media("t_max", 20.0)
    t_min_media, t_min_view = _media("t_min", 12.0)
    _, t_med_view = _media("t_med", None)

    # ultimi 10 giorni pesano di più del mese intero
    coda = df.tail(10)
    precip_10g = float(coda["precip"].sum())

    pioggia_min = regole["pioggia_min"]
    pioggia_max = regole["pioggia_max"]

    # in quota le temperature ideali sono più basse
    if quota >= 1400:
        t_max_ok = (18, 24)
        t_min_ok = (8, 14)
    elif quota >= 1000:
        t_max_ok = (20, 26)
        t_min_ok = (10, 16)
    else:
        t_max_ok = (22, 28)
        t_min_ok = (12, 18)

    if t_max_media > 27:
        pioggia_min += 15
        pioggia_max += 20
    elif t_max_media > 25:
        pioggia_min += 8
        pioggia_max += 12

    if precip_totale < pioggia_min * 0.5:
        score_pioggia = 0
    elif precip_totale < pioggia_min:
        score_pioggia = 20 * (precip_totale / pioggia_min)
    elif precip_totale <= pioggia_max:
        score_pioggia = 50
        if giorni_con_pioggia >= 5:
            score_pioggia = 55
        if giorni_con_pioggia >= 8:
            score_pioggia = 60
    else:
        score_pioggia = max(10, 40 - (precip_totale - pioggia_max) * 0.5)

    if precip_10g >= 15:
        score_pioggia = min(65, score_pioggia + 5)
    # meglio acqua distribuita (penetra) che un temporale solo
    if 4 <= giorni_con_pioggia <= 12 and precip_totale >= 35:
        score_pioggia = min(70, score_pioggia + 6)

    score_temp = 0
    if t_max_ok[0] <= t_max_media <= t_max_ok[1]:
        score_temp += 25
    elif t_max_ok[0] - 3 <= t_max_media <= t_max_ok[1] + 3:
        score_temp += 15
    else:
        score_temp += 5

    if t_min_ok[0] <= t_min_media <= t_min_ok[1]:
        score_temp += 15
    elif t_min_ok[0] - 3 <= t_min_media <= t_min_ok[1] + 3:
        score_temp += 10
    else:
        score_temp += 3

    # attesa: faggio 14, castagno 12, quercia 10 — il caldo accorcia un filo
    specie = specie_porcini(tipo_bosco, quota, t_max_media)
    giorni_attesa = giorni_attesa_bosco(tipo_bosco, t_max_media)

    vento = vento or riepilogo_vento(df if df is not None and "vento_max" in df.columns else None)
    fattore_v = float(vento.get("fattore_vento") or 1.0)
    buttate = trova_buttate(
        df, giorni_attesa, t_max_media, fattore_v,
        tipo_bosco=tipo_bosco, quota=quota, soil=soil,
    )
    attive = [b for b in buttate if b.get("attiva")]
    giorni_dalla_pioggia = 99
    if buttate:
        ultima = pd.to_datetime(buttate[-1]["data_pioggia"])
        giorni_dalla_pioggia = int((pd.Timestamp(datetime.now().date()) - ultima.normalize()).days)

    if len(attive) >= 2:
        score_tempo = 28
    elif attive:
        score_tempo = 22
    elif buttate:
        # c'è stata acqua ma la buttata è finita o non è ancora nata
        prossime = [b for b in buttate if pd.to_datetime(b["inizio"]) > pd.Timestamp(datetime.now().date())]
        score_tempo = 12 if prossime else 4
    else:
        score_tempo = 3

    score_suolo = 0
    if soil is not None:
        # valori volumetrici tipici 0.15–0.40 m3/m3
        if 0.22 <= soil <= 0.38:
            score_suolo = 10
        elif 0.18 <= soil <= 0.42:
            score_suolo = 5

    # il vento persistente brucia l'effetto della pioggia e del suolo
    umido = (score_pioggia + score_tempo + score_suolo) * fattore_v
    punteggio_totale = min(100, umido + score_temp * (0.45 + 0.55 * fattore_v))
    if attive:
        pezzi = [f"{b['pioggia_mm']} mm il {b['data_pioggia']} (fino al {b['fine']})" for b in attive]
        consiglio = "Buttata aperta: " + " · ".join(pezzi)
        if len(attive) >= 2:
            consiglio = "Buttate incrociate · " + consiglio
    elif buttate:
        ultime = buttate[-1]
        if pd.to_datetime(ultime["inizio"]) > pd.Timestamp(datetime.now().date()):
            consiglio = f"Buttata in arrivo dal {ultime['inizio']} (pioggia {ultime['pioggia_mm']} mm il {ultime['data_pioggia']})"
        else:
            consiglio = f"Buttata chiusa il {ultime['fine']} — serve una nuova spugnata"
    else:
        consiglio = finestra_uscita(giorni_dalla_pioggia, giorni_attesa, forecast)
    attese = [s for s in specie if s["stato"] in ("probabile", "possibile")]
    if attese:
        txt_sp = ", ".join(f"{s['nome']} ({s['stato']})" for s in attese[:3])
        consiglio = f"Specie: {txt_sp} · " + consiglio
    if fattore_v < 0.5:
        consiglio = vento.get("nota_vento", "Vento secco") + " · " + consiglio
    sb = stato_buttata(buttate, precip_totale, giorni_attesa)

    dettaglio = {
        "precip_totale_30g": round(precip_totale, 1),
        "precip_10g": round(precip_10g, 1),
        "giorni_con_pioggia": giorni_con_pioggia,
        "t_max_media": t_max_view if t_max_view is not None else "n/d",
        "t_min_media": t_min_view if t_min_view is not None else "n/d",
        "t_med_media": t_med_view if t_med_view is not None else "n/d",
        "giorni_dalla_buona_pioggia": giorni_dalla_pioggia if giorni_dalla_pioggia < 99 else "n/d",
        "giorni_attesa_consigliati": giorni_attesa,
        "umidita_suolo": soil if soil is not None else "n/d",
        "consiglio": consiglio,
        "vento_medio_10g": vento.get("vento_medio_10g"),
        "vento_max_10g": vento.get("vento_max_10g"),
        "giorni_vento_20": vento.get("giorni_oltre_20"),
        "giorni_vento_30": vento.get("giorni_oltre_30"),
        "giorni_vento_consecutivi": vento.get("giorni_consecutivi_venti"),
        "fattore_vento": vento.get("fattore_vento"),
        "nota_vento": vento.get("nota_vento"),
        "picchi_vento": vento.get("picchi_vento") or [],
        "picco_max_data": vento.get("picco_max_data"),
        "picco_max_kmh": vento.get("picco_max_kmh"),
        "buttate": buttate,
        "buttate_attive": len(attive),
        "stato_buttata": sb["fase"],
        "stato_buttata_testo": sb["testo"],
        "specie": specie,
        "specie_testo": ", ".join(
            f"{s['nome']} ({s['stato']})" for s in specie if s["stato"] != "fuori stagione"
        ) or "nessuna in stagione",
    }
    intercetta = {
        "faggio": 0.72, "castagno": 0.75, "quercia": 0.73, "leccio": 0.68,
        "misto_carpino_quercia": 0.74, "abete_bianco": 0.65, "abete_rosso": 0.64,
    }.get(str(tipo_bosco or "").lower(), 0.72)
    efficace = round(float(precip_totale) * intercetta, 1) if precip_totale else 0.0
    suolo8 = suolo20 = None
    if isinstance(soil, dict):
        suolo8 = soil.get("umidita_8cm") or soil.get("soil_moisture_0_to_7cm") or soil.get("u8")
        suolo20 = soil.get("umidita_20cm") or soil.get("soil_moisture_7_to_28cm") or soil.get("u20")
    manca = []
    if precip_totale < 40:
        manca.append(f"acqua 30g {precip_totale:.0f} mm su 40")
    if t_min_view is not None:
        try:
            if float(t_min_view) > 14:
                manca.append(f"minime alte ({float(t_min_view):.1f} °C)")
        except Exception:
            pass
    if fattore_v < 0.6:
        manca.append("vento persistente che asciuga")
    if not attive:
        manca.append("nessuna buttata aperta")
    dettaglio["pioggia_lorda_30g"] = round(float(precip_totale), 1)
    dettaglio["pioggia_efficace"] = efficace
    dettaglio["intercetta_chioma"] = intercetta
    dettaglio["suolo_8cm"] = suolo8 if suolo8 is not None else "n/d"
    dettaglio["suolo_20cm"] = suolo20 if suolo20 is not None else "n/d"
    dettaglio["cosa_manca"] = " · ".join(manca) if manca else "fattori allineati"

    # senza buttata aperta non è verde, anche con 60 mm a inizio mese
    if not attive:
        punteggio_totale = min(punteggio_totale, 48)
        dettaglio["consiglio"] = consiglio
    # Poca acqua nel mese: non può essere una buttata "ALTA"
    if precip_totale < 25:
        punteggio_totale = min(punteggio_totale, 42)
        consiglio = f"Poca pioggia in 30g ({precip_totale:.0f} mm) · " + consiglio
        dettaglio["consiglio"] = consiglio

    if punteggio_totale >= 70:
        livello = "🟢 ALTO - condizioni molto buone"
    elif punteggio_totale >= 50:
        livello = "🟡 MEDIO - condizioni discrete"
    elif punteggio_totale >= 30:
        livello = "🟠 BASSO - ancora presto o condizioni deboli"
    else:
        livello = "🔴 SCARSO - condizioni non favorevoli"

    return punteggio_totale, livello, dettaglio


def invia_email(destinatario, oggetto, corpo, smtp_user, smtp_pass):
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = destinatario
        msg["Subject"] = oggetto
        msg.attach(MIMEText(corpo, "plain"))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return True, "Email inviata con successo!"
    except Exception as e:
        return False, f"Errore invio email: {str(e)}"


def analizza_punto(p, regole, mn_token, max_km_stazione=5, mn_codici="", stazioni_mn=None, serie_mn=None, usa_wc=True):
    p = dict(p)
    p["tipo"] = classifica_bosco(
        p.get("nome"), p.get("quota"), p.get("regione"), p.get("lat"), p.get("tipo")
    )
    df, info_meteo, forecast, soil, vento = get_weather_data(
        p["lat"], p["lon"], days=30, mn_token=mn_token or "",
        quota=p.get("quota"), max_km_stazione=max_km_stazione,
        mn_codici=mn_codici, stazioni_mn=stazioni_mn, serie_mn=serie_mn,
        usa_wc=usa_wc, nome_zona=p.get("nome") or "", regione=p.get("regione") or "",
    )
    df = _ultimi_30g(df)
    info_meteo = info_meteo or {}
    df, vento = _completa_vento(df, p["lat"], p["lon"], vento)
    # stazione con vento/temp ma pluviometro spento (es. WU IFERRIER5 = 0 mm per 30g)
    try:
        mm_now = 0.0
        if df is not None and "precip" in df.columns:
            mm_now = float(pd.to_numeric(df["precip"], errors="coerce").fillna(0).sum())
        if (not info_meteo.get("stima_mappa")) and (df is None or _pluvio_morto(df) or mm_now < 5):
            mappa = mn_pioggia_mappa(p["lat"], p["lon"], 15) or {}
            mm_m = float(mappa.get("mese_mm") or 0) if mappa else 0
            if mappa and mappa.get("df") is not None and len(mappa["df"]) and mm_m >= 8:
                keep = df.copy() if df is not None else None
                df = mappa["df"].copy()
                if keep is not None:
                    try:
                        keep["date"] = pd.to_datetime(keep["date"], errors="coerce")
                        df["date"] = pd.to_datetime(df["date"], errors="coerce")
                        cols = [c for c in ("t_max", "t_min", "t_mean", "t_med", "vento_max") if c in keep.columns]
                        if cols:
                            if "vento_max" in df.columns:
                                df = df.drop(columns=["vento_max"])
                            df = df.merge(keep[["date"] + cols], on="date", how="left")
                    except Exception:
                        pass
                stn = info_meteo.get("stazione") or "stazione"
                info_meteo["fonte"] = (
                    f"Pluviometro assente/a 0 mm ({stn}) · pioggia mappe MN {mm_m:.0f} mm"
                )
                info_meteo["stima_mappa"] = True
                info_meteo["pioggia_stazione_30g"] = mm_m
                info_meteo["giorni_pluviometro"] = [
                    f"{pd.to_datetime(rr['date']).date()}: {float(rr['precip']):.1f} mm"
                    for _, rr in mappa["df"].iterrows()
                    if float(rr.get("precip") or 0) >= 0.2
                ]
                if "vento_max" in df.columns:
                    vento = riepilogo_vento(df)
    except Exception:
        pass
    # stazione vs mappa MN sul bosco: se i mm della stazione non ci sono in mappa, uso la mappa
    try:
        if df is not None and not info_meteo.get("stima_mappa"):
            mappa = _mappa_smentisce_stazione(df, p["lat"], p["lon"])
            if mappa and mappa.get("df") is not None and len(mappa["df"]):
                mm_st = float(pd.to_numeric(df["precip"], errors="coerce").sum()) if "precip" in df.columns else 0
                mm_m = float(mappa.get("mese_mm") or 0)
                keep_t = df.copy()
                df = mappa["df"].copy()
                try:
                    keep_t["date"] = pd.to_datetime(keep_t["date"], errors="coerce")
                    df["date"] = pd.to_datetime(df["date"], errors="coerce")
                    cols = [c for c in ("t_max", "t_min", "t_mean", "t_med", "vento_max") if c in keep_t.columns]
                    if cols:
                        if "vento_max" in df.columns:
                            df = df.drop(columns=["vento_max"])
                        df = df.merge(keep_t[["date"] + cols], on="date", how="left")
                except Exception:
                    pass
                info_meteo["fonte"] = (
                    f"Pluviometro smentito dalle mappe MN ({mm_st:.0f} mm stazione vs {mm_m:.0f} mm sul bosco) · "
                    "Mappe giornaliere MN"
                )
                info_meteo["stima_mappa"] = True
                info_meteo["pioggia_stazione_30g"] = mm_m
                info_meteo["giorni_pluviometro"] = [
                    f"{pd.to_datetime(rr['date']).date()}: {float(rr['precip']):.1f} mm"
                    for _, rr in mappa["df"].iterrows()
                    if float(rr.get("precip") or 0) >= 0.2
                ]
                if "vento_max" in df.columns:
                    vento = riepilogo_vento(df)
    except Exception:
        pass
    fonte0 = str(info_meteo.get("fonte") or "")
    if (
        fonte0.startswith("MeteoNetwork")
        and "mappe" not in fonte0.lower()
        and "realtime" not in fonte0.lower()
        and "interpolato" not in fonte0.lower()
    ):
        mcode = re.search(r"\(([a-z]{2,5}\d{2,4})\)", fonte0, flags=re.I)
        code = mcode.group(1) if mcode else None
        viva = False
        if code:
            try:
                dfa = mn_archivio_pubblico(code, 2)
                if dfa is not None and len(dfa) and "precip" in dfa.columns:
                    dfa = dfa.copy()
                    dfa["date"] = pd.to_datetime(dfa["date"], errors="coerce")
                    oggi = pd.Timestamp(datetime.now().date())
                    mese = dfa[(dfa["date"].dt.year == oggi.year) & (dfa["date"].dt.month == oggi.month)]
                    validi = int(pd.to_numeric(mese["precip"], errors="coerce").notna().sum())
                    viva = validi >= max(4, int(oggi.day * 0.45))
            except Exception:
                viva = False
        mm30 = info_meteo.get("pioggia_stazione_30g")
        try:
            mm30 = float(mm30) if mm30 is not None else 0.0
        except Exception:
            mm30 = 0.0
        n_umidi = 0
        for g in info_meteo.get("giorni_pluviometro") or []:
            try:
                n_umidi += 1 if float(str(g).rsplit(":", 1)[-1].replace("mm", "").strip().replace(",", ".")) >= 1 else 0
            except Exception:
                pass
        if not viva or (mm30 < 5 and n_umidi < 2):
            mappa = mn_pioggia_mappa(p["lat"], p["lon"], 15) or {}
            mese_r = mappa.get("mese_mm")
            oggi_r = mappa.get("oggi_mm")
            info_meteo["stima_mappa"] = True
            info_meteo["fonte"] = (
                "Stazione assente/incompleta · Mappe MN sul bosco"
                + " · Non al 100% come una stazione"
                + (f" · oggi MN {oggi_r} mm" if oggi_r is not None else "")
                + (f" · 30g MN {mese_r} mm" if mese_r is not None else "")
            )
            if mappa.get("df") is not None and len(mappa["df"]):
                df = mappa["df"]
                info_meteo["pioggia_stazione_30g"] = float(mese_r or 0)
                info_meteo["giorni_pluviometro"] = [
                    f"{pd.to_datetime(rr['date']).date()}: {float(rr['precip']):.1f} mm"
                    for _, rr in mappa["df"].iterrows()
                    if float(rr.get("precip") or 0) >= 0.2
                ]
    giorni = info_meteo.get("giorni_pluviometro") or []
    if giorni:
        taglio = (datetime.now().date() - timedelta(days=30)).isoformat()
        tenuti = []
        for g in giorni:
            gs = str(g)
            if "mese rete" in gs.lower():
                tenuti.append(g)
                continue
            data = gs.split(":")[0].strip()[:10]
            if len(data) >= 10 and data[:10] >= taglio:
                tenuti.append(g)
        info_meteo["giorni_pluviometro"] = tenuti
    if (df is None or len(df) == 0) and (info_meteo.get("giorni_pluviometro") or []):
        rows = []
        for g in info_meteo.get("giorni_pluviometro") or []:
            gs = str(g)
            try:
                data = gs.split(":")[0].strip()[:10]
                mm = float(gs.rsplit(":", 1)[-1].replace("mm", "").strip().replace(",", "."))
                rows.append({"date": pd.Timestamp(data), "precip": mm})
            except Exception:
                continue
        if rows:
            df = pd.DataFrame(rows)
    if df is not None and len(df) and "precip" in df.columns:
        try:
            info_meteo["pioggia_stazione_30g"] = round(float(pd.to_numeric(df["precip"], errors="coerce").sum()), 1)
        except Exception:
            pass
        # Sempre: lista giorni CON millimetri (WC/MN/WU/mappe)
        try:
            tmp = df.copy()
            tmp["date"] = pd.to_datetime(tmp["date"], errors="coerce")
            tmp["_p"] = pd.to_numeric(tmp["precip"], errors="coerce").fillna(0)
            taglio = pd.Timestamp(datetime.now().date() - timedelta(days=30))
            tmp = tmp[(tmp["date"].notna()) & (tmp["date"] >= taglio) & (tmp["_p"] >= 0.2)]
            tmp = tmp.sort_values("date")
            info_meteo["giorni_pluviometro"] = [
                f"{row['date'].date()}: {float(row['_p']):.1f} mm" for _, row in tmp.iterrows()
            ]
        except Exception:
            pass
    try:
        score, livello, det = calcola_punteggio(
            df, p["tipo"], regole, quota=p.get("quota", 1000),
            soil=soil, forecast=forecast, vento=vento,
        )
    except Exception:
        tot = 0.0
        try:
            tot = float(info_meteo.get("pioggia_stazione_30g") or 0)
        except Exception:
            tot = 0.0
        score = 35 if tot >= 40 else (20 if tot >= 15 else 8)
        livello = "mappa MN"
        det = {
            "precip_totale_30g": tot,
            "t_max_media": "n/d",
            "t_min_media": "n/d",
            "specie_testo": "n/d",
        }
    if not det.get("precip_totale_30g") and info_meteo.get("pioggia_stazione_30g") is not None:
        det["precip_totale_30g"] = info_meteo.get("pioggia_stazione_30g")
    return {**p, "score": score, "livello": livello, "dettaglio": det, "meteo": info_meteo}


def calcola_tutti(punti, regole, mn_token, max_km_stazione=5, max_workers=8, mn_codici="", stazioni_mn=None, serie_mn=None, usa_wc=True):
    risultati = []
    tot = max(1, len(punti))
    barra = st.progress(0, text=f"Calcolo 0/{tot} zone…")
    fatti = 0
    with ThreadPoolExecutor(max_workers=max(1, min(3, max_workers))) as ex:
        fut = {
            ex.submit(analizza_punto, p, regole, mn_token, max_km_stazione, mn_codici, stazioni_mn, serie_mn, usa_wc): p
            for p in punti
        }
        for f in as_completed(fut):
            try:
                risultati.append(f.result())
            except Exception as e:
                p = fut[f]
                risultati.append({
                    **p,
                    "score": 0,
                    "livello": f"Errore: {e}",
                    "dettaglio": {},
                    "meteo": {"fonte": "errore", "stazione": "n/d", "distanza_km": None},
                })
            fatti += 1
            pct = int(fatti * 100 / tot)
            barra.progress(pct / 100, text=f"Calcolo {fatti}/{tot} zone ({pct}%)")
    barra.progress(1.0, text=f"Calcolo {tot}/{tot} zone (100%)")
    return sorted(risultati, key=lambda x: x["score"], reverse=True)

