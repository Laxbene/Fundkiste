import streamlit as st
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np
import os

# 1. Modell laden mit Fehlerbehandlung
@st.cache_resource
def load_my_model():
    model_path = 'keras_model.h5'
    if not os.path.exists(model_path):
        st.error(f"Datei '{model_path}' wurde nicht im Verzeichnis gefunden!")
        return None
    
    try:
        # 'compile=False' verhindert Fehler durch inkompatible Optimizer-Einstellungen
        model = tf.keras.models.load_model(model_path, compile=False)
        return model
    except Exception as e:
        st.error(f"Fehler beim Laden des Modells: {e}")
        return None

# 2. Label-Parsing für deine Fundstücke 
def load_labels(label_path):
    if not os.path.exists(label_path):
        return {0: "Schuhe", 1: "Brotdose", 2: "Handschuhe", 3: "Helme"} # Fallback 
    
    label_dict = {}
    with open(label_path, "r", encoding="utf-8") as f:
        for line in f:
            # Erwartet: "0 Schuhe" oder "1 Brotdose" 
            parts = line.strip().split(" ", 1)
            if len(parts) == 2:
                idx, name = parts
                label_dict[int(idx)] = name
    return label_dict

# --- UI Setup ---
st.set_page_config(page_title="Fundkiste KI", page_icon="🎒")
st.title("🎒 Fundkiste: Objekt-Erkennung")
st.write("Lade ein Foto hoch, um zu sehen, ob es sich um Schuhe, eine Brotdose, Handschuhe oder einen Helm handelt.")

# Ressourcen initialisieren
model = load_my_model()
labels = load_labels("labels.txt")

# Bild-Upload
uploaded_file = st.file_uploader("Bild auswählen...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None and model is not None:
    # Bild anzeigen
    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, caption='Dein Foto', use_container_width=True)
    
    # Button für die Analyse
    if st.button("Gegenstand analysieren"):
        with st.spinner('KI denkt nach...'):
            # Preprocessing (Passend für Teachable Machine / Standard Keras)
            size = (224, 224)
            image_resized = ImageOps.fit(image, size, Image.LANCZOS)
            image_array = np.asarray(image_resized)
            
            # Normalisierung auf den Bereich [-1, 1]
            normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1
            
            # Batch-Dimension erstellen
            data = np.expand_dims(normalized_image_array, axis=0)

            # Vorhersage
            prediction = model.predict(data)
            index = np.argmax(prediction)
            
            # Ergebnis aus labels.txt abrufen 
            class_name = labels.get(index, "Unbekannt")
            confidence = prediction[0][index]

            # Anzeige der Ergebnisse
            st.divider()
            if confidence > 0.6:
                st.balloons()
                st.success(f"Das ist mit {confidence:.1%} Wahrscheinlichkeit: **{class_name}**")
            else:
                st.warning(f"Ich bin mir unsicher, vermute aber: **{class_name}** ({confidence:.1%})")

            # Balkendiagramm für alle Klassen
            st.write("### Details der Analyse:")
            chart_data = {labels.get(i, f"Klasse {i}"): float(prob) for i, prob in enumerate(prediction[0])}
            st.bar_chart(chart_data)
