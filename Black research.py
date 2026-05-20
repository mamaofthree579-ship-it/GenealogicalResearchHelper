import streamlit as st, sqlite3, pandas as pd, tempfile, os, re
from collections import Counter

DB = "genealogy.db"

st.set_page_config(page_title="Black Family Research Lab", layout="wide")
st.title("Processor for DNA, Surnames, and Documents")

def get_conn():
    init = not os.path.exists(DB)
    conn = sqlite3.connect(DB, check_same_thread=False)
    if init:
        with open("schema.sql") as f:
            conn.executescript(f.read())
    return conn

conn = get_conn()

def soundex(name):
    name = name.upper()
    if not name: return ""
    s = name[0]
    mapping = {"BFPV":"1","CGJKQSXZ":"2","DT":"3","L":"4","MN":"5","R":"6"}
    for ch in name[1:]:
        for k in mapping:
            if ch in k:
                code = mapping[k]
                if code != s[-1]:
                    s += code
    s = re.sub('[AEIOUHWY]','',s[1:])
    return (s + "000")[:4]

tab_up, tab_dna, tab_surname, tab_direct = st.tabs(["Upload Data","DNA Matches","Surname Clusters","Direct Lines"])

with tab_up:
    st.subheader("1. Add any dataset")
    ds_name = st.text_input("Dataset name", "Jones DNA 2024")
    ds_type = st.selectbox("Type", ["dna","census","freedmen","manual","gedcom"])
    file = st.file_uploader("CSV file", type=["csv"])
    if st.button("Load") and file and ds_name:
        cur = conn.cursor()
        cur.execute("INSERT INTO datasets(name,type) VALUES (?,?)",(ds_name, ds_type))
        dsid = cur.lastrowid
        df = pd.read_csv(file)
        if ds_type=="dna":
            # Expect columns from Ancestry: Match name, Shared DNA, Relationship
            df.columns = [c.lower().strip() for c in df.columns]
            for _,r in df.iterrows():
                cur.execute("INSERT INTO dna_matches(dataset_id, match_name, tested_with, shared_cm, relationship) VALUES (?,?,?,?,?)",
                    (dsid, r.get('match name') or r.get('name'), ds_name, r.get('shared dna') or r.get('shared_cm'), r.get('relationship')))
        else:
            # generic persons
            for col in ['given_name','surname','birth_date','birth_place']:
                if col not in df.columns: df[col]=None
            df['dataset_id']=dsid
            df[['dataset_id','given_name','surname','birth_date','birth_place']].to_sql('persons', conn, if_exists='append', index=False)
        conn.commit()
        st.success(f"Loaded {ds_name}")

with tab_dna:
    st.subheader("DNA match triage")
    dna = pd.read_sql("SELECT m.match_name, m.shared_cm, m.relationship, d.name as test FROM dna_matches m JOIN datasets d ON m.dataset_id=d.dataset_id ORDER BY m.shared_cm DESC", conn)
    if dna.empty:
        st.info("Upload an AncestryDNA 'All DNA Matches' CSV first. In Ancestry: DNA > Settings > Download raw data > Matches.")
    else:
        st.dataframe(dna, use_container_width=True)
        threshold = st.slider("Show matches above cM", 20, 200, 90)
        high = dna[dna['shared_cm']>=threshold]
        st.write(f"{len(high)} high-confidence matches")
        # group by surname in match name
        surnames = [n.split()[-1] for n in high['match_name'].dropna() if len(n.split())>1]
        counts = Counter(surnames)
        st.bar_chart(pd.DataFrame.from_dict(counts, orient='index', columns=['count']))

with tab_surname:
    st.subheader("Relative surname clusters â€“ critical for pre-1870")
    persons = pd.read_sql("SELECT given_name, surname, birth_date, birth_place FROM persons WHERE surname IS NOT NULL", conn)
    if persons.empty:
        st.info("Load census or Freedmen's Bureau CSVs first")
    else:
        persons['soundex'] = persons['surname'].apply(soundex)
        cluster = persons.groupby('soundex').agg(count=('surname','size'), examples=('surname', lambda x: ', '.join(sorted(set(x))[:5])))
        cluster = cluster.sort_values('count', ascending=False)
        st.dataframe(cluster.reset_index(), use_container_width=True)
        st.caption("Soundex groups spelling variants: Johnson, Jonson, Johnston all cluster. This helps track enslaved families who changed spellings after emancipation.")

with tab_direct:
    st.subheader("Direct line finder")
    surname = st.text_input("Focus surname", "Jones")
    if surname:
        direct = pd.read_sql("SELECT p.given_name, p.surname, p.birth_date, p.death_date, d.name as source FROM persons p LEFT JOIN datasets d ON p.dataset_id=d.dataset_id WHERE p.surname LIKE ? ORDER BY p.birth_date", conn, params=(f"%{surname}%",))
        st.dataframe(direct, use_container_width=True)
        # simple parent-child guess by 15-45 year gaps
        if not direct.empty:
            direct['birth_year'] = pd.to_numeric(direct['birth_date'].str[:4], errors='coerce')
            pairs=[]
            for i,row in direct.iterrows():
                for j,older in direct.iterrows():
                    if older['birth_year']+15 <= row['birth_year'] <= older['birth_year']+45:
                        pairs.append((older['given_name']+' '+older['surname'], row['given_name']+' '+row['surname']))
            if pairs:
                st.write("Possible parent-child pairs by age gap:")
                st.write(pd.DataFrame(pairs, columns=['Parent candidate','Child'])[:20])

st.markdown("---")
st.markdown("**Workflow for Black genealogy:** 1) Load 1870 census for your county, 2) Load Freedmen's Bureau labor contracts, 3) Upload DNA matches, 4) Use surname clusters to find white enslaver families with same soundex, 5) Triangulate DNA with documented direct lines.")
