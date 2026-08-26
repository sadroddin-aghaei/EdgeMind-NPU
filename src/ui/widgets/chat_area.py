"""
EdgeMind NPU - Chat Area Widget
Main chat display area with scrollable messages and welcome screen.
"""

from datetime import datetime
from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer

from src.ui.widgets.chat_bubble import MessageBubble, TypingIndicator


class WelcomeScreen(QWidget):
    """Welcome screen shown when no conversation is active."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # App icon
        icon = QLabel("⚡")
        icon.setStyleSheet("font-size: 64px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        # Title
        title = QLabel("EdgeMind NPU")
        title.setObjectName("welcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "font-size: 32px; font-weight: bold; color: #7c6ff7; border: none;"
        )
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Local AI Assistant • Powered by Your Hardware")
        subtitle.setObjectName("welcomeSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(
            "font-size: 16px; color: #a0a0b8; border: none;"
        )
        layout.addWidget(subtitle)

        layout.addSpacing(30)

        # Feature cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        features = [
            ("🧠", "NPU Acceleration", "Run AI models on\nIntel NPU"),
            ("🔒", "Fully Offline", "All processing\nstays on your device"),
            ("💬", "Chat Interface", "Natural conversations\nwith AI models"),
            ("📁", "File Analysis", "Upload and ask about\ndocuments and images"),
        ]

        for icon_text, title_text, desc_text in features:
            card = QFrame()
            card.setObjectName("welcomeCard")
            card.setFixedSize(180, 140)

            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 16, 16, 16)
            card_layout.setSpacing(8)

            feat_icon = QLabel(icon_text)
            feat_icon.setStyleSheet("font-size: 28px; border: none;")
            feat_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(feat_icon)

            feat_title = QLabel(title_text)
            feat_title.setStyleSheet(
                "font-size: 13px; font-weight: bold; color: #e4e4f0; border: none;"
            )
            feat_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(feat_title)

            feat_desc = QLabel(desc_text)
            feat_desc.setStyleSheet(
                "font-size: 11px; color: #a0a0b8; border: none;"
            )
            feat_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(feat_desc)

            cards_layout.addWidget(card)

        layout.addLayout(cards_layout)

        layout.addSpacing(30)

        # Quick start hint
        hint = QLabel("Select a model and start chatting!")
        hint.setStyleSheet(
            "color: #6e6e8a; font-size: 13px; border: none;"
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        layout.addStretch()


class ChatArea(QWidget):
    """Main chat display area with messages."""

    def __init__(self, rtl: bool = True, parent=None):
        super().__init__(parent)
        self.rtl = rtl
        self._messages: List[MessageBubble] = []
        self._typing_indicator: Optional[TypingIndicator] = None
        self._welcome_screen: Optional[WelcomeScreen] = None
        self._streaming_bubble: Optional[MessageBubble] = None

        # Throttled re-render timer for streaming updates
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(80)
        self._render_timer.timeout.connect(self._flush_streaming_render)

        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("chatArea")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Model info bar
        self.model_info_bar = QFrame()
        self.model_info_bar.setObjectName("modelInfoBar")
        info_layout = QHBoxLayout(self.model_info_bar)
        info_layout.setContentsMargins(16, 6, 16, 6)

        self.model_info_text = QLabel("No model selected")
        self.model_info_text.setObjectName("modelInfoText")
        self.model_info_text.setStyleSheet(
            "color: #a0a0b8; font-size: 12px; border: none;"
        )
        info_layout.addWidget(self.model_info_text)
        info_layout.addStretch()

        self.backend_badge = QLabel("")
        self.backend_badge.setObjectName("backendBadge")
        self.backend_badge.setStyleSheet(
            "background-color: #2d2d44; border: 1px solid #3a3a5c;"
            "border-radius: 4px; padding: 2px 8px; color: #a0a0b8; font-size: 11px;"
        )
        info_layout.addWidget(self.backend_badge)

        main_layout.addWidget(self.model_info_bar)

        # Scroll area for messages
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("chatScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        # Messages container
        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setContentsMargins(0, 16, 0, 16)
        self.messages_layout.setSpacing(4)
        self.messages_layout.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
        )

        # Content wrapper for max width
        self.content_wrapper = QWidget()
        self.content_wrapper.setMaximumWidth(860)
        self.content_wrapper.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.content_layout = QVBoxLayout(self.content_wrapper)
        self.content_layout.setContentsMargins(40, 0, 40, 0)
        self.content_layout.setSpacing(4)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.messages_layout.addWidget(self.content_wrapper)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_widget)
        main_layout.addWidget(self.scroll_area)

        # Show welcome screen initially
        self.show_welcome()

    def show_welcome(self):
        """Show the welcome screen."""
        self.clear_messages()
        self._welcome_screen = WelcomeScreen()
        self.content_layout.addWidget(self._welcome_screen)

    def hide_welcome(self):
        """Hide the welcome screen."""
        if self._welcome_screen:
            self._welcome_screen.setParent(None)
            self._welcome_screen.deleteLater()
            self._welcome_screen = None

    def clear_messages(self):
        """Remove all messages (and any welcome screen)."""
        self.hide_welcome()

        # Drop references to widgets we are about to destroy so late
        # streaming updates never touch deleted C++ objects.
        self._render_timer.stop()
        self.hide_typing()
        self._streaming_bubble = None

        for msg in self._messages:
            msg.setParent(None)
            msg.deleteLater()
        self._messages.clear()

        # Clear layout
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def add_user_message(self, content: str, timestamp: Optional[datetime] = None,
                         attachments: list = None):
        """Add a user message to the chat."""
        self.hide_welcome()

        # Add file references to content if any
        display_content = content
        if attachments:
            file_refs = "\n".join(f"📎 Attached: {a.split('/')[-1]}" for a in attachments)
            display_content = f"{content}\n\n{file_refs}" if content else file_refs

        bubble = MessageBubble(
            role="user",
            content=display_content,
            timestamp=timestamp,
            rtl=self.rtl,
        )
        self._messages.append(bubble)
        self.content_layout.addWidget(bubble)
        self._scroll_to_bottom()

    def add_assistant_message(self, content: str,
                               timestamp: Optional[datetime] = None,
                               model_id: str = ""):
        """Add a complete assistant message."""
        bubble = MessageBubble(
            role="assistant",
            content=content,
            timestamp=timestamp,
            model_id=model_id,
            rtl=self.rtl,
        )
        self._messages.append(bubble)
        self.content_layout.addWidget(bubble)
        self._scroll_to_bottom()
        return bubble

    def start_streaming_message(self, model_id: str = "") -> MessageBubble:
        """Start a new streaming assistant message."""
        self.hide_welcome()

        bubble = MessageBubble(
            role="assistant",
            content="",
            timestamp=datetime.now(),
            model_id=model_id,
            rtl=self.rtl,
        )
        self._streaming_bubble = bubble
        self._messages.append(bubble)
        self.content_layout.addWidget(bubble)
        self._scroll_to_bottom()
        return bubble

    def append_to_streaming(self, token: str):
        """Append a token to the current streaming message."""
        if self._streaming_bubble:
            # Buffer tokens; re-render at most every 80 ms to stay smooth
            self._streaming_bubble.content += token
            if not self._render_timer.isActive():
                self._render_timer.start()

    def _flush_streaming_render(self):
        """Re-render the streaming bubble (throttled)."""
        if self._streaming_bubble:
            self._streaming_bubble.update_content(
                self._streaming_bubble.content
            )
            self._scroll_to_bottom()

    def finish_streaming(self):
        """Finish the current streaming message."""
        self._render_timer.stop()
        if self._streaming_bubble:
            # Final full re-render so nothing buffered is lost
            self._streaming_bubble.update_content(
                self._streaming_bubble.content
            )
        self._streaming_bubble = None

    def show_typing(self):
        """Show typing indicator."""
        self.hide_typing()
        self._typing_indicator = TypingIndicator()
        self.content_layout.addWidget(self._typing_indicator)
        self._scroll_to_bottom()

    def hide_typing(self):
        """Hide typing indicator."""
        if self._typing_indicator:
            self._typing_indicator.stop()
            self._typing_indicator.setParent(None)
            self._typing_indicator.deleteLater()
            self._typing_indicator = None

    def set_model_info(self, model_name: str, backend: str = "",
                       device: str = ""):
        """Update the model info bar."""
        if model_name:
            self.model_info_text.setText(f"Model: {model_name}")
            badge_text = backend.upper()
            if device:
                badge_text += f" • {device}"
            self.backend_badge.setText(badge_text)
            self.backend_badge.setVisible(True)
        else:
            self.model_info_text.setText("No model selected")
            self.backend_badge.setVisible(False)

    def load_conversation(self, messages: List[Dict]):
        """Load a list of messages into the chat area."""
        self.clear_messages()

        for msg_data in messages:
            role = msg_data.get("role", "user")
            content = msg_data.get("content", "")
            timestamp_str = msg_data.get("created_at")

            timestamp = None
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                except Exception:
                    pass

            if role == "user":
                self.add_user_message(content, timestamp)
            elif role == "assistant":
                self.add_assistant_message(content, timestamp)

    def _scroll_to_bottom(self):
        """Scroll to the bottom of the message list."""
        QTimer.singleShot(50, self._do_scroll)

    def _do_scroll(self):
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
