import pandas as pd
import streamlit as st
import io

def run_ingestion_block():
    st.markdown("### 🧬 Block 1: Instant GEDmatch Data Ingestion")
    st.write("Run a free relative or comparison tool on GEDmatch, select the results table, copy it, and paste it below.")
    
    # Text area for immediate paste bypassing the file download delay
    raw_pasted_data = st.text_area("Paste raw GEDmatch data rows here:", height=250)
    
    if raw_pasted_data:
        try:
            # Read the pasted text dynamically using string buffers
            # sep=r'\s+' automatically handles spaces and tabs from web tables
            df = pd.read_csv(io.StringIO(raw_pasted_data), sep=r'\s+|\t', engine='python', header=None)
            
            st.info(f"Raw data captured. Processing and formatting grid...")
            
            # Dynamically rename columns based on typical GEDmatch output shapes
            # If the column count varies, we fill it with placeholder names safely
            col_count = len(df.columns)
            default_headers = [f"Col_{i}" for i in range(col_count)]
            df.columns = default_headers
            
            # Simple column detection logic to identify the shared DNA column
            # Looks for columns containing float/integer numbers representing cM
            for col in df.columns:
                if df[col].dtype in ['int64', 'float64']:
                    df = df.rename(columns={col: 'Shared_cM'})
                    break
            
            if 'Shared_cM' not in df.columns:
                df['Shared_cM'] = 0.0
                
            # Fail-safe data storage into session memory
            st.session_state['maternal_data'] = df
            st.success(f"Successfully processed {len(df)} rows from GEDmatch into memory.")
            st.dataframe(df.head(10))
            
        except Exception as e:
            st.error(f"Ingestion Block failed safely. Ensure rows are formatted as a grid table. Error: {str(e)}")
