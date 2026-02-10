/**
 * Bridge between szimek/signature_pad and the Reflex backend.
 * Requires signature_pad.umd.min.js to be loaded first.
 */
(function () {
    var signaturePad = null;

    /**
     * Initialise (or re-initialise) a SignaturePad instance on the given
     * canvas element.  Retries automatically if the canvas is not yet
     * visible / laid-out.
     */
    window.initSignaturePad = function (canvasId) {
        var canvas = document.getElementById(canvasId);
        if (!canvas || canvas.offsetWidth === 0) {
            // Canvas not ready yet – retry after a short delay
            setTimeout(function () {
                window.initSignaturePad(canvasId);
            }, 60);
            return;
        }

        // Tear down any previous instance
        if (signaturePad) {
            signaturePad.off();
            signaturePad = null;
        }

        // High-DPI handling
        var ratio = Math.max(window.devicePixelRatio || 1, 1);
        canvas.width  = canvas.offsetWidth  * ratio;
        canvas.height = canvas.offsetHeight * ratio;
        canvas.getContext('2d').scale(ratio, ratio);

        signaturePad = new SignaturePad(canvas, {
            minWidth: 0.5,
            maxWidth: 2.5,
            penColor: '#111827',
            velocityFilterWeight: 0.7,
        });

        console.log(
            '[SigPad] Initialised',
            canvas.offsetWidth + 'x' + canvas.offsetHeight,
            'ratio=' + ratio
        );
    };

    /** Clear the current drawing. */
    window.clearSignaturePad = function () {
        if (signaturePad) signaturePad.clear();
    };

    /**
     * Return the SVG representation of the current drawing, or an empty
     * string if the pad is blank.
     */
    window.getSignatureSVG = function () {
        if (!signaturePad || signaturePad.isEmpty()) return '';
        return signaturePad.toSVG();
    };
})();
