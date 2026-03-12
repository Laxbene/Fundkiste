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
from supabase import create_client, Client

# --- SUPABASE KONFIGURATION ---
SUPABASE_URL = "https://cbrbonsyglqyiefpfuhi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNicmJvbnN5Z2xxeWllZnBmdWhpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMzMTU3OTYsImV4cCI6MjA4ODg5MTc5Nn0.V2HyvfLjP5TCmwz1AqXg2CZ52odKzp2G51IG2TNYuII"
BUCKET_NAME = "mein_bucket"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- WEITERE KONFIGURATION ---
HEUTE = datetime(2026, 3, 12).date()
CONFIDENCE_THRESHOLD = 0.60
SPACE_WORDS = ["Asteroid", "Astronaut", "Apollo", "Atmosphäre", "Antimaterie", "Alien", "Aurora", "Blackhole", "Comet", "Cosmos", "Darkmatter", "Deepspace", "Eclipse", "Exoplanet", "Galaxy", "Gravity", "Hubble", "Interstellar", "Jupiter", "Kepler", "Mars", "Meteor", "Milkyway", "Moon", "Nebula", "Neptune", "Orbit", "Orion", "Planet", "Pluto", "Rocket", "Rover", "Saturn", "Shuttle", "Star", "Supernova", "Telescope", "Universe", "Uranus", "Venus", "Voyager", "Warp", "Zenith"]

QUIZ_QUESTIONS = [
    {"q": "Was ist die Hauptstadt von Frankreich?", "a": ["Berlin", "Madrid", "Paris", "Rom"], "correct": "Paris"},
    {"q": "Wie viele Planeten hat unser Sonnensystem?", "a": ["7", "8", "9", "10"], "correct": "8"},
    {"q": "Wer malte die Mona Lisa?", "a": ["Picasso", "Van Gogh", "Da Vinci", "Monet"], "correct": "Da Vinci"}
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
    try:
        response = supabase.table("fundstuecke").select("*").execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame(columns=["id", "kategorie", "funddatum", "ablaufdatum", "status", "bild_url"])

def delete_entry(entry_id, file_path):
    # 1. Aus Tabelle löschen
    supabase.table("fundstuecke").delete().eq("id", entry_id).execute()
    # 2. Aus Storage löschen
    try:
        file_name = file_path.split("/")[-1]
        supabase.storage.from_(BUCKET_NAME).remove([file_name])
    except:
        pass

# --- UI SETUP ---
st.set_page_config(page_title="Fundkiste Cloud 2026", layout="wide")
model = load_my_model()
labels = load_labels("labels.txt")

st.sidebar.title("🏢 Cloud Zentrale")
auswahl = st.sidebar.selectbox("Navigation", 
    ["Erfassen", "Datenbank", "📋 Kategorien-Galerie", "🎮 Spiele & Quiz"])

# --- MODUS: ERFASSEN ---
if auswahl == "Erfassen":
    st.header("📸 Cloud-Erfassung")
    uploaded_file = st.file_uploader("Bild hochladen", type=["jpg", "png", "jpeg"])
    
    if uploaded_file and model:
        image = Image.open(uploaded_file).convert("RGB")
        st.image(image, caption="Vorschau", width=300)
        
        # KI Vorhersage
        img_resized = ImageOps.fit(image, (224, 224), Image.LANCZOS)
        img_array = (np.asarray(img_resized).astype(np.float32) / 127.5) - 1
        pred = model.predict(np.expand_dims(img_array, axis=0))
        idx = np.argmax(pred)
        confidence = pred[0][idx]
        
        klasse = labels.get(idx, "Unbekannt") if confidence >= CONFIDENCE_THRESHOLD else "Nicht erkannt"
        if confidence < CONFIDENCE_THRESHOLD: st.warning(f"Unsicher ({confidence:.1%})")
        else: st.success(f"Erkannt: {klasse}")

        with st.form("save_form"):
            k_liste = list(labels.values()) + ["Nicht erkannt"]
            final_klasse = st.selectbox("Kategorie", k_liste, index=k_liste.index(klasse) if klasse in k_liste else 0)
            beschreibung = st.text_input("Zusatz-Info")
            if st.form_submit_button("In Cloud speichern"):
                # 1. Bild hochladen
                file_name = f"{int(time.time())}.jpg"
                img_bytes = uploaded_file.getvalue()
                supabase.storage.from_(BUCKET_NAME).upload(file_name, img_bytes)
                img_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_name)
                
                # 2. In DB speichern
                data = {
                    "kategorie": final_klasse,
                    "funddatum": str(HEUTE),
                    "ablaufdatum": str(HEUTE + timedelta(days=30)),
                    "status": beschreibung,
                    "bild_url": img_url
                }
                supabase.table("fundstuecke").insert(data).execute()
                st.success("Erfolgreich in Supabase gespeichert!")

# --- MODUS: DATENBANK ---
elif auswahl == "Datenbank":
    st.header("📊 Cloud Datenbank")
    df = get_database()
    if not df.empty:
        for _, row in df.iterrows():
            c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
            with c1: st.image(row['bild_url'], width=120)
            with c2: st.write(f"**{row['kategorie']}**\n\n{row['status']}")
            with c3: st.write(f"📅 {row['funddatum']}\n\n⏰ Ablauf: {row['ablaufdatum']}")
            with c4: 
                if st.button("✅ Weg", key=f"del_{row['id']}"):
                    delete_entry(row['id'], row['bild_url'])
                    st.rerun()
            st.divider()

# --- MODUS: GALERIE ---
elif auswahl == "📋 Kategorien-Galerie":
    st.header("📋 Cloud Inventar")
    df = get_database()
    if not df.empty:
        for kat in sorted(df['kategorie'].unique()):
            with st.expander(f"📁 {kat.upper()}"):
                kat_df = df[df['kategorie'] == kat]
                cols = st.columns(4)
                for i, (_, item) in enumerate(kat_df.iterrows()):
                    with cols[i % 4]:
                        st.image(item['bild_url'], use_container_width=True)
                        st.caption(f"{item['funddatum']}")
                        if st.button("Löschen", key=f"gal_{item['id']}"):
                            delete_entry(item['id'], item['bild_url'])
                            st.rerun()

# --- SPIELE (Vereinfacht zusammengefasst) ---
elif auswahl == "🎮 Spiele & Quiz":
    tab1, tab2 = st.tabs(["🚀 Space Typer", "🧠 Quiz"])
    with tab1:
        st.write("Space Typer wird hier gestartet...")
        # (Hier den Code für Space Typer einfügen wie oben)
    with tab2:
        # (Hier den Code für Quiz einfügen wie oben)
        st.write("Allgemeinwissen-Quiz bereit.")
