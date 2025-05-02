# views/search_view.py

import tkinter as tk
from tkinter import ttk

class SearchView(ttk.Frame):
    def __init__(self, parent, search_ctrl, on_search, on_result_select, get_concordance):
        super().__init__(parent)
        self.search_ctrl = search_ctrl  
        self.on_search = on_search
        self.get_concordance = get_concordance
        bar = ttk.LabelFrame(self, text="Поиск") 
        bar.pack(fill=tk.X)

        # Поисковая панель
        self.partial_match = tk.BooleanVar(value=False) 
        ttk.Checkbutton(
            bar, 
            text="Частичное", 
            variable=self.partial_match
        ).pack(side=tk.LEFT, padx=5)

        bar = ttk.LabelFrame(self, text="Поиск")
        bar.pack(fill=tk.X)
        self.entry = ttk.Entry(bar, width=40); self.entry.pack(side=tk.LEFT, padx=5)
        self.type_cmb = ttk.Combobox(bar, values=["Лемма","Словоформа"], state="readonly", width=12)
        self.type_cmb.current(0); self.type_cmb.pack(side=tk.LEFT)
        ttk.Button(bar, text="Искать", command=self._search).pack(side=tk.LEFT, padx=5)

        # Настройки контекста
        ctx = ttk.Frame(self); ctx.pack(fill=tk.X, pady=2)
        tk.Label(ctx, text="Слева:").pack(side=tk.LEFT)
        self.ctx_left = tk.IntVar(value=5)
        ttk.Spinbox(ctx, from_=1, to=20, textvariable=self.ctx_left, width=3).pack(side=tk.LEFT)
        tk.Label(ctx, text="Справа:").pack(side=tk.LEFT)
        self.ctx_right = tk.IntVar(value=5)
        ttk.Spinbox(ctx, from_=1, to=20, textvariable=self.ctx_right, width=3).pack(side=tk.LEFT)

        # Результаты
        pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True)
        # — дерево
        left = ttk.Frame(pane); pane.add(left, weight=1)
        self.tree = ttk.Treeview(left, columns=("token","lemma","pos","doc"), show="headings")
        for c,t in [("token","Слово"),("lemma","Лемма"),("pos","Часть речи"),("doc","Документ")]:
            self.tree.heading(c, text=t)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # — детали
        right = ttk.Frame(pane); pane.add(right, weight=2)
        info = ttk.Frame(right); info.pack(fill=tk.X, pady=2)
        tk.Label(info, text="Лемма:").grid(row=0,column=0); self.lbl_lemma = tk.StringVar()
        ttk.Label(info, textvariable=self.lbl_lemma).grid(row=0,column=1)
        tk.Label(info, text="POS:").grid(row=1,column=0); self.lbl_pos = tk.StringVar()
        ttk.Label(info, textvariable=self.lbl_pos).grid(row=1,column=1)

        ttk.Label(right, text="Грамматика:").pack(anchor="w")
        self.txt_gram = tk.Text(right, height=4, state='disabled'); self.txt_gram.pack(fill=tk.X, pady=2)

        ttk.Label(right, text="Конкорданс:").pack(anchor="w", pady=(10,0))
        fr = ttk.Frame(right); fr.pack(fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(fr); sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_conc = tk.Text(fr, wrap=tk.WORD, state='disabled', yscrollcommand=sb.set)
        sb.config(command=self.txt_conc.yview); self.txt_conc.pack(fill=tk.BOTH, expand=True)

        self.select_callback = on_result_select

    def _search(self):
        q = self.entry.get().strip()
        if not q:
            return

        search_type = self.type_cmb.get()
        is_partial = self.partial_match.get()

        where_clauses = []
        params = []

        if search_type == 'Лемма':
            if is_partial:
                where_clauses.append("LOWER(t.lemma) LIKE LOWER(?)")
                params.append(f"%{q}%")
            else:
                where_clauses.append("LOWER(t.lemma) = LOWER(?)")
                params.append(q)
        elif search_type == 'Словоформа':
            if is_partial:
                where_clauses.append("LOWER(t.token) LIKE LOWER(?)")
                params.append(f"%{q}%")
            else:
                where_clauses.append("LOWER(t.token) = LOWER(?)")
                params.append(q)
        else:
            pos_code = self.search_ctrl._translate_pos_to_code(q)
            if pos_code:
                where_clauses.append("t.pos = ?")
                params.append(pos_code)

        sql = """
            SELECT DISTINCT
                t.token,
                t.lemma,
                t.pos,
                d.title,
                s.sentence_text
            FROM tokens t
            JOIN sentences s ON t.sentence_id = s.id
            JOIN documents d ON s.doc_id = d.id
        """
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += " ORDER BY d.title, s.id, t.start LIMIT 500"

        with self.search_ctrl.db.lock, self.search_ctrl.db.conn:
            cur = self.search_ctrl.db.conn.cursor()
            cur.execute(sql, params)
            res = cur.fetchall()

        self._update_results(res)  # Теперь метод существует!

    def _on_select(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], 'values')
        # Распаковываем все 5 значений
        token, lemma, pos, doc_title, sentence_text = values
        left = self.ctx_left.get()
        right = self.ctx_right.get()
        self.select_callback(token, lemma, pos, doc_title, left, right)

    def show_grammar(self, feats):
        self.txt_gram.configure(state='normal'); self.txt_gram.delete(1.0, tk.END)
        for f,v in feats:
            self.txt_gram.insert(tk.END, f"• {f} = {v}\n")
        self.txt_gram.configure(state='disabled')

    def show_concordance(self, lines):
        self.txt_conc.configure(state='normal'); self.txt_conc.delete(1.0, tk.END)
        for l in lines: self.txt_conc.insert(tk.END, l+"\n")
        self.txt_conc.configure(state='disabled')

    def _update_results(self, results):
        """Обновить дерево результатов поиска."""
        # Очистка предыдущих результатов
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Добавление новых данных
        for row in results:
            self.tree.insert("", "end", values=row)
