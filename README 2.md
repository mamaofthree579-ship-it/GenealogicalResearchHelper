# Family Genealogy Database

A lightweight, multi-dataset genealogy engine you can run locally and on Streamlit.

## Structure
- `schema.sql` – SQLite schema designed for merging GEDCOM, census CSVs, DNA matches
- `load_data.py` – CLI loader for initial data
- `app.py` – Streamlit simulator to upload, browse, and visualize
- `requirements.txt`

## Why this design
1. **datasets table** tracks provenance. Every person keeps its source dataset_id and external_id, so you never lose where a fact came from.
2. **persons + families + child_links** mirrors GEDCOM but stays queryable in SQL.
3. **links table** stores record-linkage confidence when the same person appears in two datasets.

## Quick start
```bash
git init genealogy-lab
cd genealogy-lab
# copy these files in
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python load_data.py   # creates genealogy.db with sample
streamlit run app.py
```

## GitHub workflow
1. Push this folder to GitHub
2. Add data folders: `/data/raw/` for GEDCOMs, `/data/processed/` for cleaned CSVs
3. Use GitHub Actions to run tests on load_data.py

## Next steps for merging
- Add fuzzy matching on name+birth_date using rapidfuzz
- Store confidence in `links` table
- Build a 'canonical persons' view that collapses duplicates