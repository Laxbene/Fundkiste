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
    "Bigbang", "Blackhole", "Binary", "Booster", "Cassini", "Comet", "Cosmos", "Countdown", "Crater", 
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

# --- FUNKTIONEN ---
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

# --- MODI: ERFASSEN, DATENBANK, SUCHE (IDENTISCH ZU VORHER) ---
if auswahl == "Erfassen":
    st.header("📸 Neues Fundstück erfassen")
    uploaded_file = st.file_uploader("Bild hochladen", type=["jpg", "png", "jpeg"])
    if uploaded_file and model:
        image = Image.open(uploaded_file).convert("RGB")
        st.image(image, caption="Vorschau", width=300)
        img_resized = ImageOps.fit(image, (224, 224), Image.LANCZOS)
        img_array = (np.asarray(img_resized).astype(np.float32) / 127.5) - 1
        pred = model.predict(np.expand_dims(img_array, axis=0))
        klasse = labels.get(np.argmax(pred), "Unbekannt")
        st.info(f"KI-Vorschlag: **{klasse}**")
        with st.form("save_form"):
            final_klasse = st.selectbox("Kategorie", list(labels.values()), index=list(labels.values()).index(klasse))
            beschreibung = st.text_input("Zusatz-Beschreibung")
            if st.form_submit_button("Speichern"):
                df = get_database()
                neu = {"ID": len(df)+1, "Kategorie": final_klasse, "Funddatum": HEUTE, "Ablaufdatum": HEUTE+timedelta(days=30), "Status": beschreibung}
                pd.concat([df, pd.DataFrame([neu])], ignore_index=True).to_csv(DB_FILE, index=False)
                st.success("Gespeichert!")

elif auswahl == "Datenbank":
    st.header("📊 Datenbank")
    df = get_database()
    if not df.empty:
        st.dataframe(df.style.apply(lambda r: ['background-color: #ff4b4b' if r['Ablaufdatum'] <= HEUTE else '' for _ in r], axis=1), use_container_width=True)

elif auswahl == "Suche":
    st.header("🔍 Suche")
    query = st.text_input("Begriff eingeben...")
    df = get_database()
    if query and not df.empty:
        st.table(df[df.apply(lambda r: query.lower() in r.astype(str).str.lower().values, axis=1)])

# --- MODUS: SPACE TYPING GAME (MIT AUTO-CLEAR) ---
elif auswahl == "🎮 Space Typing":
    st.header("☄️ Space Typer")
    
    if 'game_active' not in st.session_state:
        st.session_state.game_active = False
        st.session_state.lives = 3
        st.session_state.score = 0
        st.session_state.input_key = 0 # Der Trick zum Leeren des Feldes

    if not st.session_state.game_active:
        if st.button("Spiel STARTEN"):
            st.session_state.game_active = True
            st.session_state.lives = 3
            st.session_state.score = 0
            st.session_state.current_word = random.choice(SPACE_WORDS)
            st.session_state.start_time = time.time()
            st.session_state.input_key += 1
            st.rerun()
    else:
        zeit_limit = 7.0
        vergangene_zeit = time.time() - st.session_state.start_time
        restzeit = max(0.0, zeit_limit - vergangene_zeit)

        c1, c2, c3 = st.columns(3)
        c1.metric("Leben", "❤️" * st.session_state.lives)
        c2.metric("Punkte", st.session_state.score)
        c3.metric("Zeit", f"{restzeit:.1f}s")

        st.progress(restzeit / zeit_limit)
        st.write(f"## Ziel-Wort: :orange[{st.session_state.current_word}]")

        # Dynamischer Key leert das Feld automatisch bei Änderung
        user_input = st.text_input("Tippe hier:", key=f"input_{st.session_state.input_key}").strip()

        # Check: Richtig getippt?
        if user_input.lower() == st.session_state.current_word.lower():
            st.session_state.score += 10
            st.session_state.current_word = random.choice(SPACE_WORDS)
            st.session_state.start_time = time.time()
            st.session_state.input_key += 1 # Feld wird geleert
            st.toast("TREFFER!", icon="💥")
            st.rerun()

        # Check: Zeit abgelaufen?
        if restzeit <= 0:
            st.session_state.lives -= 1
            st.session_state.current_word = random.choice(SPACE_WORDS)
            st.session_state.start_time = time.time()
            st.session_state.input_key += 1 # Feld wird geleert
            if st.session_state.lives <= 0:
                st.session_state.game_active = False
            st.rerun()
        
        # Schneller Refresh für den Timer
        time.sleep(0.1)
        st.rerun()
