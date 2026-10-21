"""Десктопное окно «Мониторинг конкурентов» — те же разделы, что у сайта."""

import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if not getattr(sys, "frozen", False) and str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap, QRadialGradient
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from backend.services.history_service import history_service
from backend.services.monitor_service import monitor_service
from tasks import AnalyzeWorker

TYPE_LABELS = {
    "text": "Текст",
    "image": "Изображение",
    "parse": "Сайт",
    "monitor": "Обход",
}

STYLE = """
QMainWindow, QWidget#root, QScrollArea, QWidget#page {
    background: transparent;
    color: #e8eefc;
    font-family: "Segoe UI";
    font-size: 14px;
}
QFrame#sidebar {
    background: rgba(10, 14, 28, 184);
    border-right: 1px solid #263049;
}
QLabel#logoTitle { font-size: 18px; font-weight: 700; color: #e8eefc; }
QLabel#logoSub, QLabel#note, QLabel#lead, QLabel#hint, QLabel#time, QLabel#empty {
    color: #93a0bd;
}
QLabel#note { font-size: 13px; }
QLabel#title { font-size: 28px; font-weight: 700; }
QLabel#section { font-size: 18px; font-weight: 650; }
QLabel#blockTitle { font-size: 16px; font-weight: 650; }
QLabel#tag { color: #3ee0c5; font-size: 13px; font-weight: 700; }
QLabel#score { color: #3ee0c5; font-size: 28px; font-weight: 700; }
QLabel#summary, QLabel#meta, QLabel#error {
    background: #0d1424;
    border-radius: 12px;
    padding: 12px;
}
QLabel#error { color: #ff8b8b; background: rgba(255, 139, 139, 0.08); }
QFrame#card, QFrame#historyRow {
    background: rgba(20, 27, 45, 235);
    border: 1px solid #263049;
    border-radius: 18px;
}
QFrame#historyRow {
    border-radius: 12px;
    background: #0d1424;
}
QFrame#mark {
    background: #3ee0c5;
    border-radius: 12px;
    min-width: 42px;
    max-width: 42px;
    min-height: 42px;
    max-height: 42px;
}
QLabel#markText { color: #04241e; font-size: 18px; font-weight: 700; background: transparent; }
QPushButton#nav {
    text-align: left;
    border: 1px solid transparent;
    background: transparent;
    color: #93a0bd;
    border-radius: 12px;
    padding: 12px 14px;
}
QPushButton#nav:hover, QPushButton#nav:checked {
    color: #e8eefc;
    background: #1c2740;
    border-color: #263049;
}
QTextEdit, QLineEdit {
    background: #0d1424;
    color: #e8eefc;
    border: 1px solid #263049;
    border-radius: 12px;
    padding: 10px 12px;
    selection-background-color: #1d6f63;
}
QTextEdit:focus, QLineEdit:focus { border: 2px solid rgba(62, 224, 197, 0.45); }
QPushButton#primary {
    background: #3ee0c5;
    color: #04241e;
    border: 0;
    border-radius: 12px;
    padding: 12px 18px;
    font-weight: 650;
}
QPushButton#primary:disabled { background: #1d6f63; color: #8fb8b0; }
QPushButton#ghost {
    background: transparent;
    color: #e8eefc;
    border: 1px solid #263049;
    border-radius: 12px;
    padding: 10px 16px;
}
QPushButton#ghost:hover, QPushButton#primary:hover { background: #7af3e2; }
QPushButton#ghost:hover { background: #1c2740; }
QFrame#dropzone {
    background: #0d1424;
    border: 1px dashed #3d4d70;
    border-radius: 14px;
    min-height: 180px;
}
QFrame#dropzone[drag="true"] { border-color: #3ee0c5; }
QLabel#dropHint { color: #93a0bd; background: transparent; }
QScrollArea { border: none; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px; }
QScrollBar::handle:vertical { background: #263049; border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QWidget#overlay { background: rgba(6, 10, 20, 190); }
QLabel#overlayText { color: #e8eefc; font-size: 16px; background: transparent; }
QProgressBar {
    background: #2a3858;
    border: 0;
    border-radius: 3px;
    max-height: 6px;
}
QProgressBar::chunk { background: #3ee0c5; border-radius: 3px; }
"""


def make_icon() -> QIcon:
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#3ee0c5"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, 64, 64, 16, 16)
    painter.setPen(QColor("#04241e"))
    painter.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "C")
    painter.end()
    return QIcon(pix)


class Backdrop(QWidget):
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0b1020"))
        glow = QRadialGradient(self.width() * 0.1, 0, 520)
        glow.setColorAt(0, QColor(62, 224, 197, 46))
        glow.setColorAt(0.65, QColor(62, 224, 197, 0))
        painter.fillRect(self.rect(), glow)
        cool = QRadialGradient(self.width(), 0, 460)
        cool.setColorAt(0, QColor(99, 132, 255, 40))
        cool.setColorAt(0.6, QColor(99, 132, 255, 0))
        painter.fillRect(self.rect(), cool)


class DropZone(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("dropzone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.path = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        self.hint = QLabel("Перетащите файл или нажмите, чтобы выбрать")
        self.hint.setObjectName("dropHint")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.hide()
        layout.addWidget(self.hint)
        layout.addWidget(self.preview)

    def mousePressEvent(self, event) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Изображение конкурента",
            "",
            "Изображения (*.png *.jpg *.jpeg *.gif *.webp)",
        )
        if path:
            self.set_path(path)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("drag", True)
            self.style().unpolish(self)
            self.style().polish(self)

    def dragLeaveEvent(self, event) -> None:
        self.setProperty("drag", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event) -> None:
        self.setProperty("drag", False)
        self.style().unpolish(self)
        self.style().polish(self)
        urls = event.mimeData().urls()
        if urls:
            self.set_path(urls[0].toLocalFile())

    def set_path(self, path: str) -> None:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return
        self.path = path
        self.preview.setPixmap(
            pixmap.scaledToHeight(240, Qt.TransformationMode.SmoothTransformation)
        )
        self.preview.show()
        self.hint.hide()


class Overlay(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("overlay")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bar = QProgressBar()
        bar.setRange(0, 0)
        bar.setFixedWidth(180)
        bar.setTextVisible(False)
        self.label = QLabel("Анализирую…")
        self.label.setObjectName("overlayText")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(bar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)


def heading(text: str, object_name: str = "blockTitle") -> QLabel:
    label = QLabel(text)
    label.setObjectName(object_name)
    label.setWordWrap(True)
    return label


def clear_layout(layout: QVBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Competition Monitor")
        self.setWindowIcon(make_icon())
        self.resize(1180, 780)
        self.setMinimumSize(980, 640)
        self.worker: AnalyzeWorker | None = None

        root = Backdrop()
        root.setObjectName("root")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(self._sidebar())
        shell.addWidget(self._content(), stretch=1)

        self.overlay = Overlay(root)
        self.overlay.hide()
        self.show_page("monitor")
        self.load_monitor_form()
        self.clock = QTimer(self)
        self.clock.setInterval(60_000)
        self.clock.timeout.connect(self.on_clock)
        self.clock.start()
        QTimer.singleShot(1500, self.on_clock)

    def _sidebar(self) -> QFrame:
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(260)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(20, 28, 20, 28)
        layout.setSpacing(8)

        brand = QHBoxLayout()
        mark = QFrame()
        mark.setObjectName("mark")
        mark_layout = QVBoxLayout(mark)
        mark_layout.setContentsMargins(0, 0, 0, 0)
        letter = QLabel("C")
        letter.setObjectName("markText")
        letter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark_layout.addWidget(letter)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel("Competition")
        title.setObjectName("logoTitle")
        sub = QLabel("монитор конкурентов")
        sub.setObjectName("logoSub")
        titles.addWidget(title)
        titles.addWidget(sub)
        brand.addWidget(mark)
        brand.addLayout(titles)
        brand.addStretch()
        layout.addLayout(brand)
        layout.addSpacing(20)

        self.nav = QButtonGroup(self)
        self.nav.setExclusive(True)
        for key, caption in (
            ("monitor", "Сайты конкурентов"),
            ("text", "Анализ текста"),
            ("image", "Анализ изображений"),
            ("parse", "Парсинг сайта"),
            ("history", "История"),
        ):
            button = QPushButton(caption)
            button.setObjectName("nav")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, name=key: self.show_page(name))
            self.nav.addButton(button)
            layout.addWidget(button)
            if key == "monitor":
                button.setChecked(True)

        layout.addStretch()
        note = QLabel("Проверка сайтов — раз в сутки, пока окно открыто.")
        note.setObjectName("note")
        note.setWordWrap(True)
        layout.addWidget(note)
        return side

    def _content(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll = scroll

        page = QWidget()
        page.setObjectName("page")
        outer = QHBoxLayout(page)
        outer.setContentsMargins(36, 32, 36, 48)
        outer.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        holder = QWidget()
        holder.setMaximumWidth(920)
        holder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        column = QVBoxLayout(holder)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(18)

        header = QLabel("Competition Monitor")
        header.setObjectName("title")
        lead = QLabel(
            "Ниша: моушн-дизайн и интерфейсная анимация. "
            "У каждого сайта свой разбор, а изменения копятся под ним."
        )
        lead.setObjectName("lead")
        lead.setWordWrap(True)
        column.addWidget(header)
        column.addWidget(lead)

        self.stack = QVBoxLayout()
        column.addLayout(self.stack)
        self.monitor_page = self._monitor_page()
        self.text_page = self._text_page()
        self.image_page = self._image_page()
        self.parse_page = self._parse_page()
        self.history_page = self._history_page()
        for widget in (
            self.monitor_page,
            self.text_page,
            self.image_page,
            self.parse_page,
            self.history_page,
        ):
            self.stack.addWidget(widget)

        self.results = self._results_card()
        column.addWidget(self.results)
        column.addStretch()
        outer.addWidget(holder, stretch=1)
        scroll.setWidget(page)
        return scroll

    def _card(self) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(8)
        return card, layout

    def _primary(self, text: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("primary")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedHeight(44)
        return button

    def _monitor_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(18)

        outer.addWidget(self._monitor_form())

        self.competitors = QVBoxLayout()
        self.competitors.setSpacing(18)
        outer.addLayout(self.competitors)
        return page

    def _monitor_form(self) -> QFrame:
        card, layout = self._card()
        layout.addWidget(heading("Сайты конкурентов", "section"))
        hint = QLabel(
            "3–5 адресов в нише. Первый запуск фиксирует разбор. "
            "Дальше приложение само проверяет сайты раз в сутки и пишет отличие с датой под этим конкурентом."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        niche_label = QLabel("Ниша")
        niche_label.setObjectName("hint")
        layout.addWidget(niche_label)
        self.niche_input = QLineEdit()
        self.niche_input.setPlaceholderText("Например, полиграфия")
        self.niche_input.setFixedHeight(46)
        layout.addWidget(self.niche_input)
        self.url_inputs: list[QLineEdit] = []
        for index in range(5):
            field = QLineEdit()
            field.setPlaceholderText(f"Сайт {index + 1}")
            field.setFixedHeight(46)
            self.url_inputs.append(field)
            layout.addWidget(field)
        self.schedule_label = QLabel("")
        self.schedule_label.setObjectName("hint")
        self.schedule_label.setWordWrap(True)
        layout.addWidget(self.schedule_label)
        button = self._primary("Проанализировать сейчас")
        button.clicked.connect(self.analyze_competitors)
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)
        return card

    def _text_page(self) -> QFrame:
        card, layout = self._card()
        layout.addWidget(heading("Текст конкурента", "section"))
        hint = QLabel("Описание продукта, лендинг или рекламное объявление. Минимум 10 символов.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Вставьте текст конкурента…")
        self.text_input.setMinimumHeight(220)
        layout.addWidget(self.text_input)
        button = self._primary("Проанализировать")
        button.clicked.connect(self.analyze_text)
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)
        return card

    def _image_page(self) -> QFrame:
        card, layout = self._card()
        layout.addWidget(heading("Изображение", "section"))
        hint = QLabel("Баннер, скриншот сайта или упаковка. PNG, JPG, GIF, WEBP до 10 МБ.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.drop = DropZone()
        layout.addWidget(self.drop)
        self.image_button = self._primary("Проанализировать")
        self.image_button.setEnabled(False)
        self.image_button.clicked.connect(self.analyze_image)
        layout.addWidget(self.image_button, alignment=Qt.AlignmentFlag.AlignLeft)
        original = self.drop.set_path

        def set_path(path: str) -> None:
            original(path)
            self.image_button.setEnabled(bool(self.drop.path))

        self.drop.set_path = set_path
        return card

    def _parse_page(self) -> QFrame:
        card, layout = self._card()
        layout.addWidget(heading("Страница конкурента", "section"))
        hint = QLabel("Selenium откроет страницу в Chrome и снимет текст со скриншотом.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        self.url_input.setFixedHeight(46)
        layout.addWidget(self.url_input)
        button = self._primary("Собрать страницу и проанализировать")
        button.clicked.connect(self.analyze_page)
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)
        return card

    def _history_page(self) -> QFrame:
        card, layout = self._card()
        row = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(heading("История", "section"))
        hint = QLabel("Последние 10 запросов.")
        hint.setObjectName("hint")
        titles.addWidget(hint)
        row.addLayout(titles)
        row.addStretch()
        clear = QPushButton("Очистить")
        clear.setObjectName("ghost")
        clear.setCursor(Qt.CursorShape.PointingHandCursor)
        clear.clicked.connect(self.clear_history)
        row.addWidget(clear, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(row)
        self.history_list = QVBoxLayout()
        self.history_list.setSpacing(10)
        layout.addLayout(self.history_list)
        return card

    def _results_card(self) -> QFrame:
        card, layout = self._card()
        row = QHBoxLayout()
        row.addWidget(heading("Результат", "section"))
        row.addStretch()
        close = QPushButton("Закрыть")
        close.setObjectName("ghost")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(card.hide)
        row.addWidget(close)
        layout.addLayout(row)
        self.results_body = QVBoxLayout()
        self.results_body.setSpacing(8)
        layout.addLayout(self.results_body)
        card.hide()
        return card

    def show_page(self, name: str) -> None:
        self.monitor_page.setVisible(name == "monitor")
        self.text_page.setVisible(name == "text")
        self.image_page.setVisible(name == "image")
        self.parse_page.setVisible(name == "parse")
        self.history_page.setVisible(name == "history")
        if name == "monitor":
            self.results.hide()
            self.refresh_schedule_label()
        if name == "history":
            self.load_history()
        for button in self.nav.buttons():
            if button.text() == {
                "monitor": "Сайты конкурентов",
                "text": "Анализ текста",
                "image": "Анализ изображений",
                "parse": "Парсинг сайта",
                "history": "История",
            }[name]:
                button.setChecked(True)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.overlay.setGeometry(self.centralWidget().rect())

    def show_overlay(self, message: str) -> None:
        self.overlay.label.setText(message)
        self.overlay.setGeometry(self.centralWidget().rect())
        self.overlay.show()
        self.overlay.raise_()

    def start_job(self, kind: str, payload: str, message: str) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        self.show_overlay(message)
        self.worker = AnalyzeWorker(kind, payload)
        self.worker.succeeded.connect(self.on_success)
        self.worker.failed.connect(self.on_fail)
        self.worker.finished.connect(self.overlay.hide)
        self.worker.start()

    def on_clock(self) -> None:
        self.refresh_schedule_label()
        if self.worker is not None and self.worker.isRunning():
            return
        if monitor_service.is_due():
            self.start_job("monitor_scheduled", "", "Ежедневная проверка сайтов…")

    def load_monitor_form(self) -> None:
        state = monitor_service.public_state()
        self.niche_input.setText(state.get("niche") or "")
        urls = state.get("urls") or state.get("defaults") or []
        for index, field in enumerate(self.url_inputs):
            field.setText(urls[index] if index < len(urls) else "")
        self.render_monitor(state, update_form=False)

    def refresh_schedule_label(self) -> None:
        state = monitor_service.public_state()
        nxt = state.get("next_run_at")
        last = state.get("last_run_at")
        if nxt:
            text = f"Следующая автоматическая проверка: {format_time(nxt)}."
            if last:
                text = f"Последний анализ: {format_time(last)}. " + text
        elif state.get("urls"):
            text = "После этого анализа следующая проверка будет через сутки."
        else:
            text = "Адреса уже подставлены: запустите анализ. Пока окно открыто, следующая проверка будет через сутки."
        self.schedule_label.setText(text)

    def analyze_competitors(self) -> None:
        urls = [field.text().strip() for field in self.url_inputs if field.text().strip()]
        if not urls:
            self.show_error("Укажите хотя бы один сайт конкурента.")
            return
        if len(urls) > 5:
            self.show_error("Можно следить не больше чем за 5 сайтами.")
            return
        payload = json.dumps({"urls": urls, "niche": self.niche_input.text().strip()}, ensure_ascii=False)
        self.start_job("monitor", payload, "Собираю страницы и сравниваю с прошлой проверкой…")

    def render_monitor(self, state: dict, update_form: bool = False) -> None:
        if update_form:
            self.niche_input.setText(state.get("niche") or "")
            urls = state.get("urls") or []
            for index, field in enumerate(self.url_inputs):
                field.setText(urls[index] if index < len(urls) else "")
        clear_layout(self.competitors)
        sites = state.get("sites") or []
        changes = state.get("changes") or []
        if not sites:
            empty = QLabel("Разбор каждого конкурента появится после первого анализа.")
            empty.setObjectName("empty")
            empty.setWordWrap(True)
            self.competitors.addWidget(empty)
        for site in sites:
            own = [item for item in changes if same_url(item.get("url"), site.get("url"))]
            self.competitors.addWidget(self._site_card(site, own))
        self.refresh_schedule_label()

    def _site_card(self, site: dict, changes: list[dict]) -> QFrame:
        row = QFrame()
        row.setObjectName("card")
        layout = QVBoxLayout(row)
        layout.setContentsMargins(22, 22, 22, 22)
        title = QLabel(site.get("title") or site.get("url") or "")
        title.setObjectName("section")
        title.setWordWrap(True)
        layout.addWidget(title)
        meta_lines = [site.get("url") or ""]
        if site.get("analyzed_at"):
            meta_lines.append(f"Снято: {format_time(site['analyzed_at'])}")
        if site.get("design_score") is not None:
            meta_lines.append(
                f"Дизайн: {site['design_score']}/10    Потенциал анимации: {site['animation_potential']}/10"
            )
        meta = QLabel("\n".join(line for line in meta_lines if line))
        meta.setObjectName("meta")
        meta.setWordWrap(True)
        layout.addWidget(meta)
        if site.get("error"):
            error = QLabel(site["error"])
            error.setObjectName("error")
            error.setWordWrap(True)
            layout.addWidget(error)
        self._add_text(layout, "Заключение", site.get("conclusion"))
        self._add_text(layout, "Резюме", site.get("summary"))
        self._add_text(layout, "Анимация", site.get("animation_notes"))
        self._add_list(layout, "Сильные стороны", site.get("strengths") or [])
        self._add_list(layout, "Слабые стороны", site.get("weaknesses") or [])
        self._add_list(layout, "Уникальные предложения", site.get("unique_offers") or [])
        self._add_list(layout, "Рекомендации", site.get("recommendations") or [])
        layout.addWidget(self._changes_block(changes))
        return row

    def _add_text(self, layout: QVBoxLayout, title: str, value: str | None) -> None:
        if not value:
            return
        layout.addWidget(heading(title))
        label = QLabel(value)
        label.setObjectName("summary")
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(label)

    def _add_list(self, layout: QVBoxLayout, title: str, items: list[str]) -> None:
        if not items:
            return
        layout.addWidget(heading(title))
        for item in items:
            label = QLabel("•  " + item)
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(label)

    def _changes_block(self, changes: list[dict]) -> QFrame:
        row = QFrame()
        row.setObjectName("historyRow")
        layout = QVBoxLayout(row)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(heading("Изменения"))
        if not changes:
            empty = QLabel("Пока пусто. После суточной проверки отличия этого сайта появятся здесь с датой.")
            empty.setObjectName("empty")
            empty.setWordWrap(True)
            layout.addWidget(empty)
            return row
        for change in changes:
            layout.addWidget(self._change_lines(change))
        return row

    def _change_lines(self, change: dict) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 8, 0, 0)
        header = QLabel(format_time(change.get("changed_at")))
        header.setObjectName("tag")
        header.setWordWrap(True)
        layout.addWidget(header)
        for item in change.get("items") or []:
            before = item.get("before") or "—"
            after = item.get("after") or "—"
            line = QLabel(f"{item.get('field')}: {before}  →  {after}")
            line.setWordWrap(True)
            line.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(line)
        return box

    def analyze_text(self) -> None:
        text = self.text_input.toPlainText().strip()
        if len(text) < 10:
            self.show_error("Нужно минимум 10 символов текста.")
            return
        self.start_job("text", text, "Анализирую…")

    def analyze_image(self) -> None:
        if not self.drop.path:
            return
        self.start_job("image", self.drop.path, "Анализирую…")

    def analyze_page(self) -> None:
        url = self.url_input.text().strip()
        if len(url) < 3:
            self.show_error("Укажите адрес страницы.")
            return
        self.start_job("parse", url, "Открываю Chrome и анализирую страницу…")

    def on_success(self, kind: str, result) -> None:
        if kind in {"monitor", "monitor_scheduled"}:
            self.render_monitor(result, update_form=kind == "monitor")
            self.show_page("monitor")
            if self.history_page.isVisible():
                self.load_history()
            return
        if kind == "text":
            self.render_analysis(result)
        elif kind == "image":
            self.render_image(result)
        elif kind == "parse":
            self.render_parse(result)
        if self.history_page.isVisible():
            self.load_history()

    def on_fail(self, message: str) -> None:
        self.show_error(message)

    def show_error(self, message: str) -> None:
        clear_layout(self.results_body)
        label = QLabel(message)
        label.setObjectName("error")
        label.setWordWrap(True)
        self.results_body.addWidget(label)
        self.reveal_results()

    def reveal_results(self) -> None:
        self.results.show()
        QTimer.singleShot(0, lambda: self.scroll.ensureWidgetVisible(self.results))

    def add_text_block(self, title: str, value: str | None) -> None:
        if not value:
            return
        self.results_body.addWidget(heading(title))
        label = QLabel(value)
        label.setObjectName("summary")
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.results_body.addWidget(label)

    def add_list_block(self, title: str, items: list[str]) -> None:
        if not items:
            return
        self.results_body.addWidget(heading(title))
        for item in items:
            label = QLabel("•  " + item)
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.results_body.addWidget(label)

    def add_scores(self, analysis) -> None:
        design = getattr(analysis, "design_score", None)
        motion = getattr(analysis, "animation_potential", None)
        if design is None and motion is None:
            return
        score = QLabel(f"Дизайн {design}/10    Анимация {motion}/10")
        score.setObjectName("score")
        score.setWordWrap(True)
        self.results_body.addWidget(score)
        self.add_text_block("Анимация", getattr(analysis, "animation_notes", ""))
        self.add_text_block("Заключение", getattr(analysis, "conclusion", ""))

    def render_analysis(self, analysis) -> None:
        clear_layout(self.results_body)
        self.add_scores(analysis)
        self.add_text_block("Резюме", analysis.summary)
        self.add_list_block("Сильные стороны", analysis.strengths)
        self.add_list_block("Слабые стороны", analysis.weaknesses)
        self.add_list_block("Уникальные предложения", analysis.unique_offers)
        self.add_list_block("Рекомендации", analysis.recommendations)
        self.reveal_results()

    def render_image(self, analysis) -> None:
        clear_layout(self.results_body)
        self.add_text_block("Описание", analysis.description)
        self.add_scores(analysis)
        self.results_body.addWidget(heading("Оценка визуального стиля"))
        score = QLabel(f"{analysis.visual_style_score}/10")
        score.setObjectName("score")
        self.results_body.addWidget(score)
        self.add_text_block("Разбор стиля", analysis.visual_style_analysis)
        self.add_list_block("Маркетинговые инсайты", analysis.marketing_insights)
        self.add_list_block("Рекомендации", analysis.recommendations)
        self.reveal_results()

    def render_parse(self, data: dict) -> None:
        clear_layout(self.results_body)
        if data.get("screenshot"):
            self.results_body.addWidget(heading("Страница в Chrome"))
            shot = QLabel()
            pixmap = QPixmap()
            pixmap.loadFromData(data["screenshot"], "PNG")
            shot.setPixmap(pixmap.scaledToWidth(820, Qt.TransformationMode.SmoothTransformation))
            self.results_body.addWidget(shot)
        lines = []
        if data.get("url"):
            lines.append(f"URL: {data['url']}")
        if data.get("title"):
            lines.append(f"Заголовок: {data['title']}")
        self.results_body.addWidget(heading("Что открыто"))
        meta = QLabel("\n".join(lines))
        meta.setObjectName("meta")
        meta.setWordWrap(True)
        self.results_body.addWidget(meta)
        if data.get("analysis"):
            analysis = data["analysis"]
            self.add_scores(analysis)
            self.add_text_block("Резюме", analysis.summary)
            self.add_list_block("Сильные стороны", analysis.strengths)
            self.add_list_block("Слабые стороны", analysis.weaknesses)
            self.add_list_block("Уникальные предложения", analysis.unique_offers)
            self.add_list_block("Рекомендации", analysis.recommendations)
        self.reveal_results()

    def load_history(self) -> None:
        clear_layout(self.history_list)
        items = history_service.get_history()
        if not items:
            empty = QLabel("История пуста")
            empty.setObjectName("empty")
            self.history_list.addWidget(empty)
            return
        for item in items:
            row = QFrame()
            row.setObjectName("historyRow")
            grid = QHBoxLayout(row)
            grid.setContentsMargins(12, 12, 12, 12)
            tag = QLabel(TYPE_LABELS.get(item.request_type, item.request_type))
            tag.setObjectName("tag")
            tag.setFixedWidth(120)
            summary = QLabel(item.request_summary or "")
            summary.setWordWrap(True)
            when = QLabel(format_time(item.timestamp))
            when.setObjectName("time")
            grid.addWidget(tag, alignment=Qt.AlignmentFlag.AlignTop)
            grid.addWidget(summary, stretch=1)
            grid.addWidget(when, alignment=Qt.AlignmentFlag.AlignTop)
            self.history_list.addWidget(row)

    def clear_history(self) -> None:
        history_service.clear_history()
        self.load_history()


def same_url(left, right) -> bool:
    return str(left or "").rstrip("/") == str(right or "").rstrip("/")


def format_time(value) -> str:
    if isinstance(value, datetime):
        moment = value
    else:
        try:
            moment = datetime.fromisoformat(str(value))
        except ValueError:
            return ""
    return moment.strftime("%d.%m.%Y, %H:%M")


def main() -> None:
    def log_crash(exc_type, exc, tb) -> None:
        target = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
        (target / "crash.log").write_text("".join(traceback.format_exception(exc_type, exc, tb)), encoding="utf-8")
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = log_crash
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    if "--preview" in sys.argv:
        def grab() -> None:
            window.grab().save(str(Path(__file__).resolve().parent / "preview.png"))
            app.quit()

        QTimer.singleShot(500, grab)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
