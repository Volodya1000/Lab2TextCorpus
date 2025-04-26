from typing import Any, Dict, List, Tuple
from models.database import Database
from utils.russian_translator import RussianTranslator

class SearchController:
    def __init__(self, db: Database):
        self.db = db
        self.translator = RussianTranslator()
   

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
    

    def search(self, search_type: str, query: str, filters: Dict[str, str]) -> List[Tuple[Any, ...]]:
        where, params = [], []

        # базовый поиск
        if search_type == 'Лемма':
            where.append('LOWER(t.lemma)=LOWER(?)'); params.append(query)
        elif search_type == 'Словоформа':
            where.append('t.token=?'); params.append(query)
        else:  # поиск по POS
            rev_pos = {v: k for k, v in self.translator.pos_translations.items()}
            pos_code = rev_pos.get(query, query)
            where.append('t.pos=?'); params.append(pos_code)

        # фильтр по POS из панели (если есть)
        if 'pos' in filters:
            rus = filters.pop('pos')
            rev_pos = {v: k for k, v in self.translator.pos_translations.items()}
            code = rev_pos.get(rus, rus)
            where.append('t.pos=?'); params.append(code)

        # остальные грамматические фильтры
        for feat, rus_val in filters.items():
            code_val = self.translator.translate_filter_display(feat, rus_val)
            where.append(
                "EXISTS(SELECT 1 FROM grammar_features gf WHERE gf.token_id=t.id AND gf.feature=? AND gf.value=?)"
            )
            params += [feat, code_val]

        sql = f"""
            SELECT t.token, t.lemma, t.pos, s.sentence_text, d.title
            FROM tokens t
            JOIN sentences s ON t.sentence_id=s.id
            JOIN documents d ON s.doc_id=d.id
            WHERE {' AND '.join(where)}
        """
        with self.db.lock, self.db.conn:
            cur = self.db.conn.cursor()
            cur.execute(sql, params)
            return cur.fetchall()