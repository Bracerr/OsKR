import os
import shutil
import subprocess

from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTreeView,
    QAction, QMenu, QInputDialog, QMessageBox, QFileSystemModel, QVBoxLayout, QWidget, QAbstractItemView
)
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QDir, QFileInfo, QMimeData, QUrl


def create_folders(folders):
    for folder_name in folders:
        executable_path = os.path.dirname(os.path.abspath(__file__))
        parent_path = os.path.dirname(executable_path)
        folder_path = os.path.join(parent_path, folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)


def open_system_settings():
    subprocess.Popen(['gnome-control-center'])


def open_resource_monitor():
    subprocess.Popen(['gnome-system-monitor'])


def open_terminal():
    subprocess.Popen(['gnome-terminal'])


class SuperApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Суперапп")
        self.resize(1920, 1080)
        create_folders(["Корзина"])
        self.current_path = os.path.dirname(os.getcwd())
        self.trash_path = os.path.join(os.path.dirname(os.getcwd()), "Корзина")
        self.deleted_folders = {}
        self.copied_folder_path = None

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

        self.menu_bar.addAction("Открыть терминал", open_terminal)
        self.menu_bar.addAction("Настройки системы", open_system_settings)
        self.menu_bar.addAction("Монитор ресурсов", open_resource_monitor)

        self.tree.setSelectionMode(self.tree.SingleSelection)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.model.setReadOnly(False)

        self.setAcceptDrops(True)

        layout = QVBoxLayout()

        # Добавляем дерево в макет
        layout.addWidget(self.tree)

        # Создаем главный виджет, который будет содержать наши виджеты
        central_widget = QWidget()
        central_widget.setLayout(layout)

        # Устанавливаем главный виджет в качестве центрального виджета окна
        self.setCentralWidget(central_widget)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def startDrag(self, event):
        drag = QDrag(self)
        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(file_path) for file_path in self.selected_files]
        mime_data.setUrls(urls)
        drag.setMimeData(mime_data)

        drop_action = drag.exec_(Qt.CopyAction | Qt.MoveAction)

    def mousePressEvent(self, event):
        index = self.tree.indexAt(event.pos())
        if not index.isValid():
            return

        if event.button() == Qt.LeftButton:
            self.selected_files = []
            self.selected_files.append(self.proxy_model.data(index, Qt.DisplayRole))
            self.startDrag(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                path = url.toLocalFile()
                if os.path.isdir(path):
                    destination_path = self.current_path
                    try:
                        shutil.move(path, destination_path)
                    except Exception as e:
                        QMessageBox.warning(self, "Ошибка перемещения", f"Не удалось переместить папку: {str(e)}")
                    self.display_folders(self.current_path)
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        modifiers = QApplication.keyboardModifiers()
        if event.key() == Qt.Key_C and modifiers == Qt.ControlModifier:
            index = self.tree.currentIndex()
            folder_name = self.proxy_model.data(index, Qt.DisplayRole)
            self.copy_folder(folder_name)
        elif event.key() == Qt.Key_V and modifiers == Qt.ControlModifier:
            self.paste_folder()
        elif event.key() == Qt.Key_Backspace:
            self.go_back()
        elif event.key() == Qt.Key_F1:
            self.about()
        elif event.key() == Qt.Key_O and modifiers == Qt.ControlModifier:
            self.create_folder()
        elif event.key() == Qt.Key_Delete:
            index = self.tree.currentIndex()
            folder_name = self.proxy_model.data(index, Qt.DisplayRole)
            self.delete_folder(folder_name)

        super().keyPressEvent(event)

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
        if os.path.basename(self.current_path) != "SYSTEM":
            folder_name, ok = QInputDialog.getText(self, "Создать папку", "Введите название папки:")
            if ok and folder_name:
                folder_path = os.path.join(self.current_path, folder_name)
                os.mkdir(folder_path)
                self.display_folders(self.current_path)
        else:
            QMessageBox.warning(self, "Предупреждение", "Внутри папки SYSTEM нельзя создавать папки.")

    def delete_folder(self, folder_name):
        if folder_name == "SYSTEM" or folder_name == "Корзина":
            QMessageBox.warning(self, "Недоступно к удалению", "Данная папка недоступна к удалению.")
            return
        confirm = QMessageBox.question(self, "Подтверждение",
                                       f"Вы уверены, что хотите переместить папку '{folder_name}' в корзину?",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            folder_path = os.path.join(self.current_path, folder_name)
            shutil.move(folder_path, self.trash_path)
            self.deleted_folders[folder_name] = os.path.dirname(folder_path)
            self.display_folders(self.current_path)

    def delete_forever(self, folder_name):
        confirm = QMessageBox.question(self, "Подтверждение", f"Вы уверены, что хотите навсегда удалить файл?",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            folder_path = os.path.join(self.current_path, folder_name)
            if folder_name in self.deleted_folders.keys():
                del self.deleted_folders[folder_name]
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
        confirm = QMessageBox.question(self, "Подтверждение", "Вы уверены, что хотите очистить корзину?",
                                       QMessageBox.Yes | QMessageBox.No)
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
        new_name, ok = QInputDialog.getText(self, "Переименовать папку",
                                            f"Введите новое имя для папки '{folder_name}':")
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
                menu.addAction("Удалить навсегда", lambda: self.delete_forever(folder_name))
                menu.exec_(self.mapToGlobal(position))
            else:
                menu = QMenu(self)
                menu.addAction("Открыть", lambda: self.open_folder(index))
                menu.addAction("Переименовать", lambda: self.rename_folder(folder_name))
                menu.addAction("Копировать", lambda: self.copy_folder(folder_name))
                menu.addAction("Удалить", lambda: self.delete_folder(folder_name))
                menu.addAction("Удалить навсегда", lambda: self.delete_forever(folder_name))
                menu.addAction("Свойства", lambda: self.show_properties(folder_name))
                menu.exec_(self.mapToGlobal(position))
        else:
            menu = QMenu(self)
            menu.addAction("Создать папку", self.create_folder)
            menu.addAction("Вставить", self.paste_folder)
            menu.exec_(self.mapToGlobal(position))

    def open_folder(self, index=None):
        if index is None:
            index = self.tree.currentIndex()
        folder_name = self.proxy_model.data(index, Qt.DisplayRole)
        folder_path = os.path.join(self.current_path, folder_name)
        self.current_path = folder_path
        self.display_folders(folder_path)

    def about(self):
        hotkeys_info = (
            "Горячие клавиши:\n"
            "Ctrl+C - Копировать\n"
            "Ctrl+V - Вставить\n"
            "Delete - Перенести в корзину\n"
            "Backspace - Назад\n"
            "F1 - Открыть справку\n"
            "Ctrl+O - Создать папку в текущей директории\n"
        )
        QMessageBox.information(self, "О программе",
                                "Операционные системы и оболочки: Linux, Ubuntu\n"
                                "Язык программирования: Python\n"
                                "ФИО: Киргизов  Андрей Геннадьевич\n"
                                "Группа разработчика: При-23\n\n"
                                + hotkeys_info)

    def show_properties(self, folder_name):
        folder_path = os.path.join(self.current_path, folder_name)
        folder_info = QFileInfo(folder_path)
        properties = {
            "Название": folder_name,
            "Тип": "Папка" if folder_info.isDir() else "Файл",
            "Содержимое": self.get_content_info(folder_path),
            "Путь": folder_path,
            "Дата изменения": folder_info.lastModified().toString(Qt.ISODate),
            "Дата создания": folder_info.created().toString(Qt.ISODate)
        }
        properties_text = "\n".join([f"{key}: {value}" for key, value in properties.items()])
        QMessageBox.information(self, "Свойства папки", properties_text)

    def get_content_info(self, folder_path):
        content = os.listdir(folder_path)
        num_files = sum(os.path.isfile(os.path.join(folder_path, item)) for item in content)
        total_size = sum(os.path.getsize(os.path.join(folder_path, item)) for item in content if
                         os.path.isfile(os.path.join(folder_path, item)))
        return f"Файлов: {num_files}, Размер: {total_size} байт"

    def copy_folder(self, folder_name):
        folder_path = os.path.join(self.current_path, folder_name)
        self.copied_folder_path = folder_path
        QMessageBox.information(self, "Папка скопирована", f"Папка '{folder_name}' скопирована и готова к вставке.")

    def paste_folder(self):
        if self.copied_folder_path:
            destination_path = self.current_path
            try:
                shutil.copytree(self.copied_folder_path,
                                os.path.join(destination_path, os.path.basename(self.copied_folder_path)))
                QMessageBox.information(self, "Папка вставлена", "Папка успешно вставлена.")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка вставки", f"Не удалось вставить папку: {str(e)}")


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

