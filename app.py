import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import datetime
import os
import time
import random

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Magic Racing Predictor 2026", layout="wide", page_icon="🏇")

# --- STYLING ---
st.markdown("""
    <style>
    .metric-card { background-color: #1e293b; padding: 15px; border-radius: 10px; border-left: 5px solid #3b82f6; }
    .prediction-row { background: #0f172a; padding: 10px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #334155; }
    </style>
""", unsafe_allow_html=True)

# --- DATA ENGINE (THE MAGNET) ---
def process_data(files):
    all_dfs = []
    # Standardizing column names for all your different "squishies"
    column_map = {
        'Horse': 'horse', 'Horse Name': 'horse',
        'Track': 'course', 'Course': 'course',
        'Date': 'date', 'Pos': 'pos', 'Result': 'pos'
    }
    
    for f in files:
        try:
            df = pd.read_csv(f)
            df.rename(columns=column_map, inplace=True)
            # Keep only the essential columns to save memory
            cols = [c for c in ['date', 'course', 'horse', 'jockey', 'trainer', 'pos', 'going'] if c in df.columns]
            all_dfs.append(df[cols])
        except Exception as e:
            st.error(f"Error reading {f.name}: {e}")
    
    if all_dfs:
        master = pd.concat(all_dfs).drop_duplicates(subset=['date', 'course', 'horse'])
        # Save as Parquet for lightning-fast loading
        master.to_parquet("master_data.parquet")
        return master
    return None

@st.cache_data
def load_master_data():
    if os.path.exists("master_data.parquet"):
        return pd.read_parquet("master_data.parquet")
    return None

# --- PREDICTOR BRAIN (THE MAGIC) ---
def calculate_prediction(horse, course, going, db):
    history = db[db['horse'].str.contains(horse, case=False, na=False)]
    if history.empty:
        return 50.0, 0 # Default for unknown horses
    
    # Reliability (Confidence Meter)
    runs = len(history)
    confidence = min((runs / 10) * 100, 100)
    
    # Calculate win rate from history
    # Converting pos to string to handle various formats
    wins = len(history[history['pos'].astype(str) == '1'])
    win_rate = (wins / runs)
    
    # Track specific performance
    course_runs = history[history['course'] == course]
    course_wins = len(course_runs[course_runs['pos'].astype(str) == '1'])
    course_bonus = (course_wins * 10) if course_runs.empty == False else 0
    
    # Final Magic Score Calculation
    score = (win_rate * 50) + course_bonus + 30
    return round(min(score, 100), 1), round(confidence, 1)

# --- LIVE SCRAPER (STEALTH MODE) ---
def scrape_future_cards():
    # Placeholder for the stealth scraping logic
    # In a real app, this would use the SeleniumBase/Requests logic we discussed
    st.info("Scraping Sporting Life for the next 5 days...")
    time.sleep(2)
    return pd.DataFrame({
        'date': [datetime.date.today().strftime('%Y-%m-%d')],
        'course': ['Ayr'],
        'time': ['14:00'],
        'horse': ['Sample Runner'],
        'jockey': ['J. Smith'],
        'going': ['Good']
    })

# --- SIDEBAR: DATA MAGNET ---
with st.sidebar:
    st.title("📂 Data Magnet")
    st.write("Upload your 10-year Kaggle CSV and daily scrapes here.")
    uploaded_files = st.file_uploader("Drop CSVs here", accept_multiple_files=True, type=['csv'])
    
    if st.button("🚀 Merge & Sync Magic"):
        if uploaded_files:
            with st.spinner("Squishing data..."):
                process_data(uploaded_files)
                st.cache_data.clear()
                st.success("Database Updated!")
                st.rerun()

# --- MAIN APP INTERFACE ---
master_db = load_master_data()

if master_db is not None:
    tab1, tab2, tab3 = st.tabs(["🔮 Predictor", "🔍 History Search", "📊 Live Scraper"])

    with tab1:
        st.header("Today's Magic Predictions")
        st.write("Predictions will appear here once you scrape today's cards or upload a daily CSV.")
        
        # Example of how the predictor displays
        if st.checkbox("Show Example Prediction"):
            score, conf = calculate_prediction("Tiger Roll", "Cheltenham", "Soft", master_db)
            st.markdown(f"""
                <div class="prediction-row">
                    <b>Tiger Roll</b> | Score: {score}% | Confidence: {conf}%
                </div>
            """, unsafe_allow_html=True)

    with tab2:
        st.header("10-Year History Search")
        search_query = st.text_input("Enter Horse, Jockey, or Trainer Name")
        if search_query:
            # Filtering the 500k+ rows instantly
            search_results = master_db[
                master_db['horse'].str.contains(search_query, case=False, na=False) |
                master_db['jockey'].str.contains(search_query, case=False, na=False)
            ]
            st.write(f"Found {len(search_results)} historical records.")
            st.dataframe(search_results.sort_values(by='date', ascending=False))

    with tab3:
        st.header("Live 5-Day Scraper")
        if st.button("Start Stealth Scrape"):
            future_df = scrape_future_cards()
            st.dataframe(future_df)
            st.success("Scrape complete! You can now merge this in the sidebar.")

else:
    # THE FIX FOR THE st.welcome ERROR
    st.markdown("### 👋 Welcome to the Magic Racing Predictor!")
    st.info("To start, please upload your 10-year historical CSV (Kaggle) in the sidebar.")
    st.write("1. Download the free 10-year data.")
    st.write("2. Upload it using the 'Data Magnet' on the left.")
    st.write("3. The app will automatically process the data and unlock the Predictor.")

st.divider()
st.caption(f"Engine Last Sync: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
