import streamlit as st
import streamlit.components.v1 as components
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np
import pandas as pd
import random
import time
from datetime import datetime, timedelta
from supabase import create_client, Client

# --- SUPABASE KONFIGURATION ---
# Ersetze diese Werte mit deinen echten Supabase-Daten!
SUPABASE_URL = "DEINE_SUPABASE_URL"
SUPABASE_KEY = "DEIN_SUPABASE_ANON_KEY"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- KONFIGURATION ---
HEUTE = datetime.now().date()
CONFIDENCE_THRESHOLD = 0.60
SPACE_WORDS = ["Asteroid", "Astronaut", "Apollo", "Galaxy", "Universe"] # Gekürzt für Übersicht
QUIZ_QUESTIONS = [{"q": "Planeten?", "a": ["7", "8"], "correct": "8"}] # Gekürzt

# --- FUNKTIONEN ---
@st.cache_resource
def load_my_model():
    try: return tf.keras.models.load_model('keras_model.h5', compile=False)
    except: return None

def load_labels(label_path):
    if not os.path.exists(label_path): return {0: "Schuhe", 1: "Brotdose", 2: "Handschuhe", 3: "Helme"}
    # ... (deine bisherige Logik)

def get_database_from_supabase():
    # Holt alle Daten aus der Tabelle 'fundstuecke'
    response = supabase.table("fundstuecke").select("*").execute()
    return pd.DataFrame(response.data)

def delete_entry_supabase(entry_id, bild_url):
    # Löscht Eintrag aus DB
    supabase.table("fundstuecke").delete().eq("id", entry_id).execute()
    # Optional: Bild aus Storage löschen (Pfad extrahieren nötig)
    st.success("Eintrag gelöscht!")

# --- UI SETUP ---
st.set_page_config(page_title="Fundkiste Supabase 2026", layout="wide")
model = load_my_model()
labels = {0: "Schuhe", 1: "Brotdose", 2: "Handschuhe", 3: "Helme"} # Vereinfacht

st.sidebar.title("🏢 Zentrale (Cloud)")
auswahl = st.sidebar.selectbox("Navigation", 
    ["📸 Erfassen", "📊 Datenbank", "📋 Kategorien-Galerie", "🔍 Suche", "🎮 Space Typing"])

# --- MODUS: ERFASSEN ---
if auswahl == "📸 Erfassen":
    st.header("📸 Cloud-Erfassung")
    uploaded_file = st.file_uploader("Bild hochladen", type=["jpg", "png", "jpeg"])
    
    if uploaded_file and model:
        image = Image.open(uploaded_file).convert("RGB")
        st.image(image, width=300)
        
        # KI LOGIK (bleibt gleich)
        img_resized = ImageOps.fit(image, (224, 224), Image.LANCZOS)
        img_array = (np.asarray(img_resized).astype(np.float32) / 127.5) - 1
        pred = model.predict(np.expand_dims(img_array, axis=0))
        idx = np.argmax(pred)
        klasse = labels.get(idx, "Unbekannt")
        
        with st.form("save_form"):
            final_klasse = st.selectbox("Kategorie", list(labels.values()), index=idx)
            beschreibung = st.text_input("Zusatz-Info")
            submit = st.form_submit_button("In die Cloud speichern")
            
            if submit:
                # 1. Bild in Supabase Storage hochladen
                file_name = f"{int(time.time())}.jpg"
                img_byte_arr = uploaded_file.getvalue()
                
                storage_res = supabase.storage.from_("images").upload(file_name, img_byte_arr)
                
                # Public URL holen
                img_url = supabase.storage.from_("images").get_public_url(file_name)
                
                # 2. Daten in Tabelle speichern
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
elif auswahl == "📊 Datenbank":
    st.header("📊 Cloud-Datenbank")
    df = get_database_from_supabase()
    
    if not df.empty:
        for _, row in df.iterrows():
            c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
            with c1:
                st.image(row['bild_url'], width=120)
            with c2: 
                st.write(f"**{row['kategorie']}**\n\n{row['status']}")
            with c3: 
                st.write(f"📅 {row['funddatum']}\n\n⏰ {row['ablaufdatum']}")
            with c4: 
                if st.button("✅ Weg", key=f"del_{row['id']}"):
                    delete_entry_supabase(row['id'], row['bild_url'])
                    st.rerun()
            st.divider()
    else:
        st.info("Cloud ist leer.")

# ... (Rest der Spiele bleibt gleich, da sie keine DB brauchen)
