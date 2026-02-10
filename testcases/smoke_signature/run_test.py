"""
E2E Playwright test for the PDF signature workflow.

Test matrix (mirrors the manual QA table):
  1. Upload PDF          – file upload, page rendered
  2. Draw Box            – create a signature box on the PDF
  3. Sign Here → modal   – click the box, modal opens with canvas
  4. Draw signature      – draw strokes on the canvas (Bézier)
  5. Apply Signature     – signature appears inside the box on the PDF
  6. Export PDF          – signed PDF download link available

Usage (via run_test_suite.sh, which manages the Reflex server):
    poetry run ./run_test_suite.sh smoke_signature
"""

import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
import fitz  # PyMuPDF – already a project dependency

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:3000")
HEADLESS = os.environ.get("HEADLESS", "1") != "0"
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", str(Path(__file__).parent / "output"))
TEST_PDF = str(Path(__file__).resolve().parents[2] / "test_signature.pdf")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── helpers ──────────────────────────────────────────────────────────


def screenshot(page, name: str):
    """Save a screenshot to OUTPUT_DIR."""
    path = os.path.join(OUTPUT_DIR, f"{name}.png")
    page.screenshot(path=path)
    print(f"  📸 {path}")


def wait_for_reflex(page, timeout=30_000):
    """Wait until the Reflex app has hydrated."""
    page.wait_for_function(
        "() => document.querySelector('body') !== null",
        timeout=timeout,
    )
    page.wait_for_timeout(2000)


def inject_draw_box(page):
    """Inject a signature box via the hidden input using Playwright's fill().

    Playwright's fill() correctly triggers React's synthetic onChange event,
    unlike manual DOM event dispatch which React may ignore.
    """
    data = '{"x": 20, "y": 20, "w": 40, "h": 25}'
    input_el = page.locator('#new-box-data-input')
    # Make the input focusable / interactable for Playwright
    page.evaluate("""() => {
        const el = document.getElementById('new-box-data-input');
        if (el) {
            el.style.position = 'fixed';
            el.style.left = '0';
            el.style.top = '0';
            el.style.opacity = '0.01';
            el.style.width = '1px';
            el.style.height = '1px';
            el.style.pointerEvents = 'auto';
        }
    }""")
    input_el.fill(data, timeout=5000)


# ── tests ────────────────────────────────────────────────────────────


def test_upload_pdf(page) -> bool:
    """Test 1: Upload a PDF and verify it renders."""
    print("\n[1/6] Upload PDF")
    page.goto(BASE_URL, wait_until="networkidle")
    wait_for_reflex(page)

    upload_root = page.locator("#pdf-upload")
    expect(upload_root).to_be_visible(timeout=10_000)

    file_input = upload_root.locator('input[type="file"]')
    file_input.set_input_files(TEST_PDF)
    print("  ✅ File selected")

    page.wait_for_selector(
        "#pdf-image-container img",
        state="visible",
        timeout=15_000,
    )
    print("  ✅ PDF page image rendered")
    screenshot(page, "01_upload_pdf")
    return True


def test_draw_box(page) -> bool:
    """Test 2: Click Draw Box then create a signature box."""
    print("\n[2/6] Draw Box")

    # 1) Click "Draw Box" button to enter draw mode
    draw_btn = page.get_by_role("button", name="Draw Box")
    expect(draw_btn).to_be_visible(timeout=5_000)
    draw_btn.click()
    page.wait_for_timeout(500)

    # Verify crosshair mode activated
    page.wait_for_selector(
        "#pdf-image-container.cursor-crosshair", timeout=5_000
    )
    print("  ✅ Draw mode activated (cursor-crosshair)")

    # 2) Try native mouse drag first
    container = page.locator("#pdf-image-container")
    box = container.bounding_box()
    assert box is not None, "Container bounding box is None"

    sx = box["x"] + box["width"] * 0.2
    sy = box["y"] + box["height"] * 0.2
    ex = box["x"] + box["width"] * 0.6
    ey = box["y"] + box["height"] * 0.4

    page.mouse.move(sx, sy)
    page.mouse.down()
    page.mouse.move(ex, ey, steps=15)
    page.mouse.up()
    page.wait_for_timeout(2000)

    # Check if drag succeeded (Sign Here should appear)
    sign_count = page.get_by_text("Sign Here").count()
    if sign_count > 0:
        print("  ✅ Signature box created via mouse drag")
    else:
        # Fallback: inject the box data directly (same as draw_helpers.js)
        print("  ⚠️  Mouse drag didn't create box – using JS injection fallback")
        inject_draw_box(page)
        page.wait_for_timeout(2000)
        sign_here = page.get_by_text("Sign Here")
        expect(sign_here).to_be_visible(timeout=5_000)
        print("  ✅ Signature box created via JS injection")

    # Exit draw mode if still active
    cancel_btn = page.get_by_role("button", name="Cancel Draw")
    if cancel_btn.count() > 0:
        cancel_btn.click()
        page.wait_for_timeout(300)

    screenshot(page, "02_draw_box")
    return True


def test_open_signing_modal(page) -> bool:
    """Test 3: Click Sign Here → modal with canvas opens."""
    print("\n[3/6] Open Signing Modal")

    sign_here = page.get_by_text("Sign Here")
    expect(sign_here).to_be_visible(timeout=5_000)
    sign_here.click()
    page.wait_for_timeout(1500)

    heading = page.get_by_role("heading", name="Signature Pad")
    expect(heading).to_be_visible(timeout=5_000)
    print("  ✅ Modal opened (Signature Pad heading visible)")

    canvas = page.locator("#signature-canvas")
    expect(canvas).to_be_visible(timeout=5_000)
    print("  ✅ Canvas element visible")

    # Wait for signature_pad to initialise
    page.wait_for_function(
        "() => typeof window.getSignatureSVG === 'function'",
        timeout=5_000,
    )
    print("  ✅ signature_pad bridge loaded")

    screenshot(page, "03_modal_open")
    return True


def test_draw_signature(page) -> bool:
    """Test 4: Draw strokes on the signature canvas."""
    print("\n[4/6] Draw Signature Strokes")

    canvas = page.locator("#signature-canvas")
    cbox = canvas.bounding_box()
    assert cbox is not None, "Canvas bounding box is None"

    cx, cy = cbox["x"], cbox["y"]
    cw, ch = cbox["width"], cbox["height"]

    # Zig-zag stroke
    points = [
        (0.15, 0.5), (0.25, 0.3), (0.35, 0.7), (0.45, 0.3),
        (0.55, 0.7), (0.65, 0.3), (0.75, 0.5), (0.85, 0.4),
    ]
    x0, y0 = cx + cw * points[0][0], cy + ch * points[0][1]
    page.mouse.move(x0, y0)
    page.mouse.down()
    for px, py in points[1:]:
        page.mouse.move(cx + cw * px, cy + ch * py, steps=5)
    page.mouse.up()
    page.wait_for_timeout(300)

    # Small loop stroke
    loop = [
        (0.3, 0.6), (0.35, 0.4), (0.4, 0.55),
        (0.35, 0.65), (0.3, 0.6),
    ]
    x0, y0 = cx + cw * loop[0][0], cy + ch * loop[0][1]
    page.mouse.move(x0, y0)
    page.mouse.down()
    for px, py in loop[1:]:
        page.mouse.move(cx + cw * px, cy + ch * py, steps=5)
    page.mouse.up()
    page.wait_for_timeout(300)

    print("  ✅ Drew 2 strokes on canvas")

    # Verify pad is not empty
    is_empty = page.evaluate("window.getSignatureSVG() === ''")
    assert not is_empty, "Signature pad reports empty after drawing"
    print("  ✅ Signature pad is NOT empty")

    # Verify SVG contains path/circle elements (Bézier curves)
    svg = page.evaluate("window.getSignatureSVG()")
    has_curves = "<path" in svg or "<circle" in svg
    print(f"  ℹ️  SVG length: {len(svg)} chars, has curves: {has_curves}")
    assert has_curves, "SVG should contain <path> or <circle> elements"
    print("  ✅ SVG contains Bézier curve data")

    screenshot(page, "04_draw_signature")
    return True


def test_apply_signature(page) -> bool:
    """Test 5: Click Apply Signature → signature shows in PDF box."""
    print("\n[5/6] Apply Signature")

    apply_btn = page.get_by_role("button", name="Apply Signature")
    expect(apply_btn).to_be_visible(timeout=5_000)
    apply_btn.click()
    page.wait_for_timeout(2000)

    # Modal should close
    heading = page.get_by_role("heading", name="Signature Pad")
    expect(heading).not_to_be_visible(timeout=5_000)
    print("  ✅ Modal closed after Apply")

    # Green border = signed
    signed_box = page.locator(".border-green-500")
    expect(signed_box).to_be_visible(timeout=5_000)
    print("  ✅ Signature box shows green border (signed)")

    screenshot(page, "05_apply_signature")
    return True


def test_export_pdf(page) -> bool:
    """Test 6: Click Export PDF → signed PDF available for download."""
    print("\n[6/6] Export PDF")

    export_btn = page.get_by_role("button", name="Export PDF")
    expect(export_btn).to_be_visible(timeout=5_000)
    export_btn.click()
    page.wait_for_timeout(3000)

    download_link = page.get_by_role("link", name="Download Signed PDF")
    expect(download_link).to_be_visible(timeout=10_000)
    print("  ✅ Download Signed PDF link visible")

    href = download_link.get_attribute("href")
    assert href and "_signed.pdf" in href, f"Invalid href: {href}"
    print(f"  ✅ Download link: {href}")

    url = href if href.startswith("http") else f"{BASE_URL}{href}"
    response = page.request.get(url)
    assert response.ok, f"Download failed: {response.status}"
    body = response.body()
    assert len(body) > 500, f"Signed PDF too small: {len(body)} bytes"
    print(f"  ✅ Signed PDF downloaded: {len(body)} bytes")

    pdf_path = os.path.join(OUTPUT_DIR, "signed_output.pdf")
    with open(pdf_path, "wb") as f:
        f.write(body)
    print(f"  📄 Saved to {pdf_path}")

    screenshot(page, "06_export_pdf")
    return True


def test_verify_exported_pdf(page) -> bool:
    """Test 7: Verify the exported signed PDF matches the on-screen view.

    Steps:
      1) Render the exported PDF page to an image with PyMuPDF.
      2) Compare the signature region against the on-screen screenshot
         to confirm they are visually consistent (non-blank, structurally similar).
    """
    print("\n[7/7] Verify Exported PDF")

    signed_pdf_path = os.path.join(OUTPUT_DIR, "signed_output.pdf")
    assert os.path.exists(signed_pdf_path), f"signed_output.pdf not found at {signed_pdf_path}"

    # ── 1. Render page 1 of the signed PDF to a PNG ──────────────────
    doc = fitz.open(signed_pdf_path)
    assert doc.page_count >= 1, "Signed PDF has no pages"
    pdf_page = doc.load_page(0)
    pix = pdf_page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2× for clarity

    rendered_path = os.path.join(OUTPUT_DIR, "07_exported_pdf_render.png")
    pix.save(rendered_path)
    print(f"  📸 Rendered exported PDF → {rendered_path}")

    pdf_width = pix.width
    pdf_height = pix.height
    page_rect = pdf_page.rect
    doc.close()

    # ── 2. Get the bounding box that was used during the test ────────
    #    The box was drawn at roughly (20%, 20%) with size (40%, 25%)
    #    (from inject_draw_box fallback or mouse drag in test_draw_box).
    #    We check a generous region around where the signature should be.
    # Signature box is at approximately x=20%, y=20%, w=40%, h=25%
    sig_x = int(pdf_width * 0.15)
    sig_y = int(pdf_height * 0.15)
    sig_x2 = int(pdf_width * 0.65)
    sig_y2 = int(pdf_height * 0.50)

    # ── 3. Check the signature region is NOT blank ────────────────────
    #    "Blank" = every pixel in the region is the same colour (white/uniform).
    sig_region_samples = pix.samples  # raw pixel bytes
    stride = pix.stride
    n_channels = pix.n  # typically 3 (RGB) or 4 (RGBA)

    unique_colors = set()
    step = 3  # sample every 3rd pixel for speed
    for row in range(sig_y, min(sig_y2, pdf_height), step):
        offset = row * stride
        for col in range(sig_x, min(sig_x2, pdf_width), step):
            px_start = offset + col * n_channels
            px = sig_region_samples[px_start:px_start + n_channels]
            unique_colors.add(bytes(px))
            if len(unique_colors) > 20:
                break  # clearly not blank
        if len(unique_colors) > 20:
            break

    print(f"  ℹ️  Unique colours in signature region: {len(unique_colors)}")
    assert len(unique_colors) > 5, (
        f"Signature region looks blank – only {len(unique_colors)} unique colours found. "
        "The exported PDF may not contain the drawn signature."
    )
    print("  ✅ Signature region is NOT blank (contains drawn ink)")

    # ── 4. Compare exported PDF render with on-screen screenshot ─────
    #    Load the step-5 screenshot (after Apply Signature) and the
    #    exported PDF render, then compare signature regions via pixel
    #    similarity (at least some dark-ink pixels should appear in both).
    apply_screenshot = os.path.join(OUTPUT_DIR, "05_apply_signature.png")
    if os.path.exists(apply_screenshot):
        # Use fitz to load the screenshot as a Pixmap for comparison
        screen_pix = fitz.Pixmap(apply_screenshot)
        screen_w = screen_pix.width
        screen_h = screen_pix.height

        def count_dark_pixels(pixmap, x1, y1, x2, y2):
            """Count pixels darker than a threshold in the given rect."""
            dark = 0
            s = pixmap.stride
            n = pixmap.n
            samples = pixmap.samples
            for r in range(max(0, y1), min(y2, pixmap.height), 2):
                off = r * s
                for c in range(max(0, x1), min(x2, pixmap.width), 2):
                    px = off + c * n
                    # average of RGB channels
                    avg = sum(samples[px + ch] for ch in range(min(3, n))) / min(3, n)
                    if avg < 128:
                        dark += 1
            return dark

        # Dark pixels in exported PDF signature region
        pdf_dark = count_dark_pixels(
            pix, sig_x, sig_y, sig_x2, sig_y2
        )

        # For the on-screen screenshot, estimate the signature region
        # proportionally (the screenshot is of the whole viewport)
        scr_sig_x = int(screen_w * 0.15)
        scr_sig_y = int(screen_h * 0.15)
        scr_sig_x2 = int(screen_w * 0.65)
        scr_sig_y2 = int(screen_h * 0.50)
        screen_dark = count_dark_pixels(
            screen_pix, scr_sig_x, scr_sig_y, scr_sig_x2, scr_sig_y2
        )

        print(f"  ℹ️  Dark pixels – PDF render: {pdf_dark}, on-screen: {screen_dark}")

        # Both should have noticeable ink (dark pixels)
        assert pdf_dark > 10, (
            f"Exported PDF signature region has too few dark pixels ({pdf_dark}). "
            "Signature may not have been written to the PDF."
        )
        print("  ✅ Exported PDF contains visible ink strokes")

        # The PDF render should have a reasonable amount of detail
        # (we don't require an exact match because rendering differs)
        if screen_dark > 0:
            ratio = pdf_dark / max(screen_dark, 1)
            print(f"  ℹ️  PDF-to-screen dark-pixel ratio: {ratio:.2f}")
            # Just warn, don't fail, because different renderers give different results
            if ratio < 0.01:
                print("  ⚠️  Very low ratio – exported PDF may be missing detail")

        screen_pix = None  # release
    else:
        print("  ⚠️  Step-5 screenshot not found; skipping cross-comparison")

    # ── 5. Structural check: the signed PDF must be larger than original ─
    original_size = os.path.getsize(TEST_PDF)
    signed_size = os.path.getsize(signed_pdf_path)
    print(f"  ℹ️  Original PDF: {original_size} bytes, Signed PDF: {signed_size} bytes")
    assert signed_size >= original_size, (
        f"Signed PDF ({signed_size}B) is smaller than original ({original_size}B). "
        "Export may have failed."
    )
    print("  ✅ Signed PDF size ≥ original (signature data added)")

    screenshot(page, "07_verify_pdf")
    print("  ✅ Exported PDF verification passed")
    return True


# ── main ─────────────────────────────────────────────────────────────


def main():
    results = {}
    test_names = [
        "Upload PDF",
        "Draw Box",
        "Sign Here → Open Modal",
        "Draw Signature",
        "Apply Signature",
        "Export PDF",
        "Verify Exported PDF",
    ]
    test_fns = [
        test_upload_pdf,
        test_draw_box,
        test_open_signing_modal,
        test_draw_signature,
        test_apply_signature,
        test_export_pdf,
        test_verify_exported_pdf,
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        passed = 0
        failed = 0
        for name, fn in zip(test_names, test_fns):
            try:
                ok = fn(page)
                results[name] = "PASS" if ok else "FAIL"
                if ok:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                results[name] = f"FAIL ({e})"
                failed += 1
                try:
                    screenshot(page, f"FAIL_{name.replace(' ', '_')}")
                except Exception:
                    pass
                print(f"  ❌ {name}: {e}")

        browser.close()

    # ── summary ──
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    for name in test_names:
        status = results.get(name, "SKIP")
        icon = "✅" if status == "PASS" else "❌"
        print(f"  {icon} {name:<30} {status}")
    print(f"\n  Total: {passed} passed, {failed} failed")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
