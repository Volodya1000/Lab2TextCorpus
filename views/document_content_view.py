# views/document_content_view.py

import tkinter as tk
from tkinter import ttk

class DocumentContentView(ttk.LabelFrame):
    def __init__(self, parent, page_size=1000, main_view=None):
        super().__init__(parent, text="Просмотр документа")
        self.main_view = main_view
        self.page_size = page_size
        self.pages = []
        self.current = 0

        self.text = tk.Text(self, wrap=tk.WORD, height=10)
        self.text.bind("<Button-1>", self._on_click) 
        self.text.pack(fill=tk.BOTH, expand=True)

        nav = ttk.Frame(self)
        nav.pack(fill=tk.X, pady=2)
        self.prev_btn = ttk.Button(nav, text="< Предыдущая", command=self.prev_page)
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        self.next_btn = ttk.Button(nav, text="Следующая >", command=self.next_page)
        self.next_btn.pack(side=tk.RIGHT, padx=5)

        
        self.text = tk.Text(self, wrap=tk.WORD, height=10)
        self.text.bind("<Button-1>", self._on_click)  # Привязка клика
        self.text.pack(fill=tk.BOTH, expand=True)

    def show_text(self, full_text):
        self.pages = [full_text[i:i+self.page_size] for i in range(0, len(full_text), self.page_size)]
        self.current = 0
        self._render()

    def _render(self):
        self.text.configure(state='normal')
        self.text.delete(1.0, tk.END)
        header = f"--- Страница {self.current+1} из {len(self.pages)} ---\n\n"
        self.text.insert(tk.END, header + (self.pages[self.current] if self.pages else ""))
        self.text.configure(state='disabled')

    def prev_page(self):
        if self.current > 0:
            self.current -= 1; self._render()

    def next_page(self):
        if self.current < len(self.pages)-1:
            self.current += 1; self._render()

    def _on_click(self, event):
        # Получаем позицию клика
        index = self.text.index(f"@{event.x},{event.y}")
        # Извлекаем слово
        word = self.text.get(f"{index} wordstart", f"{index} wordend").strip()
        
        if word and self.main_view:  # Проверяем наличие main_view
            self.main_view.on_word_selected(word) 