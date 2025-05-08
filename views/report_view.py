# views/report_view.py
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from scipy.optimize import curve_fit

class ReportWindow(tk.Toplevel):
    def __init__(self, parent, stats):
        super().__init__(parent)
        self.title("Статистика обработки")
        self.geometry("800x600")
        
          # График
        fig, ax = plt.subplots(figsize=(6, 4))
        page_counts = np.array([s[3] for s in stats])  # Страницы
        times_ms = np.array([s[2] * 1000 for s in stats])  # Время в мс

        # Экспоненциальная модель: y = a * exp(b * x)
        def exp_model(x, a, b):
            return a * np.exp(b * x)

        fig, ax = plt.subplots(figsize=(6, 4))
        page_counts = np.array([s[3] for s in stats])  # Страницы
        times_ms = np.array([s[2] * 1000 for s in stats])  # Время в мс

        # Экспоненциальная модель: y = a * exp(b * x)
        def exp_model(x, a, b):
            return a * np.exp(b * x)

        try:
            # Подгонка параметров модели
            params, _ = curve_fit(exp_model, page_counts, times_ms, p0=[1, 0.001])
            a_fit, b_fit = params
            
            # Генерация предсказаний
            x_pred = np.linspace(0, max(page_counts)*1.5, 100)
            y_pred = exp_model(x_pred, a_fit, b_fit)
            
            # Чистая визуализация без текста
            ax.scatter(page_counts, times_ms, color='skyblue', s=20)
            ax.plot(x_pred, y_pred, color='#FF6B6B', linewidth=2)
            
        except Exception as e:
            ax.scatter(page_counts, times_ms, color='skyblue')

        ax.set_xlabel('Количество страниц')
        ax.set_ylabel('Время обработки (мс)')
        ax.grid(True)
        ax.legend()
        
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