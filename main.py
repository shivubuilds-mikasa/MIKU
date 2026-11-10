import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QLockFile
from miku.config import DATA
from miku.ui import MikuWindow

app = QApplication(sys.argv)
app.setApplicationName("Miku")
lock = QLockFile(str(DATA / "miku.lock"))
if not lock.tryLock(100):
    sys.exit(0)
window = MikuWindow()
window.show()
sys.exit(app.exec())
