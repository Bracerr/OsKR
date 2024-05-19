import mmap
import re

import posix_ipc
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton, QMessageBox
from PyQt5.QtCore import QTimer


class MemoryWindow(QWidget):
    def __init__(self, memory_shared_memory):
        super().__init__()

        self.setWindowTitle("Окно памяти")
        self.setGeometry(400, 100, 300, 200)

        self.memory_shared_memory = memory_shared_memory
        self.memory_mapped_memory = mmap.mmap(self.memory_shared_memory.fd, self.memory_shared_memory.size)

        self.memory_label = QLabel(self)
        self.update_memory_data()

        self.save_button = QPushButton("Сохранить в файл", self)
        self.save_button.clicked.connect(self.save_to_file)

        layout = QVBoxLayout()
        layout.addWidget(self.memory_label)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

        # Создаем таймер для обновления данных в реальном времени
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_memory_data)
        self.timer.start(1000)  # Обновлять данные каждую секунду

    def update_memory_data(self):
        self.memory_mapped_memory.seek(0)
        memory_data = self.memory_mapped_memory.read().decode('utf-8')
        self.memory_label.setText(f"Процент памяти: {memory_data}%")

    def save_to_file(self):
        try:
            with open("memoryLog.txt", "a") as file:
                data = self.memory_label.text()
                numbers = re.findall(r'\d+\.\d+|\d+', data)[0]
                file.write(f"Процент памяти на момент сохранения: {numbers}\n")
                QMessageBox.information(self, "Сохранение", "Данные успешно сохранены в файл memoryLog.txt")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении данных в файл: {str(e)}")


if __name__ == "__main__":
    memory_shared_memory = posix_ipc.SharedMemory("/memory")
    app = QApplication([])
    memory_window = MemoryWindow(memory_shared_memory)
    memory_window.show()
    app.exec_()
