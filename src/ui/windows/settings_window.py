"""
EdgeMind NPU - Settings Window
Application settings dialog with tabs for AI, UI, and system configuration.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QPushButton, QSlider, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QLineEdit,
    QFormLayout, QGroupBox, QScrollArea, QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal

from src.utils.settings import SettingsManager
from src.config import SYSTEM_PROMPTS


class SettingsWindow(QDialog):
    """Application settings dialog."""

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = SettingsManager()
        self.setWindowTitle("Settings - EdgeMind NPU")
        self.setMinimumSize(600, 500)
        self.setModal(True)

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)

        # AI Settings tab
        self.tabs.addTab(self._create_ai_tab(), "🤖 AI Model")

        # UI Settings tab
        self.tabs.addTab(self._create_ui_tab(), "🎨 Interface")

        # System tab
        self.tabs.addTab(self._create_system_tab(), "⚙ System")

        layout.addWidget(self.tabs)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(16, 12, 16, 16)

        btn_layout.addStretch()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(reset_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("downloadBtn")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _create_ai_tab(self) -> QWidget:
        """Create AI model settings tab."""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Model Selection
        model_group = QGroupBox("Model Selection")
        model_form = QFormLayout(model_group)

        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(300)
        model_form.addRow("Active Model:", self.model_combo)

        self.backend_combo = QComboBox()
        # Only backends with engine implementations are offered
        self.backend_combo.addItems(["Auto", "llamacpp", "openvino"])
        model_form.addRow("Backend:", self.backend_combo)

        layout.addWidget(model_group)

        # Generation Parameters
        gen_group = QGroupBox("Generation Parameters")
        gen_form = QFormLayout(gen_group)

        # Temperature
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(0, 200)
        self.temp_label = QLabel("0.70")
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(self.temp_slider)
        temp_layout.addWidget(self.temp_label)
        self.temp_slider.valueChanged.connect(
            lambda v: self.temp_label.setText(f"{v/100:.2f}")
        )
        gen_form.addRow("Temperature:", temp_layout)

        # Top P
        self.top_p_slider = QSlider(Qt.Orientation.Horizontal)
        self.top_p_slider.setRange(0, 100)
        self.top_p_label = QLabel("0.90")
        top_p_layout = QHBoxLayout()
        top_p_layout.addWidget(self.top_p_slider)
        top_p_layout.addWidget(self.top_p_label)
        self.top_p_slider.valueChanged.connect(
            lambda v: self.top_p_label.setText(f"{v/100:.2f}")
        )
        gen_form.addRow("Top P:", top_p_layout)

        # Top K
        self.top_k_spin = QSpinBox()
        self.top_k_spin.setRange(1, 100)
        self.top_k_spin.setValue(40)
        gen_form.addRow("Top K:", self.top_k_spin)

        # Max Tokens
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(64, 8192)
        self.max_tokens_spin.setValue(2048)
        self.max_tokens_spin.setSingleStep(256)
        gen_form.addRow("Max Tokens:", self.max_tokens_spin)

        # Repeat Penalty
        self.repeat_spin = QDoubleSpinBox()
        self.repeat_spin.setRange(1.0, 2.0)
        self.repeat_spin.setValue(1.1)
        self.repeat_spin.setSingleStep(0.05)
        gen_form.addRow("Repeat Penalty:", self.repeat_spin)

        layout.addWidget(gen_group)

        # Context & Performance
        perf_group = QGroupBox("Context & Performance")
        perf_form = QFormLayout(perf_group)

        self.context_spin = QSpinBox()
        self.context_spin.setRange(512, 131072)
        self.context_spin.setValue(4096)
        self.context_spin.setSingleStep(1024)
        perf_form.addRow("Context Length:", self.context_spin)

        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 64)
        self.threads_spin.setValue(4)
        perf_form.addRow("CPU Threads:", self.threads_spin)

        self.gpu_layers_spin = QSpinBox()
        self.gpu_layers_spin.setRange(0, 100)
        self.gpu_layers_spin.setValue(0)
        perf_form.addRow("GPU Layers:", self.gpu_layers_spin)

        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(64, 2048)
        self.batch_spin.setValue(512)
        self.batch_spin.setSingleStep(64)
        perf_form.addRow("Batch Size:", self.batch_spin)

        layout.addWidget(perf_group)

        # System Prompt
        prompt_group = QGroupBox("System Prompt")
        prompt_layout = QVBoxLayout(prompt_group)

        self.prompt_combo = QComboBox()
        self.prompt_combo.addItems(list(SYSTEM_PROMPTS.keys()))
        self.prompt_combo.currentTextChanged.connect(self._on_prompt_preset)
        prompt_layout.addWidget(self.prompt_combo)

        self.system_prompt_edit = QLineEdit()
        self.system_prompt_edit.setPlaceholderText("Custom system prompt...")
        self.system_prompt_edit.setMinimumHeight(60)
        prompt_layout.addWidget(self.system_prompt_edit)

        layout.addWidget(prompt_group)

        layout.addStretch()
        scroll.setWidget(content)

        tab_layout = QVBoxLayout(widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        return widget

    def _create_ui_tab(self) -> QWidget:
        """Create UI settings tab."""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Appearance
        appearance_group = QGroupBox("Appearance")
        appearance_form = QFormLayout(appearance_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light", "system"])
        appearance_form.addRow("Theme:", self.theme_combo)

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["فارسی (Persian)", "English"])
        appearance_form.addRow("Language:", self.lang_combo)

        self.font_spin = QSpinBox()
        self.font_spin.setRange(10, 24)
        self.font_spin.setValue(14)
        appearance_form.addRow("Font Size:", self.font_spin)

        layout.addWidget(appearance_group)

        # Chat Options
        chat_group = QGroupBox("Chat Options")
        chat_form = QFormLayout(chat_group)

        self.timestamps_check = QCheckBox("Show message timestamps")
        self.timestamps_check.setChecked(True)
        chat_form.addRow(self.timestamps_check)

        self.streaming_check = QCheckBox("Enable response streaming")
        self.streaming_check.setChecked(True)
        chat_form.addRow(self.streaming_check)

        self.token_count_check = QCheckBox("Show token count")
        chat_form.addRow(self.token_count_check)

        layout.addWidget(chat_group)

        # RTL
        rtl_group = QGroupBox("Persian / RTL Support")
        rtl_form = QFormLayout(rtl_group)

        self.rtl_check = QCheckBox("Enable RTL (Right-to-Left) layout")
        self.rtl_check.setChecked(True)
        rtl_form.addRow(self.rtl_check)

        layout.addWidget(rtl_group)

        layout.addStretch()
        scroll.setWidget(content)

        tab_layout = QVBoxLayout(widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        return widget

    def _create_system_tab(self) -> QWidget:
        """Create system settings tab."""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Storage
        storage_group = QGroupBox("Storage")
        storage_form = QFormLayout(storage_group)

        storage_layout = QHBoxLayout()
        self.models_dir_edit = QLineEdit()
        self.models_dir_edit.setReadOnly(True)
        storage_layout.addWidget(self.models_dir_edit)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse_dir)
        storage_layout.addWidget(browse_btn)
        storage_form.addRow("Models Directory:", storage_layout)

        self.max_storage_spin = QDoubleSpinBox()
        self.max_storage_spin.setRange(1.0, 100.0)
        self.max_storage_spin.setValue(20.0)
        self.max_storage_spin.setSuffix(" GB")
        storage_form.addRow("Max Storage:", self.max_storage_spin)

        layout.addWidget(storage_group)

        # Export/Import
        data_group = QGroupBox("Data Management")
        data_layout = QVBoxLayout(data_group)

        export_btn = QPushButton("📤 Export All Conversations")
        export_btn.clicked.connect(self._on_export)
        data_layout.addWidget(export_btn)

        import_btn = QPushButton("📥 Import Conversations")
        import_btn.clicked.connect(self._on_import)
        data_layout.addWidget(import_btn)

        layout.addWidget(data_group)

        # About
        about_group = QGroupBox("About")
        about_layout = QVBoxLayout(about_group)

        about_text = QLabel(
            "<b>EdgeMind NPU</b> v1.0.0<br><br>"
            "Local AI Assistant with NPU/GPU/CPU Acceleration<br>"
            "by <b>Sadroddin Aghaei</b><br><br>"
            "All processing happens on your device. "
            "No data is sent to the cloud."
        )
        about_text.setWordWrap(True)
        about_text.setStyleSheet("color: #a0a0b8;")
        about_layout.addWidget(about_text)

        layout.addWidget(about_group)

        layout.addStretch()
        scroll.setWidget(content)

        tab_layout = QVBoxLayout(widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        return widget

    def _load_settings(self):
        """Load current settings into the UI."""
        s = self._settings.settings

        # AI
        self.temp_slider.setValue(int(s.ai.temperature * 100))
        self.top_p_slider.setValue(int(s.ai.top_p * 100))
        self.top_k_spin.setValue(s.ai.top_k)
        self.max_tokens_spin.setValue(s.ai.max_tokens)
        self.repeat_spin.setValue(s.ai.repeat_penalty)
        self.context_spin.setValue(s.ai.context_length)
        self.threads_spin.setValue(s.ai.threads)
        self.gpu_layers_spin.setValue(s.ai.gpu_layers)
        self.batch_spin.setValue(s.ai.batch_size)
        self.system_prompt_edit.setText(s.ai.system_prompt)

        # UI
        idx = self.theme_combo.findText(s.ui.theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.font_spin.setValue(s.ui.font_size)
        self.timestamps_check.setChecked(s.ui.show_timestamps)
        self.streaming_check.setChecked(s.ui.streaming_enabled)
        self.token_count_check.setChecked(s.ui.show_token_count)
        self.rtl_check.setChecked(s.ui.rtl_mode)

        # Storage
        from src.config import MODELS_DIR
        self.models_dir_edit.setText(str(MODELS_DIR))
        self.max_storage_spin.setValue(s.storage.max_storage_gb)

    def _on_save(self):
        """Save all settings."""
        s = self._settings

        # AI settings
        s.update_ai(
            temperature=self.temp_slider.value() / 100,
            top_p=self.top_p_slider.value() / 100,
            top_k=self.top_k_spin.value(),
            max_tokens=self.max_tokens_spin.value(),
            repeat_penalty=self.repeat_spin.value(),
            context_length=self.context_spin.value(),
            threads=self.threads_spin.value(),
            gpu_layers=self.gpu_layers_spin.value(),
            batch_size=self.batch_spin.value(),
            system_prompt=self.system_prompt_edit.text(),
        )

        # UI settings
        lang_text = self.lang_combo.currentText()
        lang = "fa" if "فارسی" in lang_text else "en"
        s.update_ui(
            theme=self.theme_combo.currentText(),
            language=lang,
            font_size=self.font_spin.value(),
            show_timestamps=self.timestamps_check.isChecked(),
            streaming_enabled=self.streaming_check.isChecked(),
            show_token_count=self.token_count_check.isChecked(),
            rtl_mode=self.rtl_check.isChecked(),
        )

        # Storage
        s.update_storage(
            max_storage_gb=self.max_storage_spin.value(),
        )

        self.settings_changed.emit()
        self.accept()

    def _on_reset(self):
        """Reset to default settings."""
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._settings.reset()
            self._load_settings()

    def _on_prompt_preset(self, preset_name: str):
        """Load a system prompt preset."""
        if preset_name in SYSTEM_PROMPTS:
            self.system_prompt_edit.setText(SYSTEM_PROMPTS[preset_name])

    def _on_browse_dir(self):
        """Browse for models directory."""
        from src.config import MODELS_DIR
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Models Directory", str(MODELS_DIR)
        )
        if dir_path:
            self.models_dir_edit.setText(dir_path)

    def _on_export(self):
        """Export conversations."""
        from src.config import EXPORTS_DIR
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Conversations",
            str(EXPORTS_DIR / "conversations_export.json"),
            "JSON Files (*.json)"
        )
        if filepath:
            self._do_export(filepath)

    def _do_export(self, filepath: str):
        """Perform the export."""
        import json
        from src.database.db_manager import DatabaseManager
        db = DatabaseManager()

        conversations = db.get_all_conversations(include_archived=True)
        export_data = []

        for conv in conversations:
            conv_data = db.export_conversation(conv.id)
            if conv_data:
                export_data.append(conv_data)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            QMessageBox.information(
                self, "Export Complete",
                f"Exported {len(export_data)} conversations."
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Export Error", str(e)
            )

    def _on_import(self):
        """Import conversations."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Conversations", "",
            "JSON Files (*.json)"
        )
        if filepath:
            self._do_import(filepath)

    def _do_import(self, filepath: str):
        """Perform the import."""
        import json
        from src.database.db_manager import DatabaseManager
        db = DatabaseManager()

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, list):
                count = 0
                for item in data:
                    db.import_conversation(item)
                    count += 1
                QMessageBox.information(
                    self, "Import Complete",
                    f"Imported {count} conversations."
                )
            else:
                QMessageBox.warning(
                    self, "Import Error",
                    "Invalid file format."
                )
        except Exception as e:
            QMessageBox.critical(self, "Import Error", str(e))
