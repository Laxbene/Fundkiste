import streamlit as st
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np

# 1. Modell laden
@st.cache_resource
def load_my_model():
    # Lädt das lokale Keras-Modell 
    model = tf.keras.models.load_model('keras_model.h5')
    return model

# 2. Label-Parsing
def load_labels(label_path):
    label_dict = {}
    with open(label_path, "r", encoding="utf-8") as f:
        for line in f:
            # Erwartetes Format in labels.txt: "0 Schuhe" 
            parts = line.strip().split(" ", 1)
            if len(parts) == 2:
                idx, name = parts
                label_dict[int(idx)] = name
    return label_dict

# App-Interface
st.title("🔍 Fundstück-Klassifikator")
st.write("Lade ein Foto eines Gegenstands hoch, um ihn zu identifizieren.")

# Ressourcen laden
model = load_my_model()
labels = load_labels("labels.txt")

# Bild-Upload
uploaded_file = st.file_uploader("Bild auswählen...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Bild anzeigen
    image = Image.open(uploaded_file)
    st.image(image, caption='Hochgeladenes Bild', use_container_width=True)
    
    st.write("---")
    st.write("### Vorhersage läuft...")

    # Vorbereitung des Bildes für das Modell (Preprocessing)
    # Hinweis: Viele Keras-Modelle erwarten 224x224 Pixel
    size = (224, 224)
    image = ImageOps.fit(image, size, Image.LANCZOS)
    image_array = np.asarray(image)
    
    # Normalisierung (falls das Modell auf [0,1] oder [-1,1] trainiert wurde)
    normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1
    
    # Batch-Dimension hinzufügen
    data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
    data[0] = normalized_image_array

    # Inferenz
    prediction = model.predict(data)
    index = np.argmax(prediction)
    class_name = labels.get(index, "Unbekannt")
    confidence_score = prediction[0][index]

    # Ergebnis anzeigen
    st.success(f"Gegenstand erkannt: **{class_name}**")
    st.info(f"Konfidenz: {confidence_score:.2%}")
