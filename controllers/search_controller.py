from typing import Any, Dict, List, Tuple
from models.database import Database
from utils.russian_translator import RussianTranslator
from typing import List, Tuple, Any
from models.database import Database
from utils.russian_translator import RussianTranslator
from config import Config

class SearchController:
    def __init__(self, db: Database):
        self.db = db
        self.translator = RussianTranslator()
        
    def get_grammar(
        self,
        token_text: str,
        lemma: str,
        pos: str,
        doc_title: str
    ) -> list[tuple[str, str]]:
        """
        Возвращает список грамматических признаков (feature, value)
        для данного токена в указанном документе.
        """
        feats: list[tuple[str, str]] = []
        with self.db.lock, self.db.conn:
            cur = self.db.conn.cursor()
            # Изменить SQL-запрос на:
            cur.execute("""
    SELECT gf.feature, gf.value
    FROM tokens t
    JOIN sentences s ON t.sentence_id = s.id
    JOIN documents d ON s.doc_id = d.id
    JOIN grammar_features gf ON gf.token_id = t.id
    WHERE LOWER(t.token) = LOWER(?)
    AND LOWER(t.lemma) = LOWER(?)
    AND t.pos = ?
    AND d.title = ?
""", (token_text, lemma, pos, doc_title))  # Убрано форматирование
            feats = cur.fetchall()
        return feats

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

    def search(
    self,
    search_type: str,
    query: str,
    filters: Dict[str, str],
    context_left: int = Config.CONTEXT_LEFT,
    context_right: int = Config.CONTEXT_RIGHT
    ,
    partial_match: bool = False
) -> List[Tuple[Any, ...]]:
        where = []
        params = []
        query = query.strip()

        # Базовый поиск
        if search_type == 'Лемма':
            if partial_match:  # Используем параметр partial_match
                where.append("LOWER(t.lemma) LIKE LOWER(?) || '%'")
            else:
                where.append("LOWER(t.lemma) = LOWER(?)")
            params.append(query)
        
        elif search_type == 'Словоформа':
            if partial_match:  # Используем параметр partial_match
                where.append("LOWER(t.token) LIKE LOWER(?) || '%'")
            else:
                where.append("LOWER(t.token) = LOWER(?)")
            params.append(query)

        # Фильтры из панели
        if 'pos' in filters:
            pos_code = self._translate_pos_to_code(filters.pop('pos'))
            if pos_code:
                where.append("t.pos = ?")
                params.append(pos_code)

        # Грамматические фильтры
        for feat, rus_val in filters.items():
            if rus_val:
                code_val = self.translator.translate_filter_display(feat, rus_val)
                where.append(
                    "EXISTS(SELECT 1 FROM grammar_features gf "
                    "WHERE gf.token_id = t.id AND gf.feature = ? AND gf.value = ?)"
                )
                params.extend([feat, code_val])

        # Формирование SQL-запроса
        sql = """
            SELECT 
    t.token,
    t.lemma,
    t.pos,
    d.title,
    COUNT(*) as count 
FROM tokens t
JOIN sentences s ON t.sentence_id = s.id
JOIN documents d ON s.doc_id = d.id
WHERE ...
GROUP BY t.token, t.lemma, t.pos, d.title  
ORDER BY d.title
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
            
        sql += " ORDER BY d.title, s.id, t.start LIMIT 500"

        # Отладочный вывод
        print("[DEBUG] Search SQL:", sql)
        print("[DEBUG] Params:", params)

        # Выполнение запроса
        with self.db.lock, self.db.conn:
            cur = self.db.conn.cursor()
            cur.execute(sql, params)
            return cur.fetchall()
        

    def _translate_pos_to_code(self, pos: str) -> str:
        rev_pos = {
            "Существительное": "NOUN",
            "Глагол": "VERB",
            "Прилагательное": "ADJ",
            # ... остальные части речи
        }
        return rev_pos.get(pos.strip().capitalize(), "")