import reflex as rx
from pdf_signature.states.pdf_state import PDFState
from reflex_mouse_track import MousePosition, mouse_track


def signature_strokes_svg() -> rx.Component:
    return rx.el.svg(
        rx.foreach(
            PDFState.signature_paths,
            lambda path_d: rx.el.path(
                d=path_d,
                stroke="#111827",
                stroke_width="2",
                fill="none",
                stroke_linecap="round",
                stroke_linejoin="round",
            ),
        ),
        view_box="0 0 520 220",
        class_name="absolute inset-0 w-full h-full",
    )


@rx.memo
def signature_pad_surface() -> rx.Component:
    return mouse_track(
        signature_strokes_svg(),
        rx.moment(
            interval=30,
            on_change=PDFState.sample_signature_point(
                MousePosition.x,
                MousePosition.y,
                MousePosition.defined,
            ),
            display="none",
        ),
        width=f"{PDFState.signature_pad_width}px",
        height=f"{PDFState.signature_pad_height}px",
        position="relative",
        background_color="transparent",
        class_name="rounded-lg select-none",
        style={"userSelect": "none", "WebkitUserSelect": "none"},
        on_mouse_down=PDFState.start_signature,
        on_mouse_up=PDFState.stop_signature,
    )


def signature_modal() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            class_name="fixed inset-0 bg-black/50 backdrop-blur-sm z-50",
            on_click=PDFState.close_signing_modal,
        ),
        rx.el.div(
            rx.el.div(
                rx.el.h2(
                    "Signature Pad", class_name="text-lg font-bold text-gray-900 mb-4"
                ),
                rx.el.div(
                    rx.cond(
                        PDFState.is_signing,
                        rx.el.div(
                            rx.cond(
                                PDFState.signature_paths.length() == 0,
                                rx.el.span(
                                    "Sign here",
                                    class_name="absolute inset-0 flex items-center justify-center text-xs text-gray-400 pointer-events-none select-none z-0",
                                ),
                            ),
                            signature_pad_surface(),
                            class_name="relative border border-gray-200 rounded-lg shadow-inner bg-white select-none",
                            style={
                                "width": f"{PDFState.signature_pad_width}px",
                                "height": f"{PDFState.signature_pad_height}px",
                            },
                        ),
                    ),
                    class_name="mb-6 bg-gray-50 p-3 rounded-xl flex items-center justify-center",
                ),
                rx.el.div(
                    rx.el.button(
                        "Clear",
                        on_click=PDFState.clear_signature_pad,
                        class_name="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors",
                    ),
                    rx.el.div(
                        rx.el.button(
                            "Cancel",
                            on_click=PDFState.close_signing_modal,
                            class_name="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors",
                        ),
                        rx.el.button(
                            "Apply Signature",
                            on_click=PDFState.apply_signature,
                            class_name="px-4 py-2 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-md transition-all",
                        ),
                        class_name="flex gap-3",
                    ),
                    class_name="flex justify-between items-center",
                ),
                class_name="bg-white rounded-2xl p-8 max-w-2xl w-full relative z-50 shadow-2xl",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50 p-4",
        ),
        id="sig-modal-container",
        class_name=rx.cond(PDFState.is_signing, "block", "hidden"),
    )