import mmap
import os
import shutil
import subprocess
import sys
import datetime

import posix_ipc
import psutil
import pyudev

from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTreeView,
    QAction, QMenu, QInputDialog, QMessageBox, QFileSystemModel, QVBoxLayout, QWidget, QAbstractItemView, QPushButton,
    QFileDialog, QLineEdit, QDialog, QListWidget, QListWidgetItem, QDockWidget, QSizePolicy
)
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QDir, QFileInfo, QMimeData, QUrl, QTimer


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

        self.actions = []

        self.module_shared_memory = posix_ipc.SharedMemory("/module_memory", posix_ipc.O_CREAT, size=256)
        self.module_mapped_memory = mmap.mmap(self.module_shared_memory.fd, self.module_shared_memory.size)

        self.memory_shared_memory = posix_ipc.SharedMemory("/memory", posix_ipc.O_CREAT, size=256)
        self.memory_mapped_memory = mmap.mmap(self.memory_shared_memory.fd, self.memory_shared_memory.size)

        self.process_shared_memory = posix_ipc.SharedMemory("/process_memory", posix_ipc.O_CREAT, size=256)
        self.process_mapped_memory = mmap.mmap(self.process_shared_memory.fd, self.process_shared_memory.size)

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

        self.task_menu = self.menu_bar.addMenu("Межпроцессорные взаимодействия")
        self.memory_action = QAction("Виртуальная память", self)
        self.memory_action.triggered.connect(self.show_memory_window)
        self.task_menu.addAction(self.memory_action)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_memory)
        self.timer.start(1000)

        self.module_action = QAction("Модули процессора", self)
        self.module_action.triggered.connect(self.show_module_window)
        self.task_menu.addAction(self.module_action)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_module)
        self.timer.start(1000)

        self.process_action = QAction("Пользовательские процессы", self)
        self.process_action.triggered.connect(self.show_process_window)
        self.task_menu.addAction(self.process_action)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_process)
        self.timer.start(1000)

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

        self.tree = TreeView()
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

        self.save_report_button = QPushButton("Сохранить отчет пользовательских программ", self)
        self.save_report_button.clicked.connect(self.save_report)
        self.statusBar().addPermanentWidget(self.save_report_button)

        self.open_custom_terminal_button = QPushButton("Открыть свой терминал", self)
        self.open_custom_terminal_button.clicked.connect(self.open_custom_terminal)
        self.statusBar().addPermanentWidget(self.open_custom_terminal_button)

        self.save_actions_buttons = QPushButton("Cохранить действия приложения", self)
        self.save_actions_buttons.clicked.connect(self.save_actions)
        self.statusBar().addPermanentWidget(self.save_actions_buttons)

        self.search_input = QLineEdit(self)
        self.search_input.returnPressed.connect(self.search)
        self.toolbar.addWidget(self.search_input)

        # Кнопка поиска
        self.search_button = QPushButton("Поиск", self)
        self.search_button.clicked.connect(self.search)
        self.toolbar.addWidget(self.search_button)

        self.search_results_list = QListWidget(self)
        self.search_results_list.itemDoubleClicked.connect(self.open_searched_item)
        self.search_results_list.hide()

        self.search_results_dock = QDockWidget("Результаты поиска", self)
        self.search_results_dock.setWidget(self.search_results_list)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.search_results_dock)
        self.search_results_dock.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.search_results_dock.hide()

        layout = QVBoxLayout()

        layout.addWidget(self.tree)

        central_widget = QWidget()
        central_widget.setLayout(layout)

        # Устанавливаем главный виджет в качестве центрального виджета окна
        self.setCentralWidget(central_widget)

        self.udev_context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.udev_context)
        self.monitor.filter_by(subsystem='block')
        self.observer = pyudev.MonitorObserver(self.monitor, self.handle_device_event)
        self.observer.start()

    def save_actions(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить отчет", "", "Текстовый файл (*.log)")
        if file_path:
            self.generate_actions(file_path)

    def generate_actions(self, file_path):
        with open(f"{file_path}", "w") as f:
            for action in self.actions:
                f.write(action + "\n")

    def open_custom_terminal(self):
        subprocess.Popen(["python3", "terminal.py"])
        self.actions.append(f"Открыт свой терминал - {datetime.datetime.now()}")
        print(self.actions)

    def handle_device_event(self, action, device):
        if action == 'add':
            device_path = device.device_node
            device_name = device.get('ID_FS_LABEL', os.path.basename(device_path))
            app_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if "sdb" not in device_name:
                device_directory = os.path.join(app_directory, device_name)
                os.makedirs(device_directory, exist_ok=True)
                QMessageBox.information(self, 'Подключено устройство', f"Устройство: {device_name} ({device_path})")
                self.actions.append(f"Добавлено устройство: {device_name} - {datetime.datetime.now()}")
                self.display_folders(device_directory)

        elif action == 'remove':
            device_path = device.device_node
            device_name = device.get('ID_FS_LABEL', os.path.basename(device_path))
            app_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if "sdb" not in device_name:
                device_directory = os.path.join(app_directory, device_name)
                shutil.rmtree(device_directory)
                self.actions.append(f"Удалено устройство: {device_name} - {datetime.datetime.now()}")

    def update_memory(self):
        memory_percent = psutil.virtual_memory().percent
        self.memory_mapped_memory.seek(0)
        self.memory_mapped_memory.write(str(memory_percent).encode('utf-8'))
        self.memory_mapped_memory.flush()

    def update_module(self):
        module_count = len(sys.modules)
        self.module_mapped_memory.seek(0)
        self.module_mapped_memory.write(str(module_count).encode('utf-8'))
        self.module_mapped_memory.flush()

    def update_process(self):
        process_count = sum(1 for _ in psutil.process_iter())
        self.process_mapped_memory.seek(0)
        self.process_mapped_memory.write(str(process_count).encode('utf-8'))
        self.process_mapped_memory.flush()

    def show_memory_window(self):
        self.actions.append(f"Открыто окно памяти компьютера - {datetime.datetime.now()}")
        subprocess.Popen([sys.executable, "memory_window.py"])

    def show_process_window(self):
        self.actions.append(f"Открыты пользовательские процессы - {datetime.datetime.now()}")
        subprocess.Popen([sys.executable, "process_window.py"])

    def show_module_window(self):
        self.actions.append(f"Открыты модули процессора - {datetime.datetime.now()}")
        subprocess.Popen([sys.executable, "module_window.py"])

    def __del__(self):
        self.memory_mapped_memory.close()
        self.memory_shared_memory.close_fd()

        self.process_mapped_memory.close()
        self.process_shared_memory.close_fd()

        self.module_mapped_memory.close()
        self.module_shared_memory.close_fd()

    def search(self):
        query = self.search_input.text()
        if query:
            results = self.find_files_and_folders(query)
            self.display_search_results(results)
            self.actions.append(f"Произведен поиск файла {query} - {datetime.datetime.now()}")

    def find_files_and_folders(self, query):
        import os
        results = []
        for root, dirs, files in os.walk(self.current_path):
            for name in files + dirs:
                if query.lower() in name.lower():
                    results.append(os.path.join(root, name))
        return results

    def display_search_results(self, results):
        self.search_results_list.clear()
        if results:
            self.search_results_dock.show()
            for result in results:
                item = QListWidgetItem(result)
                self.search_results_list.addItem(item)
        else:
            self.search_results_dock.hide()

    def open_searched_item(self, item):
        file_path = item.text()
        if os.path.isdir(file_path):
            self.current_path = file_path
            self.display_folders(file_path)

    def save_report(self):
        self.actions.append(f"Сохранен отчет пользовательских процессов - {datetime.datetime.now()}")
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить отчет", "", "Текстовый файл (*.txt)")
        if file_path:
            self.generate_report(file_path)

    def generate_report(self, file_path):
        with open(file_path, 'w') as file:
            file.write("Отчет о запущенных процессах во время работы 'Суперапп':\n\n")
            for process in self.get_running_processes():
                file.write(f"Имя процесса: {process.name()}, Время старта: {process.create_time()}\n")

    def get_running_processes(self):
        current_process = psutil.Process()
        children = current_process.children(recursive=True)
        return children + [current_process]

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
        self.actions.append(f"Открыта дериктория {path} - {datetime.datetime.now()}")
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
                self.actions.append(f"Cоздана папка {folder_name} - {datetime.datetime.now()}")
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
            self.actions.append(f"Удален файл {folder_name} - {datetime.datetime.now()}")

    def delete_forever(self, folder_name):
        confirm = QMessageBox.question(self, "Подтверждение", f"Вы уверены, что хотите навсегда удалить файл?",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            folder_path = os.path.join(self.current_path, folder_name)
            if folder_name in self.deleted_folders.keys():
                del self.deleted_folders[folder_name]
            shutil.rmtree(folder_path)
            self.display_folders(self.current_path)
            self.actions.append(f"Навсегда удален файл {folder_name} - {datetime.datetime.now()}")

    def restore_folder(self, folder_name):
        original_path = self.deleted_folders.get(folder_name)
        if original_path:
            folder_path = os.path.join(self.trash_path, folder_name)
            new_path = os.path.join(original_path, folder_name)
            shutil.move(folder_path, new_path)
            del self.deleted_folders[folder_name]
            self.display_folders(self.current_path)
            self.actions.append(f"Восстановлен файл {folder_name} - {datetime.datetime.now()}")

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
            self.actions.append(f"Очищена корзина - {datetime.datetime.now()}")

    def rename_folder(self, folder_name):
        new_name, ok = QInputDialog.getText(self, "Переименовать папку",
                                            f"Введите новое имя для папки '{folder_name}':")
        if ok and new_name:
            old_path = os.path.join(self.current_path, folder_name)
            new_path = os.path.join(self.current_path, new_name)
            os.rename(old_path, new_path)
            self.display_folders(self.current_path)
            self.actions.append(f"Папка {folder_name} переименована в {new_name} - {datetime.datetime.now()}")

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
        if folder_name == "Корзина":
            for f in os.scandir(folder_path):
                if f.name not in self.deleted_folders.keys():
                    self.deleted_folders[f.name] = os.path.dirname(os.getcwd())
                    print(f.name)
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
        self.actions.append(f"Открыты свойства папки {folder_name} - {datetime.datetime.now()}")
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
        self.actions.append(f"Папка {folder_name} cкопирована - {datetime.datetime.now()}")
        QMessageBox.information(self, "Папка скопирована", f"Папка '{folder_name}' скопирована и готова к вставке.")

    def paste_folder(self):
        if self.copied_folder_path:
            destination_path = self.current_path
            try:
                shutil.copytree(self.copied_folder_path,
                                os.path.join(destination_path, os.path.basename(self.copied_folder_path)))
                self.actions.append(f"Папка {self.copied_folder_path} вставлена - {datetime.datetime.now()}")
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


class TreeView(QTreeView):
    def __init__(self):
        super().__init__()
        self.dragged_item = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos())
            if index.isValid():
                source_index = self.model().mapToSource(index)
                self.dragged_item = self.model().sourceModel().filePath(source_index)
                last_folder_name = os.path.basename(self.dragged_item)
                if last_folder_name.lower() == "корзина" or last_folder_name.lower() == "system":
                    self.dragged_item = None
                else:
                    print(f"File being dragged: {self.dragged_item}")
        super().mousePressEvent(event)

    def startDrag(self, supportedActions):
        if self.dragged_item:
            drag = QDrag(self)
            mime_data = QMimeData()
            urls = [QUrl.fromLocalFile(self.dragged_item)]
            mime_data.setUrls(urls)
            drag.setMimeData(mime_data)
            drag.exec_(Qt.CopyAction | Qt.MoveAction)


if __name__ == "__main__":
    app = QApplication([])
    window = SuperApp()
    window.show()
    app.exec_()
