from typing import Any, Dict, List, Tuple
from models.database import Database
from utils.russian_translator import RussianTranslator

class SearchController:
    def __init__(self, db: Database):
        self.db = db
        self.translator = RussianTranslator()
   

    # controllers/search_controller.py

from typing import List, Tuple, Any
from models.database import Database

class SearchController:
    def __init__(self, db: Database):
        self.db = db
        # ... остальное без изменений ...

    def get_concordance(
        self,
        token_text: str,
        context_left: int = 5,
        context_right: int = 5
    ) -> List[str]:
        """
        Для каждого вхождения token_text возвращает контекст:
        context_left токенов слева + сам токен + context_right токенов справа.
        """
        concordances: List[str] = []
        with self.db.lock, self.db.conn:
            cur = self.db.conn.cursor()
            # получаем все пары (token_id, sentence_id) для данного текста токена
            cur.execute(
                "SELECT id, sentence_id FROM tokens WHERE token = ?",
                (token_text,)
            )
            hits = cur.fetchall()  # [(token_id, sentence_id), ...]

            for token_id, sent_id in hits:
                # забираем все токены этого предложения в порядке появления
                cur.execute(
                    "SELECT id, token FROM tokens "
                    "WHERE sentence_id = ? "
                    "ORDER BY start",
                    (sent_id,)
                )
                tokens = cur.fetchall()  # [(id1, tok1), (id2, tok2), ...]

                # выделяем списки отдельно
                ids = [row[0] for row in tokens]
                texts = [row[1] for row in tokens]

                # находим позицию нашего токена
                try:
                    idx = ids.index(token_id)
                except ValueError:
                    continue

                # формируем контекст
                left = texts[max(0, idx - context_left): idx]
                center = texts[idx]
                right = texts[idx + 1: idx + 1 + context_right]

                concordances.append(" ".join(left + [center] + right))

        return concordances

    

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