import streamlit as st
from src.block_ingest import run_ingestion_block

# System Page Configurations
st.set_page_config(page_title="Multi-Metric Genealogy Processor", layout="wide")
st.title("🛡️ Multi-Metric Redundant Genealogy Processor")
st.write("Processing Morning Wade tracking arrays across North Carolina & Mississippi lines.")

# Initialize global fail-safe session state variables
if 'maternal_data' not in st.session_state:
    st.session_state['maternal_data'] = None

# Sidebar Navigation (The Block Switchboard)
block_selection = st.sidebar.radio(
    "Select Processor Block to Execute",
    ["Block 1: Data Ingestion", "Block 2: Network Phasing", "Block 3: Historical Overlay"]
)

# Execution Router
if block_selection == "Block 1: Data Ingestion":
    run_ingestion_block()

elif block_selection == "Block 2: Network Phasing":
    if st.session_state['maternal_data'] is None:
        st.warning("⚠️ Block 2 is locked. Please load data via Block 1 first to maintain system continuity.")
    else:
        st.info("Ready for Block 2 deployment (Private profile structural parsing).")

elif block_selection == "Block 3: Historical Overlay":
    if st.session_state['maternal_data'] is None:
        st.warning("⚠️ Block 3 is locked. Please initialize system data in Block 1.")
    else:
        st.info("Ready for Block 3 deployment (Trafficking cluster mapping).")
