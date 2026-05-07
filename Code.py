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

# --- UI SETUP & SPACE-STYLING ---
st.set_page_config(page_title="Mission Control - Fundkiste Pro", layout="wide")

st.markdown("""
    <style>
    /* Hintergrund: Tiefer Weltraum */
    .stApp {
        background: radial-gradient(ellipse at bottom, #1B2735 0%, #090A0F 100%);
        color: #E0E0E0;
    }

    /* Animierter Sternenhimmel */
    @keyframes move-twinkle {
        from { background-position: 0 0; }
        to { background-position: -10000px 5000px; }
    }
    
    .stApp::before {
        content: "";
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        background: transparent url('https://www.transparenttextures.com/patterns/stardust.png') repeat;
        z-index: -1;
        animation: move-twinkle 200s linear infinite;
        opacity: 0.4;
    }

    /* Sidebar als Cockpit-Panel */
    [data-testid="stSidebar"] {
        background-color: rgba(10, 15, 25, 0.95);
        border-right: 1px solid #00d4ff;
    }
    
    /* Überschriften im Sci-Fi Look */
    h1, h2, h3 {
        color: #00d4ff !important;
        font-family: 'Courier New', monospace;
        text-transform: uppercase;
        letter-spacing: 3px;
        text-shadow: 0px 0px 10px rgba(0, 212, 255, 0.5);
    }

    /* Buttons */
    div.stButton > button {
        border: 1px solid #00d4ff;
        background: rgba(0, 212, 255, 0.1);
        color: #00d4ff;
        border-radius: 4px;
        transition: all 0.3s;
    }
    
    div.stButton > button:hover {
        background: #00d4ff;
        color: #000;
        box-shadow: 0px 0px 20px #00d4ff;
    }

    /* Input Felder */
    .stTextInput input {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: white !important;
        border: 1px solid #444 !important;
    }
    </style>
    
    <!-- Maus-Partikel Effekt -->
    <canvas id="starCanvas" style="position: fixed; top: 0; left: 0; pointer-events: none; z-index: 9999;"></canvas>
    <script>
        const canvas = document.getElementById('starCanvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        let stars = [];

        window.addEventListener('mousemove', (e) => {
            for(let i=0; i<2; i++) {
                stars.push({
                    x: e.clientX,
                    y: e.clientY,
                    size: Math.random() * 2 + 1,
                    vx: (Math.random() - 0.5) * 2,
                    vy: (Math.random() - 0.5) * 2,
                    alpha: 1
                });
            }
        });

        function drawStars() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            stars.forEach((s, i) => {
                s.x += s.vx; s.y += s.vy; s.alpha -= 0.015;
                if(s.alpha <= 0) stars.splice(i, 1);
                ctx.fillStyle = `rgba(0, 212, 255, ${s.alpha})`;
                ctx.beginPath(); ctx.arc(s.x, s.y, s.size, 0, Math.PI*2); ctx.fill();
            });
            requestAnimationFrame(drawStars);
        }
        drawStars();
    </script>
    """, unsafe_allow_html=True)

# --- DATENBANK FUNKTIONEN ---
def get_database():
    if os.path.exists(DB_FILE):
        try: return pd.read_csv(DB_FILE)
        except: return pd.DataFrame(columns=["ID", "Kategorie", "Funddatum", "Ablaufdatum", "Status", "Bild_Pfad"])
    return pd.DataFrame(columns=["ID", "Kategorie", "Funddatum", "Ablaufdatum", "Status", "Bild_Pfad"])

def save_database(df):
    df.to_csv(DB_FILE, index=False)

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

model = load_my_model()
labels = load_labels("labels.txt")

# --- SIDEBAR: MISSION CONTROL ---
st.sidebar.title("🚀 MISSION CONTROL")
st.sidebar.markdown(f"**Sektor:** Erdorbit-Zentrale  \n**Status:** Online  \n**Stardate:** {HEUTE}")

auswahl = st.sidebar.selectbox("Terminal-Zugriff", 
    ["🔍 Scan-Modul", "📊 Archiv-Terminal", "📋 Inventar-Matrix", "🔦 Fernsuche", "🎮 Space Typing", "⚡ Reaktionstest", "🎯 Aim-Trainer", "🧠 Allgemeinwissen", "🚀 Space Jumper"])

if st.sidebar.button("🚨 EJECT-KNOPF"):
    st.toast("System-Kern wird heruntergefahren...", icon="⚠️")
    time.sleep(1)
    st.rerun()

# --- MODUS: SCAN-MODUL (Erfassen) ---
if auswahl == "🔍 Scan-Modul":
    st.header("🔍 Objekt-Scan")
    uploaded_file = st.file_uploader("Daten-Input (Bild)", type=["jpg", "png", "jpeg"])
    
    if uploaded_file and model:
        image = Image.open(uploaded_file).convert("RGB")
        st.image(image, caption="Erfasstes Objekt", width=350)
        
        with st.spinner("Molekular-Analyse läuft..."):
            img_resized = ImageOps.fit(image, (224, 224), Image.LANCZOS)
            img_array = (np.asarray(img_resized).astype(np.float32) / 127.5) - 1
            pred = model.predict(np.expand_dims(img_array, axis=0))
            idx = np.argmax(pred)
            confidence = pred[0][idx]
            
            if confidence < CONFIDENCE_THRESHOLD:
                st.warning(f"⚠️ Signatur unklar ({confidence:.1%}).")
                klasse = "Unbekannt"
            else:
                klasse = labels.get(idx, "Unbekannt")
                st.success(f"✅ Signatur erkannt: **{klasse}** ({confidence:.1%})")

        with st.form("save_form_space"):
            k_liste = list(labels.values())
            if "Unbekannt" not in k_liste: k_liste.append("Unbekannt")
            final_klasse = st.selectbox("Kategorie-Bestätigung", k_liste, index=k_liste.index(klasse) if klasse in k_liste else 0)
            beschreibung = st.text_input("Zusatz-Spezifikationen")
            if st.form_submit_button("💾 Im Archiv speichern"):
                img_path = os.path.join(IMG_FOLDER, f"{int(time.time())}.jpg")
                image.save(img_path)
                df = get_database()
                neu = {"ID": int(time.time()), "Kategorie": final_klasse, "Funddatum": HEUTE, "Ablaufdatum": HEUTE+timedelta(days=30), "Status": beschreibung, "Bild_Pfad": img_path}
                save_database(pd.concat([df, pd.DataFrame([neu])], ignore_index=True))
                st.balloons()
                st.success("Eintrag in die Matrix übernommen!")

# --- MODUS: ARCHIV-TERMINAL (Datenbank) ---
elif auswahl == "📊 Archiv-Terminal":
    st.header("📊 Zentrales Archiv")
    df = get_database()
    if not df.empty:
        for _, row in df.iterrows():
            c1, c2, c3 = st.columns([1, 3, 1])
            with c1:
                if os.path.exists(str(row['Bild_Pfad'])): st.image(row['Bild_Pfad'], width=120)
            with c2:
                st.write(f"### {row['Kategorie']}")
                st.write(f"**Info:** {row['Status']} | **Ablauf:** {row['Ablaufdatum']}")
            with c3:
                if st.button("✅ Recovery", key=f"del_{row['ID']}"):
                    delete_entry(row['ID']); st.rerun()
            st.divider()
    else:
        st.info("Das Archiv ist derzeit leer.")

# --- MODUS: INVENTAR-MATRIX (Galerie) ---
elif auswahl == "📋 Inventar-Matrix":
    st.header("📋 Inventar-Matrix")
    df = get_database()
    if not df.empty:
        kategorien = sorted(df['Kategorie'].unique())
        for kat in kategorien:
            with st.expander(f"📁 SEKTOR: {kat.upper()}", expanded=True):
                kat_items = df[df['Kategorie'] == kat]
                cols = st.columns(4)
                for i, (_, item) in enumerate(kat_items.iterrows()):
                    with cols[i % 4]:
                        if os.path.exists(str(item['Bild_Pfad'])): st.image(item['Bild_Pfad'], use_container_width=True)
                        st.caption(f"Datum: {item['Funddatum']}")
                        if st.button("Löschen", key=f"mat_del_{item['ID']}"):
                            delete_entry(item['ID']); st.rerun()
    else:
        st.info("Keine Daten in der Matrix.")

# --- MODUS: FERN-SUCHE ---
elif auswahl == "🔦 Fernsuche":
    st.header("🔦 Deep Scan Suche")
    query = st.text_input("Suchbegriff eingeben...")
    df = get_database()
    if query and not df.empty:
        res = df[df.apply(lambda r: query.lower() in r.astype(str).str.lower().values, axis=1)]
        st.dataframe(res, use_container_width=True)

# --- SPIELE: SPACE TYPING ---
elif auswahl == "🎮 Space Typing":
    st.header("☄️ Space Typer")
    if 'input_key' not in st.session_state: st.session_state.input_key = 0
    if 'game_active' not in st.session_state: st.session_state.game_active = False
    
    if not st.session_state.game_active:
        if st.button("Triebwerke starten"):
            st.session_state.game_active, st.session_state.lives, st.session_state.score, st.session_state.current_word, st.session_state.start_time = True, 3, 0, random.choice(SPACE_WORDS), time.time()
            st.rerun()
    else:
        rest = max(0.0, 7.0 - (time.time() - st.session_state.start_time))
        st.write(f"### Ziel: :orange[{st.session_state.current_word}] | ❤️ {st.session_state.lives} | ⭐ {st.session_state.score}")
        st.progress(rest / 7.0)
        fid = f"typer_{st.session_state.input_key}"
        ui = st.text_input("Eingabe:", key=fid).strip()
        components.html(f"<script>window.parent.document.querySelector('input[id*=\"{fid}\"]').focus();</script>", height=0)
        if ui.lower() == st.session_state.current_word.lower():
            st.session_state.score += 10; st.session_state.current_word = random.choice(SPACE_WORDS); st.session_state.start_time = time.time(); st.session_state.input_key += 1; st.rerun()
        if rest <= 0:
            st.session_state.lives -= 1; st.session_state.start_time = time.time(); st.session_state.input_key += 1
            if st.session_state.lives <= 0: st.session_state.game_active = False
            st.rerun()
        time.sleep(0.1); st.rerun()

# --- SPIELE: REAKTIONSTEST ---
elif auswahl == "⚡ Reaktionstest":
    st.header("⚡ Notfall-Reaktion")
    if 'rxn_state' not in st.session_state: st.session_state.rxn_state = "idle"
    if st.session_state.rxn_state == "idle":
        if st.button("Test starten"): st.session_state.rxn_state = "waiting"; st.session_state.wait_until = time.time() + random.uniform(2, 5); st.rerun()
    elif st.session_state.rxn_state == "waiting":
        st.error("### WARTEN AUF SIGNAL..."); (time.sleep(0.05) or st.rerun()) if time.time() < st.session_state.wait_until else (setattr(st.session_state, 'rxn_state', 'go') or setattr(st.session_state, 'go_start', time.time()) or st.rerun())
    elif st.session_state.rxn_state == "go":
        if st.button("JETZT KLICKEN!"): st.session_state.last_res = (time.time() - st.session_state.go_start)*1000; st.session_state.rxn_state = "result"; st.rerun()
    elif st.session_state.rxn_state == "result":
        st.write(f"## {st.session_state.last_res:.0f} ms"); (st.button("Neustart") and setattr(st.session_state, 'rxn_state', 'idle') or st.rerun())

# --- SPIELE: DOODLE JUMP (Space Jumper) ---
elif auswahl == "🚀 Space Jumper":
    st.header("🚀 Space Jumper")
    doodle_html = """
    <canvas id="gameCanvas" width="400" height="600" style="border:3px solid #00d4ff; display:block; margin:auto; background:#050505;"></canvas>
    <script>
        const canvas = document.getElementById('gameCanvas'), ctx = canvas.getContext('2d');
        let player = { x: 180, y: 450, w: 35, h: 45, vy: 0, vx: 0 };
        let platforms = [], score = 0, keys = {};
        const gravity = 0.25, jumpPower = -9.5;

        function createPlatform(y, isBase=false) {
            let x = isBase ? 100 : Math.random() * 320; 
            return { x: x, y: y, w: isBase ? 200 : 70, h: 12, type: (Math.random() > 0.9 && !isBase) ? 'boost' : 'normal' };
        }

        function init() {
            score = 0; player.x = 180; player.y = 450; player.vy = 0;
            platforms = []; platforms.push(createPlatform(550, true));
            for(let i=0; i<7; i++) platforms.push(createPlatform(550 - (i + 1) * 85));
        }

        function update() {
            player.vy += gravity; player.y += player.vy;
            if(keys['ArrowLeft']) player.vx = -5; else if(keys['ArrowRight']) player.vx = 5; else player.vx *= 0.8;
            player.x += player.vx;
            if(player.x < -30) player.x = canvas.width; if(player.x > canvas.width) player.x = -30;
            if(player.y < 250) {
                let d = 250 - player.y; player.y = 250;
                platforms.forEach(p => { p.y += d; if(p.y > 600) { score++; Object.assign(p, createPlatform(p.y - 600)); } });
            }
            if(player.vy > 0) {
                platforms.forEach(p => {
                    if(player.x + player.w > p.x && player.x < p.x + p.w && player.y + player.h > p.y && player.y + player.h < p.y + 15) {
                        player.vy = p.type === 'boost' ? jumpPower * 2 : jumpPower;
                    }
                });
            }
            if(player.y > 600) init();
        }

        function draw() {
            ctx.clearRect(0,0,canvas.width,canvas.height);
            ctx.fillStyle = '#00d4ff'; ctx.fillRect(player.x, player.y, player.w, player.h);
            platforms.forEach(p => { ctx.fillStyle = p.type === 'boost' ? '#f1c40f' : '#2ecc71'; ctx.fillRect(p.x, p.y, p.w, p.h); });
            ctx.fillStyle = 'white'; ctx.font = '20px Arial'; ctx.fillText("Score: " + score, 20, 40);
        }

        window.onkeydown = e => { keys[e.key] = true; if(e.key.includes("Arrow")) e.preventDefault(); };
        window.onkeyup = e => keys[e.key] = false;
        init();
        function main() { update(); draw(); requestAnimationFrame(main); }
        main();
    </script>
    """
    components.html(doodle_html, height=650)
