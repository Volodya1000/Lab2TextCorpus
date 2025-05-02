# views/filter_panel.py

import tkinter as tk
from tkinter import ttk
from utils.russian_translator import RussianTranslator

class FilterPanel(ttk.LabelFrame):
    def __init__(self, parent, on_filter_change, on_reset_all):
        """
        on_filter_change(feature, value) — вызывается при смене любого фильтра
        on_reset_all()               — сбросить все фильтры
        """
        super().__init__(parent, text="Фильтры")
        self.translator = RussianTranslator()
        self.on_filter_change = on_filter_change
        self.on_reset_all = on_reset_all
        self.filter_widgets = {}
        self._build()

    def _build(self):
        # POS
        pos_frame = ttk.Frame(self)
        pos_frame.pack(fill=tk.X, pady=2)
        ttk.Label(pos_frame, text="Часть речи:").pack(side=tk.LEFT, padx=2)
        pos_vals = [""] + list(self.translator.pos_translations.values())
        cmb_pos = ttk.Combobox(pos_frame, values=pos_vals, state="readonly", width=20)
        cmb_pos.pack(side=tk.LEFT)
        cmb_pos.bind("<<ComboboxSelected>>", lambda e: self._change("pos", cmb_pos.get()))
        ttk.Button(pos_frame, text="✕", width=2, command=lambda: self._reset("pos")).pack(side=tk.LEFT)
        self.filter_widgets["pos"] = cmb_pos

        # остальные морфо-признаки
        row_frames = []
        for i, feat in enumerate(self.translator.get_all_features()):
            if i % 4 == 0:
                frame = ttk.Frame(self); frame.pack(fill=tk.X)
                row_frames.append(frame)
            cmb = ttk.Combobox(
                row_frames[-1],
                values=[""] + self.translator.get_feature_values(feat),
                state="readonly", width=20
            )
            lbl = ttk.Label(row_frames[-1], text=feat)
            btn = ttk.Button(row_frames[-1], text="✕", width=2, command=lambda f=feat: self._reset(f))
            lbl.grid(row=0, column=(i%4)*3, padx=2)
            cmb.grid(row=0, column=(i%4)*3+1, padx=2)
            btn.grid(row=0, column=(i%4)*3+2, padx=2)
            cmb.bind("<<ComboboxSelected>>", lambda e, f=feat, c=cmb: self._change(f, c.get()))
            self.filter_widgets[feat] = cmb

        ttk.Button(self, text="Сбросить все", command=self.on_reset_all).pack(anchor=tk.E, pady=5)

    def _change(self, feat, val):
        self.on_filter_change(feat, val)

    def _reset(self, feat):
        cmb = self.filter_widgets[feat]
        cmb.set("")
        self.on_filter_change(feat, "")
