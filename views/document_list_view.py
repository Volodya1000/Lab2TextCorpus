# views/document_list_view.py

import tkinter as tk
from tkinter import ttk

class DocumentListView(ttk.Frame):
    def __init__(self, parent, on_select):
        """
        on_select(doc_id) — вызывается при выборе документа
        """
        super().__init__(parent)
        ttk.Label(self, text="Документы корпуса").pack(fill=tk.X)
        self.tree = ttk.Treeview(self, columns=("title","author","date","genre"), show="headings")
        for col, txt in [("title","Заголовок"),("author","Автор"),("date","Дата"),("genre","Жанр")]:
            self.tree.heading(col, text=txt)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: on_select(self.tree.selection()[0] if self.tree.selection() else None))

    def update(self, documents):
        """documents — список кортежей (id, title, author, date, genre)"""
        for i in self.tree.get_children():
            self.tree.delete(i)
        for doc in documents:
            self.tree.insert("", "end", iid=doc[0], values=doc[1:])
