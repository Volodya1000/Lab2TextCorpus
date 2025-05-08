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
        self.geometry("1000x800")

        # Сортируем статистику по времени обработки (по возрастанию)
        sorted_stats = sorted(stats, key=lambda x: x[2])  # x[2] - processing_time

        # График
        fig, ax = plt.subplots(figsize=(10, 6))
        page_counts = np.array([s[3] for s in sorted_stats])  # Страницы
        times_ms = np.array([s[2] * 1000 for s in sorted_stats])  # Время в мс

        # Экспоненциальная модель
        def exp_model(x, a, b):
            return a * np.exp(b * x)

        try:
            params, _ = curve_fit(exp_model, page_counts, times_ms, p0=[1, 0.001])
            a_fit, b_fit = params
            x_pred = np.linspace(0, max(page_counts)*1.5, 100)
            y_pred = exp_model(x_pred, a_fit, b_fit)
        except Exception as e:
            pass

        # Рисуем точки с аннотациями
        scatter = ax.scatter(page_counts, times_ms, color='skyblue', s=50)
        
        # Добавляем номера точек
        for i, (x, y) in enumerate(zip(page_counts, times_ms)):
            ax.annotate(
                str(i+1), 
                (x, y),
                textcoords="offset points",
                xytext=(5,5),
                ha='left',
                fontsize=8,
                color='darkblue'
            )

        ax.set_xlabel('Количество страниц', fontsize=12)
        ax.set_ylabel('Время обработки (мс)', fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.legend()
        plt.tight_layout()

        # Встраиваем график
        canvas = FigureCanvasTkAgg(fig, self)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Таблица
        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(
            table_frame, 
            columns=("num", "title", "pages", "time"), 
            show="headings",
            height=8
        )
        
        # Настройка столбцов
        self.tree.heading("num", text="#", anchor=tk.W)
        self.tree.heading("title", text="Документ", anchor=tk.W)
        self.tree.heading("pages", text="Страницы", anchor=tk.CENTER)
        self.tree.heading("time", text="Время (мс)", anchor=tk.CENTER)

        self.tree.column("num", width=50, anchor=tk.W)
        self.tree.column("title", width=400, anchor=tk.W)
        self.tree.column("pages", width=100, anchor=tk.CENTER)
        self.tree.column("time", width=150, anchor=tk.CENTER)

        # Добавляем данные
        for i, (doc_id, title, time, pages) in enumerate(sorted_stats, 1):
            self.tree.insert(
                "", 
                "end", 
                values=(
                    i, 
                    title, 
                    pages, 
                    f"{time*1000:.1f}"
                )
            )

        # Скроллбар для таблицы
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Размещение элементов
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)