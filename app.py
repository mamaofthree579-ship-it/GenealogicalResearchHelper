import streamlit as st, sqlite3, pandas as pd, networkx as nx
from pyvis.network import Network
import tempfile, os
from gedcom.parser import Parser
from gedcom.element.individual import IndividualElement
from gedcom.element.family import FamilyElement

DB = "genealogy.db"

st.set_page_config(page_title="Family Tree Lab", layout="wide")
st.title("Family Genealogy Database â€“ GEDCOM ready")

def get_conn():
    init = not os.path.exists(DB)
    conn = sqlite3.connect(DB, check_same_thread=False)
    if init:
        with open("schema.sql") as f:
            conn.executescript(f.read())
    return conn

conn = get_conn()

def import_gedcom(conn, dataset_id, ged_path):
    parser = Parser()
    parser.parse_file(ged_path, False)  # False = strict=False for GEDCOM 5.5.1

    cur = conn.cursor()
    person_map = {}  # external_id -> person_id

    # 1. Individuals
    for elem in parser.get_root_child_elements():
        if not isinstance(elem, IndividualElement):
            continue
        ext_id = elem.get_pointer().strip('@')
        try:
            first, last = elem.get_name()
        except:
            name = elem.get_name()
            first, last = (name, "") if isinstance(name, str) else ("","")
        sex = elem.get_gender()
        sex = 'M' if sex=='M' else 'F' if sex=='F' else 'U'

        birth_date, birth_place = "", ""
        try:
            b = elem.get_birth_data()
            birth_date = b[0] or ""
            birth_place = b[1] or ""
        except: pass

        death_date, death_place = "", ""
        try:
            d = elem.get_death_data()
            death_date = d[0] or ""
            death_place = d[1] or ""
        except: pass

        cur.execute(
            "INSERT INTO persons(dataset_id, external_id, given_name, surname, sex, birth_date, birth_place, death_date, death_place) VALUES (?,?,?,?,?,?,?,?,?)",
            (dataset_id, ext_id, first, last, sex, birth_date, birth_place, death_date, death_place)
        )
        person_map[ext_id] = cur.lastrowid

    # 2. Families
    for elem in parser.get_root_child_elements():
        if not isinstance(elem, FamilyElement):
            continue
        fam_ext = elem.get_pointer().strip('@')
        husband = elem.get_husband()
        wife = elem.get_wife()
        husband_id = person_map.get(husband.get_pointer().strip('@')) if husband else None
        wife_id = person_map.get(wife.get_pointer().strip('@')) if wife else None

        marr_date, marr_place = "", ""
        try:
            marr = elem.get_marriage_data()
            marr_date = marr[0] or ""
            marr_place = marr[1] or ""
        except: pass

        cur.execute(
            "INSERT INTO families(dataset_id, husband_id, wife_id, marriage_date, marriage_place) VALUES (?,?,?,?,?)",
            (dataset_id, husband_id, wife_id, marr_date, marr_place)
        )
        fam_id = cur.lastrowid

        for child in elem.get_children():
            child_ext = child.get_pointer().strip('@')
            child_id = person_map.get(child_ext)
            if child_id:
                cur.execute("INSERT OR IGNORE INTO child_links(family_id, child_id) VALUES (?,?)", (fam_id, child_id))

    conn.commit()
    return len(person_map)

tab1, tab2, tab3 = st.tabs(["Upload", "Browse", "Tree"])

with tab1:
    st.subheader("Add a dataset")
    name = st.text_input("Dataset name", placeholder="Jones family GEDCOM")
    dtype = st.selectbox("Type", ["gedcom","csv","manual"])
    uploaded = st.file_uploader("Upload GEDCOM (.ged) or CSV", type=["ged","gedcom","csv"])
    if st.button("Import") and uploaded and name:
        cur = conn.cursor()
        cur.execute("INSERT INTO datasets(name,type) VALUES (?,?)", (name,dtype))
        dsid = cur.lastrowid
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded.name)[1]) as tmp:
            tmp.write(uploaded.read()); path=tmp.name
        if dtype=="gedcom":
            count = import_gedcom(conn, dsid, path)
            st.success(f"Imported {count} persons and families from {name}")
        else:
            df = pd.read_csv(path)
            df['dataset_id'] = dsid
            # ensure columns match
            for col in ['external_id','given_name','surname','sex','birth_date','birth_place','death_date','death_place']:
                if col not in df.columns: df[col] = None
            df[['dataset_id','external_id','given_name','surname','sex','birth_date','birth_place','death_date','death_place']].to_sql('persons', conn, if_exists='append', index=False)
            st.success(f"Imported CSV with {len(df)} rows")
        os.unlink(path)
        conn.commit()

with tab2:
    st.subheader("Persons across all datasets")
    df = pd.read_sql("SELECT p.person_id, p.given_name, p.surname, p.birth_date, p.death_date, d.name as dataset FROM persons p JOIN datasets d ON p.dataset_id=d.dataset_id ORDER BY p.surname LIMIT 500", conn)
    st.dataframe(df, use_container_width=True)
    q = st.text_input("Search surname")
    if q:
        res = pd.read_sql("SELECT * FROM persons WHERE surname LIKE ? ", conn, params=(f"%{q}%",))
        st.write(res)

with tab3:
    st.subheader("Visual tree")
    persons = pd.read_sql("SELECT person_id, given_name || ' ' || surname as label, birth_date FROM persons", conn)
    fams = pd.read_sql("SELECT husband_id, wife_id FROM families WHERE husband_id IS NOT NULL AND wife_id IS NOT NULL", conn)
    children = pd.read_sql("SELECT f.husband_id, f.wife_id, c.child_id FROM child_links c JOIN families f ON c.family_id=f.family_id", conn)

    G = nx.DiGraph()
    for _,r in persons.iterrows():
        G.add_node(r.person_id, label=r.label or str(r.person_id), title=r.birth_date or "")
    for _,r in fams.iterrows():
        G.add_edge(r.husband_id, r.wife_id, color='red', title='spouse')
    for _,r in children.iterrows():
        if pd.notna(r.husband_id): G.add_edge(int(r.husband_id), int(r.child_id), title='father')
        if pd.notna(r.wife_id): G.add_edge(int(r.wife_id), int(r.child_id), title='mother')

    net = Network(height="650px", width="100%", directed=True, bgcolor="#ffffff")
    net.from_nx(G)
    net.repulsion(node_distance=150)
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".html").name
    net.save_graph(path)
    with open(path, encoding='utf-8') as f: html=f.read()
    st.components.v1.html(html, height=680)
    os.unlink(path)
