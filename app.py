import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2, exp
import io
import gzip
import json
from pathlib import Path
import folium
from streamlit_folium import st_folium
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

try:
    from meteostat import Stations, Daily
    METEOSTAT_OK = True
except Exception:
    METEOSTAT_OK = False

st.set_page_config(
    page_title="Porcini Predictor - Centro-Sud Italia",
    page_icon="🍄",
    layout="wide"
)

# tipo: "faggio" -> 14 giorni | "quercia_castagno" -> 8-9 giorni
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
    {"nome": "Chieti collinare - Guardiagrele", "lat": 42.190, "lon": 14.220, "tipo": "quercia_castagno", "quota": 600, "regione": "Abruzzo"},
    {"nome": "Teramo collinare - Cermignano", "lat": 42.590, "lon": 13.800, "tipo": "quercia_castagno", "quota": 550, "regione": "Abruzzo"},
    {"nome": "Monti Frentani - Palombaro", "lat": 42.125, "lon": 14.230, "tipo": "quercia_castagno", "quota": 700, "regione": "Abruzzo"},
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
    {"nome": "Majella - Abbateggio", "lat": 42.224, "lon": 14.013, "tipo": "quercia_castagno", "quota": 500, "regione": "Abruzzo"},
    {"nome": "Morrone - Pacentro / Sulmona", "lat": 42.051, "lon": 13.948, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Morrone - Popoli", "lat": 42.174, "lon": 13.832, "tipo": "quercia_castagno", "quota": 500, "regione": "Abruzzo"},
    {"nome": "Monti Pizzi - Gamberale", "lat": 41.904, "lon": 14.208, "tipo": "faggio", "quota": 1350, "regione": "Abruzzo"},
    {"nome": "Monti Pizzi - Pizzoferrato", "lat": 41.919, "lon": 14.236, "tipo": "faggio", "quota": 1250, "regione": "Abruzzo"},
    {"nome": "Monti Pizzi - Quadri", "lat": 41.924, "lon": 14.288, "tipo": "faggio", "quota": 900, "regione": "Abruzzo"},
    {"nome": "Alto Vastese - Castiglione Messer Marino", "lat": 41.868, "lon": 14.452, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Alto Vastese - Schiavi d'Abruzzo", "lat": 41.815, "lon": 14.485, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Frentani - Roccascalegna", "lat": 42.062, "lon": 14.308, "tipo": "quercia_castagno", "quota": 550, "regione": "Abruzzo"},
    {"nome": "Frentani - Gessopalena", "lat": 42.055, "lon": 14.273, "tipo": "quercia_castagno", "quota": 650, "regione": "Abruzzo"},
    {"nome": "Frentani - Torricella Peligna", "lat": 42.025, "lon": 14.259, "tipo": "quercia_castagno", "quota": 750, "regione": "Abruzzo"},
    {"nome": "Colline Vestine - Penne", "lat": 42.455, "lon": 13.930, "tipo": "quercia_castagno", "quota": 450, "regione": "Abruzzo"},
    {"nome": "Carsoli - Oricola / Pereto", "lat": 42.049, "lon": 13.039, "tipo": "faggio", "quota": 900, "regione": "Abruzzo"},
    {"nome": "Tagliacozzo - Cappadocia", "lat": 42.008, "lon": 13.280, "tipo": "faggio", "quota": 1100, "regione": "Abruzzo"},
    {"nome": "Marsica - Cocullo", "lat": 42.033, "lon": 13.775, "tipo": "faggio", "quota": 900, "regione": "Abruzzo"},
    {"nome": "Teramo collinare - Civitella del Tronto", "lat": 42.773, "lon": 13.675, "tipo": "quercia_castagno", "quota": 550, "regione": "Abruzzo"},
    {"nome": "Teramo collinare - Campli", "lat": 42.726, "lon": 13.686, "tipo": "quercia_castagno", "quota": 500, "regione": "Abruzzo"},

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
    {"nome": "Cantalupo nel Sannio", "lat": 41.523, "lon": 14.394, "tipo": "quercia_castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Campitello Matese", "lat": 41.463, "lon": 14.394, "tipo": "faggio", "quota": 1450, "regione": "Molise"},
    {"nome": "Monte Miletto", "lat": 41.452, "lon": 14.350, "tipo": "faggio", "quota": 1700, "regione": "Molise"},
    {"nome": "Roccamandolfi - Matese", "lat": 41.493, "lon": 14.351, "tipo": "faggio", "quota": 1400, "regione": "Molise"},
    {"nome": "Pietrabbondante", "lat": 41.748, "lon": 14.385, "tipo": "quercia_castagno", "quota": 800, "regione": "Molise"},
    {"nome": "San Pietro Avellana", "lat": 41.792, "lon": 14.183, "tipo": "faggio", "quota": 960, "regione": "Molise"},
    {"nome": "Castel del Giudice", "lat": 41.856, "lon": 14.232, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "Isernia - Pineta e colline", "lat": 41.594, "lon": 14.231, "tipo": "quercia_castagno", "quota": 450, "regione": "Molise"},
    {"nome": "Campobasso - colline boschive", "lat": 41.560, "lon": 14.660, "tipo": "quercia_castagno", "quota": 600, "regione": "Molise"},
    {"nome": "Capracotta - Prato Gentile", "lat": 41.850, "lon": 14.280, "tipo": "faggio", "quota": 1600, "regione": "Molise"},
    {"nome": "Monte Capraro", "lat": 41.820, "lon": 14.250, "tipo": "faggio", "quota": 1700, "regione": "Molise"},
    {"nome": "Monte Campo", "lat": 41.800, "lon": 14.310, "tipo": "faggio", "quota": 1740, "regione": "Molise"},
    {"nome": "Pescolanciano", "lat": 41.679, "lon": 14.248, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "Roccasicura", "lat": 41.697, "lon": 14.236, "tipo": "faggio", "quota": 750, "regione": "Molise"},
    {"nome": "Rionero Sannitico", "lat": 41.713, "lon": 14.140, "tipo": "faggio", "quota": 1050, "regione": "Molise"},
    {"nome": "Forlì del Sannio", "lat": 41.695, "lon": 14.180, "tipo": "faggio", "quota": 600, "regione": "Molise"},
    {"nome": "Acquaviva d'Isernia", "lat": 41.673, "lon": 14.148, "tipo": "faggio", "quota": 750, "regione": "Molise"},
    {"nome": "Sessano del Molise", "lat": 41.639, "lon": 14.328, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "Chiauci", "lat": 41.677, "lon": 14.385, "tipo": "quercia_castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Civitanova del Sannio", "lat": 41.667, "lon": 14.393, "tipo": "quercia_castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Bagnoli del Trigno", "lat": 41.703, "lon": 14.451, "tipo": "quercia_castagno", "quota": 750, "regione": "Molise"},
    {"nome": "Salcito", "lat": 41.726, "lon": 14.511, "tipo": "quercia_castagno", "quota": 700, "regione": "Molise"},
    {"nome": "Trivento", "lat": 41.776, "lon": 14.546, "tipo": "quercia_castagno", "quota": 600, "regione": "Molise"},
    {"nome": "Poggio Sannita", "lat": 41.779, "lon": 14.584, "tipo": "quercia_castagno", "quota": 700, "regione": "Molise"},
    {"nome": "Belmonte del Sannio", "lat": 41.824, "lon": 14.423, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Castelverrino", "lat": 41.766, "lon": 14.397, "tipo": "quercia_castagno", "quota": 700, "regione": "Molise"},
    {"nome": "Longano", "lat": 41.522, "lon": 14.247, "tipo": "faggio", "quota": 700, "regione": "Molise"},
    {"nome": "Castelpizzuto", "lat": 41.519, "lon": 14.292, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Santa Maria del Molise", "lat": 41.553, "lon": 14.367, "tipo": "quercia_castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Macchiagodena", "lat": 41.560, "lon": 14.409, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Sant'Elena Sannita", "lat": 41.575, "lon": 14.472, "tipo": "faggio", "quota": 800, "regione": "Molise"},
    {"nome": "Duronia", "lat": 41.659, "lon": 14.460, "tipo": "faggio", "quota": 900, "regione": "Molise"},
    {"nome": "Torella del Sannio", "lat": 41.640, "lon": 14.521, "tipo": "faggio", "quota": 850, "regione": "Molise"},
    {"nome": "Casalciprano", "lat": 41.580, "lon": 14.529, "tipo": "quercia_castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Spinete", "lat": 41.544, "lon": 14.488, "tipo": "quercia_castagno", "quota": 650, "regione": "Molise"},
    {"nome": "San Polo Matese", "lat": 41.460, "lon": 14.495, "tipo": "faggio", "quota": 750, "regione": "Molise"},
    {"nome": "Campochiaro", "lat": 41.448, "lon": 14.507, "tipo": "faggio", "quota": 750, "regione": "Molise"},
    {"nome": "Sepino", "lat": 41.408, "lon": 14.617, "tipo": "faggio", "quota": 700, "regione": "Molise"},
    {"nome": "Sassinoro", "lat": 41.375, "lon": 14.665, "tipo": "quercia_castagno", "quota": 550, "regione": "Molise"},
    {"nome": "Cercemaggiore", "lat": 41.461, "lon": 14.724, "tipo": "quercia_castagno", "quota": 800, "regione": "Molise"},
    {"nome": "Riccia", "lat": 41.483, "lon": 14.836, "tipo": "quercia_castagno", "quota": 700, "regione": "Molise"},
    {"nome": "Campolieto", "lat": 41.633, "lon": 14.767, "tipo": "quercia_castagno", "quota": 700, "regione": "Molise"},
    {"nome": "Castropignano", "lat": 41.619, "lon": 14.559, "tipo": "quercia_castagno", "quota": 550, "regione": "Molise"},
    {"nome": "Filignano", "lat": 41.545, "lon": 14.057, "tipo": "faggio", "quota": 650, "regione": "Molise"},
    {"nome": "Scapoli", "lat": 41.615, "lon": 14.059, "tipo": "faggio", "quota": 650, "regione": "Molise"},
    {"nome": "Colli a Volturno", "lat": 41.599, "lon": 14.103, "tipo": "quercia_castagno", "quota": 450, "regione": "Molise"},
    {"nome": "Montaquila", "lat": 41.562, "lon": 14.119, "tipo": "quercia_castagno", "quota": 450, "regione": "Molise"},
    {"nome": "Venafro - monti", "lat": 41.483, "lon": 14.045, "tipo": "quercia_castagno", "quota": 500, "regione": "Molise"},
    {"nome": "Conca Casale", "lat": 41.496, "lon": 14.007, "tipo": "quercia_castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Miranda", "lat": 41.643, "lon": 14.247, "tipo": "quercia_castagno", "quota": 650, "regione": "Molise"},
    {"nome": "Pesche", "lat": 41.617, "lon": 14.278, "tipo": "quercia_castagno", "quota": 650, "regione": "Molise"},

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
    {"nome": "Monti Lucretili - Licenza", "lat": 42.074, "lon": 12.900, "tipo": "quercia_castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Monti Lucretili - Palombara", "lat": 42.068, "lon": 12.768, "tipo": "quercia_castagno", "quota": 600, "regione": "Lazio"},
    {"nome": "Monti Prenestini - Capranica Prenestina", "lat": 41.863, "lon": 13.001, "tipo": "quercia_castagno", "quota": 850, "regione": "Lazio"},
    {"nome": "Castelli Romani - Nemi / Velletri", "lat": 41.718, "lon": 12.714, "tipo": "quercia_castagno", "quota": 600, "regione": "Lazio"},
    {"nome": "Castelli Romani - Monte Cavo", "lat": 41.750, "lon": 12.717, "tipo": "quercia_castagno", "quota": 750, "regione": "Lazio"},
    {"nome": "Monti Lepini - Carpineto Romano", "lat": 41.605, "lon": 13.085, "tipo": "faggio", "quota": 900, "regione": "Lazio"},
    {"nome": "Monti Lepini - Norma", "lat": 41.585, "lon": 12.972, "tipo": "quercia_castagno", "quota": 500, "regione": "Lazio"},
    {"nome": "Monti Ausoni - Sonnino", "lat": 41.414, "lon": 13.244, "tipo": "quercia_castagno", "quota": 500, "regione": "Lazio"},
    {"nome": "Monti Aurunci - Maranola", "lat": 41.290, "lon": 13.627, "tipo": "quercia_castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Monti Aurunci - Itri boschi", "lat": 41.290, "lon": 13.530, "tipo": "quercia_castagno", "quota": 450, "regione": "Lazio"},
    {"nome": "Cimini - Soriano nel Cimino", "lat": 42.418, "lon": 12.234, "tipo": "quercia_castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Cimini - Viterbo faggete", "lat": 42.400, "lon": 12.180, "tipo": "faggio", "quota": 800, "regione": "Lazio"},
    {"nome": "Monte Amiata laziale / Alto Lazio", "lat": 42.700, "lon": 11.850, "tipo": "faggio", "quota": 900, "regione": "Lazio"},
    {"nome": "Monti della Tolfa", "lat": 42.150, "lon": 11.950, "tipo": "quercia_castagno", "quota": 500, "regione": "Lazio"},
    {"nome": "Monti Sabini - Poggio Moiano", "lat": 42.200, "lon": 12.880, "tipo": "quercia_castagno", "quota": 600, "regione": "Lazio"},
    {"nome": "Parco dei Monti Simbruini - Cervara", "lat": 41.988, "lon": 13.067, "tipo": "faggio", "quota": 1050, "regione": "Lazio"},
    {"nome": "Terminillo - Micigliano", "lat": 42.452, "lon": 13.053, "tipo": "faggio", "quota": 900, "regione": "Lazio"},
    {"nome": "Terminillo - Posta", "lat": 42.525, "lon": 13.097, "tipo": "faggio", "quota": 700, "regione": "Lazio"},
    {"nome": "Monti Reatini - Antrodoco", "lat": 42.416, "lon": 13.079, "tipo": "faggio", "quota": 750, "regione": "Lazio"},
    {"nome": "Monti Reatini - Morro Reatino", "lat": 42.449, "lon": 12.834, "tipo": "quercia_castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Monti Reatini - Rivodutri", "lat": 42.517, "lon": 12.856, "tipo": "quercia_castagno", "quota": 550, "regione": "Lazio"},
    {"nome": "Salto-Cicolano - Fiamignano", "lat": 42.268, "lon": 13.126, "tipo": "faggio", "quota": 1000, "regione": "Lazio"},
    {"nome": "Salto-Cicolano - Pescorocchiano", "lat": 42.207, "lon": 13.146, "tipo": "faggio", "quota": 850, "regione": "Lazio"},
    {"nome": "Salto-Cicolano - Petrella Salto", "lat": 42.296, "lon": 13.068, "tipo": "faggio", "quota": 800, "regione": "Lazio"},
    {"nome": "Salto-Cicolano - Varco Sabino", "lat": 42.240, "lon": 13.019, "tipo": "faggio", "quota": 750, "regione": "Lazio"},
    {"nome": "Sabina - Orvinio", "lat": 42.133, "lon": 12.993, "tipo": "quercia_castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Sabina - Collalto Sabino", "lat": 42.226, "lon": 13.049, "tipo": "faggio", "quota": 950, "regione": "Lazio"},
    {"nome": "Sabina - Turania", "lat": 42.139, "lon": 13.008, "tipo": "quercia_castagno", "quota": 750, "regione": "Lazio"},
    {"nome": "Lucretili - Percile", "lat": 42.095, "lon": 12.905, "tipo": "quercia_castagno", "quota": 600, "regione": "Lazio"},
    {"nome": "Lucretili - Orvinio / Pozzaglia", "lat": 42.170, "lon": 12.964, "tipo": "quercia_castagno", "quota": 750, "regione": "Lazio"},
    {"nome": "Lucretili - Monte Gennaro", "lat": 42.055, "lon": 12.833, "tipo": "quercia_castagno", "quota": 1000, "regione": "Lazio"},
    {"nome": "Lucretili - Monteflavio", "lat": 42.109, "lon": 12.831, "tipo": "quercia_castagno", "quota": 850, "regione": "Lazio"},
    {"nome": "Simbruini - Monte Livata", "lat": 41.950, "lon": 13.120, "tipo": "faggio", "quota": 1400, "regione": "Lazio"},
    {"nome": "Simbruini - Jenne", "lat": 41.889, "lon": 13.169, "tipo": "faggio", "quota": 850, "regione": "Lazio"},
    {"nome": "Simbruini - Trevi nel Lazio", "lat": 41.863, "lon": 13.253, "tipo": "faggio", "quota": 800, "regione": "Lazio"},
    {"nome": "Simbruini - Altipiani di Arcinazzo", "lat": 41.879, "lon": 13.114, "tipo": "faggio", "quota": 850, "regione": "Lazio"},
    {"nome": "Simbruini - Rocca di Botte", "lat": 42.026, "lon": 13.068, "tipo": "faggio", "quota": 750, "regione": "Lazio"},
    {"nome": "Ernici - Collepardo", "lat": 41.765, "lon": 13.368, "tipo": "faggio", "quota": 800, "regione": "Lazio"},
    {"nome": "Ernici - Vico nel Lazio", "lat": 41.777, "lon": 13.341, "tipo": "faggio", "quota": 700, "regione": "Lazio"},
    {"nome": "Ernici - Veroli", "lat": 41.691, "lon": 13.418, "tipo": "quercia_castagno", "quota": 600, "regione": "Lazio"},
    {"nome": "Ernici - Alatri", "lat": 41.726, "lon": 13.342, "tipo": "quercia_castagno", "quota": 500, "regione": "Lazio"},
    {"nome": "Valle di Comino - San Donato", "lat": 41.708, "lon": 13.813, "tipo": "faggio", "quota": 750, "regione": "Lazio"},
    {"nome": "Valle di Comino - Settefrati", "lat": 41.670, "lon": 13.851, "tipo": "faggio", "quota": 800, "regione": "Lazio"},
    {"nome": "Valle di Comino - Picinisco", "lat": 41.647, "lon": 13.868, "tipo": "faggio", "quota": 750, "regione": "Lazio"},
    {"nome": "Valle di Comino - Villa Latina", "lat": 41.615, "lon": 13.836, "tipo": "faggio", "quota": 600, "regione": "Lazio"},
    {"nome": "Valle di Comino - Atina", "lat": 41.620, "lon": 13.802, "tipo": "quercia_castagno", "quota": 500, "regione": "Lazio"},
    {"nome": "Valle di Comino - Alvito", "lat": 41.690, "lon": 13.744, "tipo": "faggio", "quota": 500, "regione": "Lazio"},
    {"nome": "Valle di Comino - Pescosolido", "lat": 41.749, "lon": 13.657, "tipo": "faggio", "quota": 550, "regione": "Lazio"},
    {"nome": "Valle di Comino - Campoli Appennino", "lat": 41.736, "lon": 13.683, "tipo": "faggio", "quota": 650, "regione": "Lazio"},
    {"nome": "Mainarde laziali - Vallerotonda", "lat": 41.551, "lon": 13.911, "tipo": "faggio", "quota": 700, "regione": "Lazio"},
    {"nome": "Mainarde laziali - San Biagio Saracinisco", "lat": 41.613, "lon": 13.932, "tipo": "faggio", "quota": 850, "regione": "Lazio"},
    {"nome": "Cassinate - Terelle", "lat": 41.552, "lon": 13.778, "tipo": "faggio", "quota": 900, "regione": "Lazio"},
    {"nome": "Prenestini - Capranica / Piglio", "lat": 41.828, "lon": 13.144, "tipo": "quercia_castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Lepini - Segni", "lat": 41.690, "lon": 13.016, "tipo": "quercia_castagno", "quota": 650, "regione": "Lazio"},
    {"nome": "Lepini - Montelanico", "lat": 41.651, "lon": 13.040, "tipo": "faggio", "quota": 700, "regione": "Lazio"},
    {"nome": "Lepini - Bassiano", "lat": 41.549, "lon": 13.088, "tipo": "faggio", "quota": 550, "regione": "Lazio"},
    {"nome": "Lepini - Sezze / Sermoneta", "lat": 41.498, "lon": 13.060, "tipo": "quercia_castagno", "quota": 250, "regione": "Lazio"},
    {"nome": "Ausoni - Priverno", "lat": 41.472, "lon": 13.181, "tipo": "quercia_castagno", "quota": 150, "regione": "Lazio"},
    {"nome": "Ausoni - Prossedi / Roccagorga", "lat": 41.500, "lon": 13.236, "tipo": "quercia_castagno", "quota": 300, "regione": "Lazio"},
    {"nome": "Ausoni - Lenola", "lat": 41.339, "lon": 13.359, "tipo": "quercia_castagno", "quota": 450, "regione": "Lazio"},
    {"nome": "Ausoni - Campodimele", "lat": 41.388, "lon": 13.386, "tipo": "quercia_castagno", "quota": 650, "regione": "Lazio"},
    {"nome": "Aurunci - Spigno Saturnia", "lat": 41.297, "lon": 13.735, "tipo": "quercia_castagno", "quota": 200, "regione": "Lazio"},
    {"nome": "Aurunci - Esperia", "lat": 41.385, "lon": 13.685, "tipo": "quercia_castagno", "quota": 350, "regione": "Lazio"},
    {"nome": "Cimini - Caprarola", "lat": 42.327, "lon": 12.237, "tipo": "quercia_castagno", "quota": 650, "regione": "Lazio"},
    {"nome": "Cimini - Canepina", "lat": 42.383, "lon": 12.223, "tipo": "quercia_castagno", "quota": 500, "regione": "Lazio"},
    {"nome": "Cimini - Ronciglione", "lat": 42.289, "lon": 12.197, "tipo": "quercia_castagno", "quota": 450, "regione": "Lazio"},
    {"nome": "Cimini - Monte Cimino", "lat": 42.408, "lon": 12.203, "tipo": "faggio", "quota": 1000, "regione": "Lazio"},
    {"nome": "Alto Lazio - Acquapendente", "lat": 42.744, "lon": 11.865, "tipo": "quercia_castagno", "quota": 400, "regione": "Lazio"},
    {"nome": "Alto Lazio - San Lorenzo Nuovo", "lat": 42.687, "lon": 11.907, "tipo": "quercia_castagno", "quota": 500, "regione": "Lazio"},
    {"nome": "Selva del Lamone - Farnese", "lat": 42.549, "lon": 11.726, "tipo": "quercia_castagno", "quota": 350, "regione": "Lazio"},
    {"nome": "Tolfa - Allumiere", "lat": 42.157, "lon": 11.904, "tipo": "quercia_castagno", "quota": 500, "regione": "Lazio"},
    {"nome": "Bracciano - Manziana / Oriolo", "lat": 42.130, "lon": 12.127, "tipo": "quercia_castagno", "quota": 400, "regione": "Lazio"},
    {"nome": "Veio - Sacrofano / Formello", "lat": 42.106, "lon": 12.345, "tipo": "quercia_castagno", "quota": 250, "regione": "Lazio"},
    {"nome": "Castelli Romani - Rocca di Papa", "lat": 41.766, "lon": 12.710, "tipo": "quercia_castagno", "quota": 700, "regione": "Lazio"},
    {"nome": "Castelli Romani - Tuscolo / Monte Porzio", "lat": 41.807, "lon": 12.716, "tipo": "quercia_castagno", "quota": 600, "regione": "Lazio"},

    # ===================== CAMPANIA =====================
    {"nome": "Matese - Piedimonte alto", "lat": 41.355, "lon": 14.371, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Lago del Matese", "lat": 41.410, "lon": 14.400, "tipo": "faggio", "quota": 1010, "regione": "Campania"},
    {"nome": "San Gregorio Matese", "lat": 41.385, "lon": 14.380, "tipo": "faggio", "quota": 1100, "regione": "Campania"},
    {"nome": "Gallo Matese", "lat": 41.465, "lon": 14.225, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Letino", "lat": 41.450, "lon": 14.250, "tipo": "faggio", "quota": 1000, "regione": "Campania"},
    {"nome": "Cusano Mutri - Mutria", "lat": 41.330, "lon": 14.520, "tipo": "faggio", "quota": 1200, "regione": "Campania"},
    {"nome": "Pietraroja", "lat": 41.347, "lon": 14.550, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Castello del Matese", "lat": 41.368, "lon": 14.378, "tipo": "faggio", "quota": 800, "regione": "Campania"},
    {"nome": "Taburno - Camposauro", "lat": 41.100, "lon": 14.600, "tipo": "quercia_castagno", "quota": 900, "regione": "Campania"},
    {"nome": "Partenio - Montevergine", "lat": 40.936, "lon": 14.727, "tipo": "faggio", "quota": 1200, "regione": "Campania"},
    {"nome": "Partenio - Avella", "lat": 40.960, "lon": 14.600, "tipo": "quercia_castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Picentini - Montella", "lat": 40.844, "lon": 15.018, "tipo": "faggio", "quota": 1100, "regione": "Campania"},
    {"nome": "Picentini - Bagnoli Irpino", "lat": 40.833, "lon": 15.072, "tipo": "faggio", "quota": 1200, "regione": "Campania"},
    {"nome": "Picentini - Laceno", "lat": 40.800, "lon": 15.100, "tipo": "faggio", "quota": 1100, "regione": "Campania"},
    {"nome": "Picentini - Serino", "lat": 40.795, "lon": 14.872, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Terminio - Cervialto", "lat": 40.830, "lon": 15.030, "tipo": "faggio", "quota": 1400, "regione": "Campania"},
    {"nome": "Alburni - Sicignano", "lat": 40.560, "lon": 15.305, "tipo": "faggio", "quota": 1000, "regione": "Campania"},
    {"nome": "Alburni - Ottati", "lat": 40.463, "lon": 15.321, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Cilento - Corleto Monforte", "lat": 40.437, "lon": 15.380, "tipo": "faggio", "quota": 850, "regione": "Campania"},
    {"nome": "Cilento - Piaggine", "lat": 40.345, "lon": 15.378, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Cilento - Rofrano", "lat": 40.212, "lon": 15.428, "tipo": "quercia_castagno", "quota": 500, "regione": "Campania"},
    {"nome": "Cilento - Monte Cervati", "lat": 40.285, "lon": 15.410, "tipo": "faggio", "quota": 1400, "regione": "Campania"},
    {"nome": "Cilento - Sanza", "lat": 40.244, "lon": 15.553, "tipo": "quercia_castagno", "quota": 550, "regione": "Campania"},
    {"nome": "Monti Lattari - Agerola", "lat": 40.638, "lon": 14.539, "tipo": "quercia_castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Monti Lattari - Pimonte", "lat": 40.675, "lon": 14.510, "tipo": "quercia_castagno", "quota": 500, "regione": "Campania"},
    {"nome": "Monte Faito", "lat": 40.650, "lon": 14.500, "tipo": "quercia_castagno", "quota": 1100, "regione": "Campania"},
    {"nome": "Sannio - Morcone", "lat": 41.344, "lon": 14.667, "tipo": "quercia_castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Irpinia - Trevico", "lat": 41.048, "lon": 15.233, "tipo": "faggio", "quota": 1000, "regione": "Campania"},
    {"nome": "Irpinia - Bagnoli / Laceno basso", "lat": 40.820, "lon": 15.080, "tipo": "quercia_castagno", "quota": 800, "regione": "Campania"},
    {"nome": "Matese - Faicchio", "lat": 41.278, "lon": 14.478, "tipo": "quercia_castagno", "quota": 200, "regione": "Campania"},
    {"nome": "Matese - Cerreto Sannita", "lat": 41.284, "lon": 14.557, "tipo": "quercia_castagno", "quota": 300, "regione": "Campania"},
    {"nome": "Matese - Pontelandolfo", "lat": 41.292, "lon": 14.689, "tipo": "quercia_castagno", "quota": 500, "regione": "Campania"},
    {"nome": "Fortore - San Bartolomeo in Galdo", "lat": 41.416, "lon": 15.017, "tipo": "quercia_castagno", "quota": 600, "regione": "Campania"},
    {"nome": "Fortore - Baselice", "lat": 41.394, "lon": 14.974, "tipo": "quercia_castagno", "quota": 500, "regione": "Campania"},
    {"nome": "Fortore - Circello", "lat": 41.355, "lon": 14.809, "tipo": "quercia_castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Fortore - Colle Sannita", "lat": 41.373, "lon": 14.833, "tipo": "quercia_castagno", "quota": 750, "regione": "Campania"},
    {"nome": "Irpinia - Ariano Irpino", "lat": 41.153, "lon": 15.088, "tipo": "quercia_castagno", "quota": 800, "regione": "Campania"},
    {"nome": "Irpinia - Greci", "lat": 41.191, "lon": 15.169, "tipo": "quercia_castagno", "quota": 800, "regione": "Campania"},
    {"nome": "Irpinia - Savignano Irpino", "lat": 41.227, "lon": 15.179, "tipo": "quercia_castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Irpinia - Zungoli", "lat": 41.126, "lon": 15.202, "tipo": "quercia_castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Irpinia - Bisaccia", "lat": 41.013, "lon": 15.375, "tipo": "quercia_castagno", "quota": 850, "regione": "Campania"},
    {"nome": "Irpinia - Andretta", "lat": 40.937, "lon": 15.325, "tipo": "faggio", "quota": 850, "regione": "Campania"},
    {"nome": "Irpinia - Calitri", "lat": 40.921, "lon": 15.436, "tipo": "quercia_castagno", "quota": 600, "regione": "Campania"},
    {"nome": "Irpinia - Lioni", "lat": 40.878, "lon": 15.188, "tipo": "faggio", "quota": 550, "regione": "Campania"},
    {"nome": "Irpinia - Teora", "lat": 40.852, "lon": 15.253, "tipo": "faggio", "quota": 650, "regione": "Campania"},
    {"nome": "Irpinia - Caposele", "lat": 40.815, "lon": 15.223, "tipo": "faggio", "quota": 450, "regione": "Campania"},
    {"nome": "Irpinia - Calabritto", "lat": 40.783, "lon": 15.223, "tipo": "faggio", "quota": 500, "regione": "Campania"},
    {"nome": "Irpinia - Senerchia", "lat": 40.741, "lon": 15.204, "tipo": "faggio", "quota": 600, "regione": "Campania"},
    {"nome": "Picentini - Nusco", "lat": 40.887, "lon": 15.087, "tipo": "faggio", "quota": 900, "regione": "Campania"},
    {"nome": "Picentini - Cassano Irpino", "lat": 40.870, "lon": 15.026, "tipo": "faggio", "quota": 500, "regione": "Campania"},
    {"nome": "Picentini - Volturara Irpina", "lat": 40.883, "lon": 14.918, "tipo": "faggio", "quota": 650, "regione": "Campania"},
    {"nome": "Picentini - Acerno", "lat": 40.737, "lon": 15.056, "tipo": "faggio", "quota": 750, "regione": "Campania"},
    {"nome": "Picentini - Giffoni Valle Piana", "lat": 40.718, "lon": 14.942, "tipo": "quercia_castagno", "quota": 250, "regione": "Campania"},
    {"nome": "Partenio - Summonte", "lat": 40.947, "lon": 14.775, "tipo": "faggio", "quota": 750, "regione": "Campania"},
    {"nome": "Partenio - Ospedaletto d'Alpinolo", "lat": 40.939, "lon": 14.746, "tipo": "faggio", "quota": 700, "regione": "Campania"},
    {"nome": "Partenio - Mercogliano", "lat": 40.920, "lon": 14.743, "tipo": "quercia_castagno", "quota": 400, "regione": "Campania"},
    {"nome": "Partenio - Baiano", "lat": 40.952, "lon": 14.617, "tipo": "quercia_castagno", "quota": 200, "regione": "Campania"},
    {"nome": "Taburno - Vitulano", "lat": 41.117, "lon": 14.658, "tipo": "quercia_castagno", "quota": 450, "regione": "Campania"},
    {"nome": "Taburno - Foglianise", "lat": 41.161, "lon": 14.671, "tipo": "quercia_castagno", "quota": 350, "regione": "Campania"},
    {"nome": "Taburno - Cautano", "lat": 41.150, "lon": 14.644, "tipo": "quercia_castagno", "quota": 400, "regione": "Campania"},
    {"nome": "Alburni - Petina", "lat": 40.532, "lon": 15.347, "tipo": "faggio", "quota": 650, "regione": "Campania"},
    {"nome": "Alburni - Sant'Angelo a Fasanella", "lat": 40.456, "lon": 15.341, "tipo": "faggio", "quota": 550, "regione": "Campania"},
    {"nome": "Alburni - Castelcivita", "lat": 40.495, "lon": 15.234, "tipo": "quercia_castagno", "quota": 450, "regione": "Campania"},
    {"nome": "Alburni - Sicignano / Postiglione", "lat": 40.559, "lon": 15.232, "tipo": "faggio", "quota": 600, "regione": "Campania"},
    {"nome": "Cilento - Valle dell'Angelo", "lat": 40.344, "lon": 15.366, "tipo": "faggio", "quota": 600, "regione": "Campania"},
    {"nome": "Cilento - Laurino", "lat": 40.339, "lon": 15.339, "tipo": "faggio", "quota": 500, "regione": "Campania"},
    {"nome": "Cilento - Roscigno", "lat": 40.400, "lon": 15.346, "tipo": "faggio", "quota": 550, "regione": "Campania"},
    {"nome": "Cilento - Sacco", "lat": 40.377, "lon": 15.379, "tipo": "faggio", "quota": 600, "regione": "Campania"},
    {"nome": "Cilento - Novi Velia", "lat": 40.224, "lon": 15.286, "tipo": "faggio", "quota": 650, "regione": "Campania"},
    {"nome": "Cilento - Vallo della Lucania", "lat": 40.230, "lon": 15.266, "tipo": "quercia_castagno", "quota": 400, "regione": "Campania"},
    {"nome": "Cilento - Montano Antilia", "lat": 40.163, "lon": 15.366, "tipo": "quercia_castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Cilento - Cuccaro Vetere", "lat": 40.164, "lon": 15.321, "tipo": "quercia_castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Cilento - Monte Stella", "lat": 40.233, "lon": 15.140, "tipo": "quercia_castagno", "quota": 900, "regione": "Campania"},
    {"nome": "Cilento - Stio", "lat": 40.310, "lon": 15.252, "tipo": "quercia_castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Cilento - Magliano Vetere", "lat": 40.346, "lon": 15.236, "tipo": "quercia_castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Cilento - Monte Soprano / Trentinara", "lat": 40.400, "lon": 15.115, "tipo": "quercia_castagno", "quota": 550, "regione": "Campania"},
    {"nome": "Cilento - San Giovanni a Piro", "lat": 40.051, "lon": 15.453, "tipo": "quercia_castagno", "quota": 450, "regione": "Campania"},
    {"nome": "Cilento - Roccagloriosa", "lat": 40.106, "lon": 15.429, "tipo": "quercia_castagno", "quota": 450, "regione": "Campania"},
    {"nome": "Vallo di Diano - Teggiano", "lat": 40.379, "lon": 15.540, "tipo": "quercia_castagno", "quota": 600, "regione": "Campania"},
    {"nome": "Vallo di Diano - Sassano", "lat": 40.340, "lon": 15.566, "tipo": "quercia_castagno", "quota": 500, "regione": "Campania"},
    {"nome": "Vallo di Diano - Monte San Giacomo", "lat": 40.344, "lon": 15.535, "tipo": "faggio", "quota": 700, "regione": "Campania"},
    {"nome": "Vallo di Diano - Padula", "lat": 40.337, "lon": 15.656, "tipo": "quercia_castagno", "quota": 700, "regione": "Campania"},
    {"nome": "Vallo di Diano - Montesano sulla Marcellana", "lat": 40.276, "lon": 15.705, "tipo": "faggio", "quota": 850, "regione": "Campania"},
    {"nome": "Vallo di Diano - Casalbuono", "lat": 40.214, "lon": 15.686, "tipo": "quercia_castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Vallo di Diano - Sala Consilina", "lat": 40.399, "lon": 15.596, "tipo": "quercia_castagno", "quota": 550, "regione": "Campania"},
    {"nome": "Tanagro - Atena Lucana", "lat": 40.455, "lon": 15.557, "tipo": "quercia_castagno", "quota": 650, "regione": "Campania"},
    {"nome": "Tanagro - Auletta / Pertosa", "lat": 40.561, "lon": 15.394, "tipo": "quercia_castagno", "quota": 300, "regione": "Campania"},
    {"nome": "Alto Sele - Colliano", "lat": 40.726, "lon": 15.289, "tipo": "quercia_castagno", "quota": 600, "regione": "Campania"},
    {"nome": "Alto Sele - Valva", "lat": 40.739, "lon": 15.270, "tipo": "quercia_castagno", "quota": 500, "regione": "Campania"},
    {"nome": "Alto Sele - Laviano", "lat": 40.786, "lon": 15.310, "tipo": "faggio", "quota": 500, "regione": "Campania"},
    {"nome": "Monti Lattari - Tramonti", "lat": 40.695, "lon": 14.640, "tipo": "quercia_castagno", "quota": 400, "regione": "Campania"},
    {"nome": "Monti Lattari - Scala / Ravello", "lat": 40.653, "lon": 14.608, "tipo": "quercia_castagno", "quota": 400, "regione": "Campania"},
    {"nome": "Monti Lattari - Gragnano / Lettere", "lat": 40.689, "lon": 14.515, "tipo": "quercia_castagno", "quota": 350, "regione": "Campania"},
    {"nome": "Monti Lattari - Vico Equense", "lat": 40.661, "lon": 14.427, "tipo": "quercia_castagno", "quota": 400, "regione": "Campania"},
]

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
]


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
    """Più basso è meglio. Penalizza stazioni lontane o a quota molto diversa."""
    if dist_km is None or dist_km > max_dist:
        return 9999
    dq = abs(d_quota) if d_quota is not None else 300
    return dist_km + dq / 80.0


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


def mn_giorno_pluviometro(token, code, giorno):
    """Un giorno. I successi restano in sessione; i 429 non si cachano."""
    store = st.session_state.setdefault("mn_giorni", {})
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
        return {"ok": True, "status": 200, "row": row}
    return {"ok": False, "status": r.status_code, "row": None}


def mn_serie_giornaliera(token, code, days=30, nuovi_per_volta=4):
    """Fino a 30 giorni. Ogni Calcola scarica al massimo 4 giorni nuovi."""
    if not token or not code:
        return None, 0, days
    oggi = datetime.now().date()
    righe = []
    nuovi = 0
    for i in range(min(int(days), 30)):
        d = (oggi - timedelta(days=i)).isoformat()
        store = st.session_state.setdefault("mn_giorni", {})
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
        nuovi += 1
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
    return {
        "vento_medio_10g": round(media, 1),
        "vento_max_10g": round(vmax, 1),
        "giorni_oltre_20": giorni_20,
        "giorni_oltre_30": giorni_30,
        "giorni_consecutivi_venti": streak,
        "fattore_vento": round(fattore, 3),
        "nota_vento": nota,
    }


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


@st.cache_data(ttl=3600)
def get_weather_data(lat, lon, days=30, mn_token="", quota=None, max_km_stazione=35, mn_codici="", stazioni_mn=None, serie_mn=None):
    info = {
        "fonte": "ICON-2I 2km (modello sul bosco)",
        "stazione": "n/d",
        "distanza_km": None,
        "quota_stazione": None,
        "pioggia_modello_30g": None,
        "pioggia_stazione_30g": None,
    }
    forecast = None
    soil = None
    vento = riepilogo_vento(None)

    try:
        storico_om, forecast, soil, vento = get_openmeteo_bundle(lat, lon, days)
    except Exception:
        storico_om, forecast, soil, vento = None, None, None, riepilogo_vento(None)

    if storico_om is not None and "precip" in storico_om.columns:
        info["pioggia_modello_30g"] = round(float(storico_om["precip"].sum(skipna=True)), 1)

    def _mm(df):
        if df is None or "precip" not in df.columns:
            return None
        return round(float(df["precip"].sum(skipna=True)), 1)

    # 1) MeteoNetwork: stazione più vicina. Serie 30g sul punto della centralina
    #    (evita 30 chiamate/giorno che fanno 429 e fanno sparire MN).
    if mn_token:
        stazioni = list(stazioni_mn or [])
        if not stazioni:
            stazioni = mn_stazioni_da_codici(mn_token, mn_codici)
        vicine_mn = mn_stazioni_vicine(lat, lon, stazioni, quota=quota, n=3, max_km=max_km_stazione)
        if vicine_mn:
            s = vicine_mn[0]
            df_mn = None
            if serie_mn and s.get("code") in (serie_mn or {}):
                df_mn = serie_mn.get(s["code"])
            if df_mn is None:
                df_mn = mn_dati_stazione(mn_token, s["code"], days)
            df_punto_staz = None
            try:
                df_punto_staz, _, _, _ = get_openmeteo_bundle(s["lat"], s["lon"], days)
            except Exception:
                df_punto_staz = None
            serie = df_punto_staz if df_punto_staz is not None else storico_om
            n_pluvio = 0
            if serie is not None and df_mn is not None and len(df_mn):
                serie = serie.copy()
                n_pluvio = int(df_mn["precip"].notna().sum()) if "precip" in df_mn.columns else len(df_mn)
                for _, row in df_mn.iterrows():
                    if pd.isna(row.get("date")):
                        continue
                    mask = pd.to_datetime(serie["date"]).dt.normalize() == pd.to_datetime(row["date"]).normalize()
                    if mask.any() and not pd.isna(row.get("precip")):
                        serie.loc[mask, "precip"] = row["precip"]
            if serie is not None:
                oggi_mm = None
                if df_mn is not None and len(df_mn) and "precip" in df_mn.columns:
                    oggi_mm = df_mn.iloc[-1]["precip"]
                fonte = (
                    f"MeteoNetwork {s.get('nome')} a {s.get('distanza_km')} km"
                    + (f" · oggi pluviometro {oggi_mm} mm" if oggi_mm is not None else "")
                    + (f" · {n_pluvio} gg da pluviometro" if n_pluvio else " · 30g modello sul punto stazione")
                )
                info = _info_stazione(s, fonte)
                giorni_txt = []
                if df_mn is not None and len(df_mn) and "precip" in df_mn.columns:
                    tmp = df_mn.dropna(subset=["date"]).sort_values("date")
                    for _, rr in tmp.iterrows():
                        giorni_txt.append(f"{pd.to_datetime(rr['date']).date()}: {float(rr['precip']):.1f} mm")
                info["giorni_pluviometro"] = giorni_txt
                info["pioggia_modello_30g"] = (
                    round(float(storico_om["precip"].sum(skipna=True)), 1) if storico_om is not None else None
                )
                info["pioggia_stazione_30g"] = _mm(serie)
                return serie, info, forecast, soil, vento

    # 2) ufficiale SOLO se è vicina al bosco (altrimenti i mm non c'entrano)
    limite_ufficiale = min(18, max_km_stazione)
    for s in stazioni_ufficiali_vicine(lat, lon, quota=quota, n=4, max_km=limite_ufficiale):
        dq = None
        if quota is not None and s.get("quota") is not None:
            dq = abs(quota - s["quota"])
        if dq is not None and dq > 400:
            continue
        df_st = get_stazione_dati(s["id"], days)
        if df_st is not None and df_st["precip"].notna().sum() >= 8:
            info = _info_stazione(s, "Stazione ufficiale vicina")
            info["pioggia_modello_30g"] = (
                round(float(storico_om["precip"].sum(skipna=True)), 1) if storico_om is not None else None
            )
            info["pioggia_stazione_30g"] = _mm(df_st)
            return df_st, info, forecast, soil, vento

    # 3) default: pioggia del MODELLO sul punto del bosco (non un aeroporto a 40 km)
    if storico_om is not None:
        vicine = stazioni_ufficiali_vicine(lat, lon, quota=quota, n=1, max_km=80)
        if vicine:
            s = vicine[0]
            df_st = get_stazione_dati(s["id"], days)
            info["stazione"] = f"{s['nome']} (solo confronto, {s['distanza_km']} km)"
            info["distanza_km"] = s["distanza_km"]
            info["quota_stazione"] = s.get("quota")
            info["pioggia_stazione_30g"] = _mm(df_st)
        info["fonte"] = "ICON-2I 2 km sul bosco (stazione ufficiale troppo lontana per i mm)"
        return storico_om, info, forecast, soil, vento
    return None, info, forecast, soil, vento


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
    if df is None or len(df) < 8:
        return 0, "Dati insufficienti", {}

    precip_totale = float(df["precip"].sum())
    giorni_con_pioggia = int((df["precip"] > 1).sum())
    t_max_media = float(df["t_max"].mean())
    t_min_media = float(df["t_min"].mean())

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

    giorni_attesa = 14 if tipo_bosco == "faggio" else 9

    giorni_dalla_pioggia = 99
    cum = 0
    for i in range(len(df) - 1, -1, -1):
        val = df.iloc[i]["precip"]
        if pd.isna(val):
            continue
        cum += float(val)
        if cum >= 30:
            giorni_dalla_pioggia = len(df) - 1 - i
            break

    if giorni_attesa - 4 <= giorni_dalla_pioggia <= giorni_attesa + 3:
        score_tempo = 20
    elif giorni_dalla_pioggia < giorni_attesa:
        score_tempo = 10
    else:
        score_tempo = 5

    score_suolo = 0
    if soil is not None:
        # valori volumetrici tipici 0.15–0.40 m3/m3
        if 0.22 <= soil <= 0.38:
            score_suolo = 10
        elif 0.18 <= soil <= 0.42:
            score_suolo = 5

    vento = vento or riepilogo_vento(df if df is not None and "vento_max" in df.columns else None)
    fattore_v = float(vento.get("fattore_vento") or 1.0)

    # il vento persistente brucia l'effetto della pioggia e del suolo (decadimento esponenziale)
    umido = (score_pioggia + score_tempo + score_suolo) * fattore_v
    punteggio_totale = min(100, umido + score_temp * (0.45 + 0.55 * fattore_v))
    consiglio = finestra_uscita(giorni_dalla_pioggia, giorni_attesa, forecast)
    if fattore_v < 0.5:
        consiglio = vento.get("nota_vento", "Vento secco") + " · " + consiglio

    dettaglio = {
        "precip_totale_30g": round(precip_totale, 1),
        "precip_10g": round(precip_10g, 1),
        "giorni_con_pioggia": giorni_con_pioggia,
        "t_max_media": round(t_max_media, 1),
        "t_min_media": round(t_min_media, 1),
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
    }

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


def analizza_punto(p, regole, mn_token, max_km_stazione=35, mn_codici="", stazioni_mn=None, serie_mn=None):
    df, info_meteo, forecast, soil, vento = get_weather_data(
        p["lat"], p["lon"], days=30, mn_token=mn_token or "",
        quota=p.get("quota"), max_km_stazione=max_km_stazione,
        mn_codici=mn_codici, stazioni_mn=stazioni_mn, serie_mn=serie_mn,
    )
    score, livello, det = calcola_punteggio(
        df, p["tipo"], regole, quota=p.get("quota", 1000),
        soil=soil, forecast=forecast, vento=vento,
    )
    return {**p, "score": score, "livello": livello, "dettaglio": det, "meteo": info_meteo}


def calcola_tutti(punti, regole, mn_token, max_km_stazione=35, max_workers=4, mn_codici="", stazioni_mn=None, serie_mn=None):
    risultati = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut = {
            ex.submit(analizza_punto, p, regole, mn_token, max_km_stazione, mn_codici, stazioni_mn, serie_mn): p
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
    return sorted(risultati, key=lambda x: x["score"], reverse=True)


# ===================== UI =====================
st.title("🍄 Porcini Predictor")
st.markdown("**Abruzzo • Molise • Lazio • Campania**")
st.caption(
    "Zone boschive principali delle 4 regioni. Non è ogni singolo bosco, "
    "ma i comprensori più importanti per i porcini. "
    "Le nascite reali dipendono anche da esposizione, suolo e micelio."
)

with st.sidebar:
    st.header("🌦️ Stazioni pluviometriche")
    st.caption(
        "Account gratis su my.meteonetwork.it (non meteonetwork.it). "
        "Poi email/password qui, oppure genera il token una volta e incollalo."
    )
    mn_email = st.text_input("Username o email myMeteoNetwork", value="")
    mn_pass = st.text_input("Password myMeteoNetwork", type="password", value="")
    collega_mn = st.button("Collega MeteoNetwork (una volta sola)")
    mn_token_manuale = st.text_input("Oppure incolla il token STANDARD", value="")
    mn_codici = st.text_input(
        "Codici stazioni MN (senza BULK)",
        value="",
        placeholder="es. lmb254, abc123",
        help="Li trovi nell'URL della pagina stazione su meteonetwork.it o meteonetwork.eu",
    )
    if st.session_state.get("mn_token"):
        st.caption("Token già in memoria in questa sessione. Non rilogga da solo.")

    st.markdown("---")
    st.header("⚙️ Filtri e regole")
    regioni_sel = st.multiselect(
        "Regioni da calcolare",
        ["Abruzzo", "Molise", "Lazio", "Campania"],
        default=["Molise"],
    )
    tipi_sel = st.multiselect(
        "Tipo di bosco",
        ["faggio", "quercia_castagno"],
        default=["faggio", "quercia_castagno"],
    )
    quota_range = st.slider("Quota (m)", 400, 1800, (500, 1700), step=50)
    cerca = st.text_input("Cerca zona (nome)", value="")

    st.markdown("---")
    pioggia_min = st.slider("Pioggia minima ideale (mm / 30gg)", 20, 80, 40)
    pioggia_max = st.slider("Pioggia massima ideale (mm / 30gg)", 60, 150, 100)
    max_km_stazione = st.slider(
        "Distanza max stazione (km)",
        10, 60, 35, 5,
        help="Oltre questa distanza si usa il modello ICON-2I sul punto del bosco, non un aeroporto lontano.",
    )

    st.markdown("---")
    st.subheader("📧 Notifiche Email")
    email_dest = st.text_input("Email destinatario", value="davidemenna3@gmail.com")
    smtp_user = st.text_input("La tua Gmail (mittente)", value="")
    smtp_pass = st.text_input("App Password Gmail", type="password", value="")

    st.markdown("---")
    calcola = st.button("🔄 Calcola / aggiorna dati", type="primary", use_container_width=True)
    if st.button("Svuota cache meteo", use_container_width=True):
        st.cache_data.clear()
        st.session_state.pop("risultati", None)
        st.success("Cache svuotata")

regole = {"pioggia_min": pioggia_min, "pioggia_max": pioggia_max}

def _token_dai_secrets():
    try:
        return (
            str(st.secrets.get("METEONETWORK_TOKEN", "") or "").strip()
            or str(st.secrets.get("mn_token", "") or "").strip()
        )
    except Exception:
        return ""


mn_token = (
    (mn_token_manuale or "").strip()
    or st.session_state.get("mn_token")
    or _token_dai_secrets()
)
if collega_mn:
    tok, err = mn_login(mn_email, mn_pass)
    if tok:
        st.session_state["mn_token"] = tok
        mn_token = tok
        st.sidebar.success("MeteoNetwork collegato. Copia il token e salvalo.")
        st.sidebar.code(tok, language=None)
    else:
        st.sidebar.error(err or "Login MeteoNetwork non riuscito")
elif mn_token:
    st.session_state["mn_token"] = mn_token
    n_st = 0
    try:
        n_st = len(mn_stazioni_da_codici(mn_token, mn_codici))
    except Exception:
        n_st = 0
    if n_st:
        st.sidebar.success(f"MeteoNetwork attivo · {n_st} stazioni in rete")
    else:
        st.sidebar.warning(
            "Token STANDARD ok. Inserisci i codici stazione (es. mls059) e premi Calcola. "
            "Non chiedo più l'elenco completo: quello è BULK e causa 429."
        )
else:
    st.sidebar.info("Senza MeteoNetwork uso stazioni ufficiali + modello ICON-2I. L'app funziona lo stesso.")

punti_filtrati = [
    p for p in PUNTI
    if p["regione"] in regioni_sel
    and p["tipo"] in tipi_sel
    and quota_range[0] <= p["quota"] <= quota_range[1]
    and (cerca.lower() in p["nome"].lower() if cerca else True)
]

st.header("📍 Situazione attuale")
st.write(f"Zone selezionate: **{len(punti_filtrati)}** su {len(PUNTI)} totali")

if not punti_filtrati:
    st.warning("Seleziona almeno una regione e un tipo di bosco nella sidebar.")
    st.stop()

stazioni_mn = mn_stazioni_da_codici(mn_token, mn_codici) if (mn_token and mn_codici) else []
if mn_token and mn_codici:
    if stazioni_mn:
        st.sidebar.success("Stazioni MN lette: " + ", ".join(f"{s['nome']} ({s['code']})" for s in stazioni_mn))
        if st.session_state.get("mn_progresso"):
            st.sidebar.info("Pluviometro " + st.session_state["mn_progresso"] + ". Ripremi Calcola per aggiungere altri giorni (max 4 per volta).")
    else:
        st.sidebar.error(
            "Codici inseriti ma nessuna stazione letta. Aspetta se c'è stato un 429, "
            "poi un solo Calcola. Verifica i codici sulla scheda MN."
        )

if calcola or "risultati" not in st.session_state:
    serie_mn = {}
    if calcola and stazioni_mn:
        with st.spinner(f"Scarico fino a 4 giorni nuovi di pluviometro (obiettivo 30 gg)..."):
            report = []
            for s in stazioni_mn:
                df_s, n_ok, n_tot = mn_serie_giornaliera(mn_token, s["code"], 30, 4)
                serie_mn[s["code"]] = df_s
                report.append(f"{s['nome']}: {n_ok}/{n_tot} gg")
            st.session_state["mn_progresso"] = " · ".join(report)
    with st.spinner(f"Calcolo su {len(punti_filtrati)} zone..."):
        st.session_state["risultati"] = calcola_tutti(
            punti_filtrati, regole, mn_token,
            max_km_stazione=max_km_stazione,
            mn_codici=mn_codici,
            stazioni_mn=stazioni_mn,
            serie_mn=serie_mn,
        )
        st.session_state["filtro_usato"] = {
            "regioni": regioni_sel,
            "tipi": tipi_sel,
            "n": len(punti_filtrati),
        }
elif st.session_state.get("filtro_usato", {}).get("n") != len(punti_filtrati):
    st.info("I filtri sono cambiati. Premi **Calcola / aggiorna dati** per ricalcolare.")

risultati = st.session_state.get("risultati", [])
if not risultati:
    st.stop()

# filtra i risultati già calcolati per ricerca/quota se l'utente non ha ricalcolato
risultati_view = [
    r for r in risultati
    if r["regione"] in regioni_sel
    and r["tipo"] in tipi_sel
    and quota_range[0] <= r["quota"] <= quota_range[1]
    and (cerca.lower() in r["nome"].lower() if cerca else True)
]

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
n_alto = sum(1 for r in risultati_view if r["score"] >= 70)
n_medio = sum(1 for r in risultati_view if 50 <= r["score"] < 70)
best = risultati_view[0] if risultati_view else None
kpi1.metric("Zone analizzate", len(risultati_view))
kpi2.metric("🟢 Alto", n_alto)
kpi3.metric("🟡 Medio", n_medio)
kpi4.metric("Top zona", f"{best['score']:.0f}" if best else "—", best["nome"] if best else "")

soglia = st.slider("Mostra solo zone con punteggio ≥", 0, 90, 0, 5)
risultati_view = [r for r in risultati_view if r["score"] >= soglia]

col1, col2 = st.columns([1.4, 1])

with col1:
    st.subheader("Mappa delle zone")
    if risultati_view:
        m = folium.Map(location=[41.7, 14.0], zoom_start=7)
        for r in risultati_view:
            color = (
                "green" if r["score"] >= 70
                else "orange" if r["score"] >= 50
                else "red" if r["score"] >= 30
                else "gray"
            )
            d = r.get("dettaglio", {})
            popup_html = f"""
            <b>{r['nome']}</b><br>
            Regione: {r['regione']}<br>
            Tipo: {r['tipo']}<br>
            Quota ~{r['quota']} m<br>
            <b>Punteggio: {r['score']:.0f}/100</b><br>
            {r['livello']}<br>
            {d.get('consiglio', '')}<br>
            Pioggia 30g: {d.get('precip_totale_30g', 'n/d')} mm<br>
            T max media: {d.get('t_max_media', 'n/d')} °C<br>
            Fonte: {r.get('meteo', {}).get('fonte', 'n/d')}<br>
            Stazione: {r.get('meteo', {}).get('stazione', 'n/d')}<br>
            Giorni pluviometro:<br>{'<br>'.join(r.get('meteo', {}).get('giorni_pluviometro') or ['ancora nessuno'])}
            """
            folium.CircleMarker(
                location=[r["lat"], r["lon"]],
                radius=8 + r["score"] / 12,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.75,
                popup=folium.Popup(popup_html, max_width=320),
            ).add_to(m)
        st_folium(m, width=700, height=520, returned_objects=[])
    else:
        st.info("Nessuna zona sopra la soglia scelta.")

with col2:
    st.subheader("Classifica zone")
    for r in risultati_view:
        with st.expander(f"{r['score']:.0f} • {r['nome']} ({r['regione']})", expanded=r["score"] >= 70):
            st.markdown(f"**{r['livello']}**")
            st.write(f"Tipo bosco: **{r['tipo']}** | Quota ~{r['quota']} m")
            d = r["dettaglio"]
            st.info(d.get("consiglio", ""))
            st.write(f"• Pioggia ultimi 30 giorni: **{d.get('precip_totale_30g')} mm** ({d.get('giorni_con_pioggia')} giorni con pioggia)")
            st.write(f"• Pioggia ultimi 10 giorni: **{d.get('precip_10g')} mm**")
            st.write(f"• Temperatura max media: **{d.get('t_max_media')} °C**")
            st.write(f"• Temperatura min media: **{d.get('t_min_media')} °C**")
            st.write(f"• Giorni dalla buona pioggia: **{d.get('giorni_dalla_buona_pioggia')}** (attesa: {d.get('giorni_attesa_consigliati')} gg)")
            st.write(f"• Umidità suolo (7–28 cm): **{d.get('umidita_suolo')}**")
            st.write(
                f"• Vento 10 gg: media **{d.get('vento_medio_10g')} km/h**, "
                f"max **{d.get('vento_max_10g')} km/h** "
                f"({d.get('giorni_vento_20')} gg ≥20, {d.get('giorni_vento_30')} gg ≥30, "
                f"streak {d.get('giorni_vento_consecutivi')})"
            )
            st.write(f"• Fattore vento (1=ok, ~0=letto secco): **{d.get('fattore_vento')}** — {d.get('nota_vento')}")
            meteo = r.get("meteo", {})
            dist = meteo.get("distanza_km")
            dist_txt = f" ({dist} km)" if dist is not None else ""
            st.write(f"• Fonte usata per il punteggio: **{meteo.get('fonte', 'n/d')}**")
            giorni_p = meteo.get("giorni_pluviometro") or []
            if giorni_p:
                st.write("• Mm veri già scaricati:")
                for g in giorni_p:
                    st.write(f"  – {g}")
            else:
                st.write("• Mm veri già scaricati: nessuno (ripremi Calcola, senza svuotare la cache)")
            if meteo.get("pioggia_modello_30g") is not None or meteo.get("pioggia_stazione_30g") is not None:
                st.write(
                    f"• Confronto 30 gg — modello sul bosco: **{meteo.get('pioggia_modello_30g')} mm** · "
                    f"stazione più vicina: **{meteo.get('pioggia_stazione_30g')} mm**"
                )
            qst = meteo.get("quota_stazione")
            qst_txt = f", quota stazione {int(qst)} m" if qst not in (None, "") else ""
            st.write(f"• Stazione: **{meteo.get('stazione', 'n/d')}**{dist_txt}{qst_txt}")
            st.progress(min(100, int(r["score"])) / 100)

st.markdown("---")
st.subheader("📊 Tabella e export")
if risultati_view:
    tab = pd.DataFrame([{
        "zona": r["nome"],
        "regione": r["regione"],
        "tipo": r["tipo"],
        "quota_m": r["quota"],
        "score": round(r["score"], 1),
        "livello": r["livello"],
        "consiglio": r["dettaglio"].get("consiglio"),
        "pioggia_30g_mm": r["dettaglio"].get("precip_totale_30g"),
        "pioggia_10g_mm": r["dettaglio"].get("precip_10g"),
        "t_max": r["dettaglio"].get("t_max_media"),
        "t_min": r["dettaglio"].get("t_min_media"),
        "giorni_da_pioggia": r["dettaglio"].get("giorni_dalla_buona_pioggia"),
        "suolo": r["dettaglio"].get("umidita_suolo"),
        "vento_medio_kmh": r["dettaglio"].get("vento_medio_10g"),
        "gg_vento_20": r["dettaglio"].get("giorni_vento_20"),
        "gg_vento_30": r["dettaglio"].get("giorni_vento_30"),
        "fattore_vento": r["dettaglio"].get("fattore_vento"),
        "nota_vento": r["dettaglio"].get("nota_vento"),
        "fonte": r.get("meteo", {}).get("fonte"),
        "stazione": r.get("meteo", {}).get("stazione"),
    } for r in risultati_view])
    st.dataframe(tab, use_container_width=True, hide_index=True)
    st.download_button(
        "Scarica CSV",
        tab.to_csv(index=False).encode("utf-8"),
        file_name=f"porcini_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

st.markdown("---")
st.subheader("📧 Invia report via email")

corpo = f"""Report Porcini Predictor - {datetime.now().strftime('%d/%m/%Y %H:%M')}

Regioni selezionate: {', '.join(regioni_sel)}
Zone analizzate: {len(risultati_view)}

=== CLASSIFICA ===
"""
for r in risultati_view[:15]:
    d = r["dettaglio"]
    corpo += f"""
{r['nome']} ({r['regione']})
  Punteggio: {r['score']:.0f}/100 - {r['livello']}
  {d.get('consiglio', '')}
  Pioggia 30g: {d.get('precip_totale_30g')} mm | 10g: {d.get('precip_10g')} mm
  T max media: {d.get('t_max_media')} °C
  Giorni da buona pioggia: {d.get('giorni_dalla_buona_pioggia')}
"""

if st.button("Invia report"):
    if not smtp_user or not smtp_pass:
        st.error("Inserisci Gmail e App Password nella sidebar.")
    else:
        ok, msg = invia_email(
            email_dest,
            f"🍄 Porcini Report - {datetime.now().strftime('%d/%m/%Y')}",
            corpo,
            smtp_user,
            smtp_pass,
        )
        if ok:
            st.success(msg)
        else:
            st.error(msg)

st.markdown("---")
st.caption(
    "Fonte: MeteoNetwork (se collegato), stazioni ufficiali Meteostat, riserva Open-Meteo "
    "(pioggia, temperature, previsione 7 giorni, umidità del suolo). "
    "Rispetta i regolamenti regionali su tesserini, quantitativi e specie protette."
)
