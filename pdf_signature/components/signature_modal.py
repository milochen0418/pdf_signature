import reflex as rx
from pdf_signature.states.pdf_state import PDFState

sig_pad_init_js = """
var signaturePad = null;
var sigPadInitAttempts = 0;

function initSigPad() {
    const canvas = document.getElementById('signature-pad');
    if (!canvas) return;

    if (typeof SignaturePad === 'undefined') {
        // Wait for the script loader fallback to finish.
        if (sigPadInitAttempts < 15) {
            sigPadInitAttempts += 1;
            setTimeout(initSigPad, 150);
        } else {
            console.warn('SignaturePad library still missing after retries.');
        }
        return;
    }

    signaturePad = new SignaturePad(canvas, {
        backgroundColor: 'rgb(255, 255, 255)'
    });
}

function clearSigPad() {
    if (signaturePad) signaturePad.clear();
}

function applySigPad() {
    if (signaturePad && !signaturePad.isEmpty()) {
        const data = signaturePad.toDataURL();
        // Get the hidden input and set value to trigger on_change in Reflex
        const input = document.getElementById('sig-data-receiver');
        if (input) {
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
            nativeInputValueSetter.call(input, data);
            const event = new Event('input', { bubbles: true });
            input.dispatchEvent(event);
        }
    }
}

// Observer for modal visibility to re-init signature pad
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
            if (!mutation.target.classList.contains('hidden')) {
                setTimeout(initSigPad, 100);
            }
        }
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('sig-modal-container');
    if (modal) observer.observe(modal, { attributes: true });
});
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
                        class_name="border border-gray-200 rounded-lg shadow-inner w-full bg-white",
                        width="500",
                        height="200",
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