"""
EdgeMind NPU - UI Styles
Comprehensive stylesheet for Windows 11 Fluent Design aesthetics.
Supports both dark and light themes.
"""


class Colors:
    """Color palette for themes."""

    # Dark Theme
    DARK = {
        "bg_primary": "#1e1e2e",
        "bg_secondary": "#252536",
        "bg_tertiary": "#2d2d44",
        "bg_hover": "#363654",
        "bg_active": "#414161",
        "bg_input": "#2a2a3e",
        "bg_message_user": "#3a3a5c",
        "bg_message_assistant": "#252536",
        "bg_code": "#1a1a2e",
        "bg_scrollbar": "#3a3a5c",
        "text_primary": "#e4e4f0",
        "text_secondary": "#a0a0b8",
        "text_muted": "#6e6e8a",
        "accent": "#7c6ff7",
        "accent_hover": "#9488ff",
        "accent_pressed": "#6050e0",
        "border": "#3a3a5c",
        "border_light": "#2d2d44",
        "success": "#4ecb71",
        "warning": "#f5a623",
        "error": "#f44336",
        "info": "#5c9eff",
        "shadow": "rgba(0, 0, 0, 0.3)",
    }

    # Light Theme
    LIGHT = {
        "bg_primary": "#f8f8fc",
        "bg_secondary": "#ffffff",
        "bg_tertiary": "#f0f0f6",
        "bg_hover": "#e8e8f0",
        "bg_active": "#d8d8e8",
        "bg_input": "#ffffff",
        "bg_message_user": "#e0deff",
        "bg_message_assistant": "#f4f4fa",
        "bg_code": "#f0f0f6",
        "bg_scrollbar": "#d0d0e0",
        "text_primary": "#1e1e2e",
        "text_secondary": "#5a5a72",
        "text_muted": "#8a8aa0",
        "accent": "#6355d4",
        "accent_hover": "#7c6ff7",
        "accent_pressed": "#5040b8",
        "border": "#d0d0e0",
        "border_light": "#e0e0f0",
        "success": "#3ba55c",
        "warning": "#d4910a",
        "error": "#d32f2f",
        "info": "#3d7fca",
        "shadow": "rgba(0, 0, 0, 0.1)",
    }


def get_stylesheet(theme: str = "dark") -> str:
    """Generate the complete stylesheet for the given theme."""
    c = Colors.DARK if theme == "dark" else Colors.LIGHT

    return f"""
    /* ── Global Styles ─────────────────────────────── */
    * {{
        font-family: 'Segoe UI', 'Tahoma', 'Arial', sans-serif;
        font-size: 14px;
    }}

    QWidget {{
        background-color: {c["bg_primary"]};
        color: {c["text_primary"]};
    }}

    /* ── Main Window ───────────────────────────────── */
    QMainWindow {{
        background-color: {c["bg_primary"]};
    }}

    /* ── Sidebar ────────────────────────────────────── */
    #sidebar {{
        background-color: {c["bg_secondary"]};
        border-right: 1px solid {c["border"]};
    }}

    #sidebarHeader {{
        background-color: {c["bg_secondary"]};
        border-bottom: 1px solid {c["border"]};
        padding: 12px;
    }}

    #sidebarTitle {{
        font-size: 18px;
        font-weight: bold;
        color: {c["accent"]};
        padding: 4px 0;
    }}

    #newChatBtn {{
        background-color: {c["accent"]};
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 16px;
        font-size: 14px;
        font-weight: 600;
    }}

    #newChatBtn:hover {{
        background-color: {c["accent_hover"]};
    }}

    #newChatBtn:pressed {{
        background-color: {c["accent_pressed"]};
    }}

    #searchInput {{
        background-color: {c["bg_input"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 8px 12px;
        color: {c["text_primary"]};
        font-size: 13px;
    }}

    #searchInput:focus {{
        border: 1px solid {c["accent"]};
    }}

    #searchInput::placeholder {{
        color: {c["text_muted"]};
    }}

    #conversationList {{
        background-color: transparent;
        border: none;
        padding: 4px;
    }}

    #conversationList QScrollBar:vertical {{
        width: 6px;
        background: transparent;
    }}

    #conversationList QScrollBar::handle:vertical {{
        background-color: {c["bg_scrollbar"]};
        border-radius: 3px;
        min-height: 30px;
    }}

    #conversationList QScrollBar::add-line:vertical,
    #conversationList QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    /* ── Conversation Item ──────────────────────────── */
    #convItem {{
        background-color: transparent;
        border: none;
        border-radius: 8px;
        padding: 10px 12px;
        text-align: right;
    }}

    #convItem:hover {{
        background-color: {c["bg_hover"]};
    }}

    #convItemActive {{
        background-color: {c["bg_active"]};
        border: 1px solid {c["accent"]};
    }}

    #convItemTitle {{
        color: {c["text_primary"]};
        font-size: 13px;
        font-weight: 500;
    }}

    #convItemDate {{
        color: {c["text_muted"]};
        font-size: 11px;
    }}

    /* ── Chat Area ──────────────────────────────────── */
    #chatArea {{
        background-color: {c["bg_primary"]};
        border: none;
    }}

    #chatScrollArea {{
        background-color: transparent;
        border: none;
    }}

    #chatScrollArea QScrollBar:vertical {{
        width: 8px;
        background: transparent;
    }}

    #chatScrollArea QScrollBar::handle:vertical {{
        background-color: {c["bg_scrollbar"]};
        border-radius: 4px;
        min-height: 40px;
    }}

    #chatScrollArea QScrollBar::add-line:vertical,
    #chatScrollArea QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    /* ── Messages ───────────────────────────────────── */
    #messageContainer {{
        background-color: transparent;
        border: none;
        padding: 8px 0;
    }}

    #userMessage {{
        background-color: {c["bg_message_user"]};
        border-radius: 16px;
        padding: 12px 18px;
        color: {c["text_primary"]};
        font-size: 14px;
        line-height: 1.5;
    }}

    #assistantMessage {{
        background-color: {c["bg_message_assistant"]};
        border-radius: 16px;
        padding: 12px 18px;
        color: {c["text_primary"]};
        font-size: 14px;
        line-height: 1.5;
    }}

    #systemMessage {{
        background-color: transparent;
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 8px 14px;
        color: {c["text_secondary"]};
        font-size: 12px;
        font-style: italic;
    }}

    #messageTimestamp {{
        color: {c["text_muted"]};
        font-size: 11px;
        padding: 2px 8px;
    }}

    /* ── Code Blocks ────────────────────────────────── */
    #codeBlock {{
        background-color: {c["bg_code"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 12px;
        font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
        font-size: 13px;
        color: {c["text_primary"]};
    }}

    #codeHeader {{
        background-color: {c["bg_tertiary"]};
        border-bottom: 1px solid {c["border"]};
        border-radius: 8px 8px 0 0;
        padding: 6px 12px;
    }}

    #copyBtn {{
        background-color: transparent;
        color: {c["text_secondary"]};
        border: 1px solid {c["border"]};
        border-radius: 4px;
        padding: 4px 10px;
        font-size: 12px;
    }}

    #copyBtn:hover {{
        background-color: {c["bg_hover"]};
        color: {c["text_primary"]};
    }}

    /* ── Input Area ─────────────────────────────────── */
    #inputArea {{
        background-color: {c["bg_secondary"]};
        border-top: 1px solid {c["border"]};
        padding: 12px;
    }}

    #inputContainer {{
        background-color: {c["bg_input"]};
        border: 1px solid {c["border"]};
        border-radius: 12px;
        padding: 4px;
    }}

    #inputContainer:focus-within {{
        border: 1px solid {c["accent"]};
    }}

    #messageInput {{
        background-color: transparent;
        border: none;
        color: {c["text_primary"]};
        font-size: 14px;
        padding: 8px 12px;
        selection-background-color: {c["accent"]};
    }}

    #messageInput:focus {{
        border: none;
    }}

    #sendBtn {{
        background-color: {c["accent"]};
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
        font-size: 14px;
        font-weight: 600;
    }}

    #sendBtn:hover {{
        background-color: {c["accent_hover"]};
    }}

    #sendBtn:pressed {{
        background-color: {c["accent_pressed"]};
    }}

    #sendBtn:disabled {{
        background-color: {c["bg_tertiary"]};
        color: {c["text_muted"]};
    }}

    #stopBtn {{
        background-color: {c["error"]};
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
        font-size: 14px;
        font-weight: 600;
    }}

    #stopBtn:hover {{
        background-color: #e53935;
    }}

    /* ── Model Info Bar ─────────────────────────────── */
    #modelInfoBar {{
        background-color: {c["bg_secondary"]};
        border-bottom: 1px solid {c["border"]};
        padding: 6px 16px;
    }}

    #modelInfoText {{
        color: {c["text_secondary"]};
        font-size: 12px;
    }}

    #backendBadge {{
        background-color: {c["bg_tertiary"]};
        border: 1px solid {c["border"]};
        border-radius: 4px;
        padding: 2px 8px;
        color: {c["text_secondary"]};
        font-size: 11px;
    }}

    /* ── Settings Dialog ────────────────────────────── */
    #settingsDialog {{
        background-color: {c["bg_primary"]};
    }}

    #settingsTab {{
        background-color: {c["bg_secondary"]};
        border: none;
        padding: 8px 16px;
        color: {c["text_secondary"]};
    }}

    #settingsTab:selected {{
        color: {c["accent"]};
        border-bottom: 2px solid {c["accent"]};
    }}

    /* ── General Widgets ────────────────────────────── */
    QLabel {{
        color: {c["text_primary"]};
    }}

    QLabel#labelSecondary {{
        color: {c["text_secondary"]};
    }}

    QLabel#labelMuted {{
        color: {c["text_muted"]};
    }}

    QPushButton {{
        background-color: {c["bg_tertiary"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 13px;
    }}

    QPushButton:hover {{
        background-color: {c["bg_hover"]};
        border: 1px solid {c["accent"]};
    }}

    QPushButton:pressed {{
        background-color: {c["bg_active"]};
    }}

    QLineEdit {{
        background-color: {c["bg_input"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 8px 12px;
        color: {c["text_primary"]};
        font-size: 13px;
        selection-background-color: {c["accent"]};
    }}

    QLineEdit:focus {{
        border: 1px solid {c["accent"]};
    }}

    QSpinBox, QDoubleSpinBox {{
        background-color: {c["bg_input"]};
        border: 1px solid {c["border"]};
        border-radius: 6px;
        padding: 6px 10px;
        color: {c["text_primary"]};
    }}

    QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {c["accent"]};
    }}

    QComboBox {{
        background-color: {c["bg_input"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 8px 12px;
        color: {c["text_primary"]};
    }}

    QComboBox:hover {{
        border: 1px solid {c["accent"]};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {c["bg_secondary"]};
        border: 1px solid {c["border"]};
        color: {c["text_primary"]};
        selection-background-color: {c["accent"]};
        border-radius: 8px;
        padding: 4px;
    }}

    QCheckBox {{
        color: {c["text_primary"]};
        spacing: 8px;
    }}

    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {c["border"]};
        border-radius: 4px;
        background-color: {c["bg_input"]};
    }}

    QCheckBox::indicator:checked {{
        background-color: {c["accent"]};
        border: 2px solid {c["accent"]};
    }}

    QSlider::groove:horizontal {{
        border: none;
        height: 4px;
        background-color: {c["bg_tertiary"]};
        border-radius: 2px;
    }}

    QSlider::handle:horizontal {{
        background-color: {c["accent"]};
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }}

    QSlider::handle:horizontal:hover {{
        background-color: {c["accent_hover"]};
    }}

    QProgressBar {{
        background-color: {c["bg_tertiary"]};
        border: none;
        border-radius: 4px;
        height: 8px;
        text-align: center;
    }}

    QProgressBar::chunk {{
        background-color: {c["accent"]};
        border-radius: 4px;
    }}

    QScrollBar:vertical {{
        width: 8px;
        background: transparent;
    }}

    QScrollBar::handle:vertical {{
        background-color: {c["bg_scrollbar"]};
        border-radius: 4px;
        min-height: 30px;
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QScrollBar:horizontal {{
        height: 8px;
        background: transparent;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {c["bg_scrollbar"]};
        border-radius: 4px;
        min-width: 30px;
    }}

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* ── Tooltip ────────────────────────────────────── */
    QToolTip {{
        background-color: {c["bg_secondary"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }}

    /* ── Resource Monitor ───────────────────────────── */
    #resourceMonitor {{
        background-color: {c["bg_secondary"]};
        border-top: 1px solid {c["border"]};
        padding: 4px 16px;
    }}

    #resourceText {{
        color: {c["text_muted"]};
        font-size: 11px;
    }}

    /* ── Model Card ─────────────────────────────────── */
    #modelCard {{
        background-color: {c["bg_secondary"]};
        border: 1px solid {c["border"]};
        border-radius: 12px;
        padding: 16px;
    }}

    #modelCard:hover {{
        border: 1px solid {c["accent"]};
    }}

    #modelCardName {{
        font-size: 16px;
        font-weight: 600;
        color: {c["text_primary"]};
    }}

    #modelCardDesc {{
        font-size: 13px;
        color: {c["text_secondary"]};
    }}

    #downloadBtn {{
        background-color: {c["accent"]};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 20px;
        font-size: 13px;
        font-weight: 600;
    }}

    #downloadBtn:hover {{
        background-color: {c["accent_hover"]};
    }}

    #deleteBtn {{
        background-color: transparent;
        color: {c["error"]};
        border: 1px solid {c["error"]};
        border-radius: 8px;
        padding: 8px 20px;
        font-size: 13px;
    }}

    #deleteBtn:hover {{
        background-color: {c["error"]};
        color: white;
    }}

    /* ── Welcome Screen ─────────────────────────────── */
    #welcomeTitle {{
        font-size: 28px;
        font-weight: bold;
        color: {c["text_primary"]};
    }}

    #welcomeSubtitle {{
        font-size: 16px;
        color: {c["text_secondary"]};
    }}

    #welcomeCard {{
        background-color: {c["bg_secondary"]};
        border: 1px solid {c["border"]};
        border-radius: 12px;
        padding: 16px;
    }}

    #welcomeCard:hover {{
        border: 1px solid {c["accent"]};
        background-color: {c["bg_hover"]};
    }}
    """


# RTL Stylesheet additions for Persian/Farsi
RTL_STYLES = """
    QTextEdit, QLineEdit {
        direction: rtl;
        text-align: right;
    }

    QLabel {
        text-align: right;
    }
"""
