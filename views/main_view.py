# views/main_view.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
from views.dialogs import AddDocumentDialog
from threading import Thread
import queue
from typing import Dict
from utils.russian_translator import RussianTranslator

class MainView:
    def __init__(self, root, doc_controller, search_controller):
        self.root = root
        self.doc_ctrl = doc_controller
        self.search_ctrl = search_controller

        # переводчик
        self.translator = RussianTranslator()

        # активные фильтры: ключи — названия (например, 'Case', 'Часть речи'), 
        # значения — выбранные русские значения
        self.active_filters: Dict[str, str] = {}
        # виджеты combobox, чтобы можно было сбрасывать их програмно
        self.filter_widgets: Dict[str, ttk.Combobox] = {}

        self.root.title("Корпусный менеджер - Литература")
        self.root.geometry("1200x800")

        self.create_menu()
        self.create_main_interface()
        self.create_filter_panel()     # панель с грамматикой + POS
        self.update_document_list()
        self.root.after(100, self.process_progress_queue)

        # сделать текстовые поля только для чтения
        self.concordance_text.configure(state='disabled')
        self.gram_text.configure(state='disabled')

    def create_menu(self):
        menu_bar = tk.Menu(self.root)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Добавить документ", command=self.open_add_document_dialog)
        file_menu.add_command(label="Удалить документ", command=self.delete_document)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        menu_bar.add_cascade(label="Файл", menu=file_menu)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="О программе", command=self.show_about)
        menu_bar.add_cascade(label="Помощь", menu=help_menu)

        self.root.config(menu=menu_bar)

    def create_menu(self):
        menu_bar = tk.Menu(self.root)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Добавить документ", command=self.open_add_document_dialog)
        file_menu.add_command(label="Удалить документ", command=self.delete_document)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        menu_bar.add_cascade(label="Файл", menu=file_menu)
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="О программе", command=self.show_about)
        menu_bar.add_cascade(label="Помощь", menu=help_menu)
        self.root.config(menu=menu_bar)

    def create_main_interface(self):
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        # Левый фрейм: список документов
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=1)
        ttk.Label(left_frame, text="Документы корпуса").pack(fill=tk.X)
        self.documents_tree = ttk.Treeview(
            left_frame,
            columns=("title","author","date","genre"),
            show="headings"
        )
        for col, txt in [("title","Заголовок"),("author","Автор"),("date","Дата"),("genre","Жанр")]:
            self.documents_tree.heading(col, text=txt)
        self.documents_tree.pack(fill=tk.BOTH, expand=True)
        self.documents_tree.bind('<<TreeviewSelect>>', self.show_document_content)

        # Правый фрейм: поиск + вкладки
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=3)

        # Поисковая строка
        search_frame = ttk.LabelFrame(right_frame, text="Поиск")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        self.search_entry = ttk.Entry(search_frame, width=50)
        self.search_entry.pack(side=tk.LEFT, padx=5, pady=5)
        self.search_type = ttk.Combobox(
            search_frame,
            values=["Лемма","Словоформа","Часть речи"],
            state="readonly",
            width=12
        )
        self.search_type.current(0)
        self.search_type.pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Искать", command=self.perform_search).pack(side=tk.LEFT, padx=5)

        # Настройки контекста конкорданса
        conc_frame = ttk.Frame(right_frame)
        conc_frame.pack(fill=tk.X, padx=5)
        ttk.Label(conc_frame, text="Слева:").pack(side=tk.LEFT, padx=2)
        self.context_left = tk.IntVar(value=5)
        ttk.Spinbox(conc_frame, from_=1, to=20, textvariable=self.context_left, width=3).pack(side=tk.LEFT)
        ttk.Label(conc_frame, text="Справа:").pack(side=tk.LEFT, padx=2)
        self.context_right = tk.IntVar(value=5)
        ttk.Spinbox(conc_frame, from_=1, to=20, textvariable=self.context_right, width=3).pack(side=tk.LEFT)

        # Вкладки результатов
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # --- вкладка: просмотр текста ---
        self.view_frame = ttk.Frame(self.notebook)
        self.concordance_text = tk.Text(self.view_frame, wrap=tk.WORD)
        self.concordance_text.pack(fill=tk.BOTH, expand=True)
        self.concordance_text.bind("<ButtonRelease-1>", self.handle_text_selection)
        self.notebook.add(self.view_frame, text="Просмотр")

        # --- вкладка: информация о слове ---
        self.info_frame = ttk.Frame(self.notebook)
        info_pane = ttk.PanedWindow(self.info_frame, orient=tk.VERTICAL)
        info_pane.pack(fill=tk.BOTH, expand=True)
        top_info = ttk.Frame(info_pane)
        info_pane.add(top_info, weight=1)
        ttk.Label(top_info, text="Лемма:").grid(row=0, column=0, sticky="w")
        self.lemma_var = tk.StringVar()
        ttk.Label(top_info, textvariable=self.lemma_var).grid(row=0, column=1, sticky="w")
        ttk.Label(top_info, text="Часть речи:").grid(row=1, column=0, sticky="w")
        self.pos_var = tk.StringVar()
        ttk.Label(top_info, textvariable=self.pos_var).grid(row=1, column=1, sticky="w")
        ttk.Label(top_info, text="Грамматика:").grid(row=2, column=0, sticky="nw")
        gram_frame = ttk.Frame(top_info)
        gram_frame.grid(row=2, column=1, sticky="nsew")
        self.gram_text = tk.Text(gram_frame, wrap=tk.WORD, height=4)
        scroll = ttk.Scrollbar(gram_frame, command=self.gram_text.yview)
        self.gram_text.configure(yscrollcommand=scroll.set)
        self.gram_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        bottom_info = ttk.Frame(info_pane)
        info_pane.add(bottom_info, weight=2)
        ttk.Label(bottom_info, text="Конкорданс:").pack(anchor="w")
        self.word_concordance = tk.Listbox(bottom_info)
        self.word_concordance.pack(fill=tk.BOTH, expand=True)
        self.word_concordance.bind('<<ListboxSelect>>', self.show_full_sentence)
        self.notebook.add(self.info_frame, text="Информация о слове")

        # --- вкладка: результаты поиска ---
        self.search_frame = ttk.Frame(self.notebook)
        self.results_list = tk.Listbox(self.search_frame)
        self.results_list.pack(fill=tk.BOTH, expand=True)
        self.results_list.bind('<<ListboxSelect>>', self.show_concordance)
        self.notebook.add(self.search_frame, text="Результаты поиска")

    def create_filter_panel(self):
        """
        Добавляем фильтрацию:
         - Сначала часть речи (общая для Natasha)
         - Затем все другие грамматические признаки
        """
        filter_frame = ttk.LabelFrame(self.root, text="Фильтры")
        filter_frame.pack(fill=tk.X, padx=5, pady=5)

        # 1) Фильтр по POS
        pos_frame = ttk.Frame(filter_frame)
        pos_frame.pack(fill=tk.X, pady=2)
        ttk.Label(pos_frame, text="Часть речи:").pack(side=tk.LEFT, padx=2)
        pos_values = list(self.translator.pos_translations.values())
        cmb_pos = ttk.Combobox(
            pos_frame,
            values=[""] + pos_values,
            state="readonly",
            width=20
        )
        cmb_pos.pack(side=tk.LEFT, padx=2)
        cmb_pos.bind("<<ComboboxSelected>>", lambda e: self.on_filter_change("pos", cmb_pos.get()))
        btn_pos = ttk.Button(pos_frame, text="✕", width=2, command=lambda: self.reset_filter("pos"))
        btn_pos.pack(side=tk.LEFT, padx=2)
        self.filter_widgets["pos"] = cmb_pos

        # 2) Оставшиеся грамматические признаки
        features = self.translator.get_all_features()
        rows = []
        for i, feat in enumerate(features):
            row = i // 4
            col = i % 4
            if col == 0:
                frame_row = ttk.Frame(filter_frame)
                frame_row.pack(fill=tk.X)
                rows.append(frame_row)
            ttk.Label(rows[row], text=feat).grid(row=0, column=col*3, padx=2)
            cmb = ttk.Combobox(
                rows[row],
                values=[""] + self.translator.get_feature_values(feat),
                state="readonly",
                width=20
            )
            cmb.grid(row=0, column=col*3+1, padx=2, pady=2)
            cmb.bind("<<ComboboxSelected>>", lambda e, f=feat, c=cmb: self.on_filter_change(f, c.get()))
            btn = ttk.Button(rows[row], text="✕", width=2, command=lambda f=feat: self.reset_filter(f))
            btn.grid(row=0, column=col*3+2, padx=2)
            self.filter_widgets[feat] = cmb

        ttk.Button(filter_frame, text="Сбросить все", command=self.reset_all_filters).pack(side=tk.RIGHT, padx=5)

    def on_filter_change(self, feature: str, value: str):
        if value:
            self.active_filters[feature] = value
        else:
            self.active_filters.pop(feature, None)

    def reset_filter(self, feature: str):
        cmb = self.filter_widgets.get(feature)
        if cmb:
            cmb.set("")
        self.active_filters.pop(feature, None)

    def reset_all_filters(self):
        for cmb in self.filter_widgets.values():
            cmb.set("")
        self.active_filters.clear()

    def perform_search(self):
        query = self.search_entry.get().strip()
        if not query:
            return
        search_type = self.search_type.get()
        results = self.search_ctrl.search(search_type, query, self.active_filters)
        self.results_list.delete(0, tk.END)
        for token, lemma, pos, sent, title in results:
            display_pos = self.translator.translate_pos(pos)
            self.results_list.insert(tk.END, f"{token} ({display_pos}) – {title}")

    def process_progress_queue(self):
        try:
            while True:
                msg = self.doc_ctrl.progress_queue.get_nowait()
                kind, text = msg
                if kind == "error":
                    messagebox.showerror("Ошибка", text)
                else:
                    messagebox.showinfo("Успех", text)
                    self.update_document_list()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_progress_queue)

    def update_document_list(self):
        self.documents_tree.delete(*self.documents_tree.get_children())
        with self.doc_ctrl.db.lock, self.doc_ctrl.db.conn:
            cur = self.doc_ctrl.db.conn.cursor()
            cur.execute('SELECT id, title, author, date, genre FROM documents')
            for row in cur.fetchall():
                self.documents_tree.insert('', 'end', iid=row[0], values=row[1:])

    def open_add_document_dialog(self):
        AddDocumentDialog(self.root, self.doc_ctrl)

    def delete_document(self):
        selected = self.documents_tree.selection()
        if not selected:
            return
        if messagebox.askyesno("Подтверждение", "Удалить выбранный документ?"):
            self.doc_ctrl.delete_document(selected[0])
            self.update_document_list()

    def show_document_content(self, event):
        sel = self.documents_tree.selection()
        if not sel:
            return
        text = self.doc_ctrl.get_document_content(sel[0])
        self.show_paginated_text(text)

    def show_paginated_text(self, text, page_size=1000):
        self.pages = [text[i:i+page_size] for i in range(0, len(text), page_size)]
        self.current_page = 0
        self.show_current_page()

    def show_current_page(self):
        if not hasattr(self, 'pages'):
            return
        page = self.pages[self.current_page]
        # unlock, write, lock
        self.concordance_text.configure(state='normal')
        self.concordance_text.delete(1.0, tk.END)
        self.concordance_text.insert(tk.END, f"--- Страница {self.current_page+1}/{len(self.pages)} ---\n{page}")
        # navigation
        if hasattr(self, 'nav_frame'):
            self.nav_frame.destroy()
        self.nav_frame = ttk.Frame(self.concordance_text)
        self.concordance_text.window_create(tk.END, window=self.nav_frame)
        ttk.Button(self.nav_frame, text="< Предыдущая", command=self.prev_page).pack(side=tk.LEFT)
        ttk.Button(self.nav_frame, text="Следующая >", command=self.next_page).pack(side=tk.RIGHT)
        self.concordance_text.configure(state='disabled')

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.show_current_page()

    def next_page(self):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.show_current_page()

    def handle_text_selection(self, event):
        try:
            sel = self.concordance_text.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
            if sel and len(sel.split()) == 1:
                self.show_word_info(sel)
                self.notebook.select(self.info_frame)
        except tk.TclError:
            pass

    def show_word_info(self, word: str):
        # clear
        self.lemma_var.set("")
        self.pos_var.set("")
        self.gram_text.configure(state='normal')
        self.gram_text.delete(1.0, tk.END)
        self.word_concordance.delete(0, tk.END)

        with self.doc_ctrl.db.lock, self.doc_ctrl.db.conn:
            cur = self.doc_ctrl.db.conn.cursor()
            cur.execute('SELECT DISTINCT lemma, pos FROM tokens WHERE token=?', (word,))
            info = cur.fetchone()
            if info:
                lemma, pos = info
                self.lemma_var.set(lemma or "–")
                self.pos_var.set(self.translator.translate_pos(pos) or "–")
            # fetch grammar features
            cur.execute('''
                SELECT feature, value FROM grammar_features
                WHERE token_id IN (SELECT id FROM tokens WHERE token=?)
            ''', (word,))
            feats = cur.fetchall()
            for feat, val in feats:
                rus_val = self.translator.morph_translations.get(feat, {}).get(val, val)
                self.gram_text.insert(tk.END, f"• {feat} = {rus_val}\n")
        self.gram_text.configure(state='disabled')

        # concordance for this word
        lines = self.search_ctrl.get_concordance(word, self.context_left.get(), self.context_right.get())
        for line in lines:
            self.word_concordance.insert(tk.END, line)

    def show_full_sentence(self, event):
        sel = self.word_concordance.curselection()
        if not sel:
            return
        sentence = self.word_concordance.get(sel[0])
        self.concordance_text.configure(state='normal')
        self.concordance_text.delete(1.0, tk.END)
        self.concordance_text.insert(tk.END, sentence)
        self.concordance_text.configure(state='disabled')
        self.notebook.select(self.view_frame)

    def show_concordance(self, event):
        sel = self.results_list.curselection()
        if not sel:
            return
        token = self.results_list.get(sel[0]).split(' ')[0]
        lines = self.search_ctrl.get_concordance(token, self.context_left.get(), self.context_right.get())
        self.concordance_text.configure(state='normal')
        self.concordance_text.delete(1.0, tk.END)
        self.concordance_text.insert(tk.END, '\n'.join(lines))
        self.concordance_text.configure(state='disabled')

    def show_about(self):
        messagebox.showinfo("О программе", "Корпусный менеджер v1.2\nБГУИР, 2024")
