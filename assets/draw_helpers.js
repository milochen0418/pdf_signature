
window.initDrawingValues = { startX: 0, startY: 0, isDrawing: false, box: null };

window.setupDrawListeners = function() {
    // Avoid double binding
    if (window.drawListenersAttached) return;
    window.drawListenersAttached = true;

    // Mouse Down
    document.addEventListener('mousedown', function(e) {
        const container = document.getElementById('pdf-image-container'); 
        if (!container || !container.classList.contains('cursor-crosshair')) return; // Check mode via class
        
        // Ensure click is inside container
        // Note: container might have children, e.target check might fail if we click child.
        // check if container contains target
        if (!container.contains(e.target)) return;

        window.initDrawingValues.isDrawing = true;
        window.initDrawingValues.startX = e.clientX;
        window.initDrawingValues.startY = e.clientY;
        console.log(`[DrawDebug] Mouse down at ${e.clientX}, ${e.clientY}`);
        
        // Create visual box
        const box = document.createElement('div');
        box.id = 'temp-draw-box';
        box.style.position = 'fixed';
        box.style.left = e.clientX + 'px';
        box.style.top = e.clientY + 'px';
        box.style.width = '0px';
        box.style.height = '0px';
        box.style.border = '2px dashed blue';
        box.style.backgroundColor = 'rgba(0,0,255,0.2)';
        box.style.zIndex = '9999';
        box.style.pointerEvents = 'none'; // Critical: let mouse events flow to doc for move/up
        document.body.appendChild(box);
        window.initDrawingValues.box = box;
        
        e.preventDefault();
    });

    // Mouse Move
    document.addEventListener('mousemove', function(e) {
        if (!window.initDrawingValues.isDrawing) return;
        const box = window.initDrawingValues.box;
        if (!box) return;

        const currentX = e.clientX;
        const currentY = e.clientY;
        const startX = window.initDrawingValues.startX;
        const startY = window.initDrawingValues.startY;

        const width = Math.abs(currentX - startX);
        const height = Math.abs(currentY - startY);
        const left = Math.min(currentX, startX);
        const top = Math.min(currentY, startY);

        box.style.left = left + 'px';
        box.style.top = top + 'px';
        box.style.width = width + 'px';
        box.style.height = height + 'px';
    });

    // Mouse Up
    document.addEventListener('mouseup', function(e) {
        if (!window.initDrawingValues.isDrawing) return;
        window.initDrawingValues.isDrawing = false;
        
        const box = window.initDrawingValues.box;
        if (box) {
            // Calculate percentages
            const container = document.getElementById('pdf-image-container');
            if (container) {
                const cRect = container.getBoundingClientRect();
                const bRect = box.getBoundingClientRect();
                
                const relX = (bRect.left - cRect.left) / cRect.width * 100;
                const relY = (bRect.top - cRect.top) / cRect.height * 100;
                const relW = bRect.width / cRect.width * 100;
                const relH = bRect.height / cRect.height * 100;

                console.log(`[DrawDebug] Box Calculated: x=${relX.toFixed(2)}%, y=${relY.toFixed(2)}%, w=${relW.toFixed(2)}%, h=${relH.toFixed(2)}%`);

                const data = JSON.stringify({ x: relX, y: relY, w: relW, h: relH });
                
                // Send to reflex
                const input = document.getElementById('new-box-data-input');
                if (input) {
                    console.log("[DrawDebug] Found input element, dispatching event with data:", data);
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                    nativeInputValueSetter.call(input, data);
                    
                    const evInput = new Event('input', { bubbles: true });
                    input.dispatchEvent(evInput);
                    
                    const evChange = new Event('change', { bubbles: true });
                    input.dispatchEvent(evChange);
                    console.log("[DrawDebug] Events dispatched successfully");
                } else {
                    console.error("[DrawDebug] Input element 'new-box-data-input' NOT FOUND");
                }
            }
            // Remove temp box
            box.remove();
            window.initDrawingValues.box = null;
        }
    });
};

// Auto run setup
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', window.setupDrawListeners);
} else {
    window.setupDrawListeners();
}
