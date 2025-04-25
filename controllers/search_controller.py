from models.database import Database
from config import Config

class SearchController:
    def __init__(self, db: Database):
        self.db = db

    def search_by_lemma(self, lemma):
        with self.db.lock, self.db.conn:
            cur = self.db.conn.cursor()
            cur.execute('''
                SELECT t.token, t.lemma, t.pos, s.sentence_text, d.title 
                FROM tokens t
                JOIN sentences s ON t.sentence_id = s.id
                JOIN documents d ON s.doc_id = d.id
                WHERE LOWER(t.lemma) = LOWER(?)
            ''', (lemma,))
            return cur.fetchall()

    def search_by_wordform(self, word):
        with self.db.lock, self.db.conn:
            cur = self.db.conn.cursor()
            cur.execute('''
                SELECT t.token, t.lemma, t.pos, s.sentence_text, d.title 
                FROM tokens t
                JOIN sentences s ON t.sentence_id = s.id
                JOIN documents d ON s.doc_id = d.id
                WHERE t.token = ?
            ''', (word,))
            return cur.fetchall()

    def search_by_pos(self, pos):
        with self.db.lock, self.db.conn:
            cur = self.db.conn.cursor()
            cur.execute('''
                SELECT t.token, t.lemma, t.pos, s.sentence_text, d.title 
                FROM tokens t
                JOIN sentences s ON t.sentence_id = s.id
                JOIN documents d ON s.doc_id = d.id
                WHERE t.pos = ?
            ''', (pos,))
            return cur.fetchall()

    def get_concordance(self, token, context_left=5, context_right=5):
        with self.db.lock, self.db.conn:
            cur = self.db.conn.cursor()
            cur.execute('''
                SELECT s.sentence_text, t.start, t.end 
                FROM tokens t
                JOIN sentences s ON t.sentence_id = s.id
                WHERE t.token = ?
            ''', (token,))
            results = []
            for row in cur.fetchall():
                sentence = row[0]
                start = row[1]
                end = row[2]
                pre = sentence[:start].rsplit(' ', context_left+1)[-context_left-1:]
                post = sentence[end:].split(' ', context_right)[:context_right]
                context = ' '.join(pre + [sentence[start:end]] + post)
                results.append(f"[...] {context} [...]")
            return results
        
    def search_by_grammar_feature(self, feature, value):
        with self.db.lock, self.db.conn:
            cur = self.db.conn.cursor()
            cur.execute('''
                SELECT t.token, t.lemma, t.pos, s.sentence_text, d.title 
                FROM tokens t
                JOIN grammar_features gf ON t.id = gf.token_id
                JOIN sentences s ON t.sentence_id = s.id
                JOIN documents d ON s.doc_id = d.id
                WHERE gf.feature = ? AND gf.value = ?
            ''', (feature, value))
            return cur.fetchall()