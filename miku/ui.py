import base64
import html
import subprocess
import threading

import psutil
import requests
import sounddevice as sd
from faster_whisper import WhisperModel
from PySide6.QtCore import QTimer, Signal, QObject, Qt, QSettings
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QSizePolicy,
    QTextBrowser, QVBoxLayout, QWidget,
)

from .agent import Agent
from .config import DEFAULT_MODEL, MODELS
from .memory import history


STYLE = """
* { font-family: Segoe UI; }
QMainWindow, QWidget#root { background:#212123; color:#ececf1; }
QFrame#sidebar { background:#171719; border-right:1px solid #303034; }
QLabel#brand { color:#f5f5f7; font-size:19px; font-weight:650; }
QLabel#brandMark { color:#f5f5f7; background:#343439; border-radius:12px; font-size:17px; font-weight:700; }
QLabel#section { color:#92929b; font-size:12px; font-weight:600; padding:7px 8px 2px; }
QLabel#caption, QLabel#stats { color:#92929b; font-size:11px; }
QLabel#status { color:#a5d6a7; font-size:12px; }
QListWidget { background:transparent; border:0; outline:0; color:#c9c9cf; font-size:13px; }
QListWidget::item { padding:10px 9px; border-radius:8px; }
QListWidget::item:hover { background:#29292d; }
QListWidget::item:selected { background:#303035; color:#fff; }
QPushButton { background:transparent; color:#dedee4; border:1px solid transparent; border-radius:9px; padding:9px 11px; text-align:left; }
QPushButton:hover { background:#2c2c30; }
QPushButton#newChat { background:#2b2b30; border-color:#3b3b41; color:#f1f1f3; font-weight:600; }
QPushButton#newChat:hover { background:#38383e; }
QPushButton#send { background:#f1f1f3; color:#202024; border-radius:17px; font-size:17px; font-weight:700; padding:5px 12px; }
QPushButton#send:hover { background:#d6d6dc; }
QPushButton#icon { color:#c5c5cc; font-size:16px; padding:8px; min-width:35px; }
QPushButton:disabled { color:#707078; }
QComboBox { color:#d6d6dc; background:#2c2c30; border:1px solid #3a3a40; border-radius:8px; padding:7px 10px; min-width:120px; }
QComboBox QAbstractItemView { background:#2c2c30; color:#eee; selection-background-color:#44444b; border:1px solid #44444b; }
QTextBrowser#chat { background:transparent; border:0; color:#ececf1; font-size:14px; selection-background-color:#4b4b54; }
QFrame#composer { background:#303034; border:1px solid #414146; border-radius:19px; }
QFrame#composer:focus-within { border-color:#66666d; }
QLineEdit#prompt { background:transparent; border:0; color:#f2f2f4; font-size:14px; padding:9px 5px; selection-background-color:#55555d; }
QScrollBar:vertical { background:transparent; width:9px; margin:3px; }
QScrollBar::handle:vertical { background:#45454b; min-height:34px; border-radius:4px; }
QScrollBar::handle:vertical:hover { background:#5c5c64; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
"""


class Worker(QObject):
    update = Signal(str)
    done = Signal(str)
    failed = Signal(str)
    confirmation = Signal(str)

    def __init__(self, model, prompt, context):
        super().__init__()
        self.model, self.prompt, self.context = model, prompt, context

    def ask_confirmation(self, message):
        from threading import Event
        self._approved = False
        self._decision = Event()
        self.confirmation.emit(message)
        self._decision.wait(300)
        return self._approved

    def decide(self, approved):
        self._approved = approved
        self._decision.set()

    def run(self):
        try:
            answer = Agent(self.model).run(self.prompt, self.update.emit, self.ask_confirmation, self.context)
            self.done.emit(answer)
        except Exception as exc:
            self.failed.emit(str(exc))


class MikuWindow(QMainWindow):
    voice_text = Signal(str)
    voice_error = Signal(str)
    voice_ready = Signal()
    status_updated = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Miku")
        self.setMinimumSize(920, 640)
        self.resize(1180, 790)
        self.setStyleSheet(STYLE)
        self.last_answer = ""
        self.speech_proc = None
        self.worker = None
        self.is_busy = False
        self.pending_prompts = []
        self.conversation = history(18)
        self.pending_prompt = ""

        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self._build_sidebar(shell)
        self._build_main(shell)

        self.voice_text.connect(self.input.setText)
        self.voice_error.connect(lambda text: self.error("Voice input: " + text))
        self.voice_ready.connect(self._voice_ready)
        self.status_updated.connect(self.apply_status)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(6000)
        self.refresh_status()
        self.restore_history()
        QTimer.singleShot(0, self.input.setFocus)

    def _build_sidebar(self, shell):
        sidebar = QFrame(objectName="sidebar")
        sidebar.setFixedWidth(250)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(15, 18, 13, 14)
        layout.setSpacing(9)

        brand_row = QHBoxLayout()
        mark = QLabel("M", objectName="brandMark", alignment=Qt.AlignmentFlag.AlignCenter)
        mark.setFixedSize(34, 34)
        brand = QLabel("Miku", objectName="brand")
        brand_row.addWidget(mark)
        brand_row.addSpacing(3)
        brand_row.addWidget(brand)
        brand_row.addStretch()
        layout.addLayout(brand_row)

        new = QPushButton("＋   New chat", objectName="newChat")
        new.setToolTip("Start a fresh conversation view")
        new.clicked.connect(self.new_chat)
        layout.addSpacing(9)
        layout.addWidget(new)

        section = QLabel("RECENT", objectName="section")
        layout.addWidget(section)
        self.recent = QListWidget()
        self.recent.setSpacing(2)
        self.recent.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.recent.itemClicked.connect(self.reopen_recent)
        layout.addWidget(self.recent, 1)

        footer = QVBoxLayout()
        self.sidebar_status = QLabel("●  Local Ollama", objectName="caption")
        footer.addWidget(self.sidebar_status)
        shortcut = QLabel("Ctrl + J  ·  Open Miku", objectName="caption")
        footer.addWidget(shortcut)
        layout.addLayout(footer)
        shell.addWidget(sidebar)

    def _build_main(self, shell):
        main = QWidget()
        layout = QVBoxLayout(main)
        layout.setContentsMargins(30, 16, 30, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Miku")
        title.setStyleSheet("font-size:16px;font-weight:600;color:#ececf1")
        header.addWidget(title)
        self.status = QLabel("● Connecting…", objectName="status")
        header.addWidget(self.status)
        header.addStretch()
        self.models = QComboBox()
        self.models.addItems(MODELS)
        self.settings = QSettings("Miku", "Miku")
        self.models.setCurrentText(self.settings.value("model", DEFAULT_MODEL))
        self.models.currentTextChanged.connect(lambda value: self.settings.setValue("model", value))
        self.models.setToolTip("Local Ollama model")
        header.addWidget(self.models)
        self.stats = QLabel("", objectName="stats")
        header.addWidget(self.stats)
        layout.addLayout(header)

        self.chat = QTextBrowser(objectName="chat")
        self.chat.setOpenExternalLinks(False)
        self.chat.setReadOnly(True)
        self.chat.setPlaceholderText("What can I help with?")
        layout.addWidget(self.chat, 1)

        composer_wrap = QHBoxLayout()
        composer_wrap.addStretch(1)
        self.composer = QFrame(objectName="composer")
        self.composer.setMaximumWidth(840)
        composer = QHBoxLayout(self.composer)
        composer.setContentsMargins(12, 5, 7, 5)
        composer.setSpacing(5)
        self.input = QLineEdit(objectName="prompt")
        self.input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.input.setPlaceholderText("Message Miku")
        self.input.returnPressed.connect(self.send)
        composer.addWidget(self.input, 1)
        self.voice_btn = QPushButton("🎙", objectName="icon")
        self.voice_btn.setToolTip("Push to talk · records 6 seconds locally")
        self.voice_btn.clicked.connect(self.voice_input)
        composer.addWidget(self.voice_btn)
        self.speak_btn = QPushButton("🔊", objectName="icon")
        self.speak_btn.setToolTip("Speak or stop the latest reply")
        self.speak_btn.clicked.connect(self.speak)
        composer.addWidget(self.speak_btn)
        self.send_btn = QPushButton("↑", objectName="send")
        self.send_btn.setToolTip("Send message")
        self.send_btn.clicked.connect(self.send)
        composer.addWidget(self.send_btn)
        composer_wrap.addWidget(self.composer, 6)
        composer_wrap.addStretch(1)
        layout.addLayout(composer_wrap)

        note = QLabel("Miku uses local Ollama. Replies and memory stay on this device.", objectName="caption", alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(note)
        shell.addWidget(main, 1)

    def refresh_status(self):
        if getattr(self, "_status_running", False):
            return
        self._status_running = True
        threading.Thread(target=self._collect_status, daemon=True).start()

    def _collect_status(self):
        status = {}
        try:
            tags = requests.get("http://localhost:11434/api/tags", timeout=1).json()["models"]
            available = {model["name"] for model in tags}
            status["available"] = available
        except Exception:
            status["available"] = None
        try:
            gpu = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).stdout.strip().split(",")
            gpu_text = f"GPU {gpu[0].strip()}% · VRAM {gpu[1].strip()}/{gpu[2].strip()} MB" if len(gpu) == 3 else "GPU unavailable"
            status["resources"] = f"RAM {psutil.virtual_memory().percent}% · {gpu_text}"
        except Exception:
            status["resources"] = f"RAM {psutil.virtual_memory().percent}%"
        self.status_updated.emit(status)

    def apply_status(self, status):
        self._status_running = False
        available = status.get("available")
        if available is None:
            self.status.setText("● Ollama offline")
            self.sidebar_status.setText("●  Ollama offline")
        else:
            connected = self.models.currentText() in available
            self.status.setText("● Ready" if connected else "● Model unavailable")
            self.sidebar_status.setText("●  Local Ollama connected")
        if self.is_busy:
            self.status.setText(f"● Working · {len(self.pending_prompts)} queued" if self.pending_prompts else "● Thinking…")
        self.stats.setText(status.get("resources", ""))
        if self.speech_proc and self.speech_proc.poll() is not None:
            self.speech_proc = None
            self.speak_btn.setText("🔊")

    def add_line(self, role, text, subtle=False):
        safe = html.escape(text).replace("\n", "<br>")
        if role == "user":
            body = f'<div style="margin:14px 0 6px 0;color:#c9c9cf"><b>You</b></div><div style="margin:0 0 20px 0;color:#f2f2f4">{safe}</div>'
        elif subtle:
            body = f'<div style="margin:6px 0;color:#9898a1;font-size:12px">{safe}</div>'
        else:
            body = f'<div style="margin:14px 0 6px 0;color:#f1f1f4"><b>Miku</b></div><div style="margin:0 0 20px 0;color:#ececf1;line-height:1.55">{safe}</div>'
        self.chat.append(body)
        bar = self.chat.verticalScrollBar()
        bar.setValue(bar.maximum())

    def restore_history(self):
        records = history(40)
        for item in records:
            self.add_line(item["role"], item["content"])
        prompts = [item["content"] for item in records if item["role"] == "user"]
        for prompt in reversed(prompts[-18:]):
            entry = QListWidgetItem(prompt.replace("\n", " ")[:52])
            entry.setToolTip(prompt)
            entry.setData(Qt.ItemDataRole.UserRole, prompt)
            self.recent.addItem(entry)

    def new_chat(self):
        if self.is_busy:
            return
        self.chat.clear()
        self.conversation = []
        self.add_line("assistant", "Hi, I’m Miku. What can I help with?")
        self.input.setFocus()

    def reopen_recent(self, item):
        self.input.setText(item.data(Qt.ItemDataRole.UserRole) or item.text())
        self.input.setFocus()

    def send(self):
        prompt = self.input.text().strip()
        if not prompt:
            return
        self.input.clear()
        if self.is_busy:
            self.pending_prompts.append(prompt)
            self.status.setText(f"● Working · {len(self.pending_prompts)} queued")
            return
        self._start_prompt(prompt)

    def _start_prompt(self, prompt):
        self.is_busy = True
        self.pending_prompt = prompt
        self.add_line("user", prompt)
        self.add_recent(prompt)
        context = self.conversation[-18:] + [{"role": "user", "content": prompt}]
        worker = Worker(self.models.currentText(), prompt, context)
        self.worker = worker
        worker.update.connect(lambda note: self.add_line("assistant", note, subtle=True))
        worker.confirmation.connect(lambda message, current=worker: self.confirm_action(current, message))
        worker.done.connect(self.finished)
        worker.failed.connect(self.error)
        self.status.setText("● Thinking…")
        threading.Thread(target=worker.run, daemon=True).start()

    def add_recent(self, prompt):
        item = QListWidgetItem(prompt.replace("\n", " ")[:52])
        item.setToolTip(prompt)
        item.setData(Qt.ItemDataRole.UserRole, prompt)
        self.recent.insertItem(0, item)
        while self.recent.count() > 18:
            self.recent.takeItem(self.recent.count() - 1)

    def confirm_action(self, worker, message):
        answer = QMessageBox.question(
            self, "Approve this Miku action", message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        worker.decide(answer == QMessageBox.StandardButton.Yes)

    def finished(self, answer):
        self.last_answer = answer
        self.conversation.extend([
            {"role": "user", "content": self.pending_prompt},
            {"role": "assistant", "content": answer},
        ])
        self.conversation = self.conversation[-18:]
        self.add_line("assistant", answer)
        self.input.setFocus()
        self._continue_queue()

    def error(self, message):
        self.add_line("assistant", "I hit a problem: " + message)
        if self.is_busy:
            self.is_busy = False
            self._continue_queue()

    def _continue_queue(self):
        self.is_busy = False
        if self.pending_prompts:
            next_prompt = self.pending_prompts.pop(0)
            self._start_prompt(next_prompt)
        else:
            self.status.setText("● Ready")

    def speak(self):
        if self.speech_proc and self.speech_proc.poll() is None:
            self.speech_proc.terminate()
            self.speech_proc = None
            self.speak_btn.setText("🔊")
            return
        if not self.last_answer:
            return
        encoded = base64.b64encode(self.last_answer.encode("utf-8")).decode("ascii")
        script = "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $t=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('" + encoded + "')); $s.Speak($t)"
        self.speech_proc = subprocess.Popen(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-EncodedCommand", base64.b64encode(script.encode("utf-16le")).decode("ascii")],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.speak_btn.setText("⏹")

    def voice_input(self):
        self.voice_btn.setText("…")
        self.voice_btn.setEnabled(False)

        def listen():
            try:
                audio = sd.rec(int(6 * 16000), samplerate=16000, channels=1, dtype="float32")
                sd.wait()
                model = WhisperModel("base", device="cpu", compute_type="int8")
                segments, _ = model.transcribe(audio[:, 0], language="en")
                self.voice_text.emit(" ".join(segment.text for segment in segments).strip())
            except Exception as exc:
                self.voice_error.emit(str(exc))
            finally:
                self.voice_ready.emit()

        threading.Thread(target=listen, daemon=True).start()

    def _voice_ready(self):
        self.voice_btn.setText("🎙")
        self.voice_btn.setEnabled(True)

    def closeEvent(self, event):
        if self.speech_proc and self.speech_proc.poll() is None:
            self.speech_proc.terminate()
        event.accept()
