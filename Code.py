
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

QUIZ_QUESTIONS = [
    {"q": "Was ist die Hauptstadt von Frankreich?", "a": ["Berlin", "Madrid", "Paris", "Rom"], "correct": "Paris"},
    {"q": "Wie viele Planeten hat unser Sonnensystem?", "a": ["7", "8", "9", "10"], "correct": "8"},
    {"q": "Wer malte die Mona Lisa?", "a": ["Picasso", "Van Gogh", "Da Vinci", "Monet"], "correct": "Da Vinci"},
    {"q": "Welches Element hat das Symbol 'O'?", "a": ["Gold", "Sauerstoff", "Eisen", "Kohlenstoff"], "correct": "Sauerstoff"},
    {"q": "Was ist das größte Säugetier der Welt?", "a": ["Elefant", "Blauwal", "Giraffe", "Nashorn"], "correct": "Blauwal"}
]

# --- VERBESSERTE DATENBANK-FUNKTIONEN ---
def get_database():
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE)
        except Exception as e:
            st.error(f"Fehler beim Laden der DB: {e}")
            # Backup bei Korruption
            return pd.DataFrame(columns=["ID", "Kategorie", "Funddatum", "Ablaufdatum", "Status", "Bild_Pfad"])
    return pd.DataFrame(columns=["ID", "Kategorie", "Funddatum", "Ablaufdatum", "Status", "Bild_Pfad"])

def save_database(df):
    try:
        df.to_csv(DB_FILE, index=False)
    except Exception as e:
        st.error(f"Speichern fehlgeschlagen: {e}")

def delete_entry(entry_id):
    df = get_database()
    img_to_delete = df.loc[df['ID'] == entry_id, 'Bild_Pfad'].values
    if len(img_to_delete) > 0 and os.path.exists(str(img_to_delete[0])):
        try: os.remove(str(img_to_delete[0]))
        except: pass
    df = df[df['ID'] != entry_id]
    save_database(df)

# --- KI MODELL LADEN ---
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

# --- UI SETUP ---
st.set_page_config(page_title="Fundkiste Pro 2026", layout="wide")
model = load_my_model()
labels = load_labels("labels.txt")

st.sidebar.title("🏢 Zentrale")
auswahl = st.sidebar.selectbox("Navigation", 
    ["📸 Erfassen", "📊 Datenbank", "📋 Kategorien-Galerie", "🔍 Suche", "🎮 Space Typing", "⚡ Reaktionstest", "🎯 Aim-Trainer", "🧠 Allgemeinwissen", "🚀 Doodle Jump"])

# --- MODUS: ERFASSEN ---
if auswahl == "📸 Erfassen":
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
            st.warning(f"⚠️ Nicht eindeutig erkannt ({confidence:.1%}).")
            klasse, can_save = "Nicht erkannt", False
        else:
            klasse, can_save = labels.get(idx, "Unbekannt"), True
            st.success(f"✅ Erkannt: **{klasse}** ({confidence:.1%})")
        
        with st.form("save_form"):
            k_liste = list(labels.values())
            if "Nicht erkannt" not in k_liste: k_liste.append("Nicht erkannt")
            final_klasse = st.selectbox("Kategorie", k_liste, index=k_liste.index(klasse))
            beschreibung = st.text_input("Zusatz-Info (Farbe, Marke...)")
            submit = st.form_submit_button("Speichern")
            if submit:
                img_path = os.path.join(IMG_FOLDER, f"{int(time.time())}.jpg")
                image.save(img_path)
                df = get_database()
                neu = {"ID": int(time.time()), "Kategorie": final_klasse, "Funddatum": HEUTE, "Ablaufdatum": HEUTE+timedelta(days=30), "Status": beschreibung, "Bild_Pfad": img_path}
                save_database(pd.concat([df, pd.DataFrame([neu])], ignore_index=True))
                st.success("In Datenbank archiviert!")

# --- MODUS: DATENBANK ---
elif auswahl == "📊 Datenbank":
    st.header("📊 Alle Fundstücke")
    df = get_database()
    if not df.empty:
        for _, row in df.iterrows():
            c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
            with c1:
                path = str(row['Bild_Pfad'])
                if os.path.exists(path): st.image(path, width=120)
                else: st.write("🖼️")
            with c2: st.write(f"**{row['Kategorie']}**\n\n_{row['Status']}_")
            with c3: st.write(f"📅 Fund: {row['Funddatum']}\n\n⏰ Ablauf: {row['Ablaufdatum']}")
            with c4: 
                if st.button("✅ Abgeholt", key=f"del_{row['ID']}"):
                    delete_entry(row['ID']); st.rerun()
            st.divider()

# --- NEU: MODUS: KATEGORIEN-GALERIE (MIT BILDERN) ---
elif auswahl == "📋 Kategorien-Galerie":
    st.header("📋 Inventar nach Kategorien")
    df = get_database()
    
    if not df.empty:
        kategorien = sorted(df['Kategorie'].unique())
        for kat in kategorien:
            with st.expander(f"📁 {kat.upper()} ({len(df[df['Kategorie']==kat])} Items)", expanded=True):
                kat_items = df[df['Kategorie'] == kat]
                
                # Wir erstellen ein Grid mit 4 Spalten für die Bilder
                cols = st.columns(4)
                for i, (_, item) in enumerate(kat_items.iterrows()):
                    with cols[i % 4]:
                        path = str(item['Bild_Pfad'])
                        if os.path.exists(path):
                            st.image(path, use_container_width=True)
                        else:
                            st.write("🖼️ Bild fehlt")
                        st.caption(f"📅 {item['Funddatum']}")
                        st.write(f"**{item['Status']}**")
                        if st.button("✅ Weg", key=f"kat_del_{item['ID']}"):
                            delete_entry(item['ID'])
                            st.rerun()
    else:
        st.info("Keine Daten vorhanden.")

# --- MODUS: SUCHE ---
elif auswahl == "🔍 Suche":
    st.header("🔍 Schnellsuche")
    query = st.text_input("Suchbegriff...")
    df = get_database()
    if query and not df.empty:
        res = df[df.apply(lambda r: query.lower() in r.astype(str).str.lower().values, axis=1)]
        st.dataframe(res, use_container_width=True)

# --- SPIELE SEKTION ---
elif auswahl == "🎮 Space Typing":
    st.header("☄️ Space Typer")
    if 'input_key' not in st.session_state: st.session_state.input_key = 0
    if 'game_active' not in st.session_state: st.session_state.game_active = False
    if not st.session_state.game_active:
        if st.button("Start"):
            st.session_state.game_active, st.session_state.lives, st.session_state.score, st.session_state.current_word, st.session_state.start_time = True, 3, 0, random.choice(SPACE_WORDS), time.time()
            st.rerun()
    else:
        rest = max(0.0, 7.0 - (time.time() - st.session_state.start_time))
        st.write(f"### Wort: :orange[{st.session_state.current_word}] | ❤️ {st.session_state.lives} | ⭐ {st.session_state.score}")
        st.progress(rest / 7.0)
        fid = f"typer_{st.session_state.input_key}"
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
    st.header("⚡ Reaktionstest")
    if 'rxn_state' not in st.session_state: st.session_state.rxn_state = "idle"
    if st.session_state.rxn_state == "idle":
        if st.button("Start"): st.session_state.rxn_state = "waiting"; st.session_state.wait_until = time.time() + random.uniform(2, 5); st.rerun()
    elif st.session_state.rxn_state == "waiting":
        st.error("### WARTEN..."); (time.sleep(0.05) or st.rerun()) if time.time() < st.session_state.wait_until else (setattr(st.session_state, 'rxn_state', 'go') or setattr(st.session_state, 'go_start', time.time()) or st.rerun())
    elif st.session_state.rxn_state == "go":
        if st.button("KLICK!"): st.session_state.last_res = (time.time() - st.session_state.go_start)*1000; st.session_state.rxn_state = "result"; st.rerun()
    elif st.session_state.rxn_state == "result":
        st.write(f"## {st.session_state.last_res:.0f} ms"); (st.button("Nochmal") and setattr(st.session_state, 'rxn_state', 'idle') or st.rerun())

elif auswahl == "🎯 Aim-Trainer":
    st.header("🎯 Aim-Trainer")
    if 'aim_hits' not in st.session_state: st.session_state.aim_hits = 0
    if st.session_state.aim_hits == 0:
        if st.button("Start"): st.session_state.aim_hits = 1; st.session_state.aim_start = time.time(); st.rerun()
    elif st.session_state.aim_hits <= 10:
        c = st.columns(10); (c[random.randint(0, 9)].button("🎯", key=f"aim_{st.session_state.aim_hits}") and setattr(st.session_state, 'aim_hits', st.session_state.aim_hits + 1) or st.rerun())
    else:
        st.write(f"## Zeit: {time.time()-st.session_state.aim_start:.2f}s"); (st.button("Reset") and setattr(st.session_state, 'aim_hits', 0) or st.rerun())
        
# --- MODUS: DOODLE JUMP (SAFE START & NEW BLOCKS) ---
elif auswahl == "🚀 Doodle Jump":
    st.header("🚀 Space Jumper")
    st.info("Steuerung: Pfeiltasten LINKS/RECHTS. Starte auf dem sicheren Boden!")
    
    doodle_html = """
    <canvas id="j" width="400" height="600" style="border:3px solid #444; display:block; margin:auto; background:#f5fcf9;"></canvas>
    <script>
        const c = document.getElementById('j'), ctx = c.getContext('2d');
        let p = { x: 180, y: 450, w: 35, h: 45, vy: 0, vx: 0 }, platforms = [], score = 0, keys = {};

        function createP(y, isBase=false) {
            let t = 'n'; 
            if(!isBase) {
                let r = Math.random();
                if(r > 0.88) t = 'boost'; else if(r > 0.75) t = 'break';
            } else t = 'base';
            return { x: isBase ? 100 : Math.random()*340, y: y, w: isBase ? 200 : 60, h: 12, type: t };
        }

        function init() {
            score = 0; p.x = 180; p.y = 450; p.vy = 0; platforms = [];
            platforms.push(createP(550, true)); // Sicherer Boden
            for(let i=0; i<7; i++) platforms.push(createP(i * 80));
        }

        function update() {
            p.vy += 0.25; p.y += p.vy;
            if(keys['ArrowLeft']) p.x -= 5; if(keys['ArrowRight']) p.x += 5;
            if(p.x < -30) p.x = 400; if(p.x > 400) p.x = -30;

            if(p.y < 300) {
                let d = 300 - p.y; p.y = 300;
                platforms.forEach(pl => { pl.y += d; if(pl.y > 600) { Object.assign(pl, createP(0)); score++; }});
            }

            if(p.vy > 0) {
                platforms.forEach(pl => {
                    if(p.x+p.w > pl.x && p.x < pl.x+pl.w && p.y+p.h > pl.y && p.y+p.h < pl.y+15) {
                        if(pl.type === 'boost') p.vy = -16;
                        else if(pl.type === 'break') { p.vy = -9; pl.y = 999; }
                        else p.vy = -9;
                    }
                });
            }
            if(p.y > 600) init();
        }

        function draw() {
            ctx.clearRect(0,0,400,600);
            ctx.fillStyle = '#ff4b4b'; ctx.fillRect(p.x, p.y, p.w, p.h); // Astronaut
            ctx.fillStyle = '#88ccff'; ctx.fillRect(p.x+5, p.y+8, p.w-10, 15); // Visier
            platforms.forEach(pl => {
                ctx.fillStyle = pl.type==='boost'?'#f1c40f':pl.type==='break'?'#eee':'#2ecc71';
                ctx.fillRect(pl.x, pl.y, pl.w, pl.h);
            });
            ctx.fillStyle = 'white'; ctx.font = '20px Arial'; ctx.fillText("Score: " + score, 20, 40);
        }

        window.onkeydown = e => { keys[e.key] = true; if(e.key.includes('Arrow')) e.preventDefault(); };
        window.onkeyup = e => keys[e.key] = false;
        init(); setInterval(() => { update(); draw(); }, 1000/60);
    </script>
    """
    components.html(doodle_html, height=650)

# (Andere Modi wie Space Typing etc. hier einfügen...)
