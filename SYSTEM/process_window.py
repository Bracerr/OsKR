import mmap
import re
import sys

import posix_ipc
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton, QMessageBox


class ProcessWindow(QWidget):
    def __init__(self, process_shared_memory):
        super().__init__()

        self.setWindowTitle("Окно процессов")
        self.setGeometry(400, 100, 300, 200)

        self.process_mapped_memory = mmap.mmap(process_shared_memory.fd, process_shared_memory.size)

        self.save_button = QPushButton("Сохранить в файл", self)
        self.save_button.clicked.connect(self.save_to_file)

        self.process_label = QLabel()
        self.update_process_data()
        layout = QVBoxLayout()
        layout.addWidget(self.process_label)
        layout.addWidget(self.save_button)

        self.setLayout(layout)


        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_process_data)
        self.timer.start(1000)

    def update_process_data(self):
            self.process_mapped_memory.seek(0)
            process_data = self.process_mapped_memory.read().decode('utf-8')
            self.process_label.setText(f"Количество процессов: {process_data}")

    def save_to_file(self):
        try:
            with open("processLog.txt", "a") as file:
                data = self.process_label.text()
                numbers = re.findall(r'\d+\.\d+|\d+', data)[0]
                file.write(f"Процессы пользователя: {numbers}\n")
                QMessageBox.information(self, "Сохранение", "Данные успешно сохранены в файл processLog.txt")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении данных в файл: {str(e)}")

if __name__ == "__main__":
    process_shared_memory = posix_ipc.SharedMemory("/process_memory")
    app = QApplication([])
    process_window = ProcessWindow(process_shared_memory)
    process_window.show()
    app.exec_()
