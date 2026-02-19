import streamlit as st
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np
import pandas as pd
import os
import random
import time
from datetime import datetime, timedelta
import streamlit.components.v1 as components # Für den Fokus-Hack

# --- KONFIGURATION ---# --- MODUS: SPACE TYPING GAME ---
elif auswahl == "🎮 Space Typing":
    st.header("☄️ Space Typer")
    
    # Initialisierung Game State
    if 'input_key' not in st.session_state: st.session_state.input_key = 0
    if 'game_active' not in st.session_state: st.session_state.game_active = False

    if not st.session_state.game_active:
        if st.button("Spiel STARTEN"):
            st.session_state.game_active, st.session_state.lives, st.session_state.score = True, 3, 0
            st.session_state.current_word = random.choice(SPACE_WORDS)
            st.session_state.start_time = time.time()
            st.rerun()
    else:
        # Zeitberechnung
        zeit_limit = 7.0
        vergangene_zeit = time.time() - st.session_state.start_time
        restzeit = max(0.0, zeit_limit - vergangene_zeit)

        # UI Anzeige
        c1, c2, c3 = st.columns(3)
        c1.metric("Leben", "❤️" * st.session_state.lives)
        c2.metric("Punkte", st.session_state.score)
        c3.metric("Zeit", f"{restzeit:.1f}s")

        st.progress(restzeit / zeit_limit)
        st.write(f"## Tippe: :orange[{st.session_state.current_word}]")

        # DER TRICK: Ein eindeutiger ID-Name für das Feld
        field_id = f"input_{st.session_state.input_key}"
        
        # Eingabefeld
        user_input = st.text_input("Deine Eingabe:", key=field_id).strip()

        # FOKUS-HACK: JavaScript, das das Feld nach dem Laden automatisch fokussiert
        components.html(
            f"""
            <script>
                var input = window.parent.document.querySelector("input[id*='{field_id}']");
                if (input) {{
                    input.focus();
                }}
            </script>
            """,
            height=0,
        )

        # Logik: Wort richtig getippt?
        if user_input.lower() == st.session_state.current_word.lower():
            st.session_state.score += 10
            st.session_state.current_word = random.choice(SPACE_WORDS)
            st.session_state.start_time = time.time()
            st.session_state.input_key += 1 # Ändert den Key -> Feld wird leer
            st.rerun()

        # Logik: Zeit abgelaufen?
        if restzeit <= 0:
            st.session_state.lives -= 1
            st.session_state.current_word = random.choice(SPACE_WORDS)
            st.session_state.start_time = time.time()
            st.session_state.input_key += 1 # Ändert den Key -> Feld wird leer
            if st.session_state.lives <= 0:
                st.session_state.game_active = False
            st.rerun()
        
        # Kurze Pause für den Timer-Refresh
        time.sleep(0.1)
        st.rerun()
HEUTE = datetime(2026, 2, 19).date()
DB_FILE = "fundstuecke_db.csv"
IMG_FOLDER = "images"

if not os.path.exists(IMG_FOLDER):
    os.makedirs(IMG_FOLDER)

SPACE_WORDS = ["Asteroid", "Astronaut", "Apollo", "Atmosphäre", "Antimaterie", "Alien", "Aurora", "Blackhole", "Comet", "Cosmos", "Darkmatter", "Deepspace", "Eclipse", "Exoplanet", "Galaxy", "Gravity", "Hubble", "Interstellar", "Jupiter", "Kepler", "Mars", "Meteor", "Milkyway", "Moon", "Nebula", "Neptune", "Orbit", "Orion", "Planet", "Pluto", "Rocket", "Rover", "Saturn", "Shuttle", "Star", "Supernova", "Telescope", "Universe", "Uranus", "Venus", "Voyager", "Warp", "Zenith"]

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
        return df
    return pd.DataFrame(columns=["ID", "Kategorie", "Funddatum", "Ablaufdatum", "Status", "Bild_Pfad"])

# --- UI SETUP ---
st.set_page_config(page_title="Fundkiste 2026", layout="wide")
model = load_my_model()
labels = load_labels("labels.txt")

st.sidebar.title("🏢 Fundbüro-Zentrale")
auswahl = st.sidebar.radio("Navigation", ["Erfassen", "Datenbank", "Suche", "🎮 Space Typing"])

# --- MODUS: ERFASSEN ---
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
            if st.form_submit_button("In Datenbank speichern"):
                # Bild speichern
                img_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                img_path = os.path.join(IMG_FOLDER, img_filename)
                image.save(img_path)
                
                df = get_database()
                neu = {
                    "ID": len(df)+1, 
                    "Kategorie": final_klasse, 
                    "Funddatum": HEUTE, 
                    "Ablaufdatum": HEUTE+timedelta(days=30), 
                    "Status": beschreibung,
                    "Bild_Pfad": img_path
                }
                pd.concat([df, pd.DataFrame([neu])], ignore_index=True).to_csv(DB_FILE, index=False)
                st.success("Gespeichert!")

# --- MODUS: DATENBANK ---
elif auswahl == "Datenbank":
    st.header("📊 Datenbank mit Fotos")
    df = get_database()
    if not df.empty:
        for idx, row in df.iterrows():
            col1, col2, col3 = st.columns([1, 3, 2])
            with col1:
                if os.path.exists(str(row['Bild_Pfad'])):
                    st.image(row['Bild_Pfad'], width=100)
                else:
                    st.write("Kein Bild")
            with col2:
                st.write(f"**{row['Kategorie']}** (ID: {row['ID']})")
                st.write(f"Status: {row['Status']}")
            with col3:
                farbe = "red" if str(row['Ablaufdatum']) <= str(HEUTE) else "green"
                st.markdown(f"📅 Ablauf: :{farbe}[{row['Ablaufdatum']}]")
            st.divider()
    else:
        st.write("Datenbank ist leer.")

# --- MODUS: SPACE TYPING GAME ---
elif auswahl == "🎮 Space Typing":
    st.header("☄️ Space Typer")
    
    # Initialisierung Game State
    if 'input_key' not in st.session_state: st.session_state.input_key = 0
    if 'game_active' not in st.session_state: st.session_state.game_active = False

    if not st.session_state.game_active:
        if st.button("Spiel STARTEN"):
            st.session_state.game_active, st.session_state.lives, st.session_state.score = True, 3, 0
            st.session_state.current_word = random.choice(SPACE_WORDS)
            st.session_state.start_time = time.time()
            st.rerun()
    else:
        # Zeitberechnung
        zeit_limit = 7.0
        vergangene_zeit = time.time() - st.session_state.start_time
        restzeit = max(0.0, zeit_limit - vergangene_zeit)

        # UI Anzeige
        c1, c2, c3 = st.columns(3)
        c1.metric("Leben", "❤️" * st.session_state.lives)
        c2.metric("Punkte", st.session_state.score)
        c3.metric("Zeit", f"{restzeit:.1f}s")

        st.progress(restzeit / zeit_limit)
        st.write(f"## Tippe: :orange[{st.session_state.current_word}]")

        # DER TRICK: Ein eindeutiger ID-Name für das Feld
        field_id = f"input_{st.session_state.input_key}"
        
        # Eingabefeld
        user_input = st.text_input("Deine Eingabe:", key=field_id).strip()

        # FOKUS-HACK: JavaScript, das das Feld nach dem Laden automatisch fokussiert
        components.html(
            f"""
            <script>
                var input = window.parent.document.querySelector("input[id*='{field_id}']");
                if (input) {{
                    input.focus();
                }}
            </script>
            """,
            height=0,
        )

        # Logik: Wort richtig getippt?
        if user_input.lower() == st.session_state.current_word.lower():
            st.session_state.score += 10
            st.session_state.current_word = random.choice(SPACE_WORDS)
            st.session_state.start_time = time.time()
            st.session_state.input_key += 1 # Ändert den Key -> Feld wird leer
            st.rerun()

        # Logik: Zeit abgelaufen?
        if restzeit <= 0:
            st.session_state.lives -= 1
            st.session_state.current_word = random.choice(SPACE_WORDS)
            st.session_state.start_time = time.time()
            st.session_state.input_key += 1 # Ändert den Key -> Feld wird leer
            if st.session_state.lives <= 0:
                st.session_state.game_active = False
            st.rerun()
        
        # Kurze Pause für den Timer-Refresh
        time.sleep(0.1)
        st.rerun()
