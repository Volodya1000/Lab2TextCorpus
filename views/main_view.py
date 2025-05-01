# views/main_view.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
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
        self.pages = []
        self.current_page = 0

        self.translator = RussianTranslator()
        self.active_filters: Dict[str, str] = {}
        self.filter_widgets: Dict[str, ttk.Combobox] = {}

        self.root.title("Корпусный менеджер")
        self.root.geometry("1200x800")

        self.create_menu()
        self.create_main_interface()
        self.create_filter_panel()
        self.update_document_list()
        self.root.after(100, self.process_progress_queue)

    # ----------------- Menu -----------------
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

        # --- Левый фрейм: список документов ---
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Документы корпуса").pack(fill=tk.X)
        self.documents_tree = ttk.Treeview(
            left_frame,
            columns=("title", "author", "date", "genre"),
            show="headings"
        )
        for col, text in [("title","Заголовок"),("author","Автор"),
                        ("date","Дата"),("genre","Жанр")]:
            self.documents_tree.heading(col, text=text)
        self.documents_tree.pack(fill=tk.BOTH, expand=True)
        self.documents_tree.bind('<<TreeviewSelect>>', self.show_document_content)

        # --- Правый фрейм: просмотр, поиск, результаты ---
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=3)

        # --- Панель чтения документа ---
        self.text_frame = ttk.LabelFrame(right_frame, text="Просмотр документа")
        self.text_frame.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)
        self.doc_text = tk.Text(self.text_frame, wrap=tk.WORD, height=10, state='disabled')
        self.doc_text.bind("<ButtonRelease-1>", self.handle_doc_text_click)
        self.doc_text.pack(fill=tk.BOTH, expand=True)

        nav = ttk.Frame(self.text_frame)
        nav.pack(fill=tk.X)
        self.prev_page_btn = ttk.Button(nav, text="< Предыдущая", command=self.prev_page)
        self.prev_page_btn.pack(side=tk.LEFT, padx=2)
        self.next_page_btn = ttk.Button(nav, text="Следующая >", command=self.next_page)
        self.next_page_btn.pack(side=tk.RIGHT, padx=2)

        # --- Поисковая панель ---
        search_bar = ttk.LabelFrame(right_frame, text="Поиск")
        search_bar.pack(fill=tk.X, padx=5, pady=5)
        self.search_entry = ttk.Entry(search_bar, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_type = ttk.Combobox(
            search_bar,
            values=["Лемма", "Словоформа", "Часть речи"],
            state="readonly", width=12
        )
        self.search_type.current(0)
        self.search_type.pack(side=tk.LEFT, padx=5)
        ttk.Button(search_bar, text="Искать", command=self.perform_search).pack(side=tk.LEFT, padx=5)

        # --- Настройки контекста ---
        ctx_frame = ttk.Frame(right_frame)
        ctx_frame.pack(fill=tk.X, padx=5)
        ttk.Label(ctx_frame, text="Слева:").pack(side=tk.LEFT, padx=2)
        self.context_left = tk.IntVar(value=5)
        ttk.Spinbox(ctx_frame, from_=1, to=20, textvariable=self.context_left, width=3).pack(side=tk.LEFT)
        ttk.Label(ctx_frame, text="Справа:").pack(side=tk.LEFT, padx=2)
        self.context_right = tk.IntVar(value=5)
        ttk.Spinbox(ctx_frame, from_=1, to=20, textvariable=self.context_right, width=3).pack(side=tk.LEFT, padx=2)

        self.context_left.trace_add("write", lambda *args: self._refresh_concordance())
        self.context_right.trace_add("write", lambda *args: self._refresh_concordance())

        # --- Панель результатов и деталей ---
        self.search_frame = ttk.Frame(right_frame)
        self.search_frame.pack(fill=tk.BOTH, expand=True)

        results_pane = ttk.PanedWindow(self.search_frame, orient=tk.HORIZONTAL)
        results_pane.pack(fill=tk.BOTH, expand=True)

        # -- Левая часть: дерево результатов --
        res_left = ttk.Frame(results_pane)
        results_pane.add(res_left, weight=1)

        self.results_tree = ttk.Treeview(
            res_left,
            columns=("token", "lemma", "pos", "doc"),
            show="headings"
        )
        self.results_tree.heading("token", text="Слово")
        self.results_tree.heading("lemma", text="Лемма")
        self.results_tree.heading("pos", text="Часть речи")
        self.results_tree.heading("doc", text="Документ")
        self.results_tree.pack(fill=tk.BOTH, expand=True)
        self.results_tree.bind("<<TreeviewSelect>>", lambda e: self.on_result_select())

        # -- Правая часть: детали слова --
        detail = ttk.Frame(results_pane)
        results_pane.add(detail, weight=2)

        info_frame = ttk.Frame(detail)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(info_frame, text="Лемма:").grid(row=0, column=0, sticky="w")
        self.detail_lemma = tk.StringVar()
        ttk.Label(info_frame, textvariable=self.detail_lemma).grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(info_frame, text="POS:").grid(row=1, column=0, sticky="w")
        self.detail_pos = tk.StringVar()
        ttk.Label(info_frame, textvariable=self.detail_pos).grid(row=1, column=1, sticky="w", padx=5)

        # --- Грамматические признаки ---
        ttk.Label(detail, text="Грамматика:").pack(anchor="nw", padx=5)
        self.detail_gram = tk.Text(detail, height=4, wrap=tk.WORD, state='disabled')
        self.detail_gram.pack(fill=tk.X, padx=5, pady=2)

        # --- Конкорданс ---
        ttk.Label(detail, text="Конкорданс:").pack(anchor="nw", padx=5, pady=(10, 0))

        concordance_frame = ttk.Frame(detail)
        concordance_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        scroll_y = ttk.Scrollbar(concordance_frame, orient=tk.VERTICAL)
        self.detail_concordance = tk.Text(
            concordance_frame,
            wrap=tk.WORD,
            state='disabled',
            yscrollcommand=scroll_y.set
        )
        scroll_y.config(command=self.detail_concordance.yview)

        self.detail_concordance.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.notebook = None  # старые вкладки не используются


    # ------------- Filter Panel -------------
    def create_filter_panel(self):
        filter_frame = ttk.LabelFrame(self.root, text="Фильтры")
        filter_frame.pack(fill=tk.X, padx=5, pady=5)

        # POS filter
        pos_frame = ttk.Frame(filter_frame)
        pos_frame.pack(fill=tk.X, pady=2)
        ttk.Label(pos_frame, text="Часть речи:").pack(side=tk.LEFT, padx=2)
        pos_vals = list(self.translator.pos_translations.values())
        cmb_pos = ttk.Combobox(pos_frame, values=[""]+pos_vals, state="readonly", width=20)
        cmb_pos.pack(side=tk.LEFT)
        cmb_pos.bind("<<ComboboxSelected>>", lambda e: self.on_filter_change("pos", cmb_pos.get()))
        ttk.Button(pos_frame, text="✕", width=2, command=lambda: self.reset_filter("pos")).pack(side=tk.LEFT, padx=2)
        self.filter_widgets["pos"] = cmb_pos

        # Other grammar features
        features = self.translator.get_all_features()
        rows = []
        for i, feat in enumerate(features):
            row = i//4
            col = i%4
            if col==0:
                frame_row = ttk.Frame(filter_frame)
                frame_row.pack(fill=tk.X)
                rows.append(frame_row)
            ttk.Label(rows[row], text=feat).grid(row=0, column=col*3, padx=2)
            cmb = ttk.Combobox(
                rows[row],
                values=[""]+self.translator.get_feature_values(feat),
                state="readonly", width=20
            )
            cmb.grid(row=0, column=col*3+1, padx=2)
            cmb.bind("<<ComboboxSelected>>", lambda e, f=feat, c=cmb: self.on_filter_change(f, c.get()))
            ttk.Button(rows[row], text="✕", width=2, command=lambda f=feat: self.reset_filter(f)).grid(
                row=0, column=col*3+2, padx=2
            )
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

    # -------------- Search -----------------
    def perform_search(self):
        query = self.search_entry.get().strip()
        if not query:
            return
        stype = self.search_type.get()
        results = self.search_ctrl.search(stype, query, dict(self.active_filters))
        # clear tree
        for i in self.results_tree.get_children():
            self.results_tree.delete(i)
        # insert
        for token, lemma, pos, sent, doc in results:
            self.results_tree.insert("", "end", values=(token, lemma, self.translator.translate_pos(pos), doc))
        # clear detail
        self.clear_detail()

    # ------------- Result Selection -------------
    def on_result_select(self):
        sel = self.results_tree.selection()
        if not sel:
            return
        token, lemma, pos, doc = self.results_tree.item(sel[0], 'values')
        # Обновляем лемму и POS
        self.detail_lemma.set(lemma)
        self.detail_pos.set(pos)

        # Грамматические признаки из БД
        with self.doc_ctrl.db.lock, self.doc_ctrl.db.conn:
            cur = self.doc_ctrl.db.conn.cursor()
            cur.execute('''
                SELECT feature, value 
                FROM grammar_features
                WHERE token_id IN (
                    SELECT id FROM tokens WHERE token=? AND lemma=? AND pos=?
                )
            ''', (token, lemma, self._reverse_pos(pos)))
            gf = cur.fetchall()

        self.detail_gram.configure(state='normal')
        self.detail_gram.delete(1.0, tk.END)
        for feature, val in gf:
            rus = self.translator.morph_translations.get(feature, {}).get(val, val)
            self.detail_gram.insert(tk.END, f"• {feature} = {rus}\n")
        self.detail_gram.configure(state='disabled')

        # Конкорданс
        self._refresh_concordance(token)

    def _reverse_pos(self, rus_pos: str) -> str:
        """Русское название POS → код Natasha"""
        rev = {v: k for k, v in self.translator.pos_translations.items()}
        return rev.get(rus_pos, rus_pos)


    def _refresh_concordance(self, token=None):
        sel = self.results_tree.selection()
        if not sel and not token:
            return
        if not token:
            token = self.results_tree.item(sel[0], 'values')[0]
        ctxt = self.search_ctrl.get_concordance(token, self.context_left.get(), self.context_right.get())
        self.detail_concordance.configure(state='normal')
        self.detail_concordance.delete(1.0, tk.END)
        for line in ctxt:
            self.detail_concordance.insert(tk.END, line + "\n")
        self.detail_concordance.configure(state='disabled')

    def clear_detail(self):
        self.detail_lemma.set("")
        self.detail_pos.set("")
        self.detail_gram.configure(state='normal')
        self.detail_gram.delete(1.0, tk.END)
        self.detail_gram.configure(state='disabled')
        self.detail_concordance.configure(state='normal')
        self.detail_concordance.delete(1.0, tk.END)
        self.detail_concordance.configure(state='disabled')

    # ------ Document display & progress ------
    def process_progress_queue(self):
        try:
            while True:
                kind, text = self.doc_ctrl.progress_queue.get_nowait()
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
        for i in self.documents_tree.get_children():
            self.documents_tree.delete(i)
        with self.doc_ctrl.db.lock, self.doc_ctrl.db.conn:
            cur = self.doc_ctrl.db.conn.cursor()
            cur.execute('SELECT id,title,author,date,genre FROM documents')
            for row in cur.fetchall():
                self.documents_tree.insert("", "end", iid=row[0], values=row[1:])

    def show_document_content(self, _event):
        sel = self.documents_tree.selection()
        if not sel:
            return
        full_text = self.doc_ctrl.get_document_content(sel[0])
        # разбиваем по CONFIG.PAGE_SIZE или по 1000 символов:
        page_size = 1000
        self.pages = [full_text[i:i+page_size] for i in range(0, len(full_text), page_size)]
        self.current_page = 0
        self._render_page()


    def open_add_document_dialog(self):
        AddDocumentDialog(self.root, self.doc_ctrl)

    def delete_document(self):
        sel = self.documents_tree.selection()
        if not sel:
            return
        if messagebox.askyesno("Подтверждение", "Удалить документ?"):
            self.doc_ctrl.delete_document(sel[0])
            self.update_document_list()

    def show_about(self):
        messagebox.showinfo("О программе", "Корпусный менеджер v1.2\nБГУИР, 2024")

    def _render_page(self):
        self.doc_text.configure(state='normal')
        self.doc_text.delete(1.0, tk.END)
        content = self.pages[self.current_page]
        header = f"--- Страница {self.current_page+1} из {len(self.pages)} ---\n\n"
        self.doc_text.insert(tk.END, header + content)
        self.doc_text.configure(state='disabled')

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._render_page()

    def next_page(self):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self._render_page()

    def handle_doc_text_click(self, event):
        try:
            selected = self.doc_text.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
        except tk.TclError:
            return

        if not selected or len(selected.split()) > 1:
            return

        token = selected
        self.detail_lemma.set("")
        self.detail_pos.set("")
        self.detail_gram.configure(state="normal")
        self.detail_gram.delete(1.0, tk.END)
        self.detail_gram.configure(state="disabled")
        self.detail_concordance.configure(state="normal")
        self.detail_concordance.delete(1.0, tk.END)
        self.detail_concordance.configure(state="disabled")

        with self.doc_ctrl.db.lock, self.doc_ctrl.db.conn:
            cur = self.doc_ctrl.db.conn.cursor()
            cur.execute(
                "SELECT DISTINCT lemma, pos FROM tokens WHERE token = ?",
                (token,)
            )
            row = cur.fetchone()
            if not row:
                return

            lemma, pos = row
            self.detail_lemma.set(lemma)
            self.detail_pos.set(self.translator.translate_pos(pos))

            cur.execute('''
                SELECT feature, value FROM grammar_features
                WHERE token_id IN (
                    SELECT id FROM tokens WHERE token = ? AND lemma = ? AND pos = ?
                )
            ''', (token, lemma, pos))
            feats = cur.fetchall()

        self.detail_gram.configure(state="normal")
        for f, v in feats:
            rus = self.translator.morph_translations.get(f, {}).get(v, v)
            self.detail_gram.insert(tk.END, f"• {f} = {rus}\n")
        self.detail_gram.configure(state="disabled")

        # Конкорданс
        concordance = self.search_ctrl.get_concordance(
            token, self.context_left.get(), self.context_right.get()
        )
        self.detail_concordance.configure(state="normal")
        for line in concordance:
            self.detail_concordance.insert(tk.END, line + "\n")
        self.detail_concordance.configure(state="disabled")

