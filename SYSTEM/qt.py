import os
import shutil
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTreeView,
    QAction, QMenu, QInputDialog, QMessageBox, QFileSystemModel
)
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QDir

class SuperApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Суперапп")
        self.create_folders(["Корзина"])
        self.current_path = os.path.dirname(os.getcwd())
        self.trash_path = os.path.join(os.path.dirname(os.getcwd()), "Корзина")
        self.deleted_folders = {}

        self.load_deleted_folders()

        # Меню
        self.menu_bar = self.menuBar()
        self.help_menu = self.menu_bar.addMenu("Помощь")
        self.about_action = QAction("О программе", self)
        self.about_action.triggered.connect(self.about)
        self.help_menu.addAction(self.about_action)

        # Кнопка "Назад"
        self.back_action = QAction("Назад", self)
        self.back_action.triggered.connect(self.go_back)
        self.toolbar = self.addToolBar("Toolbar")
        self.toolbar.addAction(self.back_action)

        # Создание дерева для отображения папок
        self.model = CustomFileSystemModel(self)
        self.model.setRootPath("/")
        self.model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs)
        
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)

        self.tree = QTreeView(self)
        self.tree.setModel(self.proxy_model)
        self.tree.setRootIndex(self.proxy_model.mapFromSource(self.model.index(self.current_path)))
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 150)
        self.tree.setColumnWidth(2, 100)
        self.tree.setColumnWidth(3, 100)

        self.tree.setRootIsDecorated(False)

        self.setCentralWidget(self.tree)

        self.tree.doubleClicked.connect(self.open_folder)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_popup)

    def create_folders(self, folders):    
        for folder_name in folders:
            executable_path = os.path.dirname(os.path.abspath(__file__))
            parent_path = os.path.dirname(executable_path)
            folder_path = os.path.join(parent_path, folder_name)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

    def load_deleted_folders(self):
        if os.path.exists('deleted_folders.txt'):
            with open('deleted_folders.txt', 'r') as f:
                content = f.read()
                self.deleted_folders = eval(content)
        else:
            self.deleted_folders = {}

    def save_deleted_folders(self):
        with open('deleted_folders.txt', 'w') as f:
            f.write(str(self.deleted_folders))

    def closeEvent(self, event):
        self.save_deleted_folders()  # сохраняем deleted_folders при закрытии приложения
        event.accept()

    def display_folders(self, path):
        current_column_hidden = self.tree.isColumnHidden(1) 
        
        self.model.setRootPath(path)
        self.tree.setRootIndex(self.proxy_model.mapFromSource(self.model.index(path)))
        
        self.tree.setColumnHidden(1, current_column_hidden)  # Восстанавливаем состояние столбца 'Тип'

    def go_back(self):
        parent_path = os.path.dirname(self.current_path)
        if parent_path != self.current_path:
            self.current_path = parent_path
            self.display_folders(parent_path)

    def create_folder(self):
        folder_name, ok = QInputDialog.getText(self, "Создать папку", "Введите название папки:")
        if ok and folder_name:
            folder_path = os.path.join(self.current_path, folder_name)
            os.mkdir(folder_path)
            self.display_folders(self.current_path)

    def delete_folder(self, folder_name):
        confirm = QMessageBox.question(self, "Подтверждение", f"Вы уверены, что хотите переместить папку '{folder_name}' в корзину?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            folder_path = os.path.join(self.current_path, folder_name)
            shutil.move(folder_path, self.trash_path)
            self.deleted_folders[folder_name] = os.path.dirname(folder_path)
            self.display_folders(self.current_path)

    def delete_forever(self, folder_name):
        confirm = QMessageBox.question(self, "Подтверждение", f"Вы уверены, что хотите навсегда удалить файл?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            folder_path = os.path.join(self.current_path, folder_name)
            shutil.rmtree(folder_path)
            self.display_folders(self.current_path)

    def restore_folder(self, folder_name):
        original_path = self.deleted_folders.get(folder_name)
        if original_path:
            folder_path = os.path.join(self.trash_path, folder_name)
            new_path = os.path.join(original_path, folder_name)
            shutil.move(folder_path, new_path)
            del self.deleted_folders[folder_name]
            self.display_folders(self.current_path)

    def clear_recycle_bin(self):
        confirm = QMessageBox.question(self, "Подтверждение", "Вы уверены, что хотите очистить корзину?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            for item in os.listdir(self.trash_path):
                item_path = os.path.join(self.trash_path, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            self.deleted_folders.clear()
            self.display_folders(self.current_path)


    def rename_folder(self, folder_name):
        new_name, ok = QInputDialog.getText(self, "Переименовать папку", f"Введите новое имя для папки '{folder_name}':")
        if ok and new_name:
            old_path = os.path.join(self.current_path, folder_name)
            new_path = os.path.join(self.current_path, new_name)
            os.rename(old_path, new_path)
            self.display_folders(self.current_path)

    def show_popup(self, position):
        index = self.tree.indexAt(position)
        if index.isValid():
            folder_name = self.proxy_model.data(index, Qt.DisplayRole)
            if folder_name == "SYSTEM":
                menu = QMenu(self)
                menu.addAction("ПРИКОЛ", lambda: print("ПРИКОЛ"))
                menu.exec_(self.mapToGlobal(position))
            elif folder_name == "Корзина":
                menu = QMenu(self)
                menu.addAction("Очистить корзину", self.clear_recycle_bin)
                menu.exec_(self.mapToGlobal(position))
            elif folder_name in self.deleted_folders:
                menu = QMenu(self)
                menu.addAction("Восстановить", lambda: self.restore_folder(folder_name))
                menu.exec_(self.mapToGlobal(position))
            else:
                menu = QMenu(self)
                menu.addAction("Удалить", lambda: self.delete_folder(folder_name))
                menu.addAction("Переименовать", lambda: self.rename_folder(folder_name))
                menu.addAction("Удалить навсегда", lambda: self.delete_forever(folder_name))
                menu.exec_(self.mapToGlobal(position))
        else:
            menu = QMenu(self)
            menu.addAction("Создать папку", self.create_folder)
            menu.exec_(self.mapToGlobal(position))

    def open_folder(self, index):
        if index.row() == 0:
            self.tree.setExpanded(index, False)
        folder_name = self.proxy_model.data(index, Qt.DisplayRole)
        folder_path = os.path.join(self.current_path, folder_name)
        self.current_path = folder_path
        self.display_folders(folder_path)

    def about(self):
        QMessageBox.information(self, "О программе", 
                                "Операционные системы и оболочки: Windows, Linux\n"
                                "Язык программирования: Python\n"
                                "ФИО: Иванов Иван Иванович\n"
                                "Группа разработчика: Группа 1")
        

class CustomFileSystemModel(QFileSystemModel):
    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and index.column() == 1:
            path = self.filePath(index)
            if path and os.path.isdir(path):
                return str(len(os.listdir(path)))
        return super().data(index, role)

if __name__ == "__main__":
    app = QApplication([])
    window = SuperApp()
    window.show()
    app.exec_()
