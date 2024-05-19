import mmap
import re
import sys

import posix_ipc
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton, QMessageBox


class ModuleWindow(QWidget):
    def __init__(self, module_shared_memory):
        super().__init__()

        self.setWindowTitle("Окно модулей")
        self.setGeometry(400, 100, 300, 200)

        self.module_mapped_memory = mmap.mmap(module_shared_memory.fd, module_shared_memory.size)

        self.save_button = QPushButton("Сохранить в файл", self)
        self.save_button.clicked.connect(self.save_to_file)

        self.module_label = QLabel(self)
        self.update_module_data()
        layout = QVBoxLayout()
        layout.addWidget(self.module_label)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_module_data)
        self.timer.start(1000)

    def update_module_data(self):
        self.module_mapped_memory.seek(0)
        module_data = self.module_mapped_memory.read().decode('utf-8')
        self.module_label.setText(f"Количество модулей: {module_data}")

    def save_to_file(self):
        try:
            with open("moduleLog.txt", "a") as file:
                data = self.module_label.text()
                numbers = re.findall(r'\d+\.\d+|\d+', data)[0]
                file.write(f"Модули процессора: {numbers}\n")
                QMessageBox.information(self, "Сохранение", "Данные успешно сохранены в файл moduleLog.txt")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении данных в файл: {str(e)}")

if __name__ == "__main__":
    module_shared_memory = posix_ipc.SharedMemory("/module_memory")
    app = QApplication([])
    module_window = ModuleWindow(module_shared_memory)
    module_window.show()
    app.exec_()
