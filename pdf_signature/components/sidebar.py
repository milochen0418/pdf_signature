import reflex as rx
from pdf_signature.states.pdf_state import PDFState


def signature_item(box: dict) -> rx.Component:
    """Render an item in the signature list."""
    return rx.el.div(
        rx.el.div(
            rx.icon("pen-line", class_name="h-4 w-4 text-blue-500"),
            rx.el.span(
                f"Signature Box {box['id']}",
                class_name="text-sm font-medium text-gray-700 truncate",
            ),
            class_name="flex items-center gap-2",
        ),
        rx.el.button(
            rx.icon("x", class_name="h-4 w-4"),
            on_click=PDFState.delete_box(box["id"]),
            class_name="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors",
        ),
        class_name="flex items-center justify-between p-3 bg-white border border-gray-100 rounded-lg shadow-sm group hover:border-blue-200 transition-colors",
    )


def upload_zone() -> rx.Component:
    """The drag-and-drop upload component."""
    return rx.upload.root(
        rx.el.div(
            rx.cond(
                PDFState.is_uploading,
                rx.el.div(
                    rx.spinner(size="3", class_name="text-blue-500"),
                    rx.el.p(
                        "Processing...",
                        class_name="mt-2 text-sm text-gray-500 font-medium",
                    ),
                    class_name="flex flex-col items-center py-8",
                ),
                rx.el.div(
                    rx.icon("pen", class_name="h-10 w-10 text-gray-400 mb-3"),
                    rx.el.p(
                        "Click or drag PDF here",
                        class_name="text-sm font-semibold text-gray-700",
                    ),
                    rx.el.p(
                        "Maximum size 10MB", class_name="text-xs text-gray-400 mt-1"
                    ),
                    class_name="flex flex-col items-center py-8 px-4",
                ),
            ),
            class_name="w-full border-2 border-dashed border-gray-200 rounded-xl hover:border-blue-400 hover:bg-blue-50/50 transition-all cursor-pointer",
        ),
        id="pdf-upload",
        accept={"application/pdf": [".pdf"]},
        max_files=1,
        on_drop=PDFState.handle_upload(rx.upload_files(upload_id="pdf-upload")),
    )


def sidebar() -> rx.Component:
    """Application sidebar containing branding and upload tools."""
    return rx.el.aside(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.icon("pen-tool", class_name="h-6 w-6 text-white"),
                    class_name="bg-blue-600 p-2 rounded-xl shadow-md shadow-blue-200",
                ),
                rx.el.span(
                    "SignFlow",
                    class_name="text-xl font-bold tracking-tight text-gray-900",
                ),
                class_name="flex items-center gap-3 mb-10 px-2",
            ),
            rx.el.div(
                rx.el.h3(
                    "Documents",
                    class_name="text-xs font-bold text-gray-400 uppercase tracking-widest mb-4 px-2",
                ),
                upload_zone(),
                class_name="mb-8",
            ),
            rx.cond(
                PDFState.has_pdf,
                rx.el.div(
                    rx.el.div(
                        rx.icon("file-text", class_name="h-5 w-5 text-blue-500"),
                        rx.el.div(
                            rx.el.p(
                                PDFState.uploaded_filename,
                                class_name="text-sm font-medium text-gray-900 truncate w-32",
                            ),
                            rx.el.p(
                                f"{PDFState.num_pages} pages",
                                class_name="text-xs text-gray-500",
                            ),
                        ),
                        class_name="flex items-center gap-3 p-3 bg-blue-50 rounded-xl border border-blue-100",
                    ),
                    rx.cond(
                        PDFState.signature_boxes.length() > 0,
                        rx.el.div(
                            rx.el.h3(
                                "Signature Areas",
                                class_name="text-xs font-bold text-gray-400 uppercase tracking-widest mt-8 mb-4 px-2",
                            ),
                            rx.el.div(
                                rx.foreach(PDFState.signature_boxes, signature_item),
                                class_name="flex flex-col gap-2",
                            ),
                        ),
                    ),
                    class_name="px-1",
                ),
            ),
            class_name="p-6 h-full flex flex-col overflow-y-auto custom-scrollbar",
        ),
        class_name="w-72 bg-white border-r h-screen shrink-0 hidden lg:block",
    )