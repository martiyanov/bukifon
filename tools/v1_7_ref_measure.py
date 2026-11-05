#!/usr/bin/env python3
"""Замер эталона заказчика v2: 21+21 колпачков, перебор угла + Прокруст."""
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
g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
th = cv2.threshold(g, 200, 255, cv2.THRESH_BINARY)[1]
cnts, _ = cv2.findContours(th, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

caps = []
for c in cnts:
    a = cv2.contourArea(c)
    if 9000 < a < 14000:
        m = cv2.moments(c)
        caps.append([m["m10"] / m["m00"], m["m01"] / m["m00"], a])
print(f"детект: {len(caps)} блобов 9000–14000 px²")

scale = 380.0 / W
pts = np.array([(p[0] * scale, p[1] * scale) for p in caps])
xs = np.sort(pts[:, 0])
gaps = np.diff(xs)
i = int(np.argmax(gaps))
cut = (xs[i] + xs[i + 1]) / 2
li = pts[:, 0] < cut
left, right = pts[li], pts[~li]
print(f"левая {len(left)} / правая {len(right)}")
# если не 21 — выбросить самый нетипичный по площади
if len(left) != 21 or len(right) != 21:
    areas = np.array([p[2] for p in caps])
    med = np.median(areas)
    bad = np.argsort(abs(areas - med))[-1]
    print("лишний блоб (площадь %.0f):" % areas[bad],
          "x=%.0f y=%.0f" % (pts[bad, 0], pts[bad, 1]))
    keep = np.ones(len(pts), bool)
    keep[bad] = False
    pts = pts[keep]
    li = pts[:, 0] < cut
    left, right = pts[li], pts[~li]
    print(f"после отбраковки: левая {len(left)} / правая {len(right)}")

tmpl = np.array([(x, y) for x, y, _ in L.LAPKA42_LEFT])


def rot(p, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    return p @ np.array([[c, s], [-s, c]])


def procrustes(A, B):
    """подобие A→B (без отражения); s, R, t, rms."""
    ca, cb = A.mean(0), B.mean(0)
    P, Q = A - ca, B - cb
    U, S, Vt = np.linalg.svd(P.T @ Q)
    d = 1.0 if np.linalg.det(U @ Vt) > 0 else -1.0
    R = U @ np.diag([1.0, d]) @ Vt
    s = (S * np.array([1.0, d])).sum() / (P ** 2).sum()
    t = cb - s * (R @ ca)
    rms = np.sqrt((((s * (R @ A.T).T + t) - B) ** 2).sum(1).mean())
    return s, R, t, rms


def best_fit(det, reflect):
    T0 = tmpl * np.array([-1.0, 1.0]) if reflect else tmpl.copy()
    best = None
    for ang in np.arange(-60, 60.25, 0.25):
        T = rot(T0, ang)
        cT, cD = T.mean(0), det.mean(0)
        s0 = np.sqrt(((det - cD) ** 2).sum(1).mean() / ((T - cT) ** 2).sum(1).mean())
        P = (T - cT) * s0 + cD
        try:
            for _ in range(12):
                d2 = ((P[:, None, :] - det[None, :, :]) ** 2).sum(-1)
                idx = d2.argmin(1)
                if len(np.unique(idx)) < 18:
                    raise ValueError
                s, R, t, _ = procrustes(T, det[idx])
                P = s * (R @ T.T).T + t
            rms = np.sqrt(((P - det[idx]) ** 2).sum(1).mean())
        except ValueError:
            continue
        if best is None or rms < best[0]:
            _, R, _, _ = procrustes(T, det[idx])
            angR = np.degrees(np.arctan2(R[1, 0], R[0, 0]))
            best = (rms, s, angR, idx)
    return best


print("\n== Подгонка (перебор угла + ICP-Прокруст) ==")
res = {}
for name, det in (("L", left), ("R", right)):
    for refl in (False, True):
        out = best_fit(det, refl)
        tag = "зеркало" if refl else "прямо "
        if out is None:
            print(f"{name} {tag}: сходства нет")
            res[(name, refl)] = None
            continue
        rms, s, ang, idx = out
        print(f"{name} {tag}: RMS {rms:6.2f} мм, масштаб {s:.3f}, угол {ang:+7.2f}°")
        res[(name, refl)] = (rms, s, ang)

print("\n== Положения половин на эталоне (мм; y от верхнего края) ==")
for name, p in (("L", left), ("R", right)):
    print(f"  {name}: x {p[:,0].min():6.1f}…{p[:,0].max():6.1f}  "
          f"y {p[:,1].min():6.1f}…{p[:,1].max():6.1f}")
    c = p.mean(0)
    _, sv, vt = np.linalg.svd(p - c)
    print(f"     PCA ось {np.degrees(np.arctan2(vt[0,1], vt[0,0])):+.1f}°, "
          f"разброс {sv[0]*2:.0f}×{sv[1]*2:.0f} мм")

dbg = img.copy()
for x, y, a in caps:
    cv2.circle(dbg, (int(x / scale), int(y / scale)), 8, (0, 0, 255), 2)
cv2.imwrite(os.path.join(os.path.dirname(HERE), "renders", "templates",
                         "v1_7_ref_detect.png"), dbg)
print("\nоверлей: renders/templates/v1_7_ref_detect.png")
