import tkinter as tk
from tkinter import ttk, filedialog,messagebox
from tkcalendar import DateEntry
from threading import Thread

class AddDocumentDialog(tk.Toplevel):
    def __init__(self, parent, doc_controller):
        super().__init__(parent)
        self.doc_ctrl = doc_controller
        self.title("Добавить документ")
        self.geometry("600x400")
        self.genre_values = ["Роман", "Поэзия", "Драма", "Фантастика", "Научная литература", "Публицистика"]
        form_frame = ttk.Frame(self)
        form_frame.pack(fill=tk.BOTH, padx=5, pady=5)
        
        entries = [
            ("Заголовок:", ttk.Entry),
            ("Автор:", ttk.Entry),
            ("Дата:", DateEntry),
            ("Жанр:", ttk.Combobox)
        ]
        
        self.widgets = {}
        for i, (label, widget_type) in enumerate(entries):
            ttk.Label(form_frame, text=label).grid(row=i, column=0, padx=5, pady=5)
            if widget_type == DateEntry:
                self.widgets[label] = DateEntry(form_frame, date_pattern='yyyy-mm-dd')
            elif widget_type == ttk.Combobox:
                self.widgets[label] = ttk.Combobox(form_frame, values=self.genre_values, state="readonly")
                self.widgets[label].current(0)  # по умолчанию первый жанр
            else:
                self.widgets[label] = widget_type(form_frame)
            self.widgets[label].grid(row=i, column=1, padx=5, pady=5)
        
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(button_frame, text="Выбрать файл", command=self.select_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Добавить", command=self.validate_and_add).pack(side=tk.RIGHT, padx=5)
        
        self.file_path = None

    def select_file(self):
        self.file_path = filedialog.askopenfilename(
            filetypes=[("Поддерживаемые форматы", "*.txt *.pdf *.docx")]
        )
        if self.file_path:
            self.widgets["Заголовок:"].delete(0, tk.END)
            self.widgets["Заголовок:"].insert(0, self.file_path.split('/')[-1])

    def validate_and_add(self):
        required = ["Заголовок:", "Автор:", "Дата:", "Жанр:"]
        data = {}
        for field in required:
            widget = self.widgets[field]
            if isinstance(widget, DateEntry):
                data[field] = widget.get()
            else:
                data[field] = widget.get().strip()
        
        if not all(data.values()) or not self.file_path:
            messagebox.showerror("Ошибка", "Все поля должны быть заполнены")
            return
        
        self.doc_ctrl.add_document(
            self.file_path,
            data["Заголовок:"],
            data["Автор:"],
            data["Дата:"],
            data["Жанр:"]
        )
        self.destroy()