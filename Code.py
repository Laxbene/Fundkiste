import streamlit as st
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np
import pandas as pd
import os
import random
import time
from datetime import datetime, timedelta

# --- KONFIGURATION & DATUM ---
HEUTE = datetime(2026, 2, 19).date()
DB_FILE = "fundstuecke_db.csv"

# 100 Wörter für das Spiel
SPACE_WORDS = [
    "Asteroid", "Astronaut", "Apollo", "Atmosphäre", "Antimaterie", "Alien", "Aurora", "Bahngeschwindigkeit", 
    "Bigbang", "Blackhole", "Binary", "Booster", "Cassini", "ComHandschuheBrotdoseet", "Cosmos", "Countdown", "Crater", 
    "Darkmatter", "Deepspace", "Dust", "Dwarf", "Earth", "Eclipse", "Eris", "Exoplanet", "Explorer", 
    "Falcon", "Flare", "Fragment", "Galaxy", "Gamma", "Gasgiant", "Gravity", "Gemini", "Horizon", 
    "Hubble", "Hyperdrive", "Impact", "Interstellar", "Ion", "ISS", "Jupiter", "Jetstream", "Kepler", 
    "Komet", "Kosmonaut", "Krater", "Krypton", "Launchpad", "Lightyear", "Luna", "Mars", "Mercury", 
    "Meteor", "Milkyway", "Moon", "Module", "NASA", "Nebula", "Neptune", "Neutron", "Nova", "Orbit", 
    "Orion", "Oxygen", "Parallaxe", "Photon", "Planet", "Pluto", "Pulsar", "Quasar", "Radiation", 
    "Rocket", "Rover", "Satellite", "Saturn", "Shuttle", "Singularity", "Skywalker", "Solar", "Space", 
    "Spacetime", "Star", "Supernova", "Telescope", "Terra", "Titan", "Trajectory", "Universe", "Uranus", 
    "Vacuum", "Venus", "Void", "Voyager", "Warp", "Wavelength", "White-Dwarf", "X-Ray", "Zenith", "Zodiac"
]

# --- FUNKTIONEN (Modell/Labels/DB wie zuvor) ---
@st.cache_resource
def load_my_model():
    try: return tf.keras.models.load_model('keras_model.h5', compile=False)
    except: return None

def load_labels(label_path):
    if not os.path.exists(label_path): return {0: "Schuhe", 1: "Brotdose", 2: "Handschuhe", 3: "Helme"}
    d = {}
    with open(label_path, "r", encoding="utf-8") as f:
        for l in f:
            p = l.strip().split(" ", 1)
            if len(p) == 2: d[int(p[0])] = p[1]
    return d

def get_database():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        df['Funddatum'] = pd.to_datetime(df['Funddatum']).dt.date
        df['Ablaufdatum'] = pd.to_datetime(df['Ablaufdatum']).dt.date
        return df
    return pd.DataFrame(columns=["ID", "Kategorie", "Funddatum", "Ablaufdatum", "Status"])

# --- UI SETUP ---
st.set_page_config(page_title="Fundkiste 2026", layout="wide")
model = load_my_model()
labels = load_labels("labels.txt")

# --- SIDEBAR ---
st.sidebar.title("🏢 Fundbüro-Zentrale")
auswahl = st.sidebar.radio("Navigation", ["Erfassen", "Datenbank", "Suche", "🎮 Space Typing"])

# --- MODI (Erfassen, Datenbank, Suche wie zuvor) ---
if auswahl == "Erfassen":
    st.header("📸 Neues Fundstück erfassen")
    # ... (Code wie oben)
elif auswahl == "Datenbank":
    st.header("📊 Datenbank")
    # ... (Code wie oben)
elif auswahl == "Suche":
    st.header("🔍 Suche")
    # ... (Code wie oben)

# --- MODUS: SPACE TYPING GAME ---
elif auswahl == "🎮 Space Typing":
    st.header("☄️ Space Typer: Zerstöre die Planeten!")
    
    # Initialisierung Game State
    if 'game_active' not in st.session_state:
        st.session_state.game_active = False
        st.session_state.lives = 3
        st.session_state.score = 0

    if not st.session_state.game_active:
        if st.button("Spiel STARTEN"):
            st.session_state.game_active = True
            st.session_state.lives = 3
            st.session_state.score = 0
            st.session_state.current_word = random.choice(SPACE_WORDS)
            st.session_state.start_time = time.time()
            st.rerun()
    else:
        # Timer Logik (z.B. 10 Sekunden pro Wort)
        zeit_limit = 8 # Sekunden
        vergangene_zeit = time.time() - st.session_state.start_time
        restzeit = max(0.0, zeit_limit - vergangene_zeit)

        # UI Anzeige
        c1, c2, c3 = st.columns(3)
        c1.metric("Leben", "❤️" * st.session_state.lives)
        c2.metric("Punkte", st.session_state.score)
        c3.metric("Zeit", f"{restzeit:.1f}s")

        st.progress(restzeit / zeit_limit)
        st.write(f"## Ziel-Wort: :blue[{st.session_state.current_word}]")

        # Eingabefeld (Auto-Erkennung)
        user_input = st.text_input("Tippe das Wort so schnell du kannst:", key="typing_box").strip()

        # 1. Check: Wort richtig getippt? (Auto-Erkennung)
        if user_input.lower() == st.session_state.current_word.lower():
            st.session_state.score += 10
            st.session_state.current_word = random.choice(SPACE_WORDS)
            st.session_state.start_time = time.time()
            st.toast("TREFFER! +10 Punkte", icon="💥")
            st.rerun()

        # 2. Check: Zeit abgelaufen?
        if restzeit <= 0:
            st.session_state.lives -= 1
            st.session_state.current_word = random.choice(SPACE_WORDS)
            st.session_state.start_time = time.time()
            if st.session_state.lives > 0:
                st.warning("Zeit abgelaufen! Ein Leben verloren.")
                time.sleep(1)
                st.rerun()
            else:
                st.session_state.game_active = False
                st.error(f"GAME OVER! Dein Score: {st.session_state.score}")
                if st.button("Erneut versuchen"):
                    st.rerun()
        
        # Automatischer Refresh für den Timer (alle 0.1 Sek)
        if st.session_state.game_active:
            time.sleep(0.1)
            st.rerun()
