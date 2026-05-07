import streamlit as st
import pandas as pd
import os
import datetime
import time

# --- 1. CONFIGURATION & LIMITS ---
st.set_page_config(page_title="Magic Racing Predictor", layout="wide", page_icon="🏇")

# --- 2. THE DATA MAGNET (CHUNKED VERSION) ---
def process_data_in_chunks(uploaded_files):
    """Processes large CSVs in bites to avoid crashing the app."""
    column_map = {
        'Horse': 'horse', 'Horse Name': 'horse',
        'Track': 'course', 'Course': 'course',
        'Date': 'date', 'Pos': 'pos', 'Result': 'pos'
    }
    
    master_path = "master_data.parquet"
    
    for f in uploaded_files:
        status = st.empty()
        status.info(f"⚙️ Squishing {f.name}...")
        
        # Read the CSV in chunks of 50k rows
        chunks = pd.read_csv(f, chunksize=50000, low_memory=False)
        
        first_chunk = True
        for chunk in chunks:
            # Clean and Map columns
            chunk.rename(columns=column_map, inplace=True)
            cols = [c for c in ['date', 'course', 'horse', 'jockey', 'trainer', 'pos', 'going'] if c in chunk.columns]
            chunk = chunk[cols]
            
            # Save/Append to Parquet
            if first_chunk and not os.path.exists(master_path):
                chunk.to_parquet(master_path, engine='pyarrow', index=False)
                first_chunk = False
            else:
                # Use fastparquet or pyarrow to append data
                chunk.to_parquet(master_path, engine='pyarrow', index=False)
        
        status.success(f"✅ {f.name} processed and merged!")
    
    return True

@st.cache_data
def load_master():
    if os.path.exists("master_data.parquet"):
        return pd.read_parquet("master_data.parquet")
    return None

# --- 3. THE PREDICTOR ENGINE ---
def get_prediction(horse, course, db):
    # Search for horse in history
    h_data = db[db['horse'].str.contains(horse, case=False, na=False)]
    if h_data.empty:
        return 50, 0
    
    # Confidence = How many times we've seen this horse
    confidence = min((len(h_data) / 10) * 100, 100)
    
    # Simple win calculation
    wins = len(h_data[h_data['pos'].astype(str) == '1'])
    score = (wins / len(h_data) * 70) + 30 # Base score of 30
    
    return round(score, 1), round(confidence, 1)

# --- 4. MAIN USER INTERFACE ---
st.title("🏇 Magic Racing Predictor")

# Sidebar for Uploads
with st.sidebar:
    st.header("📂 Data Magnet")
    st.write("Upload your 10yr History & Daily Cards.")
    files = st.file_uploader("Drop CSVs", accept_multiple_files=True, type=['csv'])
    
    if st.button("🚀 Process Data"):
        if files:
            process_data_in_chunks(files)
            st.cache_data.clear()
            st.rerun()

# Main App Tabs
master_db = load_master()

if master_db is not None:
    t1, t2 = st.tabs(["🔮 Predictor", "🔍 History Lookup"])
    
    with t1:
        st.header("Daily Predictions")
        target_horse = st.text_input("Enter a horse from today's card to predict:")
        target_course = st.text_input("Enter Course Name:")
        
        if target_horse and target_course:
            score, conf = get_prediction(target_horse, target_course, master_db)
            
            # Confidence Color
            color = "🔴" if conf < 40 else "🟡" if conf < 75 else "🟢"
            
            st.metric("Magic Score", f"{score}%")
            st.write(f"**Reliability:** {color} {conf}% confidence (based on {len(master_db[master_db['horse'].str.contains(target_horse, case=False, na=False)])} runs)")
            
    with t2:
        st.header("Search the 10-Year Squishy")
        search = st.text_input("Search Horse/Jockey")
        if search:
            results = master_db[master_db['horse'].str.contains(search, case=False, na=False)]
            st.dataframe(results)
else:
    st.info("👋 Welcome! Use the sidebar to upload your 10-year CSV and daily racecards to unlock the magic.")

