import sqlite3, pandas as pd, datetime

DB = "genealogy.db"

def init_db():
    conn = sqlite3.connect(DB)
    with open("schema.sql") as f:
        conn.executescript(f.read())
    conn.commit()
    return conn

def add_dataset(conn, name, type_, desc=""):
    cur = conn.cursor()
    cur.execute("INSERT INTO datasets(name,type,description) VALUES (?,?,?)", (name,type_,desc))
    conn.commit()
    return cur.lastrowid

def load_csv_persons(conn, dataset_id, csv_path):
    df = pd.read_csv(csv_path)
    df['dataset_id'] = dataset_id
    df.to_sql('persons', conn, if_exists='append', index=False)

if __name__ == "__main__":
    conn = init_db()
    ds = add_dataset(conn, "Jones sample CSV", "census", "Initial test data")
    load_csv_persons(conn, ds, "sample_persons.csv")
    print("Database created with sample data.")