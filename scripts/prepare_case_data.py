"""Материалы кейса: бриф в PDF и схемы лендингов в data/."""

from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FONT = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")

COMPETITORS = [
    ("Rive", "https://rive.app", "Интерактивная анимация и state machine прямо в продукте"),
    ("LottieFiles", "https://lottiefiles.com", "Библиотека и плеер Lottie для интерфейсов"),
    ("Jitter", "https://jitter.video", "Быстрый моушн для маркетинга и соцсетей"),
    ("School of Motion", "https://www.schoolofmotion.com", "Обучение моушн-дизайну и позиция школы на рынке"),
]


def write_brief() -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.add_font("Case", "", str(FONT))
    pdf.add_font("Case", "B", str(FONT_BOLD))
    pdf.set_font("Case", "B", 18)
    pdf.multi_cell(0, 10, "Кейс: мониторинг конкурентов в моушн-дизайне")
    pdf.ln(2)
    pdf.set_font("Case", "", 12)
    pdf.multi_cell(
        0,
        7,
        "Ниша придумана для отдельного приложения Competition Monitor: "
        "студия интерфейсной анимации для SaaS. Наблюдаем, как конкуренты "
        "показывают движение, интерактив и обучение.",
    )
    pdf.ln(2)
    pdf.multi_cell(
        0,
        7,
        "Параметры заключения берутся из промптов openaiservice.py: "
        "design_score (0–10, визуальный стиль), animation_potential (0–10), "
        "сильные и слабые стороны, уникальные предложения, рекомендации, резюме.",
    )
    pdf.ln(3)
    pdf.set_font("Case", "B", 14)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 9, "Конкуренты")
    pdf.set_font("Case", "", 12)
    for name, url, why in COMPETITORS:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 7, f"{name}: {url}. {why}.")
    pdf.ln(2)
    pdf.multi_cell(
        0,
        7,
        "Скриншоты публичных главных страниц лежат в data/screenshots, "
        "если сбор через Selenium прошёл. Схемы блоков лендинга — в data/landings. "
        "Это собственные материалы кейса, не чужие PDF-отчёты.",
    )
    pdf.ln(2)
    pdf.multi_cell(
        0,
        7,
        "Как читать изменения: первый обход сохраняет заключение. "
        "Следующие обходы раз в сутки сравнивают заголовок, H1, видимый текст и оценки. "
        "Если страница та же, новая формулировка модели в список изменений не попадает. "
        "Дата в поле «Изменения» — момент, когда отличие найдено.",
    )
    DATA.mkdir(parents=True, exist_ok=True)
    pdf.output(DATA / "motion-design-brief.pdf")


def write_list() -> None:
    lines = ["Ниша: моушн-дизайн и интерфейсная анимация для SaaS", ""]
    for name, url, why in COMPETITORS:
        lines.append(f"{name}: {url}")
        lines.append(why)
        lines.append("")
    (DATA / "competitors.txt").write_text("\n".join(lines), encoding="utf-8")


def write_boards() -> None:
    folder = DATA / "landings"
    folder.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(str(FONT), 28)
    small = ImageFont.truetype(str(FONT), 18)
    zones = [("Герой и движение", 70), ("Демо продукта", 250), ("Оффер и цена", 430), ("Призыв", 560)]
    for name, url, _why in COMPETITORS:
        image = Image.new("RGB", (1200, 700), "#0d1424")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((40, 30, 1160, 660), 24, fill="#141b2d", outline="#3ee0c5", width=2)
        draw.text((70, 50), f"Схема лендинга: {name}", font=font, fill="#e8eefc")
        draw.text((70, 96), url, font=small, fill="#93a0bd")
        for label, top in zones:
            draw.rounded_rectangle((70, top, 1130, top + 90), 16, fill="#0b1020", outline="#263049")
            draw.text((96, top + 30), label, font=small, fill="#3ee0c5")
        slug = url.split("//", 1)[-1].split("/")[0].replace(".", "-")
        image.save(folder / f"{slug}.png")


if __name__ == "__main__":
    write_brief()
    write_list()
    write_boards()
    print(DATA)
