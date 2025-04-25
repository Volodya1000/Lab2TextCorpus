import tkinter as tk
from controllers.document_controller import DocumentController
from controllers.search_controller import SearchController
from models.database import Database
from models.nlp_processor import NLPProcessor
from views.main_view import MainView

def main():
    root = tk.Tk()
    db = Database()
    nlp = NLPProcessor()
    doc_controller = DocumentController(db, nlp)
    search_controller = SearchController(db)
    MainView(root, doc_controller, search_controller)
    root.mainloop()

if __name__ == "__main__":
    main()