import reflex as rx
from pdf_signature.states.pdf_state import PDFState
from pdf_signature.components.sidebar import sidebar
from pdf_signature.components.pdf_viewer import pdf_controls, pdf_viewer_canvas
from pdf_signature.components.signature_modal import signature_modal, sig_pad_init_js

drawing_js = """
(function() {
    if (window.__drawSurfaceHandlersAttached) return;
    window.__drawSurfaceHandlersAttached = true;

    let isDrawing = false;
    let startX = 0;
    let startY = 0;
    let tempBox = null;
    let lastBox = null;
    let activePointerId = null;

    const getSurfaceMetrics = (surface) => {
        const rect = surface.getBoundingClientRect();
        const baseWidth = surface.offsetWidth || rect.width || 1;
        const baseHeight = surface.offsetHeight || rect.height || 1;
        const scaleX = rect.width / baseWidth || 1;
        const scaleY = rect.height / baseHeight || 1;
        return { rect, scaleX, scaleY };
    };

    const isDrawEnabled = (surface) => surface?.dataset?.drawEnabled === 'true';
    window.__drawDebugEnabled = true;
    const logDraw = (...args) => {
        if (window.__drawDebugEnabled) {
            console.info('[DrawBox]', ...args);
        }
    };

    const beginDraw = (e) => {
        const surface = document.getElementById('draw-surface');
        if (!surface || !surface.contains(e.target)) return;
        if (!isDrawEnabled(surface)) {
            logDraw('pointerdown ignored; draw disabled', {
                pointerId: e.pointerId,
                targetId: e.target?.id || null,
            });
            return;
        }
        if (activePointerId !== null && activePointerId !== e.pointerId) return;

        activePointerId = e.pointerId;
        surface.setPointerCapture?.(e.pointerId);
        isDrawing = true;

        const { rect } = getSurfaceMetrics(surface);
        startX = e.clientX - rect.left;
        startY = e.clientY - rect.top;
        logDraw('begin', { pointerId: e.pointerId, startX, startY });

        tempBox = document.createElement('div');
        tempBox.style.position = 'absolute';
        tempBox.style.border = '2px dashed #3b82f6';
        tempBox.style.backgroundColor = 'rgba(59, 130, 246, 0.2)';
        tempBox.style.left = startX + 'px';
        tempBox.style.top = startY + 'px';
        tempBox.style.pointerEvents = 'none';
        surface.appendChild(tempBox);
    };

    const moveDraw = (e) => {
        if (!isDrawing || !tempBox || e.pointerId !== activePointerId) return;
        const surface = document.getElementById('draw-surface');
        if (!surface) return;
        if (!isDrawEnabled(surface)) return;
        const { rect, scaleX, scaleY } = getSurfaceMetrics(surface);

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
    };

    const endDraw = (e) => {
        if (!isDrawing || e.pointerId !== activePointerId) return;
        isDrawing = false;
        activePointerId = null;

        const surface = document.getElementById('draw-surface');
        if (surface && !isDrawEnabled(surface)) return;
        surface?.releasePointerCapture?.(e.pointerId);

        if (tempBox) {
            const rect = surface ? surface.getBoundingClientRect() : null;
            const width = lastBox ? lastBox.width : 0;
            const height = lastBox ? lastBox.height : 0;
            const left = lastBox ? lastBox.left : 0;
            const top = lastBox ? lastBox.top : 0;

            tempBox.remove();
            tempBox = null;

            if (!rect) return;
            if (width < 5 || height < 5) return;

            const pctX = (left / rect.width) * 100;
            const pctY = (top / rect.height) * 100;
            const pctW = (width / rect.width) * 100;
            const pctH = (height / rect.height) * 100;

            const input = document.getElementById('new-box-data');
            if (input) {
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                nativeInputValueSetter.call(input, JSON.stringify({x: pctX, y: pctY, w: pctW, h: pctH}));
                const event = new Event('input', { bubbles: true });
                input.dispatchEvent(event);
            }
            logDraw('end', { pointerId: e.pointerId, pctX, pctY, pctW, pctH });
        }
    };

    document.addEventListener('pointerdown', beginDraw);
    document.addEventListener('pointermove', moveDraw);
    document.addEventListener('pointerup', endDraw);
    document.addEventListener('pointercancel', endDraw);
    logDraw('handlers attached');
})();
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