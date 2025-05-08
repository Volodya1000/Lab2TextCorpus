import queue
from models.database import Database
from models.nlp_processor import NLPProcessor
from models.document import Document
from utils.file_utils import extract_text
from threading import Thread
import time 

class DocumentController:
    def __init__(self, db: Database, nlp: NLPProcessor, update_callback=None):
        self.db = db
        self.nlp = nlp
        self.progress_queue = queue.Queue()
        self.update_callback = update_callback

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
        start_time = time.time() 
        try:
            extracted = extract_text(file_path)
            if not extracted or not extracted['text']:
                raise ValueError("Не удалось извлечь текст")
            doc = self.nlp.process(extracted['text'])
            processing_time = time.time() - start_time
            with self.db.lock, self.db.conn:
                doc_id = self._save_document_metadata(
                    title, author, date, genre, 
                    extracted['text'], processing_time, 
                    extracted['page_count']
                )
                self._save_sentences_and_tokens(doc, doc_id)
            self.progress_queue.put(("success", "Документ успешно добавлен"))
            if self.update_callback:
               self.update_callback()
        except Exception as e:
            self.progress_queue.put(("error", str(e)))

    def _save_document_metadata(self, title, author, date, genre, text, processing_time, page_count):
        with self.db.conn:
            cur = self.db.conn.cursor()
            cur.execute('''
                INSERT INTO documents (title, author, date, genre, text, processing_time, page_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, author, date, genre, text, processing_time, page_count))
            return cur.lastrowid
   
    def _save_sentences_and_tokens(self, doc, doc_id):
        # Сохраняем предложения
        sentences = [(doc_id, sent.text) for sent in doc.sents]
        with self.db.conn:
            cur = self.db.conn.cursor()
            
            # Вставляем предложения
            cur.executemany(
                "INSERT INTO sentences (doc_id, sentence_text) VALUES (?, ?)", 
                sentences
            )
            
            # Получаем ID вставленных предложений
            cur.execute("SELECT id FROM sentences WHERE doc_id = ? ORDER BY id", (doc_id,))
            sent_ids = [row[0] for row in cur.fetchall()]
            
            grammar_features = []
            for sent_idx, sent in enumerate(doc.sents):
                # Пропускаем если не совпадает количество предложений (защита от коррупции данных)
                if sent_idx >= len(sent_ids):
                    continue
                    
                sentence_id = sent_ids[sent_idx]
                
                for token in sent.tokens:
                    # Лемматизация
                    token.lemmatize(self.nlp.morph_vocab)
                    
                    # Обработка грамматических признаков
                    feats = token.feats or {}
                    feats_str = ""
                    if isinstance(feats, dict):
                        feats_str = "|".join([f"{k}={v}" for k, v in feats.items()])
                    else:
                        feats_str = str(feats)
                    
                    # Сохраняем токен
                    cur.execute('''
                        INSERT INTO tokens (
                            sentence_id, 
                            token, 
                            lemma, 
                            pos, 
                            start, 
                            end
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        sentence_id,
                        token.text,
                        token.lemma,
                        token.pos,
                        token.start,
                        token.stop
                    ))
                    token_id = cur.lastrowid
                    
                    # Сохраняем грамматические признаки
                    if feats_str:
                        for feat in feats_str.split('|'):
                            if '=' in feat:
                                key, val = feat.split('=', 1)
                                grammar_features.append((
                                    token_id, 
                                    key.strip(), 
                                    val.strip()
                                ))
            
            # Пакетная вставка грамматических признаков
            if grammar_features:
                cur.executemany('''
                    INSERT INTO grammar_features (
                        token_id, 
                        feature, 
                        value
                    ) VALUES (?, ?, ?)
                ''', grammar_features)

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