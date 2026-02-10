import reflex as rx
from pdf_signature.states.pdf_state import PDFState
from pdf_signature.components.sidebar import sidebar
from pdf_signature.components.pdf_viewer import pdf_controls, pdf_viewer_canvas
from pdf_signature.components.signature_modal import signature_modal, sig_pad_init_js

sig_pad_loader_js = """
(function() {
    // Reflex copies files in /assets to the public root (e.g. /signature_pad.umd.min.js)
    // so try both root and /assets prefixes before falling back to CDNs.
    const sources = [
        '/signature_pad.umd.min.js',
        '/assets/signature_pad.umd.min.js',
        'https://cdn.jsdelivr.net/npm/signature_pad@4.1.7/dist/signature_pad.umd.min.js',
        'https://unpkg.com/signature_pad@4.1.7/dist/signature_pad.umd.min.js'
    ];

    let loaded = false;
    let attempt = 0;
    let timeoutId = null;
    const fallbackDelay = 2500; // bail out if a CDN request hangs

    function markLoaded(src) {
        loaded = true;
        clearTimeout(timeoutId);
        window.__signaturePadLoaded = true;
        window.dispatchEvent(new Event('signaturepad:loaded'));
        console.info('[SignaturePad] loaded from', src);
    }

    function scheduleFallback() {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            if (loaded) return;
            console.warn('[SignaturePad] timed out; trying next source');
            loadNext();
        }, fallbackDelay);
    }

    function loadNext() {
        if (loaded || attempt >= sources.length) return;
        clearTimeout(timeoutId);
        const src = sources[attempt++];

        const script = document.createElement('script');
        script.src = src;
        script.async = true;

        script.onload = () => {
            // Some servers can respond with HTML (404) that still triggers onload.
            if (typeof window.SignaturePad === 'undefined') {
                console.warn('[SignaturePad] script loaded but global missing; trying next source', src);
                loadNext();
                return;
            }
            markLoaded(src);
        };

        script.onerror = () => {
            clearTimeout(timeoutId);
            console.warn('[SignaturePad] failed to load from', src);
            loadNext();
        };

        document.head.appendChild(script);
        scheduleFallback();
    }

    // If already present (hot reload), skip loading.
    if (typeof window.SignaturePad !== 'undefined') {
        markLoaded('preloaded');
        return;
    }

    loadNext();
})();
"""

drawing_js = """
let isDrawing = false;
let startX = 0;
let startY = 0;
let tempBox = null;
let lastBox = null;

const getSurfaceMetrics = (surface) => {
    const rect = surface.getBoundingClientRect();
    const baseWidth = surface.offsetWidth || rect.width || 1;
    const baseHeight = surface.offsetHeight || rect.height || 1;
    const scaleX = rect.width / baseWidth || 1;
    const scaleY = rect.height / baseHeight || 1;
    return { rect, scaleX, scaleY };
};

document.addEventListener('mousedown', (e) => {
    const surface = document.getElementById('draw-surface');
    if (!surface || !surface.contains(e.target)) return;
    surface.style.pointerEvents = 'auto';
    surface.style.touchAction = 'none';

    isDrawing = true;
    const { rect } = getSurfaceMetrics(surface);
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
    const { rect, scaleX, scaleY } = getSurfaceMetrics(surface);

    // Calculate coordinates relative to the overlay
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;

    const width = Math.abs(currentX - startX);
    const height = Math.abs(currentY - startY);
    const left = currentX < startX ? currentX : startX;
    const top = currentY < startY ? currentY : startY;

    lastBox = { left, top, width, height };

    tempBox.style.width = (width / scaleX) + 'px';
    tempBox.style.height = (height / scaleY) + 'px';
    tempBox.style.left = (left / scaleX) + 'px';
    tempBox.style.top = (top / scaleY) + 'px';
});

document.addEventListener('mouseup', (e) => {
    if (!isDrawing) return;
    isDrawing = false;

    if (tempBox) {
        const surface = document.getElementById('draw-surface');
        const { rect } = getSurfaceMetrics(surface);
        const width = lastBox ? lastBox.width : 0;
        const height = lastBox ? lastBox.height : 0;
        const left = lastBox ? lastBox.left : 0;
        const top = lastBox ? lastBox.top : 0;

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
        rx.script(sig_pad_loader_js),
        rx.script(sig_pad_init_js),
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