"""
EdgeMind NPU - File Processor
Handles reading and extracting text from various file formats.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    '.txt': 'text',
    '.md': 'text',
    '.csv': 'text',
    '.json': 'text',
    '.xml': 'text',
    '.html': 'text',
    '.pdf': 'pdf',
    '.docx': 'docx',  # legacy binary .doc is not supported by python-docx
    '.png': 'image',
    '.jpg': 'image',
    '.jpeg': 'image',
    '.gif': 'image',
    '.bmp': 'image',
    '.webp': 'image',
}


class FileProcessor:
    """Processes uploaded files and extracts their content."""

    def __init__(self):
        self._pdf_available = False
        self._docx_available = False
        self._pillow_available = False

        try:
            import PyPDF2
            self._pdf_available = True
        except ImportError:
            logger.debug("PyPDF2 not available")

        try:
            import docx
            self._docx_available = True
        except ImportError:
            logger.debug("python-docx not available")

        try:
            from PIL import Image
            self._pillow_available = True
        except ImportError:
            logger.debug("Pillow not available")

    def is_supported(self, filepath: str) -> bool:
        """Check if file type is supported."""
        ext = Path(filepath).suffix.lower()
        return ext in SUPPORTED_EXTENSIONS

    def get_file_type(self, filepath: str) -> Optional[str]:
        """Get the type of file."""
        ext = Path(filepath).suffix.lower()
        return SUPPORTED_EXTENSIONS.get(ext)

    def get_file_info(self, filepath: str) -> dict:
        """Get basic file information."""
        path = Path(filepath)
        stat = path.stat()
        return {
            "name": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": stat.st_size,
            "size_human": self._human_size(stat.st_size),
            "type": self.get_file_type(filepath),
        }

    def read_file(self, filepath: str) -> dict:
        """
        Read a file and extract its content.
        
        Returns:
            dict with keys: content, type, name, error
        """
        path = Path(filepath)

        if not path.exists():
            return {"content": "", "type": "unknown", "name": path.name,
                    "error": "File not found"}

        file_type = self.get_file_type(filepath)
        if file_type is None:
            return {"content": "", "type": "unknown", "name": path.name,
                    "error": f"Unsupported file type: {path.suffix}"}

        try:
            if file_type == "text":
                content = self._read_text(filepath)
            elif file_type == "pdf":
                content = self._read_pdf(filepath)
            elif file_type == "docx":
                content = self._read_docx(filepath)
            elif file_type == "image":
                content = self._read_image_info(filepath)
            else:
                content = ""

            return {
                "content": content,
                "type": file_type,
                "name": path.name,
                "size": self.get_file_info(filepath),
                "error": None,
            }
        except Exception as e:
            logger.error(f"Error reading file {filepath}: {e}")
            return {
                "content": "",
                "type": file_type,
                "name": path.name,
                "error": str(e),
            }

    def _read_text(self, filepath: str) -> str:
        """Read plain text files."""
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    content = f.read()
                return content
            except UnicodeDecodeError:
                continue
        return ""

    def _read_pdf(self, filepath: str) -> str:
        """Extract text from PDF files."""
        if not self._pdf_available:
            return "[PDF reading requires PyPDF2: pip install PyPDF2]"

        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(filepath)
            text_parts = []

            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"[Page {i + 1}]\n{page_text}")

            return "\n\n".join(text_parts)
        except Exception as e:
            return f"[Error reading PDF: {str(e)}]"

    def _read_docx(self, filepath: str) -> str:
        """Extract text from DOCX files."""
        if not self._docx_available:
            return "[DOCX reading requires python-docx: pip install python-docx]"

        try:
            import docx
            doc = docx.Document(filepath)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        except Exception as e:
            return f"[Error reading DOCX: {str(e)}]"

    def _read_image_info(self, filepath: str) -> str:
        """Get image metadata."""
        info = [f"Image file: {Path(filepath).name}"]

        if self._pillow_available:
            try:
                from PIL import Image
                with Image.open(filepath) as img:
                    info.append(f"Format: {img.format}")
                    info.append(f"Size: {img.width}x{img.height}")
                    info.append(f"Mode: {img.mode}")
            except Exception:
                pass

        return "\n".join(info)

    def prepare_for_llm(self, filepath: str) -> str:
        """
        Prepare file content for LLM context.
        Returns formatted text suitable for inclusion in prompts.
        """
        result = self.read_file(filepath)

        if result.get("error"):
            return f"[Error reading file: {result['error']}]"

        content = result.get("content", "")
        name = result.get("name", "unknown")
        file_type = result.get("type", "unknown")

        if file_type == "image":
            # For images, just provide metadata
            return f"📎 Image uploaded: {name}\n{content}\n[Note: Vision capabilities depend on model support]"

        # For text-based files, include content with header
        header = f"📄 File: {name}\n{'─' * 40}\n"
        footer = f"\n{'─' * 40}\n[End of file]"

        # Truncate very long files
        max_chars = 30000
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n[Truncated at {max_chars} characters...]"

        return header + content + footer

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        """Convert bytes to human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
