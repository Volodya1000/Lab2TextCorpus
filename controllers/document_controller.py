import queue
from models.database import Database
from models.nlp_processor import NLPProcessor
from models.document import Document
from utils.file_utils import extract_text
from threading import Thread

class DocumentController:
    def __init__(self, db: Database, nlp: NLPProcessor):
        self.db = db
        self.nlp = nlp
        self.progress_queue = queue.Queue()

    def add_document(self, file_path, title, author, date, genre):
        if self._check_document_exists(title):
            self.progress_queue.put(("error", "Документ с таким названием уже существует"))
            return

        Thread(target=self._process_document, args=(file_path, title, author, date, genre)).start()

    def _check_document_exists(self, title):
        with self.db.lock, self.db.conn:
            cur = self.db.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM documents WHERE title=?", (title,))
            return cur.fetchone()[0] > 0

    def _process_document(self, file_path, title, author, date, genre):
        try:
            text = extract_text(file_path)
            if not text:
                raise ValueError("Не удалось извлечь текст")

            doc = self.nlp.process(text)
            with self.db.lock, self.db.conn:
                doc_id = self._save_document_metadata(title, author, date, genre, text)
                self._save_sentences_and_tokens(doc, doc_id)

            self.progress_queue.put(("success", "Документ успешно добавлен"))
        except Exception as e:
            self.progress_queue.put(("error", str(e)))

    def _save_document_metadata(self, title, author, date, genre, text):
        with self.db.conn:
            cur = self.db.conn.cursor()
            cur.execute('''
                INSERT INTO documents (title, author, date, genre, text)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, author, date, genre, text))
            return cur.lastrowid

    def _save_sentences_and_tokens(self, doc, doc_id):
        sentences = [(doc_id, sent.text) for sent in doc.sents]
        with self.db.conn:
            cur = self.db.conn.cursor()
            # Вставляем предложения и получаем их ID
            cur.executemany("INSERT INTO sentences (doc_id, sentence_text) VALUES (?, ?)", sentences)
            
            # Получаем все ID предложений для текущего документа
            cur.execute("SELECT id FROM sentences WHERE doc_id = ? ORDER BY id", (doc_id,))
            sent_ids = [row[0] for row in cur.fetchall()]
            
            tokens = []
            for sent_idx, sent in enumerate(doc.sents):
                # Проверяем корректность индекса
                if sent_idx >= len(sent_ids):
                    break  # или raise IndexError("Несоответствие количества предложений")
                sentence_id = sent_ids[sent_idx]
                for token in sent.tokens:
                    tokens.append((
                        sentence_id,
                        token.text,
                        token.lemma,
                        token.pos,
                        str(token.feats) if token.feats else '',
                        token.start,
                        token.stop
                    ))
            # Вставляем токены
            cur.executemany('''
                INSERT INTO tokens (sentence_id, token, lemma, pos, feats, start, end)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', tokens)

    def delete_document(self, doc_id):
        with self.db.lock, self.db.conn:
            cur = self.db.conn.cursor()
            cur.execute('DELETE FROM documents WHERE id = ?', (doc_id,))
            cur.execute('DELETE FROM sentences WHERE doc_id = ?', (doc_id,))
            cur.execute('''
                DELETE FROM tokens 
                WHERE sentence_id IN (SELECT id FROM sentences WHERE doc_id = ?)
            ''', (doc_id,))

    def get_document_content(self, doc_id):
        with self.db.lock, self.db.conn:
            cur = self.db.conn.cursor()
            cur.execute('SELECT text FROM documents WHERE id = ?', (doc_id,))
            return cur.fetchone()[0]