"""
EdgeMind NPU - Sidebar Widget
Conversation list with search, create, rename, and delete capabilities.
"""

from datetime import datetime
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QScrollArea,
    QSizePolicy, QMenu, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QPoint

from src.database.db_manager import DatabaseManager


class ConversationItem(QWidget):
    """A single conversation item in the sidebar list."""

    clicked = Signal(str)
    rename_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, conv_id: str, title: str,
                 date: Optional[datetime] = None,
                 message_count: int = 0,
                 is_active: bool = False,
                 parent=None):
        super().__init__(parent)
        self.conv_id = conv_id
        self._is_active = is_active

        self._setup_ui(title, date, message_count)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _setup_ui(self, title: str, date: Optional[datetime],
                  message_count: int):
        self.setMinimumHeight(48)
        self.setMaximumHeight(60)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        # Title row
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)

        # Chat icon
        icon_label = QLabel("💬")
        icon_label.setStyleSheet("font-size: 14px; border: none;")
        title_layout.addWidget(icon_label)

        # Title text
        self.title_label = QLabel(title[:40])
        self.title_label.setObjectName("convItemTitle")
        self.title_label.setStyleSheet(
            "color: #e4e4f0; font-size: 13px; font-weight: 500; border: none;"
        )
        self.title_label.setWordWrap(False)
        self.title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        title_layout.addWidget(self.title_label)

        layout.addLayout(title_layout)

        # Date and count
        if date:
            date_str = date.strftime("%b %d, %H:%M")
            date_text = f"{date_str}"
            if message_count > 0:
                date_text += f"  •  {message_count} msgs"
        else:
            date_text = ""

        self.date_label = QLabel(date_text)
        self.date_label.setObjectName("convItemDate")
        self.date_label.setStyleSheet(
            "color: #6e6e8a; font-size: 11px; border: none;"
        )
        layout.addWidget(self.date_label)

        self._update_style()

    def _update_style(self):
        bg = "#414161" if self._is_active else "transparent"
        border = "1px solid #7c6ff7" if self._is_active else "1px solid transparent"
        self.setStyleSheet(
            f"ConversationItem {{ background-color: {bg}; border: {border}; "
            f"border-radius: 8px; }}"
        )

    def set_active(self, active: bool):
        self._is_active = active
        self._update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.conv_id)

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #252536; border: 1px solid #3a3a5c;"
            "border-radius: 8px; padding: 4px; }"
            "QMenu::item { color: #e4e4f0; padding: 8px 16px; border-radius: 4px; }"
            "QMenu::item:selected { background-color: #414161; }"
        )

        rename_action = menu.addAction("✏️ Rename")
        rename_action.triggered.connect(lambda: self.rename_requested.emit(self.conv_id))

        menu.addSeparator()

        delete_action = menu.addAction("🗑️ Delete")
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.conv_id))

        menu.exec(self.mapToGlobal(pos))


class Sidebar(QWidget):
    """Sidebar with conversation list and controls."""

    conversation_selected = Signal(str)
    new_chat_requested = Signal()
    conversation_deleted = Signal(str)
    settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setMinimumWidth(240)
        self.setMaximumWidth(360)

        self._db = DatabaseManager()
        self._current_conv_id = None
        self._conversation_items = {}

        self._setup_ui()
        self.refresh_conversations()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("sidebarHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 16, 16, 12)
        header_layout.setSpacing(12)

        # App title
        title_row = QHBoxLayout()
        app_title = QLabel("⚡ EdgeMind NPU")
        app_title.setObjectName("sidebarTitle")
        app_title.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #7c6ff7; border: none;"
        )
        title_row.addWidget(app_title)
        title_row.addStretch()

        # Settings button
        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(32, 32)
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(
            "QPushButton { background-color: transparent; color: #a0a0b8;"
            "border: none; font-size: 18px; border-radius: 16px; }"
            "QPushButton:hover { background-color: #363654; color: #e4e4f0; }"
        )
        settings_btn.clicked.connect(self.settings_requested.emit)
        title_row.addWidget(settings_btn)

        header_layout.addLayout(title_row)

        # New Chat button
        self.new_chat_btn = QPushButton("＋ New Chat")
        self.new_chat_btn.setObjectName("newChatBtn")
        self.new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_chat_btn.clicked.connect(self.new_chat_requested.emit)
        header_layout.addWidget(self.new_chat_btn)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("🔍 Search conversations...")
        self.search_input.textChanged.connect(self._on_search)
        header_layout.addWidget(self.search_input)

        layout.addWidget(header)

        # Conversation list
        scroll_area = QScrollArea()
        scroll_area.setObjectName("conversationList")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.conv_list_widget = QWidget()
        self.conv_list_layout = QVBoxLayout(self.conv_list_widget)
        self.conv_list_layout.setContentsMargins(8, 8, 8, 8)
        self.conv_list_layout.setSpacing(4)
        self.conv_list_layout.addStretch()

        scroll_area.setWidget(self.conv_list_widget)
        layout.addWidget(scroll_area)

        # Footer / Model info
        footer = QWidget()
        footer.setObjectName("resourceMonitor")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 8, 16, 8)

        self.model_label = QLabel("No model loaded")
        self.model_label.setObjectName("resourceText")
        self.model_label.setStyleSheet(
            "color: #6e6e8a; font-size: 11px; border: none;"
        )
        footer_layout.addWidget(self.model_label)
        footer_layout.addStretch()

        layout.addWidget(footer)

        # Width constraints are set in __init__ so the splitter stays usable

    def refresh_conversations(self):
        """Reload and display all conversations."""
        # Clear existing items
        for item in self._conversation_items.values():
            item.setParent(None)
            item.deleteLater()
        self._conversation_items.clear()

        # Clear layout (keep stretch)
        while self.conv_list_layout.count() > 1:
            item = self.conv_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Load conversations
        conversations = self._db.get_all_conversations()

        for conv in conversations:
            item = ConversationItem(
                conv_id=conv.id,
                title=conv.title,
                date=conv.updated_at,
                message_count=len(conv.messages) if conv.messages else 0,
                is_active=(conv.id == self._current_conv_id),
            )
            item.clicked.connect(self._on_conv_clicked)
            item.rename_requested.connect(self._on_rename)
            item.delete_requested.connect(self._on_delete)

            self._conversation_items[conv.id] = item
            self.conv_list_layout.insertWidget(
                self.conv_list_layout.count() - 1, item
            )

    def set_active_conversation(self, conv_id: str):
        """Set the active conversation."""
        self._current_conv_id = conv_id

        # Update visual state
        for cid, item in self._conversation_items.items():
            item.set_active(cid == conv_id)

    def _on_conv_clicked(self, conv_id: str):
        self.conversation_selected.emit(conv_id)

    def _on_search(self, text: str):
        """Filter conversations by search text."""
        if not text.strip():
            # Show all
            for item in self._conversation_items.values():
                item.setVisible(True)
            return

        # Search
        results = self._db.search_conversations(text)
        result_ids = {r.id for r in results}

        for cid, item in self._conversation_items.items():
            item.setVisible(cid in result_ids)

    def _on_rename(self, conv_id: str):
        """Handle conversation rename."""
        from PySide6.QtWidgets import QInputDialog
        current_title = ""
        conv = self._db.get_conversation(conv_id)
        if conv:
            current_title = conv.title

        new_title, ok = QInputDialog.getText(
            self, "Rename Conversation", "New title:",
            text=current_title
        )

        if ok and new_title.strip():
            self._db.update_conversation(conv_id, title=new_title.strip())
            self.refresh_conversations()

    def _on_delete(self, conv_id: str):
        """Handle conversation deletion."""
        reply = QMessageBox.question(
            self,
            "Delete Conversation",
            "Are you sure you want to delete this conversation?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._db.delete_conversation(conv_id)
            if conv_id == self._current_conv_id:
                self._current_conv_id = None
            self.conversation_deleted.emit(conv_id)
            self.refresh_conversations()

    def update_model_info(self, text: str):
        """Update the model info label in footer."""
        self.model_label.setText(text)
