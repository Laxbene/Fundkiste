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

# --- FUNKTIONEN ---
@st.cache_resource
def load_my_model():
    try:
        return tf.keras.models.load_model('keras_model.h5', compile=False)
    except Exception as e:
        return None

def load_labels(label_path):
    if not os.path.exists(label_path):
        return {0: "Schuhe", 1: "Brotdose", 2: "Handschuhe", 3: "Helme"}
    label_dict = {}
    with open(label_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(" ", 1)
            if len(parts) == 2:
                label_dict[int(parts[0])] = parts[1]
    return label_dict

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
auswahl = st.sidebar.radio("Navigation", ["Erfassen", "Datenbank", "Suche", "🎮 Planeten-Abwehr"])

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
            if st.form_submit_button("Speichern"):
                df = get_database()
                neu = {"ID": len(df)+1, "Kategorie": final_klasse, "Funddatum": HEUTE, "Ablaufdatum": HEUTE+timedelta(days=30), "Status": beschreibung}
                pd.concat([df, pd.DataFrame([neu])], ignore_index=True).to_csv(DB_FILE, index=False)
                st.success("Gespeichert!")

# --- MODUS: DATENBANK ---
elif auswahl == "Datenbank":
    st.header("📊 Alle Fundstücke")
    df = get_database()
    if not df.empty:
        st.dataframe(df.style.apply(lambda r: ['background-color: #ff4b4b' if r['Ablaufdatum'] <= HEUTE else '' for _ in r], axis=1), use_container_width=True)

# --- MODUS: SUCHE ---
elif auswahl == "Suche":
    st.header("🔍 Suche")
    query = st.text_input("Begriff eingeben...")
    df = get_database()
    if query and not df.empty:
        st.table(df[df.apply(lambda r: query.lower() in r.astype(str).str.lower().values, axis=1)])

# --- MODUS: GAME (PLANETEN-ABWEHR) ---
elif auswahl == "🎮 Planeten-Abwehr":
    st.header("☄️ Planeten-Abwehr: Tippe um zu überleben!")
    
    # Game State Initialisierung
    if 'lives' not in st.session_state or st.session_state.lives <= 0:
        st.session_state.lives = 3
        st.session_state.score = 0
        st.session_state.planet_pos = 0 # 0 = weit weg, 10 = Crash
        st.session_state.current_word = random.choice(list(labels.values()))

    # Anzeige
    col1, col2 = st.columns(2)
    col1.metric("Leben", "❤️" * st.session_state.lives)
    col2.metric("Punkte", st.session_state.score)

    # Planeten-Visualisierung (einfach per Progress Bar)
    st.write(f"### 🪐 Ein Planet nähert sich: **{st.session_state.current_word}**")
    distanz_anzeige = st.progress(st.session_state.planet_pos * 10)
    
    if st.session_state.planet_pos >= 10:
        st.error("BOOM! Der Planet ist eingeschlagen!")
        st.session_state.lives -= 1
        st.session_state.planet_pos = 0
        st.session_state.current_word = random.choice(list(labels.values()))
        st.rerun()

    # Eingabe
    user_input = st.text_input("Tippe das Wort schnell ein:", key="game_input").strip()

    if user_input.lower() == st.session_state.current_word.lower():
        st.success("ZERSTÖRT! ✨")
        st.session_state.score += 10
        st.session_state.planet_pos = 0
        st.session_state.current_word = random.choice(list(labels.values()))
        st.rerun()

    # Schwierigkeit: Mit jedem Button-Klick (Rerun) kommt der Planet näher
    if st.button("Warten / Nächster Schritt"):
        st.session_state.planet_pos += 2
        st.rerun()

    if st.session_state.lives <= 0:
        st.error(f"GAME OVER! Dein Endstand: {st.session_state.score} Punkte.")
        if st.button("Neustart"):
            st.session_state.lives = 3
            st.rerun()
