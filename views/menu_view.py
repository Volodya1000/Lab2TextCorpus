# views/menu_view.py

import tkinter as tk
from tkinter import messagebox
from views.dialogs import AddDocumentDialog

class MenuView:
    def __init__(self, root, doc_ctrl, update_list_callback):
        """
        root               — корневой Tk
        doc_ctrl           — DocumentController
        update_list_callback — функция, вызываемая после успешного добавления/удаления документа
        """
        self.root = root
        self.doc_ctrl = doc_ctrl
        self.update_list = update_list_callback
        self._build_menu()

    def _build_menu(self):
        menu_bar = tk.Menu(self.root)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Добавить документ", command=self._on_add)
        file_menu.add_command(label="Удалить документ", command=self._on_delete)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        menu_bar.add_cascade(label="Файл", menu=file_menu)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="О программе", command=self._show_about)
        menu_bar.add_cascade(label="Помощь", menu=help_menu)

        self.root.config(menu=menu_bar)

    def _on_add(self):
        dlg = AddDocumentDialog(self.root, self.doc_ctrl)
        # После закрытия диалога обновляем список
        self.root.after(100, self.update_list)

    def _on_delete(self):
        tree = self.update_list.__self__.documents_tree  # предполагаем, что update_list привязан к MainView
        sel = tree.selection()
        if not sel:
            return
        if messagebox.askyesno("Подтверждение", "Удалить документ?"):
            self.doc_ctrl.delete_document(sel[0])
            self.update_list()

    def _show_about(self):
        messagebox.showinfo("О программе", "Корпусный менеджер v1.2\nБГУИР, 2024")
