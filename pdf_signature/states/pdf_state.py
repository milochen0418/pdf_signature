import reflex as rx
import random
import string
import json
import logging
import re
import base64
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
    signature_svg: str
    signature_data_url: str


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
    signature_pad_width: int = 520
    signature_pad_height: int = 220

    # Draw Box State
    is_drawing_box: bool = False
    drawing_start_x: float = 0
    drawing_start_y: float = 0
    drawing_current_x: float = 0
    drawing_current_y: float = 0

    @rx.event
    def toggle_drawing_mode(self):
        """Toggle the signature box drawing mode."""
        self.is_drawing_box = not self.is_drawing_box
        if not self.is_drawing_box:
            # clear state if cancelled
            self.drawing_start_x = 0
            self.drawing_start_y = 0
            self.drawing_current_x = 0
            self.drawing_current_y = 0

    def start_drawing_box(self, client_x: float, client_y: float):
        """Start drawing a box."""
        self.drawing_start_x = client_x
        self.drawing_start_y = client_y
        self.drawing_current_x = client_x
        self.drawing_current_y = client_y

    def update_drawing_box(self, client_x: float, client_y: float):
        """Update drawing box coordinates."""
        if self.is_drawing_box:
            self.drawing_current_x = client_x
            self.drawing_current_y = client_y

    def end_drawing_box(self):
        """End drawing and request container rect for saving."""
        if not self.is_drawing_box:
            return
        
        # Only process if we actually dragged somewhere
        if abs(self.drawing_current_x - self.drawing_start_x) < 5 or abs(self.drawing_current_y - self.drawing_start_y) < 5:
            # Treat as click or tiny drag - ignore or maybe exit mode?
            # self.is_drawing_box = False # Keep mode on for multiple boxes? User preference.
            return

        # Execute JS to get the container's bounding rect
        yield rx.call_script(
            "document.getElementById('pdf-image-container').getBoundingClientRect()",
            callback=PDFState.save_box_with_rect
        )

    def save_box_with_rect(self, rect: dict):
        """Calculate relative coordinates and save the box."""
        if not rect:
            return

        # Container Rect
        c_left = rect["left"]
        c_top = rect["top"]
        c_width = rect["width"]
        c_height = rect["height"]

        # Box Screen Coords
        # Use min/max to handle drawing in any direction
        b_left = min(self.drawing_start_x, self.drawing_current_x)
        b_top = min(self.drawing_start_y, self.drawing_current_y)
        b_width = abs(self.drawing_current_x - self.drawing_start_x)
        b_height = abs(self.drawing_current_y - self.drawing_start_y)

        # Convert to Relative %
        # Relative X = (BoxScreenLeft - ContainerScreenLeft) / ContainerWidth
        rel_x = (b_left - c_left) / c_width * 100
        rel_y = (b_top - c_top) / c_height * 100
        rel_w = b_width / c_width * 100
        rel_h = b_height / c_height * 100

        # Save
        new_id = "".join(random.choices(string.ascii_letters + string.digits, k=6))
        new_box = {
            "id": new_id,
            "x": rel_x,
            "y": rel_y,
            "w": rel_w,
            "h": rel_h,
            "page": self.current_page,
            "signature_svg": "",
            "signature_data_url": "",
        }
        self.signature_boxes.append(new_box)
        
        # Reset current drawing state but stay in draw mode? 
        # Usually easier to exit draw mode to avoid accidental clicks
        self.is_drawing_box = False
        self.drawing_start_x = 0
        self.drawing_start_y = 0
        self.drawing_current_x = 0
        self.drawing_current_y = 0

    def _emit_interaction_log(self, message: str):
        logging.getLogger("interaction").info(message)
        return rx.call_script(f"console.log({json.dumps(message)})")

    @rx.event
    def open_signing_modal(self, box_id: str):
        """Open the signature pad for a specific box."""
        self.selected_box_id = box_id
        self.is_signing = True
        yield self._emit_interaction_log(
            "signature:open "
            f"box_id={box_id} page={self.current_page} zoom={self.zoom_level:.2f}"
        )
        yield rx.call_script(
            "setTimeout(function(){ window.initSignaturePad('signature-canvas'); }, 150)"
        )

    @rx.event
    def close_signing_modal(self):
        """Close the signature pad modal."""
        self.is_signing = False
        self.selected_box_id = ""
        return self._emit_interaction_log("signature:close")

    @rx.event
    def apply_signature_data(self, svg_string: str):
        """Apply signature SVG from signature_pad to the selected box."""
        if not svg_string:
            # Canvas was empty – just close without changing existing signature
            self.is_signing = False
            self.selected_box_id = ""
            return
        # Build data-URL for display (stretch to fill box)
        svg_display = svg_string.replace(
            "<svg ", '<svg preserveAspectRatio="none" ', 1
        )
        data_url = "data:image/svg+xml;base64," + base64.b64encode(
            svg_display.encode("utf-8")
        ).decode("ascii")
        for box in self.signature_boxes:
            if box["id"] == self.selected_box_id:
                box["signature_svg"] = svg_string
                box["signature_data_url"] = data_url
                break
        self.signature_boxes = list(self.signature_boxes)
        self.is_signing = False
        self.selected_box_id = ""
        return self._emit_interaction_log("signature:apply (svg)")

    @rx.event
    def clear_signature_pad(self):
        """Clear the signature pad canvas."""
        yield self._emit_interaction_log("signature:clear")
        yield rx.call_script("window.clearSignaturePad()")

    @rx.event
    def add_box(self, data: str):
        """Add a new signature box from JSON data."""
        logging.info(f"add_box called with data: {data}")
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
                "signature_svg": "",
                "signature_data_url": "",
            }
            self.signature_boxes.append(new_box)
            self.is_drawing_box = False
            logging.info(f"Successfully added box: {new_box['id']}")
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

    def _parse_signature_svg(self, svg_string: str) -> dict:
        """Parse signature_pad SVG into Bézier segments and dots for PDF export."""
        paths: list[dict] = []
        circles: list[dict] = []
        # Extract viewBox to know the coordinate system
        vb_m = re.search(r'viewBox="([^"]*)"', svg_string)
        vb_w = float(self.signature_pad_width)
        vb_h = float(self.signature_pad_height)
        if vb_m:
            parts = vb_m.group(1).split()
            if len(parts) == 4:
                try:
                    vb_w = float(parts[2])
                    vb_h = float(parts[3])
                except ValueError:
                    pass
        # Extract <path d="M sx,sy C c1x,c1y c2x,c2y ex,ey" stroke-width="W" ...>
        for m in re.finditer(r"<path\s([^>]*?)/?>", svg_string):
            attrs = m.group(1)
            d_m = re.search(r'd="([^"]*)"', attrs)
            w_m = re.search(r'stroke-width="([^"]*)"', attrs)
            if not (d_m and w_m):
                continue
            tokens = d_m.group(1).strip().split()
            width = float(w_m.group(1))
            if len(tokens) >= 6 and tokens[0] == "M" and tokens[2] == "C":
                try:
                    start = [float(v) for v in tokens[1].split(",")]
                    c1 = [float(v) for v in tokens[3].split(",")]
                    c2 = [float(v) for v in tokens[4].split(",")]
                    end = [float(v) for v in tokens[5].split(",")]
                    paths.append(
                        {"start": start, "c1": c1, "c2": c2, "end": end, "width": width}
                    )
                except (ValueError, IndexError):
                    continue
        # Extract <circle r="R" cx="X" cy="Y" ...>
        for m in re.finditer(r"<circle\s([^>]*?)/?>", svg_string):
            attrs = m.group(1)
            r_m = re.search(r'\br="([^"]*)"', attrs)
            cx_m = re.search(r'cx="([^"]*)"', attrs)
            cy_m = re.search(r'cy="([^"]*)"', attrs)
            if r_m and cx_m and cy_m:
                try:
                    circles.append(
                        {
                            "cx": float(cx_m.group(1)),
                            "cy": float(cy_m.group(1)),
                            "r": float(r_m.group(1)),
                        }
                    )
                except ValueError:
                    continue
        return {"paths": paths, "circles": circles, "viewBox_w": vb_w, "viewBox_h": vb_h}

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
            pad_w = float(self.signature_pad_width) or 1.0
            pad_h = float(self.signature_pad_height) or 1.0

            for box in self.signature_boxes:
                svg_string = box.get("signature_svg", "")
                if not svg_string:
                    continue
                page_index = int(box.get("page", 1)) - 1
                if page_index < 0 or page_index >= doc.page_count:
                    continue
                page = doc.load_page(page_index)
                page_rect = page.rect
                bx = page_rect.width * (float(box["x"]) / 100.0)
                by = page_rect.height * (float(box["y"]) / 100.0)
                bw = page_rect.width * (float(box["w"]) / 100.0)
                bh = page_rect.height * (float(box["h"]) / 100.0)
                rect = fitz.Rect(bx, by, bx + bw, by + bh)

                parsed = self._parse_signature_svg(svg_string)
                svg_w = parsed["viewBox_w"] or pad_w
                svg_h = parsed["viewBox_h"] or pad_h
                scale_x = rect.width / svg_w
                scale_y = rect.height / svg_h
                scale_w = min(scale_x, scale_y)  # keep stroke width proportional

                ink_color = (0.067, 0.094, 0.153)  # #111827

                shape = page.new_shape()
                for pd in parsed["paths"]:
                    p1 = fitz.Point(
                        rect.x0 + pd["start"][0] * scale_x,
                        rect.y0 + pd["start"][1] * scale_y,
                    )
                    p2 = fitz.Point(
                        rect.x0 + pd["c1"][0] * scale_x,
                        rect.y0 + pd["c1"][1] * scale_y,
                    )
                    p3 = fitz.Point(
                        rect.x0 + pd["c2"][0] * scale_x,
                        rect.y0 + pd["c2"][1] * scale_y,
                    )
                    p4 = fitz.Point(
                        rect.x0 + pd["end"][0] * scale_x,
                        rect.y0 + pd["end"][1] * scale_y,
                    )
                    shape.draw_bezier(p1, p2, p3, p4)
                    shape.finish(
                        color=ink_color,
                        width=pd["width"] * scale_w,
                        closePath=False,
                        lineCap=1,   # round
                        lineJoin=1,  # round
                    )
                for cd in parsed["circles"]:
                    cx = rect.x0 + cd["cx"] * scale_x
                    cy = rect.y0 + cd["cy"] * scale_y
                    r = cd["r"] * scale_w
                    shape.draw_circle(fitz.Point(cx, cy), max(r, 0.5))
                    shape.finish(fill=ink_color, closePath=True)
                shape.commit()

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