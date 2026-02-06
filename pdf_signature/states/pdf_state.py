import reflex as rx
import random
import string
import json
import logging
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
    async def handle_upload(self, files: list[rx.UploadFile]):
        """Handle PDF file upload."""
        self.is_uploading = True
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
            self.has_pdf = True
            self.current_page = 1
            self.signature_boxes = []
            yield rx.toast(f"Uploaded: {file.name}", duration=3000)
        self.is_uploading = False

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

    @rx.event
    def prev_page(self):
        """Navigate to previous page."""
        if self.current_page > 1:
            self.current_page -= 1

    @rx.event
    def update_page_count(self, count: int):
        """Update total pages from JS side."""
        self.num_pages = count

    @rx.var
    def pdf_url(self) -> str:
        """Get the URL for the uploaded PDF."""
        if not self.uploaded_filename:
            return ""
        return f"/_upload/{self.uploaded_filename}"