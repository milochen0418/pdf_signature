import reflex as rx
from pdf_signature.states.pdf_state import PDFState
from pdf_signature.components.sidebar import sidebar
from pdf_signature.components.pdf_viewer import pdf_controls, pdf_viewer_canvas
from pdf_signature.components.signature_modal import signature_modal, sig_pad_init_js



def index() -> rx.Component:
    return rx.el.main(
        signature_modal(),
        rx.el.div(
            sidebar(),
            rx.el.div(
                rx.cond(
                    PDFState.has_pdf,
                    rx.el.div(
                        pdf_controls(),
                        pdf_viewer_canvas(),
                        class_name="flex flex-col h-screen flex-1",
                    ),
                    rx.el.div(
                        rx.el.div(
                            rx.icon(
                                "file-up", class_name="h-16 w-16 text-gray-200 mb-4"
                            ),
                            rx.el.h2(
                                "No Document Open",
                                class_name="text-xl font-semibold text-gray-900",
                            ),
                            rx.el.p(
                                "Upload a PDF document from the sidebar to get started.",
                                class_name="text-gray-500 mt-2",
                            ),
                            class_name="flex flex-col items-center justify-center h-full",
                        ),
                        class_name="flex-1 bg-gray-50",
                    ),
                ),
                class_name="flex-1 flex flex-col h-screen overflow-hidden",
            ),
            class_name="flex min-h-screen bg-white",
        ),
        class_name="font-['Inter'] selection:bg-blue-100",
    )


app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.script(src="/signature_pad.umd.min.js"),
        rx.el.script(sig_pad_init_js),
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(rel="preconnect", href="https://fonts.gstatic.com", cross_origin=""),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
            rel="stylesheet",
        ),
    ],
)
app.add_page(index, route="/")