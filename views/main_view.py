import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
from views.dialogs import AddDocumentDialog
from threading import Thread
import queue

class MainView:
    def __init__(self, root, doc_controller, search_controller):
        self.root = root
        self.doc_ctrl = doc_controller
        self.search_ctrl = search_controller
        self.root.title("Корпусный менеджер - Литература")
        self.root.geometry("1200x800")
        self.create_menu()
        self.create_main_interface()
        self.update_document_list()
        self.root.after(100, self.process_progress_queue)

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

        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=1)
        ttk.Label(left_frame, text="Документы корпуса").pack(fill=tk.X)
        self.documents_tree = ttk.Treeview(left_frame, columns=("title", "author", "date", "genre"), show="headings")
        self.documents_tree.heading("title", text="Заголовок")
        self.documents_tree.heading("author", text="Автор")
        self.documents_tree.heading("date", text="Дата")
        self.documents_tree.heading("genre", text="Жанр")
        self.documents_tree.pack(fill=tk.BOTH, expand=True)
        self.documents_tree.bind('<<TreeviewSelect>>', self.show_document_content)

        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=3)

        search_frame = ttk.LabelFrame(right_frame, text="Поиск")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        self.search_entry = ttk.Entry(search_frame, width=50)
        self.search_entry.pack(side=tk.LEFT, padx=5, pady=5)
        self.search_type = ttk.Combobox(search_frame, values=["Лемма", "Словоформа", "Часть речи"], state="readonly")
        self.search_type.current(0)
        self.search_type.pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(search_frame, text="Искать", command=self.perform_search).pack(side=tk.LEFT, padx=5, pady=5)

        conc_settings = ttk.Frame(right_frame)
        conc_settings.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(conc_settings, text="Слева:").pack(side=tk.LEFT, padx=5)
        self.context_left = tk.IntVar(value=5)
        ttk.Spinbox(conc_settings, from_=1, to=20, textvariable=self.context_left, width=3).pack(side=tk.LEFT)
        ttk.Label(conc_settings, text="Справа:").pack(side=tk.LEFT, padx=5)
        self.context_right = tk.IntVar(value=5)
        ttk.Spinbox(conc_settings, from_=1, to=20, textvariable=self.context_right, width=3).pack(side=tk.LEFT)

        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.view_frame = ttk.Frame(self.notebook)
        self.concordance_text = tk.Text(self.view_frame, wrap=tk.WORD)
        self.concordance_text.pack(fill=tk.BOTH, expand=True)
        self.concordance_text.bind("<ButtonRelease-1>", self.handle_text_selection)
        self.notebook.add(self.view_frame, text="Просмотр")

        self.info_frame = ttk.Frame(self.notebook)
        info_pane = ttk.PanedWindow(self.info_frame, orient=tk.VERTICAL)
        info_pane.pack(fill=tk.BOTH, expand=True)
        top_info = ttk.Frame(info_pane)
        info_pane.add(top_info, weight=1)
        ttk.Label(top_info, text="Лемма:").grid(row=0, column=0)
        self.lemma_var = tk.StringVar()
        ttk.Label(top_info, textvariable=self.lemma_var).grid(row=0, column=1)
        ttk.Label(top_info, text="Часть речи:").grid(row=1, column=0)
        self.pos_var = tk.StringVar()
        ttk.Label(top_info, textvariable=self.pos_var).grid(row=1, column=1)
        ttk.Label(top_info, text="Грамматика:").grid(row=2, column=0)
        self.gram_var = tk.StringVar()
        ttk.Label(top_info, textvariable=self.gram_var).grid(row=2, column=1)
        bottom_info = ttk.Frame(info_pane)
        info_pane.add(bottom_info, weight=2)
        ttk.Label(bottom_info, text="Конкорданс:").pack(fill=tk.X)
        self.word_concordance = tk.Listbox(bottom_info)
        self.word_concordance.pack(fill=tk.BOTH, expand=True)
        self.word_concordance.bind('<<ListboxSelect>>', self.show_full_sentence)
        self.notebook.add(self.info_frame, text="Информация о слове")

        self.search_frame = ttk.Frame(self.notebook)
        self.results_list = tk.Listbox(self.search_frame)
        self.results_list.pack(fill=tk.BOTH, expand=True)
        self.results_list.bind('<<ListboxSelect>>', self.show_concordance)
        self.notebook.add(self.search_frame, text="Результаты поиска")

    def process_progress_queue(self):
        try:
            while True:
                msg = self.doc_ctrl.progress_queue.get_nowait()
                if msg[0] == "error":
                    messagebox.showerror("Ошибка", msg[1])
                elif msg[0] == "success":
                    messagebox.showinfo("Успех", msg[1])
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
        confirm = messagebox.askyesno("Подтверждение", "Удалить выбранный документ?")
        if confirm:
            self.doc_ctrl.delete_document(selected[0])
            self.update_document_list()

    def show_document_content(self, event):
        selected = self.documents_tree.selection()
        if not selected:
            return
        text = self.doc_ctrl.get_document_content(selected[0])
        self.show_paginated_text(text)

    def show_paginated_text(self, text, page_size=1000):
        self.pages = [text[i:i+page_size] for i in range(0, len(text), page_size)]
        self.current_page = 0
        self.show_current_page()

    def show_current_page(self):
        if not self.pages:
            return
        page = self.pages[self.current_page]
        self.concordance_text.delete(1.0, tk.END)
        self.concordance_text.insert(tk.END, f"--- Страница {self.current_page+1}/{len(self.pages)} ---\n{page}")
        self.create_navigation_buttons()

    def create_navigation_buttons(self):
        if hasattr(self, 'nav_frame'):
            self.nav_frame.destroy()
        self.nav_frame = ttk.Frame(self.concordance_text)
        self.concordance_text.window_create(tk.END, window=self.nav_frame)
        prev_btn = ttk.Button(self.nav_frame, text="< Предыдущая", command=self.prev_page)
        prev_btn.pack(side=tk.LEFT)
        next_btn = ttk.Button(self.nav_frame, text="Следующая >", command=self.next_page)
        next_btn.pack(side=tk.RIGHT)

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.show_current_page()

    def next_page(self):
        if self.current_page < len(self.pages)-1:
            self.current_page += 1
            self.show_current_page()

    def handle_text_selection(self, event):
        try:
            selection = self.concordance_text.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
            if selection and len(selection.split()) == 1:
                self.show_word_info(selection)
                self.notebook.select(self.info_frame)
        except tk.TclError:
            pass

    def show_word_info(self, word):
        self.lemma_var.set("")
        self.pos_var.set("")
        self.gram_var.set("")
        self.word_concordance.delete(0, tk.END)
        
        doc = self.doc_ctrl.nlp.process(word)
        for token in doc.tokens:
            token.lemmatize(self.doc_ctrl.nlp.morph_vocab)  # Используем морфологию из контроллера
        
        if doc.tokens:
            token = doc.tokens[0]
            self.lemma_var.set(token.lemma)       # Исправлено
            self.pos_var.set(token.pos)           # Исправлено
            self.gram_var.set(
                str(token.feats) if token.feats else '-'
            )                                     # Исправлено
        else:
            self.lemma_var.set("Не найдено")
            return

        concordance = self.search_ctrl.get_concordance(
            word,
            self.context_left.get(),
            self.context_right.get()
        )
        for line in concordance:
            self.word_concordance.insert(tk.END, line)

    def show_full_sentence(self, event):
        selection = self.word_concordance.curselection()
        if selection:
            sentence = self.word_concordance.get(selection[0])
            self.concordance_text.delete(1.0, tk.END)
            self.concordance_text.insert(tk.END, sentence)
            self.notebook.select(self.view_frame)

    def perform_search(self):
        query = self.search_entry.get().strip()
        if not query:
            return

        search_type = self.search_type.get()
        self.results_list.delete(0, tk.END)
        
        if search_type == "Лемма":
            results = self.search_ctrl.search_by_lemma(query)
        elif search_type == "Словоформа":
            results = self.search_ctrl.search_by_wordform(query)
        else:
            results = self.search_ctrl.search_by_pos(query)

        for row in results:
            self.results_list.insert(tk.END, f"{row[0]} ({row[2]}) - {row[4]}")

    def show_concordance(self, event):
        selection = self.results_list.curselection()
        if not selection:
            return
        item = self.results_list.get(selection[0])
        token = item.split(' ')[0]
        concordance = self.search_ctrl.get_concordance(
            token,
            self.context_left.get(),
            self.context_right.get()
        )
        self.concordance_text.delete(1.0, tk.END)
        self.concordance_text.insert(tk.END, '\n'.join(concordance))

    def show_about(self):
        messagebox.showinfo("О программе", "Корпусный менеджер v1.2\nРазработан для лабораторной работы #2 БГУИР 2024")