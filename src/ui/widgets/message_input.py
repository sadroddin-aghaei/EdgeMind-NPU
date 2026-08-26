"""
EdgeMind NPU - Message Input Widget
Rich input area with file attachment, send button, and keyboard shortcuts.
"""

import os
from pathlib import Path
from typing import List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QFrame, QFileDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QDragEnterEvent, QDropEvent


class AutoGrowingTextEdit(QTextEdit):
    """Text edit that grows with content up to a max height."""

    enter_pressed = Signal()

    def __init__(self, parent=None, min_height: int = 40, max_height: int = 200,
                 rtl: bool = False):
        super().__init__(parent)
        self.min_height = min_height
        self.max_height = max_height
        self.rtl = rtl
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setMinimumHeight(min_height)
        self.setMaximumHeight(max_height)
        self.document().contentsChanged.connect(self._adjust_height)
        self.document().contentsChanged.connect(self.viewport().update)

        # Placeholder text
        self._placeholder = ""
        self._placeholder_color = QColor("#6e6e8a")

    def setPlaceholderText(self, text: str):
        self._placeholder = text
        self.viewport().update()

    def _adjust_height(self):
        doc_height = int(self.document().size().height()) + 16
        new_height = max(self.min_height, min(doc_height, self.max_height))
        if self.height() != new_height:
            self.setMinimumHeight(new_height)
            self.setMaximumHeight(new_height)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                self.enter_pressed.emit()
                return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if (not self.toPlainText().strip() and self._placeholder
                and not self.hasFocus()):
            painter = QPainter(self.viewport())
            try:
                painter.setPen(self._placeholder_color)
                align = (Qt.AlignmentFlag.AlignRight if self.rtl
                         else Qt.AlignmentFlag.AlignLeft)
                painter.drawText(
                    self.viewport().rect().adjusted(8, 8, -8, -8),
                    align | Qt.AlignmentFlag.AlignVCenter,
                    self._placeholder,
                )
            finally:
                painter.end()


class AttachmentPreview(QFrame):
    """Preview of an attached file."""

    removed = Signal(str)

    def __init__(self, filepath: str, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(
            "QFrame { background-color: #2d2d44; border: 1px solid #3a3a5c;"
            "border-radius: 8px; padding: 6px; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # File icon
        path = Path(self.filepath)
        ext = path.suffix.lower()
        icon_map = {
            '.txt': '📄', '.md': '📄', '.pdf': '📕',
            '.docx': '📘', '.doc': '📘',
            '.png': '🖼️', '.jpg': '🖼️', '.jpeg': '🖼️',
            '.gif': '🖼️', '.bmp': '🖼️',
        }
        icon = icon_map.get(ext, '📎')

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(icon_label)

        # File name and size
        name = path.name
        if len(name) > 30:
            name = name[:27] + "..."

        file_label = QLabel(name)
        file_label.setStyleSheet(
            "color: #e4e4f0; font-size: 12px; border: none;"
        )
        layout.addWidget(file_label)

        layout.addStretch()

        # Remove button
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setStyleSheet(
            "QPushButton { background-color: transparent; color: #6e6e8a;"
            "border: none; font-size: 14px; border-radius: 10px; }"
            "QPushButton:hover { color: #f44336; background-color: #3a3a5c; }"
        )
        remove_btn.clicked.connect(lambda: self.removed.emit(self.filepath))
        layout.addWidget(remove_btn)


class MessageInput(QWidget):
    """Message input area with file attachment support."""

    message_sent = Signal(str, list)  # (text, file_paths)
    stop_requested = Signal()

    def __init__(self, rtl: bool = True, parent=None):
        super().__init__(parent)
        self.rtl = rtl
        self._attached_files: List[str] = []
        self._is_generating = False

        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("inputArea")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 8, 16, 12)
        main_layout.setSpacing(8)

        # Attached files preview
        self.attachments_container = QVBoxLayout()
        self.attachments_container.setSpacing(4)
        self.attachments_layout_widget = QWidget()
        self.attachments_layout_widget.setLayout(self.attachments_container)
        self.attachments_layout_widget.setVisible(False)
        main_layout.addWidget(self.attachments_layout_widget)

        # Input container
        input_frame = QFrame()
        input_frame.setObjectName("inputContainer")

        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(4, 4, 4, 4)
        input_layout.setSpacing(4)

        # Text input
        self.text_input = AutoGrowingTextEdit(min_height=40, max_height=200,
                                              rtl=self.rtl)
        self.text_input.setObjectName("messageInput")
        # Don't accept drops here so they fall through to this widget's
        # dragEnterEvent/dropEvent handlers
        self.text_input.setAcceptDrops(False)

        direction = "rtl" if self.rtl else "ltr"
        self.text_input.document().setDefaultStyleSheet(
            f"* {{ direction: {direction}; }}"
        )

        placeholder = "پیام خود را بنویسید..." if self.rtl else "Type your message..."
        self.text_input.setPlaceholderText(placeholder)
        self.text_input.enter_pressed.connect(self._on_send)

        input_layout.addWidget(self.text_input)

        # Bottom toolbar
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 0, 4, 4)

        # Attach button
        self.attach_btn = QPushButton("📎 Attach")
        self.attach_btn.setObjectName("copyBtn")
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.clicked.connect(self._on_attach)
        self.attach_btn.setFixedHeight(32)
        toolbar.addWidget(self.attach_btn)

        toolbar.addStretch()

        # Token count (optional)
        self.token_label = QLabel("")
        self.token_label.setStyleSheet(
            "color: #6e6e8a; font-size: 11px; border: none;"
        )
        toolbar.addWidget(self.token_label)

        # Send / Stop button
        self.send_btn = QPushButton("Send ➤")
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self._on_send)
        self.send_btn.setFixedHeight(36)
        self.send_btn.setMinimumWidth(80)
        toolbar.addWidget(self.send_btn)

        self.stop_btn = QPushButton("■ Stop")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.setMinimumWidth(80)
        self.stop_btn.setVisible(False)
        toolbar.addWidget(self.stop_btn)

        input_layout.addLayout(toolbar)
        main_layout.addWidget(input_frame)

        # Enable drag and drop
        self.setAcceptDrops(True)

    def set_generating(self, is_generating: bool):
        """Toggle between send and stop states."""
        self._is_generating = is_generating
        self.send_btn.setVisible(not is_generating)
        self.stop_btn.setVisible(is_generating)
        self.text_input.setReadOnly(is_generating)

    def clear_input(self):
        """Clear the text input."""
        self.text_input.clear()
        self._attached_files.clear()
        self._update_attachments_ui()

    def _on_send(self):
        """Handle send button click."""
        text = self.text_input.toPlainText().strip()
        if not text and not self._attached_files:
            return

        self.message_sent.emit(text, list(self._attached_files))
        self.clear_input()

    def _on_stop(self):
        """Handle stop button click."""
        self.stop_requested.emit()

    def _on_attach(self):
        """Open file dialog to attach files."""
        filetypes = (
            "All Supported (*.txt *.md *.csv *.json *.pdf *.docx "
            "*.png *.jpg *.jpeg *.gif *.bmp *.webp);;"
            "Text Files (*.txt *.md *.csv *.json);;"
            "Documents (*.pdf *.docx);;"
            "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;"
            "All Files (*)"
        )

        files, _ = QFileDialog.getOpenFileNames(
            self, "Attach Files", "", filetypes
        )

        for filepath in files:
            if filepath not in self._attached_files:
                self._attached_files.append(filepath)

        self._update_attachments_ui()

    def _remove_attachment(self, filepath: str):
        """Remove an attached file."""
        if filepath in self._attached_files:
            self._attached_files.remove(filepath)
            self._update_attachments_ui()

    def _update_attachments_ui(self):
        """Update the attachments preview area."""
        # Clear existing previews
        while self.attachments_container.count():
            item = self.attachments_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add new previews
        for filepath in self._attached_files:
            preview = AttachmentPreview(filepath)
            preview.removed.connect(self._remove_attachment)
            self.attachments_container.addWidget(preview)

        self.attachments_layout_widget.setVisible(len(self._attached_files) > 0)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            filepath = url.toLocalFile()
            if os.path.isfile(filepath):
                if filepath not in self._attached_files:
                    self._attached_files.append(filepath)
        self._update_attachments_ui()
