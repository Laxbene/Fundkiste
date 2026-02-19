import streamlit as st
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np
import pandas as pd
import os
from datetime import datetime, timedelta

# --- KONFIGURATION & DATUM ---
HEUTE = datetime(2026, 2, 19).date()
DB_FILE = "fundstuecke_db.csv"

# --- FUNKTIONEN ---

@st.cache_resource
def load_my_model():
    try:
        # 'compile=False' gegen den TypeError bei Keras 3
        return tf.keras.models.load_model('keras_model.h5', compile=False)
    except Exception as e:
        st.error(f"Modellfehler: {e}")
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

# --- SIDEBAR MENÜ ---
st.sidebar.title("🏢 Fundbüro-Zentrale")
auswahl = st.sidebar.radio("Navigation", ["Erfassen", "Datenbank", "Suche"])

# --- MODUS: ERFASSEN ---
if auswahl == "Erfassen":
    st.header("📸 Neues Fundstück erfassen")
    uploaded_file = st.file_uploader("Bild des Fundstücks hochladen", type=["jpg", "png", "jpeg"])

    if uploaded_file and model:
        image = Image.open(uploaded_file).convert("RGB")
        st.image(image, caption="Vorschau", width=300)
        
        # KI-Analyse
        size = (224, 224)
        img_resized = ImageOps.fit(image, size, Image.LANCZOS)
        img_array = (np.asarray(img_resized).astype(np.float32) / 127.5) - 1
        pred = model.predict(np.expand_dims(img_array, axis=0))
        idx = np.argmax(pred)
        klasse = labels.get(idx, "Unbekannt")
        
        st.info(f"KI-Vorschlag: **{klasse}** (Sicherheit: {pred[0][idx]:.1%})")
        
        # Bestätigung & Speichern
        with st.form("save_form"):
            final_klasse = st.selectbox("Kategorie bestätigen", list(labels.values()), index=list(labels.values()).index(klasse))
            beschreibung = st.text_input("Zusatz-Beschreibung (z.B. 'Farbe blau')")
            submit = st.form_submit_button("In Datenbank speichern")
            
            if submit:
                df = get_database()
                ablauf = HEUTE + timedelta(days=30)
                neu_eintrag = {
                    "ID": len(df) + 1,
                    "Kategorie": final_klasse,
                    "Funddatum": HEUTE,
                    "Ablaufdatum": ablauf,
                    "Status": beschreibung
                }
                df = pd.concat([df, pd.DataFrame([neu_eintrag])], ignore_index=True)
                df.to_csv(DB_FILE, index=False)
                st.success("Erfolgreich gespeichert!")

# --- MODUS: DATENBANK ---
elif auswahl == "Datenbank":
    st.header("📊 Alle Fundstücke")
    df = get_database()
    
    if not df.empty:
        # Markierung: Ablaufsdatum <= Heute
        def highlight_expired(row):
            return ['background-color: #ff4b4b; color: white' if row['Ablaufdatum'] <= HEUTE else '' for _ in row]

        st.write("Einträge in Rot sind seit 30 Tagen un abgeholt und können entsorgt/gespendet werden.")
        st.dataframe(df.style.apply(highlight_expired, axis=1), use_container_width=True)
    else:
        st.write("Die Datenbank ist noch leer.")

# --- MODUS: SUCHE ---
elif auswahl == "Suche":
    st.header("🔍 Fundstücke suchen")
    suchbegriff = st.text_input("Suche nach Kategorie oder Beschreibung...")
    df = get_database()
    
    if suchbegriff and not df.empty:
        ergebnis = df[df.apply(lambda row: suchbegriff.lower() in row.astype(str).str.lower().values, axis=1)]
        st.write(f"{len(ergebnis)} Treffer gefunden:")
        st.table(ergebnis)
    elif not df.empty:
        st.write("Gib einen Suchbegriff ein.")
