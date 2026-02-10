import reflex as rx
from pdf_signature.states.pdf_state import PDFState


def signature_modal() -> rx.Component:
    """Signature-pad modal using szimek/signature_pad on a <canvas>."""
    return rx.el.div(
        # ── backdrop ──
        rx.el.div(
            class_name="fixed inset-0 bg-black/50 backdrop-blur-sm z-50",
            on_click=PDFState.close_signing_modal,
        ),
        # ── centred card ──
        rx.el.div(
            rx.el.div(
                rx.el.h2(
                    "Signature Pad",
                    class_name="text-lg font-bold text-gray-900 mb-4",
                ),
                # ── drawing area ──
                rx.el.div(
                    rx.cond(
                        PDFState.is_signing,
                        rx.el.div(
                            # placeholder text (behind canvas)
                            rx.el.span(
                                "Sign here",
                                class_name=(
                                    "absolute inset-0 flex items-center "
                                    "justify-center text-xs text-gray-400 "
                                    "pointer-events-none select-none z-0"
                                ),
                            ),
                            # canvas – signature_pad draws here
                            rx.el.canvas(
                                id="signature-canvas",
                                class_name=(
                                    "absolute inset-0 w-full h-full "
                                    "cursor-crosshair z-10"
                                ),
                                style={"touchAction": "none"},
                            ),
                            class_name=(
                                "relative border border-gray-200 rounded-lg "
                                "shadow-inner bg-white select-none overflow-hidden"
                            ),
                            style={
                                "width": f"{PDFState.signature_pad_width}px",
                                "height": f"{PDFState.signature_pad_height}px",
                            },
                        ),
                    ),
                    class_name="mb-6 bg-gray-50 p-3 rounded-xl flex items-center justify-center",
                ),
                # ── buttons ──
                rx.el.div(
                    rx.el.button(
                        "Clear",
                        on_click=PDFState.clear_signature_pad,
                        class_name=(
                            "px-4 py-2 text-sm font-medium text-gray-700 "
                            "bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                        ),
                    ),
                    rx.el.div(
                        rx.el.button(
                            "Cancel",
                            on_click=PDFState.close_signing_modal,
                            class_name=(
                                "px-4 py-2 text-sm font-medium text-gray-700 "
                                "hover:bg-gray-100 rounded-lg transition-colors"
                            ),
                        ),
                        rx.el.button(
                            "Apply Signature",
                            on_click=rx.call_script(
                                "window.getSignatureSVG()",
                                callback=PDFState.apply_signature_data,
                            ),
                            class_name=(
                                "px-4 py-2 text-sm font-bold text-white "
                                "bg-blue-600 hover:bg-blue-700 rounded-lg "
                                "shadow-md transition-all"
                            ),
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