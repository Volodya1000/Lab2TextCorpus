import xml.etree.ElementTree as ET
from models.document import Document


def _build_document_element(db, document_id: int) -> ET.Element:
    """
    Создаёт XML-элемент <document> с метаданными и аннотациями,
    основанными на данных SQLite (таблицы documents, sentences, tokens).
    """
    with db.lock, db.conn:
        cur = db.conn.cursor()
        # Метаданные документа
        cur.execute(
            "SELECT title, author, date, genre FROM documents WHERE id = ?",
            (document_id,)
        )
        meta = cur.fetchone()
        if not meta:
            raise ValueError(f"Документ с id={document_id} не найден")
        title, author, date, genre = meta

        doc_elem = ET.Element('document', id=str(document_id))
        ET.SubElement(doc_elem, 'title').text = title
        ET.SubElement(doc_elem, 'author').text = author
        ET.SubElement(doc_elem, 'date').text = date
        ET.SubElement(doc_elem, 'genre').text = genre

        # Аннотации: предложения
        cur.execute(
            "SELECT id, sentence_text FROM sentences WHERE doc_id = ? ORDER BY id",
            (document_id,)
        )
        sentences = cur.fetchall()

        annotations = ET.SubElement(doc_elem, 'annotations')
        for sent_id, sent_text in sentences:
            sent_elem = ET.SubElement(annotations, 'sentence', id=str(sent_id))
            ET.SubElement(sent_elem, 'text').text = sent_text

            # Токены соответствующего предложения
            cur.execute(
                "SELECT id, token, lemma, pos, start, end FROM tokens "
                "WHERE sentence_id = ? ORDER BY id",
                (sent_id,)
            )
            tokens = cur.fetchall()
            for tok_id, tok_text, lemma, pos_tag, start, end in tokens:
                token_elem = ET.SubElement(sent_elem, 'token', id=str(tok_id))
                ET.SubElement(token_elem, 'text').text = tok_text
                ET.SubElement(token_elem, 'lemma').text = lemma
                ET.SubElement(token_elem, 'pos').text = pos_tag
                ET.SubElement(token_elem, 'start').text = str(start)
                ET.SubElement(token_elem, 'end').text = str(end)

    return doc_elem


def export_document_to_xml(db, document_id: int, file_path: str):
    """
    Экспорт конкретного документа в XML с аннотацией из SQLite.
    """
    doc_elem = _build_document_element(db, document_id)
    tree = ET.ElementTree(doc_elem)
    tree.write(file_path, encoding='utf-8', xml_declaration=True)


def export_database_to_xml(db, file_path: str):
    """
    Экспорт всей базы документов в один XML-файл с аннотациями.
    """
    root = ET.Element('corpus')
    with db.lock, db.conn:
        cur = db.conn.cursor()
        cur.execute("SELECT id FROM documents ORDER BY id")
        doc_ids = [r[0] for r in cur.fetchall()]

    for doc_id in doc_ids:
        doc_elem = _build_document_element(db, doc_id)
        root.append(doc_elem)

    tree = ET.ElementTree(root)
    tree.write(file_path, encoding='utf-8', xml_declaration=True)


def import_database_from_xml(db, file_path: str):
    """
    Импорт документов и аннотаций из XML, добавление без удаления существующих.
    Предполагает таблицы documents, sentences и tokens.
    """
    tree = ET.parse(file_path)
    root = tree.getroot()

    with db.lock, db.conn:
        cur = db.conn.cursor()
        for doc_elem in root.findall('document'):
            title = doc_elem.findtext('title')
            author = doc_elem.findtext('author')
            date = doc_elem.findtext('date')
            genre = doc_elem.findtext('genre')

            # Вставляем новый документ, если ещё нет
            cur.execute("SELECT COUNT(*) FROM documents WHERE title = ?", (title,))
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO documents (title, author, date, genre, text, processing_time, page_count) "
                    "VALUES (?, ?, ?, ?, '', NULL, NULL)",
                    (title, author, date, genre)
                )
                new_doc_id = cur.lastrowid

                # Вставляем предложения и токены
                for sent_elem in doc_elem.find('annotations').findall('sentence'):
                    sent_text = sent_elem.findtext('text') or ''
                    cur.execute(
                        "INSERT INTO sentences (doc_id, sentence_text) VALUES (?, ?)",
                        (new_doc_id, sent_text)
                    )
                    new_sent_id = cur.lastrowid
                    for token_elem in sent_elem.findall('token'):
                        tok_text = token_elem.findtext('text')
                        lemma = token_elem.findtext('lemma')
                        pos_tag = token_elem.findtext('pos')
                        start = int(token_elem.findtext('start') or 0)
                        end = int(token_elem.findtext('end') or 0)
                        cur.execute(
                            "INSERT INTO tokens (sentence_id, token, lemma, pos, start, end) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (new_sent_id, tok_text, lemma, pos_tag, start, end)
                        )
        db.conn.commit()
