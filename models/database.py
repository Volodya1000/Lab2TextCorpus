import sqlite3
from config import Config
from threading import Lock

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_PATH, check_same_thread=False)
        self.lock = Lock()
        self.create_tables()

    def create_tables(self):
        with self.lock, self.conn:
            self.conn.executescript('''
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY,
                    title TEXT UNIQUE,
                    author TEXT,
                    date TEXT,
                    genre TEXT,
                    text TEXT,
                    processing_time REAL,
                    page_count INTEGER
                );
                CREATE TABLE IF NOT EXISTS sentences (
                    id INTEGER PRIMARY KEY,
                    doc_id INTEGER,
                    sentence_text TEXT,
                    FOREIGN KEY(doc_id) REFERENCES documents(id)
                );
                CREATE TABLE IF NOT EXISTS tokens (
                    id INTEGER PRIMARY KEY,
                    sentence_id INTEGER,
                    token TEXT,
                    lemma TEXT,
                    pos TEXT,
                    start INTEGER,
                    end INTEGER,
                    FOREIGN KEY(sentence_id) REFERENCES sentences(id)
                );
                CREATE TABLE IF NOT EXISTS grammar_features (
                    token_id INTEGER,
                    feature TEXT,
                    value TEXT,
                    FOREIGN KEY(token_id) REFERENCES tokens(id)
                );
                CREATE INDEX IF NOT EXISTS idx_lemma ON tokens(lemma);
                CREATE INDEX IF NOT EXISTS idx_pos ON tokens(pos);
                CREATE INDEX IF NOT EXISTS idx_token ON tokens(token);
                CREATE INDEX IF NOT EXISTS idx_token_id ON grammar_features(token_id);
                CREATE INDEX IF NOT EXISTS idx_grammar_feature ON grammar_features(feature, value);
            ''')

    def get_processing_stats(self):
        with self.lock, self.conn:
            cur = self.conn.cursor()
            cur.execute('''
                SELECT id, title, processing_time, page_count 
                FROM documents 
                WHERE processing_time IS NOT NULL AND page_count IS NOT NULL
                ORDER BY id
            ''')
            return cur.fetchall()