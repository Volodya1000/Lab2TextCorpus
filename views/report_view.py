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
        ids = [s[0] for s in stats]
        times = [s[2] for s in stats]
        labels = [s[1] for s in stats]
        
        ax.bar(ids, times)
        ax.set_xlabel('Порядковый номер')
        ax.set_ylabel('Время обработки (сек)')
        ax.set_title('Время обработки документов')
        
        canvas = FigureCanvasTkAgg(fig, self)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Таблица
        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.tree = ttk.Treeview(frame, columns=("num", "title", "time"), show="headings")
        for col, text in [("num", "#"), ("title", "Документ"), ("time", "Время (сек)")]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=100 if col != "title" else 400)
        
        for i, (doc_id, title, time) in enumerate(stats, 1):
            self.tree.insert("", "end", values=(i, title, f"{time:.2f}"))
        
        self.tree.pack(fill=tk.BOTH, expand=True)