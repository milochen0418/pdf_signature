import reflex as rx
import random
import string
import json
import logging
import base64
import fitz
from reflex.config import get_config
from typing import Optional


class PDFState(rx.State):
    """State for managing PDF document interactions."""

    uploaded_filename: str = ""
    is_uploading: bool = False
    has_pdf: bool = False
    current_page: int = 1
    num_pages: int = 1
    zoom_level: float = 1.0
    scale_percent: int = 100
    is_draw_mode: bool = False
    signature_boxes: list[dict[str, str | float | int]] = []
    selected_box_id: str = ""
    is_signing: bool = False
    is_rendering: bool = False
    render_error: str = ""
    page_image_filename: str = ""
    signed_filename: str = ""
    file_token: str = ""

    @rx.event
    def toggle_draw_mode(self):
        """Toggle the rectangle drawing mode."""
        self.is_draw_mode = not self.is_draw_mode
        if self.is_draw_mode:
            self.is_signing = False

    @rx.event
    def open_signing_modal(self, box_id: str):
        """Open the signature pad for a specific box."""
        if not self.is_draw_mode:
            self.selected_box_id = box_id
            self.is_signing = True

    @rx.event
    def close_signing_modal(self):
        """Close the signature pad modal."""
        self.is_signing = False
        self.selected_box_id = ""

    @rx.event
    def save_signature(self, signature_data: str):
        """Save base64 signature data to the selected box."""
        for box in self.signature_boxes:
            if box["id"] == self.selected_box_id:
                box["signature"] = signature_data
                break
        self.signature_boxes = list(self.signature_boxes)
        self.is_signing = False
        self.selected_box_id = ""

    @rx.event
    def add_box(self, data: str):
        """Add a new signature box from JSON data."""
        try:
            box_data = json.loads(data)
            new_box = {
                "id": "".join(
                    random.choices(string.ascii_letters + string.digits, k=6)
                ),
                "x": box_data["x"],
                "y": box_data["y"],
                "w": box_data["w"],
                "h": box_data["h"],
                "page": self.current_page,
                "signature": "",
            }
            self.signature_boxes.append(new_box)
        except Exception as e:
            logging.exception(f"Error adding box: {e}")

    @rx.event
    def delete_box(self, box_id: str):
        """Delete a signature box by ID."""
        self.signature_boxes = [
            box for box in self.signature_boxes if box["id"] != box_id
        ]

    @rx.event
    def clear_boxes(self):
        """Remove all signature boxes."""
        self.signature_boxes = []

    @rx.event
    def set_rendering(self, is_rendering: bool):
        """Update rendering status from the JS side."""
        self.is_rendering = is_rendering

    @rx.event
    def set_render_error(self, message: str):
        """Update render error message from the JS side."""
        self.render_error = message

    def _render_page_image(self, page_index: int, file_path):
        """Render a specific PDF page to an image in the upload directory."""
        self.is_rendering = True
        self.render_error = ""
        doc = None
        try:
            doc = fitz.open(file_path)
            self.num_pages = doc.page_count
            page = doc.load_page(page_index - 1)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image_name = f"{self.file_token}_page{page_index}.png"
            image_path = rx.get_upload_dir() / image_name
            pix.save(image_path)
            self.page_image_filename = image_name
        except Exception as e:
            self.render_error = str(e)
            logging.exception("Error rendering PDF preview")
        finally:
            if doc is not None:
                try:
                    doc.close()
                except Exception:
                    pass
            self.is_rendering = False

    @rx.event
    async def handle_upload(self, files: list[rx.UploadFile]):
        """Handle PDF file upload."""
        self.is_uploading = True
        self.is_rendering = False
        self.render_error = ""
        self.page_image_filename = ""
        self.signed_filename = ""
        self.file_token = ""
        yield
        for file in files:
            if not file.name.lower().endswith(".pdf"):
                yield rx.toast("Please upload a valid PDF file.")
                continue
            upload_data = await file.read()
            upload_dir = rx.get_upload_dir()
            upload_dir.mkdir(parents=True, exist_ok=True)
            unique_name = (
                "".join(random.choices(string.ascii_letters + string.digits, k=8))
                + "_"
                + file.name
            )
            file_path = upload_dir / unique_name
            with file_path.open("wb") as f:
                f.write(upload_data)
            self.uploaded_filename = unique_name
            self.file_token = "".join(
                random.choices(string.ascii_letters + string.digits, k=12)
            )
            self.has_pdf = True
            self.current_page = 1
            self.signature_boxes = []
            self.is_rendering = True
            self.render_error = ""
            yield
            self._render_page_image(1, file_path)
            yield rx.toast(f"Uploaded: {file.name}", duration=3000)
        self.is_uploading = False
        self.is_rendering = False

    @rx.event
    def set_zoom(self, value: list[int]):
        """Set zoom level from slider."""
        self.scale_percent = value[0]
        self.zoom_level = value[0] / 100.0

    @rx.event
    def zoom_in(self):
        """Increment zoom level."""
        if self.scale_percent < 300:
            self.scale_percent += 10
            self.zoom_level = self.scale_percent / 100.0

    @rx.event
    def zoom_out(self):
        """Decrement zoom level."""
        if self.scale_percent > 25:
            self.scale_percent -= 10
            self.zoom_level = self.scale_percent / 100.0

    @rx.event
    def next_page(self):
        """Navigate to next page."""
        if self.current_page < self.num_pages:
            self.current_page += 1
            upload_dir = rx.get_upload_dir()
            file_path = upload_dir / self.uploaded_filename
            if file_path.exists():
                self._render_page_image(self.current_page, file_path)

    @rx.event
    def prev_page(self):
        """Navigate to previous page."""
        if self.current_page > 1:
            self.current_page -= 1
            upload_dir = rx.get_upload_dir()
            file_path = upload_dir / self.uploaded_filename
            if file_path.exists():
                self._render_page_image(self.current_page, file_path)

    @rx.event
    def update_page_count(self, count: int):
        """Update total pages from JS side."""
        self.num_pages = count

    @rx.event
    def export_signed_pdf(self):
        """Export a signed PDF with signature overlays applied."""
        if not self.uploaded_filename:
            return

        upload_dir = rx.get_upload_dir()
        pdf_path = upload_dir / self.uploaded_filename
        if not pdf_path.exists():
            self.render_error = "Original PDF not found."
            return

        try:
            doc = fitz.open(pdf_path)
            for box in self.signature_boxes:
                signature = box.get("signature")
                if not signature:
                    continue
                if "," in signature:
                    signature = signature.split(",", 1)[1]
                page_index = int(box.get("page", 1)) - 1
                if page_index < 0 or page_index >= doc.page_count:
                    continue
                page = doc.load_page(page_index)
                page_rect = page.rect
                img_bytes = base64.b64decode(signature)
                x = page_rect.width * (float(box["x"]) / 100.0)
                y = page_rect.height * (float(box["y"]) / 100.0)
                w = page_rect.width * (float(box["w"]) / 100.0)
                h = page_rect.height * (float(box["h"]) / 100.0)
                rect = fitz.Rect(x, y, x + w, y + h)
                page.insert_image(rect, stream=img_bytes)

            signed_name = f"{self.file_token}_signed.pdf"
            signed_path = upload_dir / signed_name
            doc.save(signed_path)
            self.signed_filename = signed_name
            self.render_error = ""
        except Exception as e:
            self.render_error = str(e)
            logging.exception("Error exporting signed PDF")
        finally:
            try:
                doc.close()
            except Exception:
                pass

    @rx.var
    def pdf_url(self) -> str:
        """Get the URL for the uploaded PDF."""
        if not self.uploaded_filename:
            return ""
        api_url = get_config().api_url.rstrip("/")
        return f"{api_url}/_upload/{self.uploaded_filename}"

    @rx.var
    def page_image_url(self) -> str:
        """Get the URL for the rendered PDF page image."""
        if not self.page_image_filename:
            return ""
        api_url = get_config().api_url.rstrip("/")
        return f"{api_url}/_upload/{self.page_image_filename}"

    @rx.var
    def signed_pdf_url(self) -> str:
        """Get the URL for the signed PDF."""
        if not self.signed_filename:
            return ""
        api_url = get_config().api_url.rstrip("/")
        return f"{api_url}/_upload/{self.signed_filename}"