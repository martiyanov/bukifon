"""make_paperkit.py — печатный «бумажный набор» 1:1 для проверки эргономики.

Выход:
  renders/templates/bukifon_paperkit_1to1.pdf  (4 страницы A4 landscape)
    стр.1–2 — панель v0.4 1:1 (берутся из bukifon_v04_panel_1to1.pdf: 2 листа
              A4 с перекрытием 10 мм — не перерисовываются, чтобы не разойтись
              с каноном);
    стр.3   — боковой профиль клина 8° 1:1 (перед 32 / зад 61.5, глубина 210,
              R4), лапки склейки, линии сгиба, линейка 50 мм, место под панель;
    стр.4   — карта проверки: зоны панели + чек-лист 7 проверок + поля заметок.

  mechanical/preview_v05_B/paperkit_page3_profile.png, page4_checkmap.png —
  превью для быстрой проверки (не являются печатными листами 1:1).

    MPLCONFIGDIR=/tmp/mplcache /tmp/msvenv/bin/python mechanical/generator/make_paperkit.py
"""
from __future__ import annotations

import io
import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, FancyBboxPatch, Polygon, Rectangle
from matplotlib.lines import Line2D
from pypdf import PdfReader, PdfWriter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SPEC_JSON = os.path.join(ROOT, "spec", "panel-spec-v0.4.json")
PANEL_PDF = os.path.join(ROOT, "renders", "templates", "bukifon_v04_panel_1to1.pdf")
OUT_PDF = os.path.join(ROOT, "renders", "templates", "bukifon_paperkit_1to1.pdf")
PREVIEW = os.path.join(ROOT, "mechanical", "preview_v05_B")
TMP_PDF = os.path.join("/tmp", "paperkit_pages34.pdf")
os.makedirs(PREVIEW, exist_ok=True)

A4W, A4H = 297.0, 210.0            # мм, landscape
MM = 1.0 / 25.4

FRONT, REAR, DEPTH, ANG, R = 32.0, 61.5, 210.0, 8.0, 4.0
PANEL_T = 3.0

# ---- геометрия профиля -----------------------------------------------------
RIM_FRONT = FRONT - PANEL_T        # 29.0 — кромка корпуса (панель сверху)
RIM_REAR = REAR - PANEL_T          # 58.5


def profile_contour(ox, oy):
    """Контур профиля (x — глубина, y — высота) с R4 у переднего верхнего угла."""
    # передняя стенка снизу вверх до начала радиуса
    pts = [(DEPTH, 0.0), (DEPTH, RIM_FRONT - R)]
    # дуга R4 от вертикали к наклонной верхней линии (центр на пересечении
    # нормалей: примерно (DEPTH-R, RIM_FRONT-R/1))
    cx, cy = DEPTH - R, RIM_FRONT - R * 0.35
    # строим плавную дугу от (DEPTH, RIM_FRONT-R) к точке на верхней линии
    for i in range(1, 13):
        a = math.pi / 2 * i / 12
        pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
    # верхняя линия к задней стенке (скос 8°)
    pts.append((0.0, RIM_REAR))
    pts.append((0.0, 0.0))
    return [(ox + x, oy + y) for x, y in pts]


def page3_profile():
    fig = plt.figure(figsize=(A4W * MM, A4H * MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4W); ax.set_ylim(0, A4H)
    ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Rectangle((4, 4), A4W - 8, A4H - 8, fc="white", ec="#dddddd", lw=0.4))

    ax.text(A4W / 2, A4H - 10,
            "БУКИФОН — БУМАЖНЫЙ МАКЕТ v0.5-B (клин 8°) · стр.3/4",
            ha="center", fontsize=12.5, fontweight="bold")
    ax.text(A4W / 2, A4H - 15.5,
            "Печать A4 100 % (без «по размеру страницы»). Проверка масштаба — линейка "
            "50 мм. Вырезать 2 одинаковых профиля (левый и правый борт).",
            ha="center", fontsize=6.0, color="#444")

    # ---- инструкция сверху (3 колонки) -----------------------------------
    cols = [
        (10, "1. ВЫРЕЗАТЬ", [
            "• 2 профиля по сплошной",
            "  линии (борта L/R).",
            "• Картон 2 мм: низ",
            "  380 × 210; передняя",
            "  планка 380 × 29;",
            "  задняя 380 × 58.5.",
        ]),
        (108, "2. СОБРАТЬ", [
            "• Отогнуть лапки по",
            "  пунктиру (10 мм).",
            "• Склеить борта с низом",
            "  и планками (ПВА /",
            "  двусторонний скотч).",
            "• Дать просохнуть 5 мин.",
        ]),
        (206, "3. ПАНЕЛЬ И ПРОВЕРКИ", [
            "• Наклеить панель",
            "  (листы 1–2) на кромку:",
            "  перед 32, зад 61.5 мм.",
            "• Ручки Ø14×15, экран-",
            "  картонка на шарнире.",
            "• Пройти 7 проверок (стр.4).",
        ]),
    ]
    for cx0, head, lines in cols:
        ax.text(cx0, 179, head, fontsize=6.6, fontweight="bold", color="#111")
        for i, ln in enumerate(lines):
            ax.text(cx0 + 1, 173 - i * 4.2, ln, fontsize=5.3, color="#222")
    ax.text(A4W / 2, 143.5,
            "ВРЕМЯ: 30 МИН · МАТЕРИАЛЫ: КАРТОН 2 ММ, КЛЕЙ, НОЖНИЦЫ, ЛИНЕЙКА",
            ha="center", fontsize=5.8, color="#555")

    # ---- профиль 1:1 ------------------------------------------------------
    ox, oy = 42.0, 54.0
    k = math.tan(math.radians(ANG))
    zc = RIM_FRONT + R * k - R * math.sqrt(1 + k * k)
    cx = ox + DEPTH - R
    cy = oy + zc
    arc = []
    for i in range(0, 25):
        a = math.radians(90.0 - ANG * 0 + 0) * 0  # placeholder
        aa = (math.pi / 2 - math.radians(ANG)) * i / 24
        arc.append((cx + R * math.cos(aa), cy + R * math.sin(aa)))
    # arc: от вертикали (aa=0) к верхней линии (aa=90°−8°=82°)
    contour = [(ox, oy), (ox + DEPTH, oy), (ox + DEPTH, oy + zc)] + arc[1:] + \
              [(ox + 0.0, oy + RIM_REAR), (ox, oy)]
    ax.add_patch(Polygon(contour, closed=True, fc="#f4f4f4", ec="#111", lw=1.6,
                         joinstyle="round"))

    # место панели
    ax.plot([ox, ox + DEPTH], [oy + RIM_REAR, oy + RIM_FRONT],
            color="#1f4e9c", lw=1.2, linestyle=(0, (5, 2)))
    ax.plot([ox, ox + DEPTH], [oy + REAR, oy + FRONT],
            color="#1f4e9c", lw=1.8, linestyle=(0, (2, 1.6)))
    ax.text(ox + DEPTH * 0.52, oy + (FRONT + REAR) / 2 + 8,
            "МЕСТО ПАНЕЛИ: наклеить листы 1–2 (панель v0.4, 1:1)",
            fontsize=6.0, color="#1f4e9c", ha="center", rotation=-1.9)

    # лапки склейки
    tab = 10.0
    ax.add_patch(Rectangle((ox, oy - tab), DEPTH, tab, fc="none", ec="#c06000",
                           lw=0.8, linestyle=(0, (4, 2))))
    ax.add_patch(Rectangle((ox - tab, oy), tab, RIM_REAR, fc="none", ec="#c06000",
                           lw=0.8, linestyle=(0, (4, 2))))
    ax.add_patch(Rectangle((ox + DEPTH, oy), tab, RIM_FRONT, fc="none", ec="#c06000",
                           lw=0.8, linestyle=(0, (4, 2))))
    ax.text(ox + DEPTH / 2, oy - tab - 15.0,
            "лапка склейки 10 мм — отогнуть по пунктиру и приклеить к нижней пластине",
            ha="center", fontsize=5.6, color="#c06000")
    ax.text(ox - tab / 2, oy + RIM_REAR / 2, "10", ha="center", va="center",
            fontsize=5.2, color="#c06000", rotation=90)

    # размеры
    def dim(x1, y1, x2, y2, text, fs=7.2, color="#8b0000", off=(0, 0), rot=0):
        ax.annotate("", xy=(x1, y1), xytext=(x2, y2),
                    arrowprops=dict(arrowstyle="<->", lw=0.7, color=color))
        ax.text((x1 + x2) / 2 + off[0], (y1 + y2) / 2 + off[1], text,
                ha="center", va="center", fontsize=fs, color=color, rotation=rot)

    dim(ox, oy - tab - 5.0, ox + DEPTH, oy - tab - 5.0,
        "210 мм — глубина (Y)", off=(0, -5.5))
    dim(ox + DEPTH + tab + 6, oy, ox + DEPTH + tab + 6, oy + FRONT,
        "32 мм\n(перед)", off=(9, 0))
    dim(ox - tab - 6, oy, ox - tab - 6, oy + REAR, "61.5 мм\n(зад)", off=(-10, 0))
    dim(ox - tab - 6, oy + RIM_REAR, ox - tab - 6, oy + REAR, "3", fs=4.8,
        color="#555", off=(-3, 0))
    dim(ox + 12, oy + RIM_FRONT + 1, ox + 12, oy + RIM_REAR - 1.0,
        "29.5 мм (210·tan 8°)", fs=5.8, color="#006400", off=(22, 0))

    # угол и R4
    ax.plot([ox + 6, ox + 24], [oy + RIM_REAR, oy + RIM_REAR - 18 * k], color="#006400",
            lw=0.6)
    ax.text(ox + 21, oy + RIM_REAR - 4.2, "8°", fontsize=8.5, color="#006400")
    ax.annotate("R4 — кромка под запястье", xy=(ox + DEPTH - 1.0, oy + zc + 2.0),
                xytext=(ox + DEPTH - 74, oy + zc + 21), fontsize=6.0, color="#333",
                arrowprops=dict(arrowstyle="->", lw=0.6))
    ax.text(ox + 3, oy + RIM_REAR + 5.0,
            "верхняя линия = кромка корпуса; панель 3 мм — сверху", fontsize=5.2,
            color="#555")

    # линейка
    rx, ry = 205.0, 16.0
    ax.plot([rx, rx + 50], [ry, ry], color="#000", lw=1.0)
    for i in range(51):
        h = 4.0 if i % 10 == 0 else (2.4 if i % 5 == 0 else 1.3)
        ax.plot([rx + i, rx + i], [ry, ry + h], color="#000", lw=0.5)
    ax.text(rx + 25, ry - 4.5, "50 мм — контроль печати 1:1", ha="center", fontsize=6.2)
    ax.text(rx + 25, ry + 8.0, "если линейка не 50 мм — печатать заново, 100 %",
            ha="center", fontsize=5.4, color="#8b0000")
    ax.text(14, 22,
            "Профиль — это борт макета. Вырезать ДВА (L и R), зеркалить не нужно.\n"
            "Низ 380×210 склеить из двух A4-листов картона встык (2 мм).",
            fontsize=5.2, color="#555", va="top")

    fig.savefig(TMP_PDF, format="pdf")
    fig.savefig(os.path.join(PREVIEW, "paperkit_page3_profile.png"), dpi=140)
    plt.close(fig)


# ---- стр.4: карта проверки -------------------------------------------------
def load_spec():
    return json.load(open(SPEC_JSON))


def _wrap(text, width=54):
    words, line, out = text.split(), "", []
    for w_ in words:
        if len(line) + len(w_) + 1 > width:
            out.append(line)
            line = w_
        else:
            line = (line + " " + w_).strip()
    out.append(line)
    return out


def page4_checkmap():
    spec = load_spec()["controls"]
    knobs = [dict(center_mm=e["center_mm"])
             for e in spec["encoders_left"] + spec["encoders_right"]]
    keys = spec["keyboard_left"] + spec["keyboard_right"]
    jacks = spec["jacks"]
    scr = spec["lcd"]["active_cutout"]
    faders = spec["faders"]

    fig = plt.figure(figsize=(A4W * MM, A4H * MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4W); ax.set_ylim(0, A4H)
    ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Rectangle((4, 4), A4W - 8, A4H - 8, fc="white", ec="#dddddd", lw=0.4))
    ax.text(A4W / 2, A4H - 10,
            "БУКИФОН — КАРТА ПРОВЕРКИ ЭРГОНОМИКИ · стр.4/4",
            ha="center", fontsize=12.5, fontweight="bold")
    ax.text(A4W / 2, A4H - 15.5,
            "Ставится на собранный картонный макет. Версия панели: v0.4 "
            "(канон, 42 клавиши ±18°). Печать A4 100 %.",
            ha="center", fontsize=6.0, color="#444")

    # --- схема зон (1:2) ---------------------------------------------------
    sx = sy = 0.46
    ox, oy = 14.0, 74.0
    pw, ph = 380 * sx, 210 * sy
    ax.add_patch(Rectangle((ox, oy), pw, ph, fc="#333333", ec="#111", lw=1.0))
    ax.text(ox + pw / 2, oy + ph + 3.5, "СХЕМА ЗОН ПАНЕЛИ (1:2)",
            ha="center", fontsize=6.6, color="#333", fontweight="bold")

    def P(x, y):
        return (ox + x * sx, oy + (210 - y) * sy)

    s_ = scr
    ax.add_patch(Rectangle(P(s_["center_mm"][0] - s_["opening_size_mm"][0] / 2,
                             s_["center_mm"][1] + s_["opening_size_mm"][1] / 2),
                           s_["opening_size_mm"][0] * sx,
                           s_["opening_size_mm"][1] * sy,
                           fc="#0b2a4a", ec="#9ab"))
    ax.text(*P(190, 96), "экран 5\" 108 × 64.8", ha="center", va="top",
            fontsize=4.6, color="#9ab")
    for j in jacks:
        ax.add_patch(plt.Circle(P(j["center_mm"][0], j["center_mm"][1]), 2.6,
                                fc="#ddd", ec="#333", lw=0.3))
    ax.text(*P(190, 20), "10 × mini-jack (Y 10.5)", ha="center", va="center",
            fontsize=4.6, color="#cfd8e6")
    for k in knobs:
        ax.add_patch(plt.Circle(P(*k["center_mm"]), 14 * sx / 2, fc="#111",
                                ec="#999", lw=0.3))
    # (подпись «16 × энкодер» — в легенде ниже, чтобы не наезжать на ручки)
    for k in keys:
        x, y = P(*k["center_mm"])
        ax.add_patch(Rectangle((x - 17.5 * sx / 2, y - 16.5 * sy / 2),
                               17.5 * sx, 16.5 * sy, angle=-k["angle_deg"],
                               rotation_point="center", fc="#e8e2d6", ec="#777",
                               lw=0.25))
    ax.text(*P(190, 206), "42 клавиши Lapka-42 ±18°", ha="center", va="center",
            fontsize=4.6, color="#cfd8e6")
    ax.text(*P(190, 199), "внутри: CORE-2 · PANEL-2 · PWR-2 · 1S2P 18650",
            ha="center", va="center", fontsize=3.9, color="#9aa4b2")
    for f in faders:
        x, y = P(f["slot"]["center_mm"][0], f["slot"]["center_mm"][1])
        ax.add_patch(Rectangle((x - 1.3, y - 63 * sy / 2), 2.6, 63 * sy,
                               fc="#000", ec="#999", lw=0.3))
    ax.text(*P(190, 111), "2 × фейдер (Y 150)", ha="center", va="center",
            fontsize=4.4, color="#cfd8e6")
    # внутри: CORE-2 и батарея (тонкий пунктир)
    ax.add_patch(Rectangle(P(90, 159), 200 * sx, 108 * sy, fc="none", ec="#aaa",
                           lw=0.5, linestyle=(0, (2, 2))))

    ax.add_patch(Rectangle(P(302, 121), 40 * sx, 65 * sy, fc="none", ec="#2c6fbb",
                           lw=0.6, linestyle=(0, (3, 2))))

    ax.text(ox, oy - 4, "лев. половина", fontsize=4.4, color="#666")
    ax.text(ox + pw, oy - 4, "прав. половина", fontsize=4.4, color="#666", ha="right")

    # --- справочная таблица зон -------------------------------------------
    ax.text(14, 62, "ЗОНЫ ПАНЕЛИ (координаты — spec/panel-spec-v0.4.json):",
            fontsize=6.2, fontweight="bold")
    zone = [
        "• 42 клавиши Choc, колпачок 17.5×16.5, шаг 18×17, половины ±18°",
        "• 16 энкодеров Ø14: X 25.2/54.1/82.6/111.4 и 269.3/297.8/326.6/355.8; Y 35.7/68.5",
        "• экран 5\" 800×480: вырез 108 × 64.8, центр (190; 58.7), без рамки",
        "• 10 mini-jack 3.5 мм: X 129.9…247.8 (шаг 13.1), Y 10.5",
        "• 2 фейдера: X 175.1 / 204.0, центр Y 150, прорезь 2.5 × 63",
        "• внутри: CORE-2 200×108 (Z12), PANEL-2 360×190, PWR-2 90×70, 1S2P 18650",
    ]
    for i, t in enumerate(zone):
        ax.text(16, 56 - i * 4.2, t, fontsize=4.8, color="#222")

    # --- чек-лист ----------------------------------------------------------
    cx = 206.0
    ax.text(cx, A4H - 22, "7 ПРОВЕРОК (docs/21-ergonomics.md)",
            fontsize=7.6, fontweight="bold")
    checks = [
        ("1", "Ладони/кисти", "Ладони на панели, большие пальцы — на зоне ввода "
                              "(клавиши/фейдеры), локти не висят."),
        ("2", "Дальний энкодер", "Дотянуться до заднего ряда ENC A/H без отрыва "
                                 "локтя и наклона корпуса."),
        ("3", "Угол экрана", "Картонка 108×64.8: 30° / 35° / 45° к панели "
                             "(реком. 35° ≈ 43° к столу)."),
        ("4", "Блики", "Два источника света (сверху/сбоку): читаемость экрана "
                       "и подписей."),
        ("5", "Кромка R4", "Запястье на передней кромке: нет давления/острого "
                           "края (картон скруглить R4)."),
        ("6", "Фейдеры", "Фейдеры двигаются большими пальцами, не задевая клавиши."),
        ("7", "Позы", "Три позы: сидя низко, сидя прямо, стоя. Перехват не нужен."),
    ]
    y = A4H - 27
    for num, title, text in checks:
        ax.add_patch(FancyBboxPatch((cx, y - 13.0), 78, 12.4,
                                    boxstyle="round,pad=0.25,rounding_size=1.0",
                                    fc="#fafafa", ec="#bbb", lw=0.4))
        ax.text(cx + 1.5, y - 3.4, "☐", fontsize=8.5)
        ax.text(cx + 6.0, y - 3.0, f"{num}. {title}", fontsize=6.2, fontweight="bold")
        lines = _wrap(text, 56)
        for i, ln in enumerate(lines[:2]):
            ax.text(cx + 6.0, y - 7.2 - i * 3.4, ln, fontsize=4.6, color="#333")
        y -= 14.4

    # --- критерии отказа ---------------------------------------------------
    y -= 2.0
    ax.text(cx, y, "КРИТЕРИИ ОТКАЗА (любой → пересмотр):", fontsize=5.8,
            fontweight="bold", color="#8b0000")
    fails = ["кисть задевает соседние энкодеры;",
             "дальний ряд требует отрыва локтя;",
             "экран перекрывает разъёмы/ручки;",
             "запястье на острой кромке;",
             "фейдеры недоступны большими пальцами."]
    for i, t in enumerate(fails):
        ax.text(cx + 1.5, y - 5.0 - i * 3.9, "• " + t, fontsize=4.6, color="#8b0000")

    # --- фото и поля -------------------------------------------------------
    yf = y - 5.0 - len(fails) * 3.9 - 2.0
    ax.text(cx, yf, "ФОТО для обратной связи:", fontsize=5.8, fontweight="bold")
    ax.text(cx + 1.5, yf - 4.6,
            "1) сверху; 2) сбоку (профиль); 3) три позы; 4) экран при 35°.",
            fontsize=4.5, color="#333")
    ax.text(cx, yf - 12.0, "Дата / имя: ______________________", fontsize=5.2)
    ax.text(cx, yf - 18.0, "Заметки: ______________________________", fontsize=5.2)
    ax.text(cx + 4, yf - 23.5, "_______________________________________",
            fontsize=5.2)
    ax.text(cx, yf - 30.0, "Вердикт: ☐ ок   ☐ доработать: ______________",
            fontsize=5.2)

    fig.savefig(TMP_PDF.replace(".pdf", "_p4.pdf"), format="pdf")
    fig.savefig(os.path.join(PREVIEW, "paperkit_page4_checkmap.png"), dpi=140)
    plt.close(fig)


def merge():
    panel = PdfReader(PANEL_PDF)
    pages34 = PdfReader(TMP_PDF.replace(".pdf", "_p4.pdf"))
    # стр.3 и стр.4 лежат в одном файле? генерируем стр.3 отдельно
    p3 = PdfReader(TMP_PDF)
    writer = PdfWriter()
    for p in panel.pages[:2]:
        writer.add_page(p)
    writer.add_page(p3.pages[0])
    writer.add_page(pages34.pages[0])
    with open(OUT_PDF, "wb") as f:
        writer.write(f)
    print("PDF:", OUT_PDF, "pages:", len(writer.pages))


if __name__ == "__main__":
    page3_profile()
    page4_checkmap()
    merge()
