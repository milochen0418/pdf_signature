import reflex as rx
from pdf_signature.states.pdf_state import PDFState
from reflex_mouse_track import MousePosition, mouse_track


def signature_svg(paths: list[str]) -> rx.Component:
    return rx.el.svg(
        rx.foreach(
            paths,
            lambda path_d: rx.el.path(
                d=path_d,
                stroke="#111827",
                stroke_width="2",
                fill="none",
                stroke_linecap="round",
                stroke_linejoin="round",
            ),
        ),
        viewBox="0 0 100 100",
        class_name="w-full h-full",
    )


def render_signature_box(box: dict) -> rx.Component:
    """Render a single signature box overlay."""
    paths = box["signature_paths"]
    is_signed = paths.length() > 0
    return rx.el.div(
        rx.cond(
            is_signed,
            rx.el.div(
                signature_svg(paths),
                rx.el.div(
                    rx.icon(
                        "lamp_wall_down",
                        class_name="h-3 w-3 text-green-500 bg-white rounded-full",
                    ),
                    class_name="absolute top-1 right-1",
                ),
                class_name="relative w-full h-full flex items-center justify-center",
            ),
            rx.el.span(
                "Sign Here",
                class_name="text-[10px] font-bold text-blue-600 bg-white/90 px-1 py-0.5 rounded shadow-sm select-none whitespace-nowrap",
            ),
        ),
        style={
            "left": f"{box['x']}%",
            "top": f"{box['y']}%",
            "width": f"{box['w']}%",
            "height": f"{box['h']}%",
        },
        on_click=lambda: PDFState.open_signing_modal(box["id"]),
        class_name=rx.cond(
            is_signed,
            "absolute border-2 border-green-500 bg-green-50/20 flex items-center justify-center z-10 hover:bg-green-100/30 transition-colors pointer-events-auto cursor-pointer",
            "absolute border-2 border-blue-500 bg-blue-400/20 flex items-center justify-center z-10 hover:bg-blue-400/30 transition-colors pointer-events-auto cursor-pointer",
        ),
    )


def selecting_box() -> rx.Component:
    return rx.cond(
        PDFState.is_box_selecting,
        rx.el.div(
            class_name="absolute border-2 border-dashed border-blue-500 bg-blue-400/20 pointer-events-none",
            style={
                "left": rx.cond(
                    PDFState.box_start_x < MousePosition.x,
                    PDFState.box_start_x,
                    MousePosition.x,
                ),
                "top": rx.cond(
                    PDFState.box_start_y < MousePosition.y,
                    PDFState.box_start_y,
                    MousePosition.y,
                ),
                "width": abs(MousePosition.x - PDFState.box_start_x),
                "height": abs(MousePosition.y - PDFState.box_start_y),
            },
        ),
    )


@rx.memo
def draw_surface() -> rx.Component:
    return mouse_track(
        selecting_box(),
        width=PDFState.page_image_width_px,
        height=PDFState.page_image_height_px,
        position="absolute",
        left="0",
        top="0",
        class_name=rx.cond(
            PDFState.is_draw_mode,
            "absolute inset-0 cursor-crosshair z-20 touch-none",
            "absolute inset-0 z-20 touch-none",
        ),
        style={
            "pointerEvents": rx.cond(PDFState.is_draw_mode, "auto", "none"),
        },
        on_mouse_down=PDFState.start_box_selection,
        on_mouse_up=PDFState.end_box_selection,
    )


def pdf_viewer_canvas() -> rx.Component:
    """The canvas element where PDF.js will render."""
    return rx.el.div(
        rx.el.div(
            rx.cond(
                PDFState.page_image_url != "",
                rx.image(
                    src=PDFState.page_image_url,
                    class_name="shadow-2xl border border-gray-200 bg-white rounded-sm max-w-full",
                ),
                rx.el.div(
                    class_name="shadow-2xl border border-gray-200 bg-white rounded-sm w-[640px] h-[820px]",
                ),
            ),
            rx.cond(
                PDFState.is_rendering,
                rx.el.div(
                    rx.el.div(
                        rx.spinner(size="3", class_name="text-blue-500"),
                        rx.el.p(
                            "Rendering PDF...",
                            class_name="mt-2 text-sm text-gray-600",
                        ),
                        class_name="flex flex-col items-center",
                    ),
                    class_name="absolute inset-0 bg-white/80 backdrop-blur-sm z-30 flex items-center justify-center",
                ),
            ),
            rx.cond(
                PDFState.render_error != "",
                rx.el.div(
                    rx.el.div(
                        rx.icon("message_circle_warning", class_name="h-6 w-6 text-red-500"),
                        rx.el.p(
                            "Failed to render PDF.",
                            class_name="mt-2 text-sm font-semibold text-gray-800",
                        ),
                        rx.el.p(
                            PDFState.render_error,
                            class_name="mt-1 text-xs text-gray-500 max-w-xs text-center",
                        ),
                        class_name="flex flex-col items-center",
                    ),
                    class_name="absolute inset-0 bg-white/90 z-30 flex items-center justify-center",
                ),
            ),
            rx.el.div(
                rx.foreach(PDFState.signature_boxes, render_signature_box),
                class_name="absolute inset-0 z-10",
            ),
            rx.cond(
                ~PDFState.is_signing,
                draw_surface(),
                rx.fragment(),
            ),
            class_name="relative inline-block m-auto",
            style={
                "transform": f"scale({PDFState.zoom_level})",
                "transformOrigin": "top center",
            },
            id="pdf-wrapper",
        ),
        class_name="flex w-full overflow-auto bg-gray-100/50 p-8 custom-scrollbar justify-center items-start",
        id="canvas-container",
    )


def pdf_controls() -> rx.Component:
    """Toolbar for controlling the PDF viewer."""
    return rx.el.div(
        rx.el.div(
            rx.el.button(
                rx.icon("chevron-left", class_name="h-5 w-5"),
                on_click=PDFState.prev_page,
                disabled=PDFState.current_page <= 1,
                class_name="p-2 hover:bg-gray-100 rounded-lg disabled:opacity-30 transition-colors",
            ),
            rx.el.span(
                f"Page {PDFState.current_page} of {PDFState.num_pages}",
                class_name="text-sm font-semibold text-gray-700 min-w-[100px] text-center",
            ),
            rx.el.button(
                rx.icon("chevron-right", class_name="h-5 w-5"),
                on_click=PDFState.next_page,
                disabled=PDFState.current_page >= PDFState.num_pages,
                class_name="p-2 hover:bg-gray-100 rounded-lg disabled:opacity-30 transition-colors",
            ),
            class_name="flex items-center gap-2 border-r pr-4",
        ),
        rx.el.div(
            rx.el.button(
                rx.icon("minus", class_name="h-4 w-4"),
                on_click=PDFState.zoom_out,
                class_name="p-2 hover:bg-gray-100 rounded-lg transition-colors",
            ),
            rx.el.input(
                type="range",
                min=25,
                max=300,
                step=5,
                key=PDFState.scale_percent.to(str),
                default_value=PDFState.scale_percent.to(str),
                on_change=lambda v: PDFState.set_zoom([v.to(int)]).throttle(100),
                class_name="w-32 h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600",
            ),
            rx.el.button(
                rx.icon("plus", class_name="h-4 w-4"),
                on_click=PDFState.zoom_in,
                class_name="p-2 hover:bg-gray-100 rounded-lg transition-colors",
            ),
            rx.el.span(
                f"{PDFState.scale_percent}%",
                class_name="text-sm font-medium text-gray-600 w-12",
            ),
            class_name="flex items-center gap-4 pl-4 border-r pr-4",
        ),
        rx.el.div(
            rx.el.button(
                rx.cond(
                    PDFState.is_draw_mode,
                    rx.icon("languages", class_name="h-4 w-4 text-blue-600"),
                    rx.icon("square", class_name="h-4 w-4"),
                ),
                "Draw Box",
                on_click=PDFState.toggle_draw_mode,
                class_name=rx.cond(
                    PDFState.is_draw_mode,
                    "flex items-center gap-2 px-3 py-1.5 bg-blue-100 text-blue-700 rounded-lg font-medium text-sm transition-colors",
                    "flex items-center gap-2 px-3 py-1.5 hover:bg-gray-100 text-gray-700 rounded-lg font-medium text-sm transition-colors",
                ),
            ),
            rx.cond(
                PDFState.signature_boxes.length() > 0,
                rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    "Clear",
                    on_click=PDFState.clear_boxes,
                    class_name="flex items-center gap-2 px-3 py-1.5 hover:bg-red-50 text-red-600 rounded-lg font-medium text-sm transition-colors",
                ),
            ),
            rx.el.button(
                rx.icon("download", class_name="h-4 w-4"),
                "Export PDF",
                on_click=PDFState.export_signed_pdf,
                class_name="flex items-center gap-2 px-3 py-1.5 bg-gray-900 text-white rounded-lg font-medium text-sm hover:bg-gray-800 transition-colors",
            ),
            class_name="flex items-center gap-2 pl-4",
        ),
        class_name="flex items-center justify-between h-14 bg-white/80 backdrop-blur-md border-b sticky top-0 z-30 px-6",
    )