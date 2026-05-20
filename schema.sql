-- Core genealogy schema for multi-dataset research
PRAGMA foreign_keys = ON;

CREATE TABLE datasets (
    dataset_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT, -- 'gedcom','census','dna','manual'
    description TEXT,
    imported_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE persons (
    person_id INTEGER PRIMARY KEY,
    dataset_id INTEGER NOT NULL,
    external_id TEXT, -- ID from source file
    given_name TEXT,
    surname TEXT,
    sex TEXT CHECK(sex IN ('M','F','U')),
    birth_date TEXT,
    birth_place TEXT,
    death_date TEXT,
    death_place TEXT,
    notes TEXT,
    FOREIGN KEY(dataset_id) REFERENCES datasets(dataset_id)
);

CREATE TABLE names (
    name_id INTEGER PRIMARY KEY,
    person_id INTEGER NOT NULL,
    given_name TEXT,
    surname TEXT,
    type TEXT, -- 'birth','married','aka'
    FOREIGN KEY(person_id) REFERENCES persons(person_id)
);

CREATE TABLE families (
    family_id INTEGER PRIMARY KEY,
    dataset_id INTEGER NOT NULL,
    husband_id INTEGER,
    wife_id INTEGER,
    marriage_date TEXT,
    marriage_place TEXT,
    FOREIGN KEY(dataset_id) REFERENCES datasets(dataset_id),
    FOREIGN KEY(husband_id) REFERENCES persons(person_id),
    FOREIGN KEY(wife_id) REFERENCES persons(person_id)
);

CREATE TABLE child_links (
    family_id INTEGER NOT NULL,
    child_id INTEGER NOT NULL,
    PRIMARY KEY(family_id, child_id),
    FOREIGN KEY(family_id) REFERENCES families(family_id),
    FOREIGN KEY(child_id) REFERENCES persons(person_id)
);

CREATE TABLE events (
    event_id INTEGER PRIMARY KEY,
    person_id INTEGER NOT NULL,
    type TEXT, -- 'birth','death','census','military','immigration'
    event_date TEXT,
    place TEXT,
    source TEXT,
    FOREIGN KEY(person_id) REFERENCES persons(person_id)
);

CREATE TABLE links (
    link_id INTEGER PRIMARY KEY,
    person_a INTEGER NOT NULL,
    person_b INTEGER NOT NULL,
    confidence REAL, -- 0-1 from record linkage
    reason TEXT,
    FOREIGN KEY(person_a) REFERENCES persons(person_id),
    FOREIGN KEY(person_b) REFERENCES persons(person_id)
);