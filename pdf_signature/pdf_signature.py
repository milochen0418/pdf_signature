import logging

import reflex as rx
from fastapi import Request
from starlette.responses import JSONResponse
from pdf_signature.states.pdf_state import PDFState
from pdf_signature.components.sidebar import sidebar
from pdf_signature.components.pdf_viewer import pdf_controls, pdf_viewer_canvas
from pdf_signature.components.signature_modal import signature_modal



def index() -> rx.Component:
    return rx.el.main(
        rx.script(src="/draw_helpers.js"),
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


logging.basicConfig(level=logging.INFO)
logging.getLogger("interaction").setLevel(logging.INFO)

app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(rel="preconnect", href="https://fonts.gstatic.com", cross_origin=""),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
            rel="stylesheet",
        ),
        rx.el.script(
            """
(function () {
    if (window.__rxFrontendLogInstalled) return;
    window.__rxFrontendLogInstalled = true;

    function resolveApiUrl() {
        var loc = window.location;
        if (!loc || !loc.origin) return "/api/frontend-log";
        if (loc.port && loc.port !== "8000") {
            var base = loc.origin.replace(":" + loc.port, ":8000");
            return base + "/api/frontend-log";
        }
        return loc.origin + "/api/frontend-log";
    }

    function send(level, message, stack) {
        try {
            fetch(resolveApiUrl(), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    level: level,
                    message: message,
                    stack: stack || "",
                    url: window.location.href
                })
            });
        } catch (e) {
            /* ignore */
        }
    }

    ["log", "warn", "error"].forEach(function (level) {
        var original = console[level];
        console[level] = function () {
            try {
                var msg = Array.prototype.slice.call(arguments).map(function (arg) {
                    if (typeof arg === "string") return arg;
                    try { return JSON.stringify(arg); } catch (e) { return String(arg); }
                }).join(" ");
                send(level, msg, "");
            } catch (e) {
                /* ignore */
            }
            if (original) return original.apply(console, arguments);
        };
    });

    window.addEventListener("error", function (event) {
        var msg = event.message || "window.error";
        var stack = event.error && event.error.stack ? event.error.stack : "";
        send("error", msg, stack);
    });

    window.addEventListener("unhandledrejection", function (event) {
        var reason = event.reason;
        var msg = reason && reason.message ? reason.message : String(reason);
        var stack = reason && reason.stack ? reason.stack : "";
        send("error", "unhandledrejection: " + msg, stack);
    });
})();
"""
    ),
    ],
)


async def frontend_log(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    level = str(data.get("level", "log")).lower()
    message = str(data.get("message", ""))
    stack = str(data.get("stack", ""))
    url = str(data.get("url", ""))
    prefix = "[frontend]"
    text = f"{prefix} {level}: {message} ({url})"
    if stack:
        text = f"{text}\n{stack}"
    logger = logging.getLogger("frontend")
    if level == "error":
        logger.error(text)
    elif level == "warn":
        logger.warning(text)
    else:
        logger.info(text)
    return JSONResponse({"ok": True})


if app._api:
    app._api.add_route("/api/frontend-log", frontend_log, methods=["POST"])
app.add_page(index, route="/")