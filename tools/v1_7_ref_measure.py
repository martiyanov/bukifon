#!/usr/bin/env python3
"""Замер эталонного рендера заказчика: центры 42 колпачков → преобразование
из геометрии Lapka-42 (подобие, опционально зеркало) → желаемый угол/положение."""
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lapka42_geometry as L

REF = "~/.zcode/cli/image-cache/sess_2a9e5206-3359-479d-9f72-d9f7e3203971/image-637f5da3ade50873dfde9062dff83aa1.png"
img = cv2.imread(REF)
H, W = img.shape[:2]
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# колпачки светлые на тёмной панели
th = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]
th = cv2.morphologyEx(th, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

blobs = []
for c in cnts:
    x, y, w, h = cv2.boundingRect(c)
    a = cv2.contourArea(c)
    if a < 100 or not (0.6 < w / max(h, 1) < 1.7):
        continue
    blobs.append((x + w / 2, y + h / 2, a, w * h))
if len(blobs) < 42:
    print(f"найдено только {len(blobs)} блобов — фильтр слабый, беру крупные")
areas = np.array([b[2] for b in blobs])
med = np.median(areas)
caps = [b for b in blobs if 0.35 * med < b[2] < 3.0 * med]
print(f"блобы: {len(blobs)}, похоже на колпачки: {len(caps)}")

pts = np.array([(b[0], b[1]) for b in caps])
# панель = вся ширина кадра? Оценим по разбросу: возьмём min/max x колпачков не годится.
# Масштаб: ширина панели 380 мм ≈ ширина изображения (рендер почти вплотную).
scale = 380.0 / W
pts_mm = pts * scale
pts_mm[:, 1] = pts_mm[:, 1]  # y вниз, как в нашей системе

# делим на половины: кластеризация по x относительно самого большого разрыва
xs = np.sort(pts_mm[:, 0])
gaps = np.diff(xs)
cut = xs[np.argmax(gaps)] + gaps.max() / 2
left = pts_mm[pts_mm[:, 0] < cut]
right = pts_mm[pts_mm[:, 0] >= cut]
print(f"левая: {len(left)} клавиш, правая: {len(right)}")

# углы рядов по PCA каждой половины
for name, p in (("L", left), ("R", right)):
    c = p.mean(axis=0)
    u, s, vt = np.linalg.svd(p - c)
    ang = np.degrees(np.arctan2(vt[0, 1], vt[0, 0]))
    print(f"{name}: главная ось {ang:+.1f}° (row-dir), размер {s[0]*2:.0f}×{s[1]*2:.0f} мм")

tmpl = np.array([(x, y) for x, y, _ in L.LAPKA42_LEFT])


def procrustes(src, dst, allow_reflect=True):
    """подобие src→dst: [s·R | t] (+опц. отражение), returns params, rms."""
    sc, dc = src.mean(0), dst.mean(0)
    A, B = src - sc, dst - dc
    best = None
    for refl in ((False, True) if allow_reflect else (False,)):
        M = A.copy()
        if refl:
            M = M * np.array([-1.0, 1.0])
        U, S, Vt = np.linalg.svd(M.T @ B)
        d = np.sign(np.linalg.det(U @ Vt))
        D = np.diag([1, d])
        R = U @ D @ Vt
        s = (S * np.diag(D)).sum() / (M ** 2).sum()
        t = dc - s * (R @ M.T).T.mean(0)
        pred = (s * (R @ M.T).T + t)
        rms = np.sqrt(((pred - B) ** 2).sum(1).mean())
        if best is None or rms < best[0]:
            best = (rms, s, R, t, refl)
    return best


def icp_match(tpl, det, iters=40):
    """соответствие точек шаблона детектам через ICP-подобие."""
    cur = tpl.copy()
    rms = s = None
    R = np.eye(2)
    t = det.mean(0) - tpl.mean(0)
    for _ in range(iters):
        pred = (cur - cur.mean(0)) + det.mean(0)
        rms, s, R, t, refl = procrustes(tpl, pred)  #粗
        # nearest neighbor: каждую точку tpl при текущем преобразовании → ближайший детект
        Ti = (s * (R @ (tpl - tpl.mean(0)).T).T + t)
        d2 = ((Ti[:, None, :] - det[None, :, :]) ** 2).sum(-1)
        idx = d2.argmin(1)
        cur = det[idx]
        # пересчёт на прямое соответствие
        rms2, s2, R2, t2, refl2 = procrustes(tpl, det[idx], allow_reflect=True)
        rms, s, R, t, refl = rms2, s2, R2, t2, refl2
    ang = np.degrees(np.arctan2(R[1, 0], R[0, 0]))
    return rms, s, ang, refl


for name, det in (("ЛЕВОЙ", left), ("ПРАВОЙ", right)):
    if len(det) < 15:
        print(f"{name}: мало точек ({len(det)})")
        continue
    rms, s, ang, refl = icp_match(tmpl, det)
    print(f"{name} половины: подобие Lapka-сырца: угол {ang:+.1f}°, масштаб {s:.3f}, "
          f"зеркало={refl}, RMS={rms:.2f} мм")

dbg = img.copy()
for (x, y, a, wh) in caps:
    cv2.circle(dbg, (int(x), int(y)), 6, (0, 0, 255), 2)
cv2.imwrite("<repo>/renders/templates/v1_7_ref_detect.png", dbg)
print("детект-оверлей: renders/templates/v1_7_ref_detect.png")
