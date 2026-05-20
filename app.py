import streamlit as st, sqlite3, pandas as pd, networkx as nx
from pyvis.network import Network
import tempfile, os
from gedcom.parser import Parser

DB = "genealogy.db"

st.set_page_config(page_title="Family Tree Lab", layout="wide")
st.title("Family Genealogy Database")

def get_conn():
    init = not os.path.exists(DB)
    conn = sqlite3.connect(DB, check_same_thread=False)
    if init:
        with open("schema.sql") as f:
            conn.executescript(f.read())
    return conn

conn = get_conn()

tab1, tab2, tab3 = st.tabs(["Upload", "Browse", "Tree"])

with tab1:
    st.subheader("Add a dataset")
    name = st.text_input("Dataset name")
    dtype = st.selectbox("Type", ["gedcom","csv","manual"])
    uploaded = st.file_uploader("Upload GEDCOM or CSV", type=["ged","gedcom","csv"])
    if st.button("Import") and uploaded and name:
        cur = conn.cursor()
        cur.execute("INSERT INTO datasets(name,type) VALUES (?,?)", (name,dtype))
        dsid = cur.lastrowid
        if dtype=="csv":
            df = pd.read_csv(uploaded)
            df['dataset_id'] = dsid
            df.to_sql('persons', conn, if_exists='append', index=False)
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ged") as tmp:
                tmp.write(uploaded.read()); path=tmp.name
            p = Parser(); p.parse_file(path)
            for i, person in enumerate(p.get_root_child_elements()):
                # simplified extraction
                pass
            os.unlink(path)
        conn.commit()
        st.success(f"Imported {name} as dataset {dsid}")

with tab2:
    st.subheader("Persons")
    df = pd.read_sql("SELECT person_id, given_name, surname, birth_date, death_date, dataset_id FROM persons LIMIT 500", conn)
    st.dataframe(df, use_container_width=True)
    q = st.text_input("Search surname")
    if q:
        res = pd.read_sql("SELECT * FROM persons WHERE surname LIKE ? ", conn, params=(f"%{q}%",))
        st.write(res)

with tab3:
    st.subheader("Visual tree")
    persons = pd.read_sql("SELECT person_id, given_name, surname FROM persons", conn)
    fams = pd.read_sql("SELECT husband_id, wife_id FROM families WHERE husband_id IS NOT NULL AND wife_id IS NOT NULL", conn)
    children = pd.read_sql("SELECT family_id, child_id FROM child_links", conn)
    G = nx.DiGraph()
    for _,r in persons.iterrows():
        G.add_node(r.person_id, label=f"{r.given_name} {r.surname}")
    for _,r in fams.iterrows():
        G.add_edge(r.husband_id, r.wife_id, relation="spouse")
    # add parent-child edges via families
    fam_map = pd.read_sql("SELECT family_id, husband_id, wife_id FROM families", conn)
    for _,cl in children.iterrows():
        fam = fam_map[fam_map.family_id==cl.child_id] if False else fam_map[fam_map.family_id==cl.family_id]
        if not fam.empty:
            for _,f in fam.iterrows():
                if f.husband_id: G.add_edge(f.husband_id, cl.child_id, relation="parent")
                if f.wife_id: G.add_edge(f.wife_id, cl.child_id, relation="parent")
    net = Network(height="600px", width="100%", directed=True)
    net.from_nx(G)
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".html").name
    net.save_graph(path)
    with open(path) as f: html=f.read()
    st.components.v1.html(html, height=620)