import reflex as rx
import random
import string
import json
import logging
from typing import TypedDict

import fitz
from reflex.config import get_config


class SignatureBox(TypedDict):
    id: str
    x: float
    y: float
    w: float
    h: float
    page: int
    signature_strokes: list[list[dict[str, float]]]
    signature_paths: list[str]


class PDFState(rx.State):
    """State for managing PDF document interactions."""

    uploaded_filename: str = ""
    is_uploading: bool = False
    has_pdf: bool = False
    current_page: int = 1
    num_pages: int = 1
    zoom_level: float = 1.0
    scale_percent: int = 100
    signature_boxes: list[SignatureBox] = []
    selected_box_id: str = ""
    is_signing: bool = False
    is_rendering: bool = False
    render_error: str = ""
    page_image_filename: str = ""
    page_image_width: int = 0
    page_image_height: int = 0
    signed_filename: str = ""
    file_token: str = ""
    signature_is_drawing: bool = False
    signature_strokes: list[list[dict[str, float]]] = []
    signature_paths: list[str] = []
    signature_last_x: float = 0.0
    signature_last_y: float = 0.0
    signature_pad_width: int = 520
    signature_pad_height: int = 220

    def _emit_interaction_log(self, message: str):
        logging.getLogger("interaction").info(message)
        return rx.call_script(f"console.log({json.dumps(message)})")

    @rx.event
    def open_signing_modal(self, box_id: str):
        """Open the signature pad for a specific box."""
        self.selected_box_id = box_id
        self.is_signing = True
        self.signature_is_drawing = False
        self.signature_strokes = []
        self.signature_paths = []
        log = self._emit_interaction_log(
            "signature:open "
            f"box_id={box_id} page={self.current_page} zoom={self.zoom_level:.2f}"
        )
        for box in self.signature_boxes:
            if box["id"] == box_id:
                strokes = box.get("signature_strokes", [])
                self.signature_strokes = [
                    [point.copy() for point in stroke] for stroke in strokes
                ]
                box_paths = box.get("signature_paths")
                if box_paths is None or len(box_paths) != len(self.signature_strokes):
                    box_paths = self._build_paths_from_strokes(
                        self.signature_strokes
                    )
                self.signature_paths = list(box_paths)
                break
        return log

    @rx.event
    def close_signing_modal(self):
        """Close the signature pad modal."""
        self.is_signing = False
        self.selected_box_id = ""
        self.signature_is_drawing = False
        self.signature_paths = []
        self.signature_last_x = 0.0
        self.signature_last_y = 0.0
        return self._emit_interaction_log("signature:close")

    @rx.event
    def apply_signature(self):
        """Apply the captured signature strokes to the selected box."""
        for box in self.signature_boxes:
            if box["id"] == self.selected_box_id:
                box["signature_strokes"] = [
                    [point.copy() for point in stroke]
                    for stroke in self.signature_strokes
                ]
                box["signature_paths"] = list(self.signature_paths)
                break
        self.signature_boxes = list(self.signature_boxes)
        self.is_signing = False
        self.selected_box_id = ""
        self.signature_is_drawing = False
        self.signature_paths = []
        self.signature_last_x = 0.0
        self.signature_last_y = 0.0
        return self._emit_interaction_log(
            f"signature:apply strokes={len(self.signature_strokes)}"
        )

    @rx.event
    def clear_signature_pad(self):
        """Clear the current signature strokes."""
        self.signature_strokes = []
        self.signature_paths = []
        self.signature_is_drawing = False
        self.signature_last_x = 0.0
        self.signature_last_y = 0.0
        return self._emit_interaction_log("signature:clear")

    @rx.event
    def start_signature(self, mouse: dict[str, int]):
        """Start capturing a signature stroke."""
        if not self.is_signing:
            return
        self.signature_is_drawing = True
        self._append_signature_point(mouse)
        return self._emit_interaction_log(
            "signature:start "
            f"x={mouse.get('x', 0)} y={mouse.get('y', 0)} "
            f"pad=({self.signature_pad_width}x{self.signature_pad_height})"
        )

    @rx.event
    def stop_signature(self, mouse: dict[str, int]):
        """Stop capturing a signature stroke."""
        if not self.is_signing:
            return
        self._append_signature_point(mouse)
        self.signature_is_drawing = False
        return self._emit_interaction_log(
            "signature:stop "
            f"x={mouse.get('x', 0)} y={mouse.get('y', 0)} "
            f"strokes={len(self.signature_strokes)}"
        )

    @rx.event
    def sample_signature_point(self, x: int, y: int, defined: bool):
        """Sample a point while drawing in the signature pad."""
        if not (self.is_signing and self.signature_is_drawing and defined):
            return
        self._append_signature_point({"x": x, "y": y})
        return self._emit_interaction_log(f"signature:sample x={x} y={y}")

    def _append_signature_point(self, mouse: dict[str, int]):
        if not mouse:
            return
        if self.signature_pad_width <= 0 or self.signature_pad_height <= 0:
            return
        x_pct = (mouse.get("x", 0) / self.signature_pad_width) * 100.0
        y_pct = (mouse.get("y", 0) / self.signature_pad_height) * 100.0
        x_pct = max(0.0, min(100.0, x_pct))
        y_pct = max(0.0, min(100.0, y_pct))
        if self.signature_strokes and self.signature_strokes[-1]:
            dx = x_pct - self.signature_last_x
            dy = y_pct - self.signature_last_y
            if (dx * dx + dy * dy) < 0.15:
                return
        if not self.signature_strokes or not self.signature_is_drawing:
            self.signature_strokes.append([])
            self.signature_paths.append("")
        if len(self.signature_paths) < len(self.signature_strokes):
            self.signature_paths.append("")
        current_path = self.signature_paths[-1]
        if not self.signature_strokes[-1]:
            current_path = f"M {x_pct:.2f} {y_pct:.2f}"
        else:
            current_path = f"{current_path} L {x_pct:.2f} {y_pct:.2f}"
        self.signature_strokes[-1].append({"x": x_pct, "y": y_pct})
        self.signature_paths[-1] = current_path
        self.signature_last_x = x_pct
        self.signature_last_y = y_pct
        self.signature_strokes = [list(stroke) for stroke in self.signature_strokes]
        self.signature_paths = list(self.signature_paths)

    def _build_paths_from_strokes(
        self, strokes: list[list[dict[str, float]]]
    ) -> list[str]:
        paths: list[str] = []
        for stroke in strokes:
            if not stroke:
                paths.append("")
                continue
            parts = [f"M {stroke[0]['x']:.2f} {stroke[0]['y']:.2f}"]
            for point in stroke[1:]:
                parts.append(f"L {point['x']:.2f} {point['y']:.2f}")
            paths.append(" ".join(parts))
        return paths

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
                "signature_strokes": [],
                "signature_paths": [],
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
            self.page_image_width = int(pix.width)
            self.page_image_height = int(pix.height)
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
        self.page_image_width = 0
        self.page_image_height = 0
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
            self.signature_strokes = []
            self.signature_paths = []
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
                strokes = box.get("signature_strokes", [])
                if not strokes:
                    continue
                page_index = int(box.get("page", 1)) - 1
                if page_index < 0 or page_index >= doc.page_count:
                    continue
                page = doc.load_page(page_index)
                page_rect = page.rect
                x = page_rect.width * (float(box["x"]) / 100.0)
                y = page_rect.height * (float(box["y"]) / 100.0)
                w = page_rect.width * (float(box["w"]) / 100.0)
                h = page_rect.height * (float(box["h"]) / 100.0)
                rect = fitz.Rect(x, y, x + w, y + h)
                for stroke in strokes:
                    if len(stroke) < 2:
                        continue
                    for idx in range(1, len(stroke)):
                        p0 = stroke[idx - 1]
                        p1 = stroke[idx]
                        x0 = rect.x0 + rect.width * (float(p0["x"]) / 100.0)
                        y0 = rect.y0 + rect.height * (float(p0["y"]) / 100.0)
                        x1 = rect.x0 + rect.width * (float(p1["x"]) / 100.0)
                        y1 = rect.y0 + rect.height * (float(p1["y"]) / 100.0)
                        page.draw_line(
                            fitz.Point(x0, y0),
                            fitz.Point(x1, y1),
                            color=(0, 0, 0),
                            width=2,
                        )

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

    @rx.var
    def page_image_width_px(self) -> str:
        """Get the rendered page width in px."""
        return f"{self.page_image_width}px"

    @rx.var
    def page_image_height_px(self) -> str:
        """Get the rendered page height in px."""
        return f"{self.page_image_height}px"

    @rx.var
    def page_image_scaled_width_px(self) -> str:
        """Get the scaled page width in px."""
        return f"{self.page_image_width * self.zoom_level:.2f}px"

    @rx.var
    def page_image_scaled_height_px(self) -> str:
        """Get the scaled page height in px."""
        return f"{self.page_image_height * self.zoom_level:.2f}px"