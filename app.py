import streamlit as st
import pandas as pd
import os
import datetime
import time

# --- 1. CONFIGURATION ---
# Note: Streamlit usually reads maxUploadSize from config.toml.
# We set the page config first.
st.set_page_config(page_title="Magic Racing Predictor", layout="wide", page_icon="🏇")

# --- 2. DATA ENGINE (The Magnet) ---
def process_large_csv(uploaded_files):
    """Processes large CSVs in small bites to stay under the 1GB RAM limit."""
    column_map = {
        'Horse': 'horse', 'Horse Name': 'horse',
        'Track': 'course', 'Course': 'course',
        'Date': 'date', 'Pos': 'pos', 'Result': 'pos'
    }
    
    master_path = "master_data.parquet"
    
    for f in uploaded_files:
        status = st.empty()
        status.info(f"⚙️ Squishing {f.name} into the database...")
        
        try:
            # Chunksize is the key! It reads 50,000 rows at a time
            chunks = pd.read_csv(f, chunksize=50000, low_memory=False)
            
            first_chunk = True
            for chunk in chunks:
                chunk.rename(columns=column_map, inplace=True)
                # Keep only necessary columns to keep the file small and fast
                available_cols = [c for c in ['date', 'course', 'horse', 'jockey', 'trainer', 'pos'] if c in chunk.columns]
                chunk = chunk[available_cols]
                
                # If first time, create the file. If not, append to it.
                if first_chunk and not os.path.exists(master_path):
                    chunk.to_parquet(master_path, engine='pyarrow', index=False)
                    first_chunk = False
                else:
                    # Append mode is handled by the parquet engine
                    chunk.to_parquet(master_path, engine='pyarrow', index=False)
            
            status.success(f"✅ {f.name} successfully merged!")
        except Exception as e:
            st.error(f"Error processing {f.name}: {e}")
    
    return True

@st.cache_data
def load_master():
    """Loads the squished data instantly."""
    if os.path.exists("master_data.parquet"):
        return pd.read_parquet("master_data.parquet")
    return None

# --- 3. PREDICTOR ENGINE ---
def get_prediction(horse, course, db):
    # Find horse history
    h_data = db[db['horse'].str.contains(horse, case=False, na=False)]
    
    if h_data.empty:
        return 50.0, 0.0, 0
    
    # Confidence Score (How much data do we have?)
    run_count = len(h_data)
    confidence = min((run_count / 10) * 100, 100)
    
    # Win Rate calculation
    wins = len(h_data[h_data['pos'].astype(str) == '1'])
    score = (wins / run_count * 70) + 30 
    
    return round(score, 1), round(confidence, 1), run_count

# --- 4. MAIN USER INTERFACE ---
st.title("🏇 Magic Racing Predictor")
st.markdown("---")

# Sidebar for Uploads
with st.sidebar:
    st.header("📂 Data Magnet")
    st.write("Merge your 10-year CSVs and daily racecards here.")
    
    # UI FOR UPLOADER
    files = st.file_uploader(
        "Upload CSV Files", 
        accept_multiple_files=True, 
        type=['csv'],
        help="Make sure .streamlit/config.toml is set to 1000MB!"
    )
    
    if st.button("🚀 Process & Merge Data"):
        if files:
            process_large_csv(files)
            st.cache_data.clear() # Clear memory so the new data shows up
            st.rerun()
        else:
            st.warning("Please upload at least one CSV file.")

# Main App Logic
master_db = load_master()

if master_db is not None:
    t1, t2 = st.tabs(["🔮 Predictor", "🔍 History Lookup"])
    
    with t1:
        st.header("Daily Predictions")
        col1, col2 = st.columns(2)
        with col1:
            target_horse = st.text_input("Horse Name:", placeholder="e.g. Tiger Roll")
        with col2:
            target_course = st.text_input("Course/Track:", placeholder="e.g. Cheltenham")
        
        if target_horse:
            score, conf, runs = get_prediction(target_horse, target_course, master_db)
            
            # Show the Results
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Magic Score", f"{score}%")
            
            # Confidence Meter Visual
            color = "🔴 Low" if conf < 40 else "🟡 Medium" if conf < 75 else "🟢 High"
            c2.metric("Reliability", color)
            c3.metric("Historical Runs", runs)
            
            # Visual Progress Bar for Confidence
            st.write(f"**Data Confidence:** {conf}%")
            st.progress(conf / 100)
            
    with t2:
        st.header("Search the 10-Year History")
        search = st.text_input("Type Horse, Jockey, or Trainer:")
        if search:
            # Fast filter
            results = master_db[
                master_db['horse'].str.contains(search, case=False, na=False) |
                master_db.get('jockey', pd.Series()).str.contains(search, case=False, na=False)
            ]
            st.write(f"Showing {len(results)} historical records.")
            st.dataframe(results.sort_values(by='date', ascending=False), use_container_width=True)

else:
    st.info("👋 **Welcome!** The Magic Engine is empty.")
    st.write("To get started:")
    st.write("1. Upload your 10-year Kaggle CSV in the sidebar.")
    st.write("2. Click **Process & Merge Data**.")
    st.write("3. The Predictor will unlock automatically once the data is 'squished'.")

st.markdown("---")
st.caption(f"Engine Status: {'Ready' if master_db is not None else 'Waiting for Data'}")
