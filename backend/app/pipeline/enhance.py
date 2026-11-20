"""Image analysis + non-destructive enhancement.

The original is never modified. Every geometric step is folded into a single 3x3 matrix
`M` (original -> processed) so recognised boxes can be mapped back onto the untouched
original for overlays and click-to-highlight.
"""
import math
import cv2
import numpy as np


def _order_quad(pts):
    pts = np.array(pts, dtype=np.float32).reshape(4, 2)
    s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
    return np.array([pts[s.argmin()], pts[d.argmin()], pts[s.argmax()], pts[d.argmax()]], np.float32)


def estimate_skew(gray):
    """Projection-profile skew search (degrees). Returns (angle, relative_gain)."""
    h, w = gray.shape
    sc = 900 / max(h, w)
    g = cv2.resize(gray, (int(w * sc), int(h * sc)), interpolation=cv2.INTER_AREA) if sc < 1 else gray
    bw = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    ys, xs = np.nonzero(bw)
    if len(xs) < 200:
        return 0.0, 0.0
    pts = np.stack([xs, ys], 1).astype(np.float32)
    cx, cy = bw.shape[1] / 2, bw.shape[0] / 2

    def score(a):
        r = math.radians(a)
        y = (-(pts[:, 0] - cx) * math.sin(r) + (pts[:, 1] - cy) * math.cos(r))
        hist, _ = np.histogram(y, bins=max(bw.shape[0] // 2, 1))
        return float(np.sum(np.diff(hist.astype(np.float64)) ** 2))

    coarse = max(np.arange(-20, 20.1, 1.0), key=score)
    fine = max(np.arange(coarse - 1, coarse + 1.01, 0.1), key=score)
    base = score(0.0)
    gain = (score(fine) - base) / (base + 1e-9)
    return float(fine), float(gain)


def detect_document_quad(bgr):
    """Find the page boundary (largest convex quadrilateral). Ordered TL,TR,BR,BL or None."""
    h, w = bgr.shape[:2]
    sc = 700 / max(h, w)
    small = cv2.resize(bgr, (int(w * sc), int(h * sc))) if sc < 1 else bgr.copy()
    g = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    best = None
    for edges in (cv2.Canny(g, 40, 130), cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]):
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=2)
        cnts, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for c in sorted(cnts, key=cv2.contourArea, reverse=True)[:5]:
            area = cv2.contourArea(c) / (small.shape[0] * small.shape[1])
            if area < 0.2 or area > 0.97:
                continue
            ap = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
            if len(ap) == 4 and cv2.isContourConvex(ap):
                if best is None or area > best[0]:
                    best = (area, ap.reshape(4, 2) / sc)
        if best:
            break
    return _order_quad(best[1]) if best else None


def remove_shadows(bgr):
    """Divide out slowly varying illumination (keeps ink, flattens shadows/gradients)."""
    k = max(31, (min(bgr.shape[:2]) // 12) | 1)
    chans = []
    for c in cv2.split(bgr):
        bg = cv2.medianBlur(cv2.dilate(c, np.ones((7, 7), np.uint8)), k)
        chans.append(cv2.divide(c, bg, scale=255))
    return cv2.merge(chans)


def analyze(bgr):
    """Cheap diagnostics shown to the user and used to choose enhancement steps."""
    h, w = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    contrast = float(gray.std())
    bright = float(gray.mean())
    sw = min(w, 1000)
    bw = cv2.adaptiveThreshold(cv2.resize(gray, (sw, max(1, int(h * sw / w)))), 255,
                               cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    ink = float((bw > 0).mean())
    skew, skew_gain = estimate_skew(gray)
    quad = detect_document_quad(bgr)
    low = cv2.GaussianBlur(cv2.resize(gray, (64, 64)), (0, 0), 6)
    uneven = float(low.std() / (low.mean() + 1e-6))
    hp = gray.astype(np.float32) - cv2.GaussianBlur(gray, (0, 0), 1.2).astype(np.float32)
    noise = float(np.median(np.abs(hp)) / 0.6745)
    issues = []
    if sharp < 60:
        issues.append("blurry")
    if min(h, w) < 600 or max(h, w) < 900:
        issues.append("low-resolution")
    if abs(skew) >= 1.0 and skew_gain > 0.15:
        issues.append(f"skewed ({skew:+.1f}°)")
    if quad is not None:
        issues.append("page boundary / perspective")
    if uneven > 0.12:
        issues.append("uneven lighting or shadows")
    if contrast < 40:
        issues.append("low contrast")
    if noise > 6:
        issues.append("noisy")
    return {"width": w, "height": h, "megapixels": round(w * h / 1e6, 2), "sharpness": round(sharp, 1),
            "contrast": round(contrast, 1), "brightness": round(bright, 1), "ink_ratio": round(ink, 4),
            "skew_deg": round(skew, 2), "skew_confidence": round(skew_gain, 2), "has_page_quad": quad is not None,
            "page_quad": None if quad is None else quad.tolist(), "lighting_unevenness": round(uneven, 3),
            "noise": round(noise, 2), "issues": issues}


def enhance(bgr, info, level="auto", rotate90=0, max_side=3200):
    """Returns (processed_bgr, M[orig->processed], steps). level: off | auto | aggressive."""
    M = np.eye(3)
    img = bgr
    steps = []

    def compose(T):
        nonlocal M
        M = T @ M

    if rotate90:
        k = rotate90 % 4
        for _ in range(k):  # 90 degrees clockwise each
            hh = img.shape[0]
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
            compose(np.array([[0, -1, hh - 1], [1, 0, 0], [0, 0, 1]], float))
        steps.append(f"rotated {90 * k}°")
    if level == "off":
        return _cap(img, M, steps, max_side)

    # 1) perspective correction, only when a convincing page quadrilateral exists
    quad = detect_document_quad(img) if (info.get("has_page_quad") and not rotate90) else None
    if quad is not None:
        tl, tr, br, bl = quad
        W = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
        Hh = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))
        if W > 300 and Hh > 300:
            dst = np.float32([[0, 0], [W - 1, 0], [W - 1, Hh - 1], [0, Hh - 1]])
            P = cv2.getPerspectiveTransform(quad, dst)
            img = cv2.warpPerspective(img, P, (W, Hh), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            compose(P)
            steps.append("perspective correction")

    # 2) deskew (re-estimated after perspective so we do not double-correct)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ang, gain = estimate_skew(gray)
    if 0.6 <= abs(ang) <= 20 and gain > 0.1:
        hh, ww = img.shape[:2]
        R = cv2.getRotationMatrix2D((ww / 2, hh / 2), ang, 1.0)
        c, s = abs(R[0, 0]), abs(R[0, 1])
        nw, nh = int(hh * s + ww * c), int(hh * c + ww * s)
        R[0, 2] += nw / 2 - ww / 2
        R[1, 2] += nh / 2 - hh / 2
        img = cv2.warpAffine(img, R, (nw, nh), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        compose(np.vstack([R, [0, 0, 1]]))
        steps.append(f"deskew {ang:+.1f}°")

    # 3) lighting / shadows
    if info["lighting_unevenness"] > 0.08 or level == "aggressive":
        img = remove_shadows(img)
        steps.append("shadow & background flattening")
    # 4) denoise only when noisy
    if info["noise"] > 6 or level == "aggressive":
        img = (cv2.fastNlMeansDenoisingColored(img, None, 5, 5, 5, 15) if max(img.shape[:2]) <= 2200
               else cv2.bilateralFilter(img, 5, 40, 40))
        steps.append("noise reduction")
    # 5) local contrast
    if info["contrast"] < 70 or level == "aggressive":
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
        img = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
        steps.append("local contrast (CLAHE)")
    # 6) upscale small images (cubic interpolation, no invented detail)
    side = max(img.shape[:2])
    if side < 1400 and ("low-resolution" in info["issues"] or level == "aggressive"):
        f = min(2.5, 1800 / side)
        img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
        compose(np.diag([f, f, 1.0]))
        steps.append(f"upscale x{f:.1f}")
    # 7) mild sharpen
    if "blurry" in info["issues"] or level == "aggressive":
        blur = cv2.GaussianBlur(img, (0, 0), 1.6)
        img = cv2.addWeighted(img, 1.6, blur, -0.6, 0)
        steps.append("unsharp mask")
    return _cap(img, M, steps, max_side)


def _cap(img, M, steps, max_side):
    side = max(img.shape[:2])
    if side > max_side:
        f = max_side / side
        img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        M = np.diag([f, f, 1.0]) @ M
        steps.append(f"downscale to {img.shape[1]}x{img.shape[0]} (memory cap)")
    return img, M, steps


def adaptive_binary(bgr):
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41, 12),
                        cv2.COLOR_GRAY2BGR)


def map_points(M_inv, pts):
    p = np.asarray(pts, np.float64).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(p, M_inv).reshape(-1, 2)
