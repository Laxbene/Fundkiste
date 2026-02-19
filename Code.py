import streamlit as st
import streamlit.components.v1 as components
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np
import pandas as pd
import os
import random
import time
from datetime import datetime, timedelta

# --- KONFIGURATION ---
HEUTE = datetime(2026, 2, 19).date()
DB_FILE = "fundstuecke_db.csv"
IMG_FOLDER = "images"

if not os.path.exists(IMG_FOLDER):
    os.makedirs(IMG_FOLDER)

# 100 Wörter für das Spiel
SPACE_WORDS = ["Asteroid", "Astronaut", "Apollo", "Atmosphäre", "Antimaterie", "Alien", "Aurora", "Blackhole", "Comet", "Cosmos", "Darkmatter", "Deepspace", "Eclipse", "Exoplanet", "Galaxy", "Gravity", "Hubble", "Interstellar", "Jupiter", "Kepler", "Mars", "Meteor", "Milkyway", "Moon", "Nebula", "Neptune", "Orbit", "Orion", "Planet", "Pluto", "Rocket", "Rover", "Saturn", "Shuttle", "Star", "Supernova", "Telescope", "Universe", "Uranus", "Venus", "Voyager", "Warp", "Zenith"]

# --- FUNKTIONEN ---
@st.cache_resource
def load_my_model():
    try:
        return tf.keras.models.load_model('keras_model.h5', compile=False)
    except:
        return None

def load_labels(label_path):
    if not os.path.exists(label_path):
        return {0: "Schuhe", 1: "Brotdose", 2: "Handschuhe", 3: "Helme"}
    d = {}
    with open(label_path, "r", encoding="utf-8") as f:
        for l in f:
            p = l.strip().split(" ", 1)
            if len(p) == 2: d[int(p[0])] = p[1]
    return d

def get_database():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["ID", "Kategorie", "Funddatum", "Ablaufdatum", "Status", "Bild_Pfad"])

def delete_entry(entry_id):
    df = get_database()
    # Bild löschen, falls vorhanden
    img_to_delete = df.loc[df['ID'] == entry_id, 'Bild_Pfad'].values
    if len(img_to_delete) > 0 and os.path.exists(str(img_to_delete[0])):
        os.remove(str(img_to_delete[0]))
    # Aus DF entfernen und speichern
    df = df[df['ID'] != entry_id]
    df.to_csv(DB_FILE, index=False)

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
                img_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                img_path = os.path.join(IMG_FOLDER, img_filename)
                image.save(img_path)
                
                df = get_database()
                neu = {
                    "ID": int(time.time()), # Eindeutige ID über Timestamp
                    "Kategorie": final_klasse, 
                    "Funddatum": HEUTE, "Ablaufdatum": HEUTE+timedelta(days=30), 
                    "Status": beschreibung, "Bild_Pfad": img_path
                }
                pd.concat([df, pd.DataFrame([neu])], ignore_index=True).to_csv(DB_FILE, index=False)
                st.success("Gespeichert!")

# --- MODUS: DATENBANK ---
elif auswahl == "Datenbank":
    st.header("📊 Datenbank mit Fotos")
    df = get_database()
    if not df.empty:
        for idx, row in df.iterrows():
            col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
            with col1:
                if os.path.exists(str(row['Bild_Pfad'])):
                    st.image(row['Bild_Pfad'], width=100)
                else: st.write("🖼️")
            with col2:
                st.write(f"**{row['Kategorie']}**")
                st.write(f"Notiz: {row['Status']}")
            with col3:
                farbe = "red" if str(row['Ablaufdatum']) <= str(HEUTE) else "green"
                st.markdown(f"📅 Ablauf: :{farbe}[{row['Ablaufdatum']}]")
            with col4:
                if st.button("✅ Abgeholt", key=f"del_{row['ID']}"):
                    delete_entry(row['ID'])
                    st.rerun()
            st.divider()
    else:
        st.write("Die Datenbank ist leer.")

# --- MODUS: SUCHE ---
elif auswahl == "Suche":
    st.header("🔍 Suche")
    query = st.text_input("Suchen...")
    df = get_database()
    if query and not df.empty:
        ergebnis = df[df.apply(lambda r: query.lower() in r.astype(str).str.lower().values, axis=1)]
        st.dataframe(ergebnis)

# --- MODUS: SPACE TYPING GAME ---
elif auswahl == "🎮 Space Typing":
    if 'game_active' not in st.session_state: st.session_state.game_active = False
    if 'input_key' not in st.session_state: st.session_state.input_key = 0

    if not st.session_state.game_active:
        if st.button("Spiel STARTEN"):
            st.session_state.game_active, st.session_state.lives, st.session_state.score = True, 3, 0
            st.session_state.current_word = random.choice(SPACE_WORDS)
            st.session_state.start_time = time.time()
            st.rerun()
    else:
        restzeit = max(0.0, 7.0 - (time.time() - st.session_state.start_time))
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Leben", "❤️" * st.session_state.lives)
        c2.metric("Score", st.session_state.score)
        c3.metric("Zeit", f"{restzeit:.1f}s")
        
        st.progress(restzeit / 7.0)
        st.write(f"## Ziel: :orange[{st.session_state.current_word}]")

        field_id = f"typing_field_{st.session_state.input_key}"
        # Automatische Überprüfung durch direkten Vergleich des Rückgabewerts
        user_input = st.text_input("Tippe hier (automatische Erkennung):", key=field_id).strip()

        # JS Fokus-Hack, damit der Cursor immer im Feld bleibt
        components.html(f"""<script>var input = window.parent.document.querySelector("input[id*='{field_id}']"); if(input) {{ input.focus(); }}</script>""", height=0)

        # Logik: Automatische Erkennung ohne Enter
        if user_input.lower() == st.session_state.current_word.lower():
            st.session_state.score += 10
            st.session_state.current_word = random.choice(SPACE_WORDS)
            st.session_state.start_time = time.time()
            st.session_state.input_key += 1 # Leert das Feld
            st.rerun()

        if restzeit <= 0:
            st.session_state.lives -= 1
            st.session_state.current_word = random.choice(SPACE_WORDS)
            st.session_state.start_time = time.time()
            st.session_state.input_key += 1
            if st.session_state.lives <= 0: st.session_state.game_active = False
            st.rerun()
        
        time.sleep(0.1)
        st.rerun()
