import reflex as rx
from pdf_signature.states.pdf_state import PDFState

sig_pad_init_js = """
console.info('[SigPad] boot');

var signaturePad = null;
var sigPadInitAttempts = 0;
var sigPadWatchdogStarted = false;
var sigPadWatchdogTimer = null;
var sigPadWatchdogDeadline = 0;

function resizeCanvasForHiDpi(canvas) {
    const ratio = Math.max(window.devicePixelRatio || 1, 1);
    const width = canvas.offsetWidth || canvas.width;
    const height = canvas.offsetHeight || canvas.height;
    if (!width || !height) return false;
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    const ctx = canvas.getContext('2d');
    if (ctx) ctx.scale(ratio, ratio);
    return true;
}

function initSigPad(force) {
    const canvas = document.getElementById('signature-pad');
    if (!canvas) return;

    if (signaturePad && !force) return;

    resizeCanvasForHiDpi(canvas);

    if (typeof SignaturePad === 'undefined') {
        if (sigPadInitAttempts < 20) {
            sigPadInitAttempts += 1;
            setTimeout(initSigPad, 150);
        } else {
            console.warn('[SignaturePad] library still missing after retries.');
        }
        return;
    }

    canvas.style.touchAction = 'none';
    signaturePad = new SignaturePad(canvas, {
        backgroundColor: 'rgba(0, 0, 0, 0)'
    });
    signaturePad.clear();
    console.info('[SignaturePad] initialized');
}

function clearSigPad() {
    if (signaturePad) signaturePad.clear();
}

function applySigPad() {
    if (signaturePad && !signaturePad.isEmpty()) {
        const data = signaturePad.toDataURL();
        const input = document.getElementById('sig-data-receiver');
        if (input) {
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
            nativeInputValueSetter.call(input, data);
            const event = new Event('input', { bubbles: true });
            input.dispatchEvent(event);
        }
    }
}

const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
            if (!mutation.target.classList.contains('hidden')) {
                setTimeout(() => initSigPad(true), 100);
            }
        }
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('sig-modal-container');
    if (modal) observer.observe(modal, { attributes: true });
    initSigPad();

    if (!sigPadWatchdogStarted) {
        sigPadWatchdogStarted = true;
        sigPadWatchdogDeadline = Date.now() + 6000;
        sigPadWatchdogTimer = setInterval(() => {
            if (typeof window.SignaturePad !== 'undefined') {
                clearInterval(sigPadWatchdogTimer);
                return;
            }
            if (Date.now() >= sigPadWatchdogDeadline) {
                clearInterval(sigPadWatchdogTimer);
                console.error('[SignaturePad] library not available after 6s; check static path and server logs.');
            }
        }, 400);
    }
});

window.addEventListener('resize', () => initSigPad(true));
window.addEventListener('load', () => setTimeout(() => initSigPad(true), 0));

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

    const isDrawEnabled = (surface) => surface && surface.dataset && surface.dataset.drawEnabled === 'true';
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
                targetId: e.target && e.target.id ? e.target.id : null,
            });
            return;
        }
        if (activePointerId !== null && activePointerId !== e.pointerId) return;

        activePointerId = e.pointerId;
        surface.setPointerCapture && surface.setPointerCapture(e.pointerId);
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
        surface && surface.releasePointerCapture && surface.releasePointerCapture(e.pointerId);

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
                    rx.el.canvas(
                        id="signature-pad",
                        class_name="border border-gray-200 rounded-lg shadow-inner w-full h-[220px] bg-transparent",
                    ),
                    class_name="mb-6 bg-gray-50 p-2 rounded-xl",
                ),
                rx.el.div(
                    rx.el.button(
                        "Clear",
                        on_click=rx.call_script("clearSigPad()"),
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
                            on_click=rx.call_script("applySigPad()"),
                            class_name="px-4 py-2 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-md transition-all",
                        ),
                        class_name="flex gap-3",
                    ),
                    class_name="flex justify-between items-center",
                ),
                rx.el.input(
                    id="sig-data-receiver",
                    class_name="hidden",
                    on_change=PDFState.save_signature,
                ),
                class_name="bg-white rounded-2xl p-8 max-w-lg w-full relative z-50 shadow-2xl",
            ),
            class_name="fixed inset-0 flex items-center justify-center z-50 p-4",
        ),
        id="sig-modal-container",
        class_name=rx.cond(PDFState.is_signing, "block", "hidden"),
    )