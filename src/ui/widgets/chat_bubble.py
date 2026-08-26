"""
EdgeMind NPU - Chat Bubble Widget
Renders individual chat messages with markdown, code blocks, and copy support.
"""

import re
from datetime import datetime
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QFrame, QPushButton, QApplication,
    QSizePolicy, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import (
    QFont, QColor, QSyntaxHighlighter, QTextCharFormat, QPalette,
)


class CodeHighlighter(QSyntaxHighlighter):
    """Simple syntax highlighter for code blocks."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []

        # Keywords
        kw_format = QTextCharFormat()
        kw_format.setForeground(QColor("#c792ea"))
        kw_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            r'\b(def|class|return|if|else|elif|for|while|import|from|'
            r'try|except|finally|with|as|yield|lambda|pass|break|continue|'
            r'True|False|None|self|print|raise|async|await)\b'
        ]
        for pattern in keywords:
            self._rules.append((re.compile(pattern), kw_format))

        # Strings
        str_format = QTextCharFormat()
        str_format.setForeground(QColor("#c3e88d"))
        self._rules.append((re.compile(r'(["\'])(?:(?=(\\?))\2.)*?\1'), str_format))

        # Numbers
        num_format = QTextCharFormat()
        num_format.setForeground(QColor("#f78c6c"))
        self._rules.append((re.compile(r'\b\d+\.?\d*\b'), num_format))

        # Comments
        cmt_format = QTextCharFormat()
        cmt_format.setForeground(QColor("#546e7a"))
        self._rules.append((re.compile(r'#.*$'), cmt_format))

    def highlightBlock(self, text: str):
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, fmt)


class MessageBubble(QWidget):
    """A single chat message bubble."""

    copy_requested = Signal(str)

    def __init__(self, role: str, content: str,
                 timestamp: Optional[datetime] = None,
                 model_id: str = "",
                 rtl: bool = True,
                 parent=None):
        super().__init__(parent)
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.model_id = model_id
        self.rtl = rtl

        self._setup_ui()
        self._render_content()

    def _setup_ui(self):
        """Set up the widget layout."""
        self.setObjectName("messageContainer")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 4, 0, 4)
        self.main_layout.setSpacing(4)

        # Role label
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(8, 0, 8, 0)

        role_text = "🤖 EdgeMind" if self.role == "assistant" else "👤 You"
        self.role_label = QLabel(role_text)
        self.role_label.setStyleSheet(
            "color: #a0a0b8; font-size: 12px; font-weight: 600;"
        )
        header_layout.addWidget(self.role_label)

        header_layout.addStretch()

        # Timestamp
        time_str = self.timestamp.strftime("%H:%M")
        self.time_label = QLabel(time_str)
        self.time_label.setObjectName("messageTimestamp")
        self.time_label.setStyleSheet("color: #6e6e8a; font-size: 11px;")
        header_layout.addWidget(self.time_label)

        self.main_layout.addLayout(header_layout)

        # Content bubble
        self.bubble = QFrame()
        is_user = self.role == "user"
        self.bubble.setObjectName("userMessage" if is_user else "assistantMessage")

        self.bubble_layout = QVBoxLayout(self.bubble)
        bubble_layout = self.bubble_layout
        bubble_layout.setContentsMargins(14, 10, 14, 10)
        bubble_layout.setSpacing(4)

        # Content display
        self.content_widget = self._create_content_widget()
        bubble_layout.addWidget(self.content_widget)

        # Copy button for assistant messages
        self._has_copy_row = False
        if not is_user:
            self._has_copy_row = True
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()

            self.copy_btn = QPushButton("📋 Copy")
            self.copy_btn.setObjectName("copyBtn")
            self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.copy_btn.clicked.connect(self._on_copy)
            self.copy_btn.setFixedHeight(28)
            btn_layout.addWidget(self.copy_btn)

            bubble_layout.addLayout(btn_layout)

        # Adjust alignment
        align = Qt.AlignmentFlag.AlignRight if is_user else Qt.AlignmentFlag.AlignLeft
        self.main_layout.addWidget(self.bubble, alignment=align)

        # Shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.bubble.setGraphicsEffect(shadow)

    def _create_content_widget(self):
        """Create the appropriate content widget based on content type."""
        if self._has_code_blocks():
            return self._create_rich_text_widget()
        else:
            return self._create_text_widget()

    def _create_text_widget(self):
        """Create a simple text label for non-code content."""
        label = QLabel()
        label.setWordWrap(True)
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Style for RTL/LTR
        style = ""
        if self.rtl and self.role == "user":
            style = "text-align: right;"
        label.setStyleSheet(f"font-size: 14px; line-height: 1.5; {style}")

        return label

    def _create_rich_text_widget(self):
        """Create a text edit for content with code blocks."""
        text_edit = QReadOnlyTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFrameShape(QFrame.Shape.NoFrame)
        text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Set minimum height based on content
        text_edit.setMinimumHeight(30)
        text_edit.setMaximumHeight(5000)

        # Apply syntax highlighter
        self._highlighter = CodeHighlighter(text_edit.document())

        return text_edit

    def _render_content(self):
        """Render the message content into the content widget."""
        if isinstance(self.content_widget, QLabel):
            self.content_widget.setText(self._format_text(self.content))
        elif isinstance(self.content_widget, QReadOnlyTextEdit):
            self.content_widget.setHtml(self._format_rich_text(self.content))
            # Auto-resize
            doc = self.content_widget.document()
            doc.adjustSize()
            height = int(doc.size().height()) + 20
            self.content_widget.setMinimumHeight(min(height, 5000))

    def _format_text(self, text: str) -> str:
        """Format plain text with basic markdown."""
        # Bold
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        # Italic
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        # Inline code
        text = re.sub(r'`([^`]+)`',
                       r'<code style="background:#2d2d44;padding:2px 6px;'
                       r'border-radius:4px;font-family:Consolas;">\1</code>',
                       text)
        # Line breaks
        text = text.replace('\n', '<br>')
        return text

    def _format_rich_text(self, text: str) -> str:
        """Format text with code blocks into HTML."""
        # Split by code blocks
        parts = re.split(r'```(\w*)\n(.*?)```', text, flags=re.DOTALL)
        html_parts = []

        for i, part in enumerate(parts):
            if i % 3 == 0:
                # Regular text
                formatted = self._format_text(part)
                html_parts.append(f'<div style="margin: 4px 0;">{formatted}</div>')
            elif i % 3 == 1:
                # Language identifier (skip, used for display)
                pass
            elif i % 3 == 2:
                # Code content
                lang = parts[i - 1] if i > 0 else ""
                lang_label = f'<span style="color:#6e6e8a;font-size:11px;">{lang}</span>' if lang else ""

                html_parts.append(
                    f'<div style="margin: 8px 0;">'
                    f'<div style="background:#252536;border:1px solid #3a3a5c;'
                    f'border-radius:8px;overflow:hidden;">'
                    f'<div style="padding:6px 12px;background:#2d2d44;'
                    f'border-bottom:1px solid #3a3a5c;">'
                    f'{lang_label}</div>'
                    f'<pre style="margin:0;padding:12px;font-family:Cascadia Code,Consolas,monospace;'
                    f'font-size:13px;color:#e4e4f0;overflow-x:auto;">'
                    f'<code>{self._escape_html(part.strip())}</code></pre>'
                    f'</div></div>'
                )

        return '\n'.join(html_parts)

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))

    def _has_code_blocks(self) -> bool:
        """Check if content contains code blocks."""
        return '```' in self.content

    def _on_copy(self):
        """Copy message content to clipboard."""
        clipboard = QApplication.clipboard()
        # Get plain text without markdown
        plain_text = self._strip_markdown(self.content)
        clipboard.setText(plain_text)

        # Visual feedback
        original_text = self.copy_btn.text()
        self.copy_btn.setText("✓ Copied!")
        QTimer.singleShot(1500, lambda: self.copy_btn.setText(original_text))

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Strip markdown formatting for plain text copy."""
        # Remove code blocks
        text = re.sub(r'```\w*\n(.*?)```', r'\1', text, flags=re.DOTALL)
        # Remove inline code
        text = re.sub(r'`([^`]+)`', r'\1', text)
        # Remove bold
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        # Remove italic
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        # Remove headers
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        return text.strip()

    def update_content(self, content: str):
        """Update the message content (for streaming)."""
        self.content = content

        # Switch widget type if code blocks appeared or disappeared
        needs_rich = self._has_code_blocks()
        is_rich = isinstance(self.content_widget, QReadOnlyTextEdit)
        if needs_rich != is_rich:
            self._rebuild_content_widget()
        else:
            self._render_content()

    def _rebuild_content_widget(self):
        """Replace the content widget (e.g. plain label -> rich text)."""
        old = self.content_widget
        self.bubble_layout.removeWidget(old)
        old.setParent(None)
        old.deleteLater()

        self.content_widget = self._create_content_widget()
        if self._has_copy_row:
            # Keep it above the copy-button row (last layout item)
            self.bubble_layout.insertWidget(
                self.bubble_layout.count() - 1, self.content_widget
            )
        else:
            self.bubble_layout.addWidget(self.content_widget)
        self._render_content()


class TypingIndicator(QWidget):
    """Animated typing indicator shown while assistant is generating."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)

        self.label = QLabel("🤖 EdgeMind is thinking...")
        self.label.setStyleSheet(
            "color: #a0a0b8; font-size: 13px; font-style: italic;"
        )
        layout.addWidget(self.label)
        layout.addStretch()

        self._dots = 0
        self._timer = QTimer()
        self._timer.timeout.connect(self._animate)
        self._timer.start(500)

    def _animate(self):
        self._dots = (self._dots + 1) % 4
        dots = '.' * self._dots
        self.label.setText(f"🤖 EdgeMind is thinking{dots}")

    def stop(self):
        self._timer.stop()


class QReadOnlyTextEdit(QTextEdit):
    """QTextEdit configured as read-only."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAcceptRichText(True)

        # Set background transparent
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        self.setPalette(palette)

    def sizeHint(self):
        doc = self.document()
        doc.adjustSize()
        return QSize(
            int(doc.size().width()) + 20,
            int(doc.size().height()) + 20,
        )

    def wheelEvent(self, event):
        """Prevent scroll events on the text edit."""
        event.ignore()
