"""Скриншоты лендингов и PDF-отчёт по сайтам из monitor_state.json."""

import json
import re
from pathlib import Path

from fpdf import FPDF

from backend.services.parsingservice import ParsingService

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SHOTS = DATA / "screenshots"
LANDINGS = DATA / "landings"
STATE = ROOT / "monitor_state.json"
FONT = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")


def slug(url: str) -> str:
    host = re.sub(r"^https?://", "", url).split("/")[0]
    host = host.replace("www.", "")
    return re.sub(r"[^a-z0-9]+", "-", host.lower()).strip("-")


def paragraph(pdf: FPDF, text: str, size: int = 11, bold: bool = False) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Case", "B" if bold else "", size)
    pdf.multi_cell(0, 6, text)
    pdf.ln(1)


def bullets(pdf: FPDF, title: str, items: list) -> None:
    if not items:
        return
    paragraph(pdf, title, 12, bold=True)
    pdf.set_font("Case", "", 11)
    for item in items:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 6, f"- {item}")
    pdf.ln(1)


def main() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    SHOTS.mkdir(parents=True, exist_ok=True)
    LANDINGS.mkdir(parents=True, exist_ok=True)
    parser = ParsingService()
    captured = []

    for url in state["urls"]:
        name = slug(url)
        snapshot, error = parser.capture_sync(url)
        path = SHOTS / f"{name}.png"
        if snapshot and snapshot.screenshot_png:
            path.write_bytes(snapshot.screenshot_png)
            (LANDINGS / f"{name}.png").write_bytes(snapshot.screenshot_png)
            print(f"OK {url} {path.stat().st_size}")
        else:
            print(f"FAIL {url} {error}")
        captured.append((url, path if path.exists() else None, error, snapshot))

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_font("Case", "", str(FONT))
    pdf.add_font("Case", "B", str(FONT_BOLD))
    pdf.add_page()
    paragraph(pdf, "Отчёт по сайтам конкурентов", 18, bold=True)
    paragraph(
        pdf,
        "Ниша: полиграфия и онлайн-заказ печати. "
        f"Снимок страниц и заключение на {state.get('last_run_at', '')}.",
    )
    paragraph(
        pdf,
        "Оценки design_score и animation_potential — от 0 до 10. "
        "Скриншоты лендингов лежат в data/screenshots и data/landings.",
    )

    lines = ["Ниша: полиграфия и онлайн-заказ печати", ""]
    for url, path, error, snapshot in captured:
        site = state["sites"].get(url, {})
        analysis = site.get("analysis") or {}
        title = site.get("title") or (snapshot.title if snapshot else url)
        lines.append(title or url)
        lines.append(url)
        lines.append("")
        pdf.add_page()
        paragraph(pdf, title or url, 16, bold=True)
        paragraph(pdf, url)
        if error and not path:
            paragraph(pdf, f"Скриншот не снят: {error}")
        elif path and path.exists():
            pdf.image(str(path), x=pdf.l_margin, w=pdf.epw)
            pdf.ln(3)
        design = analysis.get("design_score")
        motion = analysis.get("animation_potential")
        if design is not None:
            paragraph(pdf, f"Дизайн: {design}/10. Потенциал анимации: {motion}/10.", bold=True)
        paragraph(pdf, "Заключение", 12, bold=True)
        paragraph(pdf, site.get("conclusion") or analysis.get("conclusion") or "")
        paragraph(pdf, "Резюме", 12, bold=True)
        paragraph(pdf, analysis.get("summary") or "")
        if analysis.get("animation_notes"):
            paragraph(pdf, "Анимация", 12, bold=True)
            paragraph(pdf, analysis["animation_notes"])
        bullets(pdf, "Сильные стороны", analysis.get("strengths") or [])
        bullets(pdf, "Слабые стороны", analysis.get("weaknesses") or [])
        bullets(pdf, "Уникальные предложения", analysis.get("unique_offers") or [])
        bullets(pdf, "Рекомендации", analysis.get("recommendations") or [])

    report = DATA / "competitor-report.pdf"
    pdf.output(report)
    (DATA / "competitors.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"PDF {report} {report.stat().st_size}")


if __name__ == "__main__":
    main()
