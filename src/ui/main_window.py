"""
EdgeMind NPU - Main Window
The primary application window that orchestrates all components.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QMessageBox, QFileDialog,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QFont, QAction

from src.config import APP_NAME, APP_VERSION, APP_AUTHOR, UI_CONFIG, BASE_DIR
from src.database.db_manager import DatabaseManager
from src.utils.settings import SettingsManager
from src.utils.hardware import HardwareDetector
from src.utils.file_processor import FileProcessor
from src.ai_engine.engine_manager import EngineManager
from src.model_manager.manager import ModelManager
from src.ui.styles import get_stylesheet, RTL_STYLES
from src.ui.widgets.sidebar import Sidebar
from src.ui.widgets.chat_area import ChatArea
from src.ui.widgets.message_input import MessageInput
from src.ui.widgets.resource_monitor import ResourceMonitor
from src.ui.windows.settings_window import SettingsWindow
from src.ui.windows.model_manager_window import ModelManagerWindow

logger = logging.getLogger(__name__)


class GenerationThread(QThread):
    """Background thread for AI generation."""

    token_generated = Signal(str)
    generation_complete = Signal(str, float)
    generation_error = Signal(str)

    def __init__(self, engine: EngineManager, messages: list):
        super().__init__()
        self.engine = engine
        self.messages = messages
        self._stop = False

    def run(self):
        try:
            full_response = ""
            start_time = datetime.now()

            for token in self.engine.generate_stream(self.messages):
                if self._stop:
                    break
                full_response += token
                self.token_generated.emit(token)

            elapsed = (datetime.now() - start_time).total_seconds()
            self.generation_complete.emit(full_response, elapsed)

        except Exception as e:
            self.generation_error.emit(str(e))

    def stop(self):
        self._stop = True
        self.engine.stop_generation()


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # Core components
        self._db = DatabaseManager()
        self._settings = SettingsManager()
        self._hardware = HardwareDetector()
        self._engine = EngineManager()
        self._model_manager = ModelManager()
        self._file_processor = FileProcessor()

        # State
        self._current_conv_id: Optional[str] = None
        self._generation_thread: Optional[GenerationThread] = None
        self._generating_conv_id: Optional[str] = None
        self._attached_files = []

        # Setup UI
        self._setup_window()
        self._setup_ui()
        self._setup_menu()
        self._apply_theme()
        self._setup_connections()
        self._detect_hardware()

    def _setup_window(self):
        """Configure the main window."""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(
            UI_CONFIG["window_min_width"],
            UI_CONFIG["window_min_height"],
        )
        self.resize(1200, 800)

        # Set app icon
        icon_path = BASE_DIR / "icons" / "app.ico"
        if not icon_path.exists():
            icon_path = BASE_DIR / "icons" / "app.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _setup_ui(self):
        """Set up all UI components."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Splitter for sidebar/main area
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)

        # Sidebar
        self.sidebar = Sidebar()
        self.splitter.addWidget(self.sidebar)

        # Main chat area
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Chat area
        rtl = self._settings.settings.ui.rtl_mode
        self.chat_area = ChatArea(rtl=rtl)
        right_layout.addWidget(self.chat_area, stretch=1)

        # Message input
        self.message_input = MessageInput(rtl=rtl)
        right_layout.addWidget(self.message_input)

        # Resource monitor
        self.resource_monitor = ResourceMonitor()
        right_layout.addWidget(self.resource_monitor)

        self.splitter.addWidget(right_widget)

        # Set splitter proportions
        self.splitter.setSizes([280, 920])

        main_layout.addWidget(self.splitter)

    def _setup_menu(self):
        """Set up the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        new_chat_action = QAction("New Chat", self)
        new_chat_action.setShortcut("Ctrl+N")
        new_chat_action.triggered.connect(self._on_new_chat)
        file_menu.addAction(new_chat_action)

        file_menu.addSeparator()

        import_action = QAction("Import Conversations", self)
        import_action.triggered.connect(self._on_import)
        file_menu.addAction(import_action)

        export_action = QAction("Export Conversations", self)
        export_action.triggered.connect(self._on_export)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        quit_action = QAction("Exit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Model menu
        model_menu = menubar.addMenu("Model")

        model_manager_action = QAction("Model Manager", self)
        model_manager_action.setShortcut("Ctrl+M")
        model_manager_action.triggered.connect(self._open_model_manager)
        model_menu.addAction(model_manager_action)

        # View menu
        view_menu = menubar.addMenu("View")

        settings_action = QAction("Settings", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._open_settings)
        view_menu.addAction(settings_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_connections(self):
        """Connect signals between components."""
        # Sidebar
        self.sidebar.new_chat_requested.connect(self._on_new_chat)
        self.sidebar.conversation_selected.connect(self._on_select_conversation)
        self.sidebar.conversation_deleted.connect(self._on_conversation_deleted)

        # Message input
        self.message_input.message_sent.connect(self._on_send_message)
        self.message_input.stop_requested.connect(self._on_stop_generation)

        # Settings
        self.sidebar.settings_requested.connect(self._open_settings)

    def _apply_theme(self):
        """Apply the current theme stylesheet."""
        theme = self._settings.settings.ui.theme
        stylesheet = get_stylesheet(theme)

        # Add RTL styles if needed
        if self._settings.settings.ui.rtl_mode:
            stylesheet += RTL_STYLES

        self.setStyleSheet(stylesheet)

        # Set font
        font = QFont(UI_CONFIG["font_family"], self._settings.settings.ui.font_size)
        self.setFont(font)

    def _detect_hardware(self):
        """Detect hardware and display status."""
        try:
            info = self._hardware.detect()

            # Update resource monitor
            if info.npu.available:
                self.resource_monitor.set_npu_info(f"Ready ({info.npu.name})")
            else:
                self.resource_monitor.set_npu_info("Not available")

            if info.gpus:
                gpu = info.gpus[0]
                vram = f" ({gpu.vram_mb} MB)" if gpu.vram_mb > 0 else ""
                self.resource_monitor.set_gpu_info(f"{gpu.name}{vram}")
            else:
                self.resource_monitor.set_gpu_info("Not detected")

            # Update sidebar model info
            backends = self._hardware.get_available_backends()
            backend_text = ", ".join(b.value for b in backends[:3])
            self.sidebar.update_model_info(
                f"Tier: {info.tier.value} • {backend_text}"
            )

        except Exception as e:
            logger.error(f"Hardware detection error: {e}")

    def _on_new_chat(self):
        """Create a new conversation."""
        conv = self._db.create_conversation()
        self._current_conv_id = conv.id

        self.sidebar.set_active_conversation(conv.id)
        self.sidebar.refresh_conversations()
        self.chat_area.show_welcome()

    def _on_select_conversation(self, conv_id: str):
        """Load and display a conversation."""
        self._current_conv_id = conv_id
        self.sidebar.set_active_conversation(conv_id)

        # Load messages
        messages = self._db.get_messages(conv_id)
        msg_data = [m.to_dict() for m in messages]

        self.chat_area.clear_messages()
        self.chat_area.load_conversation(msg_data)

    def _on_conversation_deleted(self, conv_id: str):
        """Handle conversation deletion."""
        if conv_id == self._current_conv_id:
            self._current_conv_id = None
            self.chat_area.show_welcome()

    def _on_send_message(self, text: str, file_paths: list):
        """Handle sending a message."""
        if not text.strip() and not file_paths:
            return

        # Create conversation if needed
        if not self._current_conv_id:
            conv = self._db.create_conversation()
            self._current_conv_id = conv.id
            self.sidebar.set_active_conversation(conv.id)

        # Process file attachments
        file_context = ""
        for fp in file_paths:
            if self._file_processor.is_supported(fp):
                file_context += self._file_processor.prepare_for_llm(fp) + "\n\n"

        # Combine text with file context
        full_content = text
        if file_context:
            full_content = f"{text}\n\n--- Attached Files ---\n{file_context}"

        # Save user message
        self._db.add_message(
            self._current_conv_id, "user", full_content,
            attachments=file_paths,
        )

        # Update sidebar title on first message
        messages = self._db.get_messages(self._current_conv_id)
        if len(messages) == 1:
            self._db.auto_title_conversation(self._current_conv_id, text)
            self.sidebar.refresh_conversations()

        # Display user message
        self.chat_area.add_user_message(text, attachments=file_paths)

        # Check if model is loaded
        if not self._engine.is_model_loaded:
            self.chat_area.add_assistant_message(
                "⚠️ No model loaded. Please load a model first.\n\n"
                "Go to **Model Manager** (Ctrl+M) to download and load a model."
            )
            return

        # Prepare messages for generation
        conv_messages = []
        system_prompt = self._settings.settings.ai.system_prompt
        memory_context = self._db.get_memory_context()

        if system_prompt:
            conv_messages.append({"role": "system", "content": system_prompt})

        if memory_context:
            conv_messages.append({"role": "system", "content": memory_context})

        for msg in messages:
            conv_messages.append({
                "role": msg.role,
                "content": msg.content,
            })

        # Start generation
        self._start_generation(conv_messages)

    def _start_generation(self, messages: list):
        """Start AI generation in background thread."""
        # Remember which conversation this generation belongs to, so a
        # mid-generation conversation switch cannot misplace the reply.
        self._generating_conv_id = self._current_conv_id

        self.message_input.set_generating(True)
        self.chat_area.show_typing()

        self._generation_thread = GenerationThread(self._engine, messages)
        self._generation_thread.token_generated.connect(self._on_token)
        self._generation_thread.generation_complete.connect(self._on_generation_complete)
        self._generation_thread.generation_error.connect(self._on_generation_error)
        self._generation_thread.start()

    def _on_token(self, token: str):
        """Handle a generated token."""
        if not self.chat_area._streaming_bubble:
            # Tokens from a generation started in another conversation
            # must not create a bubble in the currently viewed one.
            if self._generating_conv_id != self._current_conv_id:
                return
            self.chat_area.hide_typing()
            self.chat_area.start_streaming_message()

        self.chat_area.append_to_streaming(token)

    def _on_generation_complete(self, text: str, elapsed: float):
        """Handle generation completion."""
        conv_id = self._generating_conv_id or self._current_conv_id
        self._generating_conv_id = None

        # The view may have moved on; only finish the bubble we own.
        if conv_id == self._current_conv_id or text:
            self.chat_area.finish_streaming()

        # Save assistant message to the conversation it belongs to
        if conv_id and text:
            self._db.add_message(
                conv_id, "assistant", text,
                model_id=self._engine.active_model_id,
                latency_ms=elapsed * 1000,
            )

        if conv_id == self._current_conv_id:
            self.message_input.set_generating(False)
            self.sidebar.refresh_conversations()
        elif self._generation_thread is None:
            self.message_input.set_generating(False)

    def _on_generation_error(self, error: str):
        """Handle generation error."""
        conv_id = self._generating_conv_id
        self._generating_conv_id = None

        if conv_id == self._current_conv_id or conv_id is None:
            self.chat_area.hide_typing()
            self.chat_area.add_assistant_message(f"❌ Error: {error}")
            self.message_input.set_generating(False)

    def _on_stop_generation(self):
        """Stop the current generation."""
        if self._generation_thread:
            self._generation_thread.stop()
            self._generation_thread.wait(2000)
            self._generation_thread = None

        self._generating_conv_id = None
        self.chat_area.finish_streaming()
        self.message_input.set_generating(False)

    def _open_model_manager(self):
        """Open the Model Manager window."""
        dialog = ModelManagerWindow(self)
        dialog.model_loaded.connect(self._on_model_loaded)
        dialog.exec()

    def _on_model_loaded(self, model_id: str):
        """Handle a model being loaded."""
        success = self._model_manager.load_model(model_id)
        if success:
            status = self._engine.get_status()
            model_info = self._model_manager.get_model_info(model_id)

            model_name = model_info.get("name", model_id) if model_info else model_id
            backend = status.get("backend", "")
            device = status.get("device", "")

            self.chat_area.set_model_info(model_name, backend, device)
            self.resource_monitor.set_backend(backend, device)
            self.sidebar.update_model_info(f"Active: {model_name}")

            # Apply recommended GPU layers
            if self._settings.settings.ai.gpu_layers == 0:
                gpu_layers = self._hardware.get_recommended_gpu_layers()
                self._settings.update_ai(gpu_layers=gpu_layers)

            self.chat_area.add_assistant_message(
                f"✅ Model loaded: **{model_name}**\n"
                f"Backend: {backend.upper()} ({device})\n\n"
                f"You can start chatting now!"
            )
        else:
            self.chat_area.add_assistant_message(
                f"❌ Failed to load model: {model_id}\n\n"
                f"Please check the logs for more details."
            )

    def _open_settings(self):
        """Open the Settings window."""
        dialog = SettingsWindow(self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def _on_settings_changed(self):
        """Handle settings changes."""
        self._apply_theme()

    def _on_import(self):
        """Import conversations from file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Conversations", "",
            "JSON Files (*.json)"
        )
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if isinstance(data, list):
                    for item in data:
                        self._db.import_conversation(item)
                    self.sidebar.refresh_conversations()
                    QMessageBox.information(
                        self, "Import Complete",
                        f"Imported {len(data)} conversations."
                    )
            except Exception as e:
                QMessageBox.critical(self, "Import Error", str(e))

    def _on_export(self):
        """Export conversations to file."""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Conversations", "conversations.json",
            "JSON Files (*.json)"
        )
        if filepath:
            try:
                conversations = self._db.get_all_conversations()
                export_data = []
                for conv in conversations:
                    data = self._db.export_conversation(conv.id)
                    if data:
                        export_data.append(data)

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

                QMessageBox.information(
                    self, "Export Complete",
                    f"Exported {len(export_data)} conversations."
                )
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def _show_about(self):
        """Show About dialog."""
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            f"<p>Local AI Assistant with NPU/GPU/CPU Acceleration</p>"
            f"<p>by <b>{APP_AUTHOR}</b></p>"
            f"<p>Run AI models like Gemma and Qwen locally on your "
            f"Windows device with hardware acceleration.</p>"
            f"<p>All processing happens on your device. "
            f"No data is sent to the cloud.</p>"
            f"<hr>"
            f"<p><small>© 2024 {APP_AUTHOR}. All rights reserved.</small></p>"
        )

    def closeEvent(self, event):
        """Handle window close."""
        # Stop any ongoing generation
        if self._generation_thread:
            self._generation_thread.stop()
            self._generation_thread.wait(2000)

        # Unload model
        self._engine.unload_model()

        event.accept()
