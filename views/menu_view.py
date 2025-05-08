import tkinter as tk
from tkinter import messagebox
from views.dialogs import AddDocumentDialog
from views.report_view import ReportWindow
from tkinter import filedialog, messagebox
from utils.xml_utils import (
    import_database_from_xml,
    export_database_to_xml,
    export_document_to_xml
)
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

        report_menu = tk.Menu(menu_bar, tearoff=0)
        report_menu.add_command(label="Статистика обработки", command=self._show_report)
        menu_bar.add_cascade(label="Отчеты", menu=report_menu)

        file_menu.add_separator()
        file_menu.add_command(
            label="Импорт из XML…",
            command=self._on_import_xml
        )
        file_menu.add_command(
            label="Экспорт базы в XML…",
            command=self._on_export_xml
        )
        file_menu.add_command(
            label="Экспорт документа в XML…",
            command=self._on_export_document_xml
        )


        self.root.config(menu=menu_bar)


    def _show_report(self):
        stats = self.doc_ctrl.db.get_processing_stats()
        if not stats:
            tk.messagebox.showinfo("Информация", "Нет данных для отображения")
            return
        ReportWindow(self.root, stats)

    def _on_add(self):
        dlg = AddDocumentDialog(self.root, self.doc_ctrl)
        # После закрытия диалога обновляем список
        self.root.after(100, self.update_list)

    def _on_delete(self):
        tree = self.update_list.__self__.doc_list.tree
        sel = tree.selection()
        if not sel:
            return
        if messagebox.askyesno("Подтверждение", "Удалить документ?"):
            self.doc_ctrl.delete_document(sel[0])
            self.update_list()

    def _show_about(self):
        messagebox.showinfo("О программе", "Корпусный менеджер v1.2\nБГУИР, 2024")

    def _on_import_xml(self):
        path = filedialog.askopenfilename(
            title="Выберите XML для импорта",
            filetypes=[("XML-файлы", "*.xml")]
        )
        if not path:
            return
        try:
            import_database_from_xml(self.doc_ctrl.db, path)
            self.update_list()
            messagebox.showinfo("Импорт", "Импорт успешно завершён")
        except Exception as e:
            messagebox.showerror("Ошибка импорта", str(e))

    def _on_export_xml(self):
        path = filedialog.asksaveasfilename(
            title="Сохранить полную базу в XML",
            defaultextension=".xml",
            filetypes=[("XML-файлы", "*.xml")]
        )
        if not path:
            return
        try:
            export_database_to_xml(self.doc_ctrl.db, path)
            messagebox.showinfo("Экспорт", "База успешно экспортирована")
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))

    def _on_export_document_xml(self):
        # Получаем выбранный документ
        tree = self.update_list.__self__.doc_list.tree
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Экспорт", "Сначала выберите документ")
            return
        doc_id = sel[0]
        path = filedialog.asksaveasfilename(
            title="Сохранить документ в XML",
            defaultextension=".xml",
            filetypes=[("XML-файлы", "*.xml")]
        )
        if not path:
            return
        try:
            export_document_to_xml(self.doc_ctrl.db, int(doc_id), path)
            messagebox.showinfo("Экспорт", "Документ успешно экспортирован")
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))

