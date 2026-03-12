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
HEUTE = datetime(2026, 3, 12).date()
DB_FILE = "fundstuecke_db.csv"
IMG_FOLDER = "images"
CONFIDENCE_THRESHOLD = 0.60

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
    if os.path.exists(DB_FILE): return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["ID", "Kategorie", "Funddatum", "Ablaufdatum", "Status", "Bild_Pfad"])

def delete_entry(entry_id):
    df = get_database()
    img_to_delete = df.loc[df['ID'] == entry_id, 'Bild_Pfad'].values
    if len(img_to_delete) > 0 and os.path.exists(str(img_to_delete[0])):
        try: os.remove(str(img_to_delete[0]))
        except: pass
    df = df[df['ID'] != entry_id]
    df.to_csv(DB_FILE, index=False)

# --- UI SETUP ---
st.set_page_config(page_title="Fundkiste Pro 2026", layout="wide")
model = load_my_model()
labels = load_labels("labels.txt")

st.sidebar.title("🏢 Zentrale")
auswahl = st.sidebar.selectbox("Navigation", 
    ["Erfassen", "Datenbank", "Suche", "🎮 Space Typing", "⚡ Reaktionstest", "🎯 Aim-Trainer", "🏃 Jump & Run"])

# --- MODI: ERFASSEN / DATENBANK / SUCHE ---
# (Wie im vorherigen Code...)
if auswahl == "Erfassen":
    st.header("📸 Neues Fundstück erfassen")
    uploaded_file = st.file_uploader("Bild hochladen", type=["jpg", "png", "jpeg"])
    if uploaded_file and model:
        image = Image.open(uploaded_file).convert("RGB")
        st.image(image, caption="Vorschau", width=300)
        img_resized = ImageOps.fit(image, (224, 224), Image.LANCZOS)
        img_array = (np.asarray(img_resized).astype(np.float32) / 127.5) - 1
        pred = model.predict(np.expand_dims(img_array, axis=0))
        idx = np.argmax(pred)
        confidence = pred[0][idx]
        if confidence < CONFIDENCE_THRESHOLD:
            st.warning(f"⚠️ Nicht erkannt ({confidence:.1%}).")
            klasse, can_save = "Nicht erkannt", False
        else:
            klasse, can_save = labels.get(idx, "Unbekannt"), True
            st.success(f"✅ Erkannt: **{klasse}** ({confidence:.1%})")
        with st.form("save_form"):
            k_liste = list(labels.values()) + ["Nicht erkannt"]
            final_klasse = st.selectbox("Kategorie", k_liste, index=k_liste.index(klasse))
            beschreibung = st.text_input("Zusatz-Info")
            if st.form_submit_button("Speichern", disabled=not can_save):
                img_path = os.path.join(IMG_FOLDER, f"{int(time.time())}.jpg")
                image.save(img_path)
                df = get_database(); neu = {"ID": int(time.time()), "Kategorie": final_klasse, "Funddatum": HEUTE, "Ablaufdatum": HEUTE+timedelta(days=30), "Status": beschreibung, "Bild_Pfad": img_path}
                pd.concat([df, pd.DataFrame([neu])], ignore_index=True).to_csv(DB_FILE, index=False)
                st.success("Gespeichert!")

elif auswahl == "Datenbank":
    st.header("📊 Archiv")
    df = get_database()
    if not df.empty:
        for _, row in df.iterrows():
            c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
            with c1:
                if os.path.exists(str(row['Bild_Pfad'])): st.image(row['Bild_Pfad'], width=100)
                else: st.write("🖼️")
            with c2: st.write(f"**{row['Kategorie']}**\n\n{row['Status']}")
            with c3: st.write(f"Ablauf: {row['Ablaufdatum']}")
            with c4: 
                if st.button("✅ Weg", key=f"d_{row['ID']}"):
                    delete_entry(row['ID']); st.rerun()
            st.divider()

elif auswahl == "Suche":
    st.header("🔍 Suche")
    q = st.text_input("Begriff...")
    df = get_database()
    if q and not df.empty:
        st.dataframe(df[df.apply(lambda r: q.lower() in r.astype(str).str.lower().values, axis=1)])

# --- MODI: SPIELE (TYPING, REAKTION, AIM) ---
elif auswahl == "🎮 Space Typing":
    # (Typing Code von vorher...)
    if 'input_key' not in st.session_state: st.session_state.input_key = 0
    if 'game_active' not in st.session_state: st.session_state.game_active = False
    if not st.session_state.game_active:
        if st.button("Start"):
            st.session_state.game_active, st.session_state.lives, st.session_state.score, st.session_state.current_word, st.session_state.start_time = True, 3, 0, random.choice(SPACE_WORDS), time.time()
            st.rerun()
    else:
        rest = max(0.0, 7.0 - (time.time() - st.session_state.start_time))
        st.write(f"### Wort: {st.session_state.current_word} | ❤️ {st.session_state.lives}")
        fid = f"t_{st.session_state.input_key}"
        ui = st.text_input("Tippen:", key=fid).strip()
        components.html(f"<script>window.parent.document.querySelector('input[id*=\"{fid}\"]').focus();</script>", height=0)
        if ui.lower() == st.session_state.current_word.lower():
            st.session_state.score += 10; st.session_state.current_word = random.choice(SPACE_WORDS); st.session_state.start_time = time.time(); st.session_state.input_key += 1; st.rerun()
        if rest <= 0:
            st.session_state.lives -= 1; st.session_state.start_time = time.time(); st.session_state.input_key += 1
            if st.session_state.lives <= 0: st.session_state.game_active = False
            st.rerun()
        time.sleep(0.1); st.rerun()

elif auswahl == "⚡ Reaktionstest":
    # (Reaktions-Code von vorher...)
    if 'rxn_state' not in st.session_state: st.session_state.rxn_state = "idle"
    if st.session_state.rxn_state == "idle":
        if st.button("Start"): st.session_state.rxn_state = "waiting"; st.session_state.wait_until = time.time() + random.uniform(2, 4); st.rerun()
    elif st.session_state.rxn_state == "waiting":
        st.error("WARTEN..."); (time.sleep(0.05) or st.rerun()) if time.time() < st.session_state.wait_until else (setattr(st.session_state, 'rxn_state', 'go') or setattr(st.session_state, 'go_start', time.time()) or st.rerun())
    elif st.session_state.rxn_state == "go":
        if st.button("JETZT!"): st.session_state.last_res = (time.time() - st.session_state.go_start)*1000; st.session_state.rxn_state = "result"; st.rerun()
    elif st.session_state.rxn_state == "result":
        st.write(f"## {st.session_state.last_res:.0f} ms"); (st.button("Nochmal") and setattr(st.session_state, 'rxn_state', 'idle') or st.rerun())

elif auswahl == "🎯 Aim-Trainer":
    # (Aim-Code von vorher...)
    if 'aim_hits' not in st.session_state: st.session_state.aim_hits = 0
    if st.session_state.aim_hits == 0:
        if st.button("Start"): st.session_state.aim_hits = 1; st.session_state.aim_start = time.time(); st.rerun()
    elif st.session_state.aim_hits <= 10:
        c = st.columns(10); (c[random.randint(0,9)].button("🎯", key=f"a_{st.session_state.aim_hits}") and setattr(st.session_state, 'aim_hits', st.session_state.aim_hits + 1) or st.rerun())
    else:
        st.write(f"Zeit: {time.time()-st.session_state.aim_start:.2f}s"); (st.button("Reset") and setattr(st.session_state, 'aim_hits', 0) or st.rerun())

# --- NEU: MODUS: JUMP & RUN (Dino Style) ---
elif auswahl == "🏃 Jump & Run":
    st.header("🏃 Dino-Jump: Spring über das Hindernis!")
    
    if 'jr_active' not in st.session_state:
        st.session_state.jr_active = False
        st.session_state.jr_pos = 0     # Position des Hindernisses (10 bis 0)
        st.session_state.jr_score = 0
        st.session_state.is_jumping = False

    if not st.session_state.jr_active:
        if st.button("Spiel Starten"):
            st.session_state.jr_active = True
            st.session_state.jr_pos = 10
            st.session_state.jr_score = 0
            st.session_state.is_jumping = False
            st.rerun()
    else:
        # Spiel-Logik
        st.session_state.jr_pos -= 1  # Hindernis bewegt sich nach links
        
        # Anzeige
        st.write(f"### Punkte: {st.session_state.jr_score}")
        
        # Den "Dino" und die Welt zeichnen
        # Wir nutzen eine Reihe von Spalten als Spielfeld
        field = ["_"] * 11
        dino_char = "🦖" if not st.session_state.is_jumping else "⬆️"
        
        # Hindernis setzen
        if st.session_state.jr_pos >= 0:
            field[st.session_state.jr_pos] = "🌵"
        
        # Spielfeld anzeigen
        st.subheader("".join(field[::-1]) + dino_char)
        
        # Steuerung
        if st.button("SPRINGEN!"):
            st.session_state.is_jumping = True
        
        # Kollisionsabfrage
        if st.session_state.jr_pos == 0:
            if st.session_state.is_jumping:
                st.session_state.jr_score += 1
                st.toast("Gut gesprungen!", icon="✨")
            else:
                st.error(f"💥 Autsch! Game Over. Endstand: {st.session_state.jr_score}")
                st.session_state.jr_active = False
                if st.button("Neustart"): st.rerun()
                st.stop()
        
        # Hindernis resetten
        if st.session_state.jr_pos < 0:
            st.session_state.jr_pos = 10
            st.session_state.is_jumping = False # Landen
            
        time.sleep(0.3) # Geschwindigkeit des Spiels
        st.rerun()
