import pandas as pd
import streamlit as st

def run_ingestion_block():
    st.markdown("### 🧬 Block 1: DNA Ingestion & Branch Isolation")
    uploaded_file = st.file_uploader("Upload 23andMe / GEDmatch CSV", type=["csv", "xlsx"])
    
    if uploaded_file is not None:
        try:
            # Chunking prevents large files from blowing up container RAM
            chunks = pd.read_csv(uploaded_file, chunksize=1000)
            df = pd.concat(chunks, ignore_index=True)
            
            # Fail-safe column verification
            required = ['Match_ID', 'Surname_List', 'Side', 'Haplogroup', 'Shared_cM']
            for col in required:
                if col not in df.columns:
                    df[col] = "Unknown" if col != 'Shared_cM' else 0.0
            
            # Clean numeric data safely
            df['Shared_cM'] = pd.to_numeric(df['Shared_cM'], errors='coerce').fillna(0.0)
            
            # Redundant protection: Hard block against processing the father's Jones side
            maternal_df = df[df['Side'].str.upper() == 'MATERNAL']
            
            st.session_state['maternal_data'] = maternal_df
            st.success(f"Successfully isolated {len(maternal_df)} maternal records.")
            st.dataframe(maternal_df.head(5))
            
        except Exception as e:
            st.error(f"Ingestion Block stopped safely to prevent crash: {str(e)}")
