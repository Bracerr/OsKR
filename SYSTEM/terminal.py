import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget
from PyQt5.QtGui import QColor, QFont

class TerminalEmulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('PyQt5 Terminal Emulator')

        self.textEdit = QTextEdit(self)
        self.textEdit.setStyleSheet("background-color: black; color: white;")
        self.textEdit.setFont(QFont('Courier', 10))

        self.textEdit.setAcceptRichText(False)
        self.textEdit.setPlainText("$ ")
        self.textEdit.textChanged.connect(self.onTextChanged)

        layout = QVBoxLayout()
        layout.addWidget(self.textEdit)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def onTextChanged(self):
        if self.textEdit.toPlainText().endswith('\n'):
            self.textEdit.textChanged.disconnect(self.onTextChanged)  # Отключение обработчика сигналов
            command = self.textEdit.toPlainText().strip().split('\n')[-1][2:]
            self.executeCommand(command)
            self.textEdit.append("$ ")
            self.textEdit.textChanged.connect(self.onTextChanged)  # Включение обработчика сигналов

    def executeCommand(self, command):
        output = ""
        parts = command.split()
        if not parts:
            return

        cmd, args = parts[0], parts[1:]

        if cmd == "ls":
            output = self.ls()
        elif cmd == "pwd":
            output = self.pwd()
        elif cmd == "cd":
            if args:
                output = self.cd(args[0])
            else:
                output = "cd: missing argument"
        elif cmd == "cat":
            if args:
                output = self.cat(args[0])
            else:
                output = "cat: missing argument"
        elif cmd == "touch":
            if args:
                output = self.touch(args[0])
            else:
                output = "touch: missing argument"
        elif cmd == "mkdir":
            if args:
                output = self.mkdir(args[0])
            else:
                output = "mkdir: missing argument"
        elif cmd == "rmdir":
            if args:
                output = self.rmdir(args[0])
            else:
                output = "rmdir: missing argument"
        elif cmd == "rm":
            if args:
                output = self.rm(args[0])
            else:
                output = "rm: missing argument"
        elif cmd == "ping":
            if args:
                output = self.ping(args[0])
            else:
                output = "ping: missing argument"
        elif cmd == "ifconfig":
            output = self.ifconfig()
        elif cmd == "help":
            output = self.help()
        elif cmd == "clear":
            output = self.clear()
        else:
            output = f"{cmd}: command not found"

        self.textEdit.append(output)

    def ls(self):
        import os
        return "\n".join(os.listdir('.'))

    def pwd(self):
        import os
        return os.getcwd()

    def cd(self, path):
        import os
        try:
            os.chdir(path)
            return ""
        except Exception as e:
            return str(e)

    def cat(self, filename):
        try:
            with open(filename, 'r') as f:
                return f.read()
        except Exception as e:
            return str(e)

    def touch(self, filename):
        import os
        try:
            with open(filename, 'a'):
                os.utime(filename, None)
            return ""
        except Exception as e:
            return str(e)

    def mkdir(self, dirname):
        import os
        try:
            os.mkdir(dirname)
            return ""
        except Exception as e:
            return str(e)

    def rmdir(self, dirname):
        import os
        try:
            os.rmdir(dirname)
            return ""
        except Exception as e:
            return str(e)

    def rm(self, filename):
        import os
        try:
            os.remove(filename)
            return ""
        except Exception as e:
            return str(e)

    def ping(self, hostname):
        import socket
        try:
            host_ip = socket.gethostbyname(hostname)
            return f"Ping to {hostname} [{host_ip}] successful"
        except Exception as e:
            return str(e)

    def ifconfig(self):
        import socket
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        return f"Hostname: {hostname}\nIP Address: {ip_address}"

    def clear(self):
        self.textEdit.clear()
        return ""

    def help(self):
        return (
            "Available commands:\n"
            "  ls         - List directory contents\n"
            "  pwd        - Print working directory\n"
            "  cd <path>  - Change directory\n"
            "  cat <file> - Concatenate and display file\n"
            "  touch <file> - Change file timestamps or create empty file\n"
            "  mkdir <dir> - Make directories\n"
            "  rmdir <dir> - Remove empty directories\n"
            "  rm <file>  - Remove file\n"
            "  ping <host> - Ping host\n"
            "  ifconfig  - Display network configuration\n"
            "  clear     - Clear the terminal\n"
            "  help      - Display this help message\n"
        )

if __name__ == '__main__':
    app = QApplication(sys.argv)
    terminal = TerminalEmulator()
    terminal.resize(800, 600)
    terminal.show()
    sys.exit(app.exec_())
