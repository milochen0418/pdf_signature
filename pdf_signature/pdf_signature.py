import reflex as rx
from pdf_signature.states.pdf_state import PDFState
from pdf_signature.components.sidebar import sidebar
from pdf_signature.components.pdf_viewer import pdf_controls, pdf_viewer_canvas
from pdf_signature.components.signature_modal import signature_modal, sig_pad_init_js

pdf_js_script = """
var pdfDoc = null,
    pageNum = 1,
    pageRendering = false,
    pageNumPending = null,
    scale = 1.0,
    canvas = null,
    ctx = null;

async function renderPage(num, newScale) {
  if (!pdfDoc) return;
  pageRendering = true;
  scale = newScale || scale;

  const page = await pdfDoc.getPage(num);
  const viewport = page.getViewport({scale: scale});

  canvas.height = viewport.height;
  canvas.width = viewport.width;

  const renderContext = {
    canvasContext: ctx,
    viewport: viewport
  };
  const renderTask = page.render(renderContext);

  await renderTask.promise;
  pageRendering = false;
  if (pageNumPending !== null) {
    renderPage(pageNumPending);
    pageNumPending = null;
  }
}

async function loadPDF(url, page, currentScale) {
  const loadingTask = pdfjsLib.getDocument(url);
  pdfDoc = await loadingTask.promise;

  // Send page count back to Reflex
  const state = window.next.router.state.pdf_state;
  if (state) {
      // Logic to update state via a hidden trigger or direct call if available
      // For now, we rely on the state being reactive
  }

  renderPage(page, currentScale);
}

// Watch for changes in the Reflex State to re-render
window.addEventListener('pdf_state_updated', (e) => {
    const s = e.detail;
    if (s.pdf_url && canvas) {
        if (!pdfDoc || s.pdf_url !== pdfDoc._transport._params.url) {
            loadPDF(s.pdf_url, s.current_page, s.zoom_level);
        } else {
            renderPage(s.current_page, s.zoom_level);
        }
    }
});

// Initial hook
document.addEventListener('DOMContentLoaded', () => {
    canvas = document.getElementById('pdf-canvas');
    if (canvas) ctx = canvas.getContext('2d');
});
"""
drawing_js = """
let isDrawing = false;
let startX = 0;
let startY = 0;
let tempBox = null;

document.addEventListener('mousedown', (e) => {
    const surface = document.getElementById('draw-surface');
    if (!surface || e.target !== surface) return;

    isDrawing = true;
    const rect = surface.getBoundingClientRect();
    startX = e.clientX - rect.left;
    startY = e.clientY - rect.top;

    tempBox = document.createElement('div');
    tempBox.style.position = 'absolute';
    tempBox.style.border = '2px dashed #3b82f6';
    tempBox.style.backgroundColor = 'rgba(59, 130, 246, 0.2)';
    tempBox.style.left = startX + 'px';
    tempBox.style.top = startY + 'px';
    tempBox.style.pointerEvents = 'none'; // Ensure mouse events fall through during drag if needed
    surface.appendChild(tempBox);
});

document.addEventListener('mousemove', (e) => {
    if (!isDrawing || !tempBox) return;
    const surface = document.getElementById('draw-surface');
    const rect = surface.getBoundingClientRect();

    // Calculate coordinates relative to the overlay
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;

    const width = Math.abs(currentX - startX);
    const height = Math.abs(currentY - startY);
    const left = currentX < startX ? currentX : startX;
    const top = currentY < startY ? currentY : startY;

    tempBox.style.width = width + 'px';
    tempBox.style.height = height + 'px';
    tempBox.style.left = left + 'px';
    tempBox.style.top = top + 'px';
});

document.addEventListener('mouseup', (e) => {
    if (!isDrawing) return;
    isDrawing = false;

    if (tempBox) {
        const surface = document.getElementById('draw-surface');
        const rect = surface.getBoundingClientRect();

        const width = parseFloat(tempBox.style.width);
        const height = parseFloat(tempBox.style.height);
        const left = parseFloat(tempBox.style.left);
        const top = parseFloat(tempBox.style.top);

        tempBox.remove();
        tempBox = null;

        // Ignore tiny accidental clicks (<5px)
        if (width < 5 || height < 5) return;

        // Calculate percentages to handle zooming
        const pctX = (left / rect.width) * 100;
        const pctY = (top / rect.height) * 100;
        const pctW = (width / rect.width) * 100;
        const pctH = (height / rect.height) * 100;

        // Update hidden input to notify Reflex state
        const input = document.getElementById('new-box-data');
        if (input) {
            // Use native setter to ensure React/Reflex picks up the change
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
            nativeInputValueSetter.call(input, JSON.stringify({x: pctX, y: pctY, w: pctW, h: pctH}));

            const event = new Event('input', { bubbles: true });
            input.dispatchEvent(event);
        }
    }
});
"""


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
        rx.script(
            src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"
        ),
        rx.script(
            src="https://cdn.jsdelivr.net/npm/signature_pad@4.1.7/dist/signature_pad.umd.min.js"
        ),
        rx.script("""
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        """),
        rx.script(sig_pad_init_js),
        rx.script(
            f'''\n            document.addEventListener('DOMContentLoaded', () => {{\n                const canvas = document.getElementById('pdf-canvas');\n                if (!canvas) return;\n                const ctx = canvas.getContext('2d');\n                let pdfDoc = null;\n\n                const render = async () => {{\n                    const url = "{PDFState.pdf_url}";\n                    const pageNum = {PDFState.current_page};\n                    const scale = {PDFState.zoom_level};\n                    \n                    if (!url) return;\n                    \n                    try {{\n                        if (!pdfDoc || pdfDoc.url !== url) {{\n                            const loadingTask = pdfjsLib.getDocument(url);\n                            pdfDoc = await loadingTask.promise;\n                            pdfDoc.url = url;\n                            // Call back to reflex to set page count\n                            const count = pdfDoc.numPages;\n                            // We use a small hack to trigger state update if needed, \n                            // but usually we rely on current state values\n                        }}\n                        \n                        const page = await pdfDoc.getPage(pageNum);\n                        const viewport = page.getViewport({{scale: scale}});\n                        canvas.height = viewport.height;\n                        canvas.width = viewport.width;\n                        \n                        await page.render({{canvasContext: ctx, viewport: viewport}}).promise;\n                    }} catch (e) {{\n                        console.error("PDF Render Error:", e);\n                    }}\n                }};\n\n                // Polling for state changes as a simple bridge for Phase 1\n                setInterval(render, 300); \n            }});\n            '''
        ),
        rx.script(drawing_js),
        class_name="font-['Inter'] selection:bg-blue-100",
    )


app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(rel="preconnect", href="https://fonts.gstatic.com", cross_origin=""),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
            rel="stylesheet",
        ),
    ],
)
app.add_page(index, route="/")