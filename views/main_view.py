# views/main_view.py

import tkinter as tk
from views.menu_view import MenuView
from views.filter_panel import FilterPanel
from views.document_list_view import DocumentListView
from views.document_content_view import DocumentContentView
from views.search_view import SearchView

class MainView:
    def __init__(self, root, doc_ctrl, search_ctrl):
        self.root = root
        self.root.title("Корпусный менеджер")
        self.root.geometry("1200x800")

        self.last_search_query = ""
        self.last_search_type = "Лемма"
        self.search_debounce_id = None

        # контроллеры и словарь активных фильтров
        self.doc_ctrl = doc_ctrl
        self.search_ctrl = search_ctrl
        self.active_filters: dict[str, str] = {}

        # Меню
        MenuView(root, self.doc_ctrl, self.update_document_list)

        # Основной лэйаут
        main_pane = tk.PanedWindow(root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)
        
        # Левый фрейм: фильтры + список документов
        left_frame = tk.Frame(main_pane)
        main_pane.add(left_frame)
        self.filter_panel = FilterPanel(
            left_frame,
            on_filter_change=self.on_filter_change,
            on_reset_all=self.on_reset_all_filters,
            main_view=self  # Pass reference here
        )
        self.filter_panel.pack(fill=tk.X)
        self.doc_list = DocumentListView(left_frame, on_select=self.show_document)
        self.doc_list.pack(fill=tk.BOTH, expand=True)
        
        # Правый фрейм: просмотр документа + поиск
        right_frame = tk.Frame(main_pane)
        main_pane.add(right_frame)
        self.doc_view = DocumentContentView(
            right_frame, 
            page_size=1000,
            main_view=self  # Передаем контроллер поиска
        )
        self.doc_view.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)
        self.search_view = SearchView(
            right_frame,
            main_view=self,  # Добавить эту строку
            search_ctrl=self.search_ctrl,
            on_search=self.perform_search,
            on_result_select=self.on_search_result_selected,
            get_concordance=self.search_ctrl.get_concordance
        )
        self.search_view.pack(fill=tk.BOTH, expand=True)

        # Инициализируем список документов
        self.update_document_list()

       
        
       

    def update_document_list(self):
        """Обновить дерево документов из БД"""
        with self.doc_ctrl.db.lock, self.doc_ctrl.db.conn:
            cur = self.doc_ctrl.db.conn.cursor()
            cur.execute('SELECT id, title, author, date, genre FROM documents')
            docs = cur.fetchall()
        self.doc_list.update(docs)

    def show_document(self, doc_id):
        """Показать текст выбранного документа"""
        if not doc_id:
            return
        text = self.doc_ctrl.get_document_content(doc_id)
        self.doc_view.show_text(text)

    def on_filter_change(self, feat: str, val: str):
        """Обновление фильтра и автоматический поиск"""
        if val:
            self.active_filters[feat] = val
        else:
            self.active_filters.pop(feat, None)
    
        # Запускаем поиск с задержкой 500 мс
        if self.search_debounce_id:
            self.root.after_cancel(self.search_debounce_id)
        self.search_debounce_id = self.root.after(500, self.trigger_search_update)

    def trigger_search_update(self):
        """Обновление результатов с текущими параметрами"""
        current_query = self.search_view.entry.get().strip()
        current_type = self.search_view.type_cmb.get()
        
        if current_query or self.active_filters:
            results = self.perform_search(
                stype=current_type,
                query=current_query,
                _filters=self.active_filters.copy(),
                left=self.search_view.ctx_left.get(),
                right=self.search_view.ctx_right.get()
            )
            self.search_view._update_results(results)

    def on_reset_all_filters(self):
        self.active_filters.clear()
        for widget in self.filter_panel.filter_widgets.values():
            widget.set("")
        if self.search_debounce_id:
            self.root.after_cancel(self.search_debounce_id)
        self.search_debounce_id = self.root.after(500, self.trigger_search_update)

    def perform_search(self, stype: str, query: str, _filters: dict, left: int, right: int):
        return self.search_ctrl.search(stype, query, self.active_filters.copy(), left, right)

    def on_search_result_selected(self, token: str, lemma: str, pos: str, doc_title: str, left: int, right: int):
        lines = self.search_ctrl.get_concordance(token, left, right)
        self.search_view.show_concordance(lines)
        # 1) грамматика
        translated_pos = self.search_ctrl.translator.translate_filter_display("pos", pos) 
        feats = self.search_ctrl.get_grammar(token, lemma, translated_pos, doc_title)
        self.search_view.show_grammar(feats)

        # 2) конкорданс
        left = self.search_view.ctx_left.get()
        right = self.search_view.ctx_right.get()
        lines = self.search_ctrl.get_concordance(token, left, right)
        self.search_view.show_concordance(lines)

    def on_word_selected(self, word: str):
        try:
            if not self.doc_list.tree.selection():
                print("Документ не выбран.")
                return
            
            doc_id = self.doc_list.tree.selection()[0]
            doc_title = self.doc_list.tree.item(doc_id, "values")[0]
            
            # Получаем pos и lemma токена из БД
            with self.search_ctrl.db.lock, self.search_ctrl.db.conn:
                cur = self.search_ctrl.db.conn.cursor()
                cur.execute("""
                    SELECT t.lemma, t.pos 
                    FROM tokens t
                    JOIN sentences s ON t.sentence_id = s.id
                    JOIN documents d ON s.doc_id = d.id
                    WHERE t.token = ? AND d.title = ?
                    LIMIT 1
                """, (word, doc_title))
                result = cur.fetchone()
            
            if not result:
                print(f"Токен '{word}' не найден в документе '{doc_title}'.")
                return
            
            lemma, pos = result
            # Переводим часть речи
            translated_pos = self.search_ctrl.translator.translate_pos(pos)
            # Получаем грамматику
            feats = self.search_ctrl.get_grammar(word, lemma, translated_pos, doc_title)
            lines = self.search_ctrl.get_concordance(word, 5, 5)
            
            self.search_view.show_grammar(feats)
            self.search_view.show_concordance(lines)
        except Exception as e:
            print(f"Ошибка: {e}")