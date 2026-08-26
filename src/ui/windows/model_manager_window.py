"""
EdgeMind NPU - Model Manager Window
UI for browsing, downloading, and managing AI models.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QProgressBar,
    QSizePolicy, QMessageBox, QWidget,
)
from PySide6.QtCore import Qt, Signal

from src.config import AVAILABLE_MODELS
from src.model_manager.manager import ModelManager
from src.model_manager.downloader import DownloadProgress


class ModelCard(QFrame):
    """A card displaying model information and actions."""

    download_requested = Signal(str)
    load_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, model_data: dict, parent=None):
        super().__init__(parent)
        self.model_data = model_data
        self.model_id = model_data.get("id", "")
        self._is_downloading = False
        self._progress = 0

        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("modelCard")
        self.setMinimumHeight(120)
        self.setMaximumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(20)

        # Left side - Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)

        # Model name and family
        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        icon = self.model_data.get("icon", "")
        icon_map = {"gemma": "💎", "qwen": "🌊", "phi": "🔬"}
        icon_text = icon_map.get(icon, "🤖")

        icon_label = QLabel(icon_text)
        icon_label.setStyleSheet("font-size: 24px; border: none;")
        name_row.addWidget(icon_label)

        name_label = QLabel(self.model_data.get("name", self.model_id))
        name_label.setObjectName("modelCardName")
        name_row.addWidget(name_label)

        # Tags
        tags = self.model_data.get("tags", [])
        for tag in tags[:2]:
            tag_label = QLabel(tag)
            tag_label.setStyleSheet(
                "background-color: #7c6ff7; color: white; border-radius: 4px;"
                "padding: 2px 8px; font-size: 10px; border: none;"
            )
            name_row.addWidget(tag_label)

        name_row.addStretch()
        info_layout.addLayout(name_row)

        # Description
        desc = QLabel(self.model_data.get("description", ""))
        desc.setObjectName("modelCardDesc")
        desc.setWordWrap(True)
        desc.setStyleSheet(
            "color: #a0a0b8; font-size: 13px; border: none;"
        )
        info_layout.addWidget(desc)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        size = self.model_data.get("size_gb", 0)
        stats_row.addWidget(self._stat_label(f"📦 {size} GB"))

        memory = self.model_data.get("memory_required_gb", 0)
        stats_row.addWidget(self._stat_label(f"💾 ~{memory} GB RAM"))

        ctx = self.model_data.get("context_length", 0)
        stats_row.addWidget(self._stat_label(f"📏 {ctx//1024}K context"))

        stats_row.addStretch()
        info_layout.addLayout(stats_row)

        layout.addLayout(info_layout, stretch=1)

        # Right side - Actions
        action_layout = QVBoxLayout()
        action_layout.setSpacing(8)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignCenter)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(
            "color: #a0a0b8; font-size: 12px; border: none;"
        )
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        action_layout.addWidget(self.status_label)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(180)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setVisible(False)
        action_layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignRight)

        # Action buttons
        is_downloaded = self.model_data.get("is_downloaded", False)

        if is_downloaded:
            self.load_btn = QPushButton("▶ Load Model")
            self.load_btn.setObjectName("downloadBtn")
            self.load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.load_btn.clicked.connect(lambda: self.load_requested.emit(self.model_id))
            self.load_btn.setFixedWidth(160)
            action_layout.addWidget(self.load_btn, alignment=Qt.AlignmentFlag.AlignRight)

            self.delete_btn = QPushButton("🗑 Delete")
            self.delete_btn.setObjectName("deleteBtn")
            self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.model_id))
            self.delete_btn.setFixedWidth(160)
            action_layout.addWidget(self.delete_btn, alignment=Qt.AlignmentFlag.AlignRight)

            file_size = self.model_data.get("file_size", 0)
            if file_size > 0:
                size_text = DownloadProgress._human_size(file_size)
                self.status_label.setText(f"✅ Downloaded ({size_text})")
        else:
            self.download_btn = QPushButton("⬇ Download")
            self.download_btn.setObjectName("downloadBtn")
            self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.download_btn.clicked.connect(lambda: self.download_requested.emit(self.model_id))
            self.download_btn.setFixedWidth(160)
            action_layout.addWidget(self.download_btn, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addLayout(action_layout)

    def _stat_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(
            "color: #6e6e8a; font-size: 11px; border: none;"
        )
        return label

    def set_progress(self, progress: DownloadProgress):
        """Update download progress."""
        if progress.status == "downloading":
            self._is_downloading = True
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(int(progress.percent))
            self.status_label.setText(
                f"⬇ {progress.percent:.1f}%  •  {progress.speed_human}"
            )
            if hasattr(self, 'download_btn'):
                self.download_btn.setEnabled(False)
                self.download_btn.setText("Downloading...")

        elif progress.status == "completed":
            self._is_downloading = False
            self.progress_bar.setVisible(False)
            self.status_label.setText("✅ Download complete!")
            if hasattr(self, 'download_btn'):
                self.download_btn.setText("✅ Downloaded")
                self.download_btn.setEnabled(False)

        elif progress.status == "error":
            self._is_downloading = False
            self.progress_bar.setVisible(False)
            error_text = progress.error[:60] + "..." if len(progress.error) > 60 else progress.error
            self.status_label.setText(f"❌ {error_text}")
            self.status_label.setStyleSheet(
                "color: #f44336; font-size: 12px; border: none;"
            )
            if hasattr(self, 'download_btn'):
                self.download_btn.setText("⬇ Retry Download")
                self.download_btn.setEnabled(True)

        elif progress.status == "cancelled":
            self._is_downloading = False
            self.progress_bar.setVisible(False)
            self.status_label.setText("Cancelled")
            if hasattr(self, 'download_btn'):
                self.download_btn.setText("⬇ Download")
                self.download_btn.setEnabled(True)


class ModelManagerWindow(QDialog):
    """Model Manager dialog window."""

    model_loaded = Signal(str)  # model_id

    # Internal signals: download callbacks fire on the worker thread,
    # these marshal updates onto the GUI thread safely.
    _download_progress = Signal(str, object)
    _download_complete = Signal(str, bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = ModelManager()
        self.setWindowTitle("Model Manager - EdgeMind NPU")
        self.setMinimumSize(700, 500)
        self.setModal(False)

        self._model_cards: dict = {}

        self._download_progress.connect(self._on_progress)
        self._download_complete.connect(self._on_complete)

        self._setup_ui()
        self._refresh_models()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet(
            "background-color: #252536; border-bottom: 1px solid #3a3a5c; padding: 16px;"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)

        title = QLabel("📦 Model Manager")
        title.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #e4e4f0; border: none;"
        )
        header_layout.addWidget(title)
        header_layout.addStretch()

        storage = self._manager.get_storage_usage()
        storage_label = QLabel(f"Used: {storage['total_human']}")
        storage_label.setStyleSheet(
            "color: #a0a0b8; font-size: 12px; border: none;"
        )
        header_layout.addWidget(storage_label)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._refresh_models)
        header_layout.addWidget(refresh_btn)

        layout.addWidget(header)

        # Model list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.model_list_widget = QWidget()
        self.model_list_layout = QVBoxLayout(self.model_list_widget)
        self.model_list_layout.setContentsMargins(20, 16, 20, 16)
        self.model_list_layout.setSpacing(12)

        self.model_list_layout.addStretch()
        scroll.setWidget(self.model_list_widget)
        layout.addWidget(scroll)

    def _refresh_models(self):
        """Refresh the model list."""
        # Clear existing cards
        for card in self._model_cards.values():
            card.setParent(None)
            card.deleteLater()
        self._model_cards.clear()

        while self.model_list_layout.count() > 1:
            item = self.model_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add model cards
        models = self._manager.get_available_models()

        for model_data in models:
            card = ModelCard(model_data)
            card.download_requested.connect(self._on_download)
            card.load_requested.connect(self._on_load)
            card.delete_requested.connect(self._on_delete)

            self._model_cards[model_data["id"]] = card
            self.model_list_layout.insertWidget(
                self.model_list_layout.count() - 1, card
            )

    def _on_download(self, model_id: str):
        """Handle download request."""
        card = self._model_cards.get(model_id)
        if not card:
            return

        success = self._manager.download_model(
            model_id,
            on_progress=lambda p: self._download_progress.emit(model_id, p),
            on_complete=lambda s, m: self._download_complete.emit(model_id, s, m),
        )

        if not success:
            QMessageBox.warning(
                self, "Download",
                "A download is already in progress."
            )

    def _on_progress(self, model_id: str, progress: DownloadProgress):
        """Handle download progress update."""
        card = self._model_cards.get(model_id)
        if card:
            card.set_progress(progress)

    def _on_complete(self, model_id: str, success: bool, message: str):
        """Handle download completion."""
        if success:
            # Refresh the specific card
            self._refresh_models()
        else:
            card = self._model_cards.get(model_id)
            if card:
                card.set_progress(DownloadProgress(status="error", error=message))

    def _on_load(self, model_id: str):
        """Handle load model request."""
        self.model_loaded.emit(model_id)
        self.accept()

    def _on_delete(self, model_id: str):
        """Handle delete model request."""
        model_info = AVAILABLE_MODELS.get(model_id, {})
        reply = QMessageBox.question(
            self,
            "Delete Model",
            f"Delete '{model_info.get('name', model_id)}'?\n"
            f"This will remove the model from disk.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            success = self._manager.delete_model(model_id)
            if success:
                self._refresh_models()
            else:
                QMessageBox.critical(
                    self, "Error", "Failed to delete model."
                )
