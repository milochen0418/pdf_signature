import reflex as rx
from pdf_signature.states.pdf_state import PDFState

sig_pad_init_js = """
console.info('[SigPad] boot');
/*! Signature Pad v4.1.7 | https://github.com/szimek/signature_pad */
!function(t,e){"object"==typeof exports&&"undefined"!=typeof module?module.exports=e():"function"==typeof define&&define.amd?define(e):(t="undefined"!=typeof globalThis?globalThis:t||self).SignaturePad=e()}(this,(function(){"use strict";class t{constructor(t,e,i,s){if(isNaN(t)||isNaN(e))throw new Error(`Point is invalid: (${t}, ${e})`);this.x=+t,this.y=+e,this.pressure=i||0,this.time=s||Date.now()}distanceTo(t){return Math.sqrt(Math.pow(this.x-t.x,2)+Math.pow(this.y-t.y,2))}equals(t){return this.x===t.x&&this.y===t.y&&this.pressure===t.pressure&&this.time===t.time}velocityFrom(t){return this.time!==t.time?this.distanceTo(t)/(this.time-t.time):0}}class e{static fromPoints(t,i){const s=this.calculateControlPoints(t[0],t[1],t[2]).c2,n=this.calculateControlPoints(t[1],t[2],t[3]).c1;return new e(t[1],s,n,t[2],i.start,i.end)}static calculateControlPoints(e,i,s){const n=e.x-i.x,o=e.y-i.y,h=i.x-s.x,r=i.y-s.y,a=(e.x+i.x)/2,c=(e.y+i.y)/2,d=(i.x+s.x)/2,l=(i.y+s.y)/2,u=Math.sqrt(n*n+o*o),v=Math.sqrt(h*h+r*r),_=v/(u+v),p=d+(a-d)*_,m=l+(c-l)*_,g=i.x-p,w=i.y-m;return{c1:new t(a+g,c+w),c2:new t(d+g,l+w)}}constructor(t,e,i,s,n,o){this.startPoint=t,this.control2=e,this.control1=i,this.endPoint=s,this.startWidth=n,this.endWidth=o}length(){let t,e,i=0;for(let s=0;s<=10;s+=1){const n=s/10,o=this.point(n,this.startPoint.x,this.control1.x,this.control2.x,this.endPoint.x),h=this.point(n,this.startPoint.y,this.control1.y,this.control2.y,this.endPoint.y);if(s>0){const s=o-t,n=h-e;i+=Math.sqrt(s*s+n*n)}t=o,e=h}return i}point(t,e,i,s,n){return e*(1-t)*(1-t)*(1-t)+3*i*(1-t)*(1-t)*t+3*s*(1-t)*t*t+n*t*t*t}}class i{constructor(){try{this._et=new EventTarget}catch(t){this._et=document}}addEventListener(t,e,i){this._et.addEventListener(t,e,i)}dispatchEvent(t){return this._et.dispatchEvent(t)}removeEventListener(t,e,i){this._et.removeEventListener(t,e,i)}}class s extends i{constructor(t,e={}){super(),this.canvas=t,this._drawingStroke=!1,this._isEmpty=!0,this._lastPoints=[],this._data=[],this._lastVelocity=0,this._lastWidth=0,this._handleMouseDown=t=>{1===t.buttons&&this._strokeBegin(t)},this._handleMouseMove=t=>{this._strokeMoveUpdate(t)},this._handleMouseUp=t=>{1===t.buttons&&this._strokeEnd(t)},this._handleTouchStart=t=>{if(t.cancelable&&t.preventDefault(),1===t.targetTouches.length){const e=t.changedTouches[0];this._strokeBegin(e)}},this._handleTouchMove=t=>{t.cancelable&&t.preventDefault();const e=t.targetTouches[0];this._strokeMoveUpdate(e)},this._handleTouchEnd=t=>{if(t.target===this.canvas){t.cancelable&&t.preventDefault();const e=t.changedTouches[0];this._strokeEnd(e)}},this._handlePointerStart=t=>{t.preventDefault(),this._strokeBegin(t)},this._handlePointerMove=t=>{this._strokeMoveUpdate(t)},this._handlePointerEnd=t=>{this._drawingStroke&&(t.preventDefault(),this._strokeEnd(t))},this.velocityFilterWeight=e.velocityFilterWeight||.7,this.minWidth=e.minWidth||.5,this.maxWidth=e.maxWidth||2.5,this.throttle="throttle"in e?e.throttle:16,this.minDistance="minDistance"in e?e.minDistance:5,this.dotSize=e.dotSize||0,this.penColor=e.penColor||"black",this.backgroundColor=e.backgroundColor||"rgba(0,0,0,0)",this.compositeOperation=e.compositeOperation||"source-over",this._strokeMoveUpdate=this.throttle?function(t,e=250){let i,s,n,o=0,h=null;const r=()=>{o=Date.now(),h=null,i=t.apply(s,n),h||(s=null,n=[])};return function(...a){const c=Date.now(),d=e-(c-o);return s=this,n=a,d<=0||d>e?(h&&(clearTimeout(h),h=null),o=c,i=t.apply(s,n),h||(s=null,n=[])):h||(h=window.setTimeout(r,d)),i}}(s.prototype._strokeUpdate,this.throttle):s.prototype._strokeUpdate,this._ctx=t.getContext("2d"),this.clear(),this.on()}clear(){const{_ctx:t,canvas:e}=this;t.fillStyle=this.backgroundColor,t.clearRect(0,0,e.width,e.height),t.fillRect(0,0,e.width,e.height),this._data=[],this._reset(this._getPointGroupOptions()),this._isEmpty=!0}fromDataURL(t,e={}){return new Promise(((i,s)=>{const n=new Image,o=e.ratio||window.devicePixelRatio||1,h=e.width||this.canvas.width/o,r=e.height||this.canvas.height/o,a=e.xOffset||0,c=e.yOffset||0;this._reset(this._getPointGroupOptions()),n.onload=()=>{this._ctx.drawImage(n,a,c,h,r),i()},n.onerror=t=>{s(t)},n.crossOrigin="anonymous",n.src=t,this._isEmpty=!1}))}toDataURL(t="image/png",e){return"image/svg+xml"===t?("object"!=typeof e&&(e=void 0),`data:image/svg+xml;base64,${btoa(this.toSVG(e))}`):("number"!=typeof e&&(e=void 0),this.canvas.toDataURL(t,e))}on(){this.canvas.style.touchAction="none",this.canvas.style.msTouchAction="none",this.canvas.style.userSelect="none";const t=/Macintosh/.test(navigator.userAgent)&&"ontouchstart"in document;window.PointerEvent&&!t?this._handlePointerEvents():(this._handleMouseEvents(),"ontouchstart"in window&&this._handleTouchEvents())}off(){this.canvas.style.touchAction="auto",this.canvas.style.msTouchAction="auto",this.canvas.style.userSelect="auto",this.canvas.removeEventListener("pointerdown",this._handlePointerStart),this.canvas.removeEventListener("pointermove",this._handlePointerMove),this.canvas.ownerDocument.removeEventListener("pointerup",this._handlePointerEnd),this.canvas.removeEventListener("mousedown",this._handleMouseDown),this.canvas.removeEventListener("mousemove",this._handleMouseMove),this.canvas.ownerDocument.removeEventListener("mouseup",this._handleMouseUp),this.canvas.removeEventListener("touchstart",this._handleTouchStart),this.canvas.removeEventListener("touchmove",this._handleTouchMove),this.canvas.removeEventListener("touchend",this._handleTouchEnd)}isEmpty(){return this._isEmpty}fromData(t,{clear:e=!0}={}){e&&this.clear(),this._fromData(t,this._drawCurve.bind(this),this._drawDot.bind(this)),this._data=this._data.concat(t)}toData(){return this._data}_getPointGroupOptions(t){return{penColor:t&&"penColor"in t?t.penColor:this.penColor,dotSize:t&&"dotSize"in t?t.dotSize:this.dotSize,minWidth:t&&"minWidth"in t?t.minWidth:this.minWidth,maxWidth:t&&"maxWidth"in t?t.maxWidth:this.maxWidth,velocityFilterWeight:t&&"velocityFilterWeight"in t?t.velocityFilterWeight:this.velocityFilterWeight,compositeOperation:t&&"compositeOperation"in t?t.compositeOperation:this.compositeOperation}}_strokeBegin(t){if(!this.dispatchEvent(new CustomEvent("beginStroke",{detail:t,cancelable:!0})))return;this._drawingStroke=!0;const e=this._getPointGroupOptions(),i=Object.assign(Object.assign({},e),{points:[]});this._data.push(i),this._reset(e),this._strokeUpdate(t)}_strokeUpdate(t){if(!this._drawingStroke)return;if(0===this._data.length)return void this._strokeBegin(t);this.dispatchEvent(new CustomEvent("beforeUpdateStroke",{detail:t}));const e=t.clientX,i=t.clientY,s=void 0!==t.pressure?t.pressure:void 0!==t.force?t.force:0,n=this._createPoint(e,i,s),o=this._data[this._data.length-1],h=o.points,r=h.length>0&&h[h.length-1],a=!!r&&n.distanceTo(r)<=this.minDistance,c=this._getPointGroupOptions(o);if(!r||!r||!a){const t=this._addPoint(n,c);r?t&&this._drawCurve(t,c):this._drawDot(n,c),h.push({time:n.time,x:n.x,y:n.y,pressure:n.pressure})}this.dispatchEvent(new CustomEvent("afterUpdateStroke",{detail:t}))}_strokeEnd(t){this._drawingStroke&&(this._strokeUpdate(t),this._drawingStroke=!1,this.dispatchEvent(new CustomEvent("endStroke",{detail:t})))}_handlePointerEvents(){this._drawingStroke=!1,this.canvas.addEventListener("pointerdown",this._handlePointerStart),this.canvas.addEventListener("pointermove",this._handlePointerMove),this.canvas.ownerDocument.addEventListener("pointerup",this._handlePointerEnd)}_handleMouseEvents(){this._drawingStroke=!1,this.canvas.addEventListener("mousedown",this._handleMouseDown),this.canvas.addEventListener("mousemove",this._handleMouseMove),this.canvas.ownerDocument.addEventListener("mouseup",this._handleMouseUp)}_handleTouchEvents(){this.canvas.addEventListener("touchstart",this._handleTouchStart),this.canvas.addEventListener("touchmove",this._handleTouchMove),this.canvas.addEventListener("touchend",this._handleTouchEnd)}_reset(t){this._lastPoints=[],this._lastVelocity=0,this._lastWidth=(t.minWidth+t.maxWidth)/2,this._ctx.fillStyle=t.penColor,this._ctx.globalCompositeOperation=t.compositeOperation}_createPoint(e,i,s){const n=this.canvas.getBoundingClientRect();return new t(e-n.left,i-n.top,s,(new Date).getTime())}_addPoint(t,i){const{_lastPoints:s}=this;if(s.push(t),s.length>2){3===s.length&&s.unshift(s[0]);const t=this._calculateCurveWidths(s[1],s[2],i),n=e.fromPoints(s,t);return s.shift(),n}return null}_calculateCurveWidths(t,e,i){const s=i.velocityFilterWeight*e.velocityFrom(t)+(1-i.velocityFilterWeight)*this._lastVelocity,n=this._strokeWidth(s,i),o={end:n,start:this._lastWidth};return this._lastVelocity=s,this._lastWidth=n,o}_strokeWidth(t,e){return Math.max(e.maxWidth/(t+1),e.minWidth)}_drawCurveSegment(t,e,i){const s=this._ctx;s.moveTo(t,e),s.arc(t,e,i,0,2*Math.PI,!1),this._isEmpty=!1}_drawCurve(t,e){const i=this._ctx,s=t.endWidth-t.startWidth,n=2*Math.ceil(t.length());i.beginPath(),i.fillStyle=e.penColor;for(let i=0;i<n;i+=1){const o=i/n,h=o*o,r=h*o,a=1-o,c=a*a,d=c*a;let l=d*t.startPoint.x;l+=3*c*o*t.control1.x,l+=3*a*h*t.control2.x,l+=r*t.endPoint.x;let u=d*t.startPoint.y;u+=3*c*o*t.control1.y,u+=3*a*h*t.control2.y,u+=r*t.endPoint.y;const v=Math.min(t.startWidth+r*s,e.maxWidth);this._drawCurveSegment(l,u,v)}i.closePath(),i.fill()}_drawDot(t,e){const i=this._ctx,s=e.dotSize>0?e.dotSize:(e.minWidth+e.maxWidth)/2;i.beginPath(),this._drawCurveSegment(t.x,t.y,s),i.closePath(),i.fillStyle=e.penColor,i.fill()}_fromData(e,i,s){for(const n of e){const{points:e}=n,o=this._getPointGroupOptions(n);if(e.length>1)for(let s=0;s<e.length;s+=1){const n=e[s],h=new t(n.x,n.y,n.pressure,n.time);0===s&&this._reset(o);const r=this._addPoint(h,o);r&&i(r,o)}else this._reset(o),s(e[0],o)}}toSVG({includeBackgroundColor:t=!1}={}){const e=this._data,i=Math.max(window.devicePixelRatio||1,1),s=this.canvas.width/i,n=this.canvas.height/i,o=document.createElementNS("http://www.w3.org/2000/svg","svg");if(o.setAttribute("xmlns","http://www.w3.org/2000/svg"),o.setAttribute("xmlns:xlink","http://www.w3.org/1999/xlink"),o.setAttribute("viewBox",`0 0 ${s} ${n}`),o.setAttribute("width",s.toString()),o.setAttribute("height",n.toString()),t&&this.backgroundColor){const t=document.createElement("rect");t.setAttribute("width","100%"),t.setAttribute("height","100%"),t.setAttribute("fill",this.backgroundColor),o.appendChild(t)}return this._fromData(e,((t,{penColor:e})=>{const i=document.createElement("path");if(!(isNaN(t.control1.x)||isNaN(t.control1.y)||isNaN(t.control2.x)||isNaN(t.control2.y))){const s=`M ${t.startPoint.x.toFixed(3)},${t.startPoint.y.toFixed(3)} C ${t.control1.x.toFixed(3)},${t.control1.y.toFixed(3)} ${t.control2.x.toFixed(3)},${t.control2.y.toFixed(3)} ${t.endPoint.x.toFixed(3)},${t.endPoint.y.toFixed(3)}`;i.setAttribute("d",s),i.setAttribute("stroke-width",(2.25*t.endWidth).toFixed(3)),i.setAttribute("stroke",e),i.setAttribute("fill","none"),i.setAttribute("stroke-linecap","round"),o.appendChild(i)}}),((t,{penColor:e,dotSize:i,minWidth:s,maxWidth:n})=>{const h=document.createElement("circle"),r=i>0?i:(s+n)/2;h.setAttribute("r",r.toString()),h.setAttribute("cx",t.x.toString()),h.setAttribute("cy",t.y.toString()),h.setAttribute("fill",e),o.appendChild(h)})),o.outerHTML}}return s}));

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

    if (signaturePad && !force) return; // Already initialized

    // Reset drawing buffer to match displayed size before instantiating
    resizeCanvasForHiDpi(canvas);

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