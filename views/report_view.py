# views/report_view.py
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class ReportWindow(tk.Toplevel):
    def __init__(self, parent, stats):
        super().__init__(parent)
        self.title("Статистика обработки")
        self.geometry("800x600")
        
        # График
        fig, ax = plt.subplots(figsize=(6, 4))
        page_counts = [s[3] for s in stats]  # Колонка page_count
        times_ms = [s[2] * 1000 for s in stats]  # Секунды в миллисекунды
        
        ax.plot(page_counts, times_ms, marker='o', linestyle='-', color='skyblue')
        ax.set_xlabel('Количество страниц')
        ax.set_ylabel('Время обработки (миллисекунды)')
        ax.set_title('Время обработки документов относительно количества страниц')
        ax.grid(True)
        
        canvas = FigureCanvasTkAgg(fig, self)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Таблица
        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.tree = ttk.Treeview(frame, columns=("num", "title", "pages", "time"), show="headings")
        for col, text in [
            ("num", "#"),
            ("title", "Документ"),
            ("pages", "Страницы"),
            ("time", "Время (мс)")
        ]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=100 if col != "title" else 400)
        
        for i, (doc_id, title, time, pages) in enumerate(stats, 1):
            self.tree.insert("", "end", values=(i, title, pages, f"{time*1000:.2f}"))
        
        self.tree.pack(fill=tk.BOTH, expand=True)