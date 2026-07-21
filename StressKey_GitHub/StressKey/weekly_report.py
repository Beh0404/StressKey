"""
StressKey - Weekly Report Generator
====================================
Reads the persistent stress_log.jsonl and produces a professional
PDF report summarising the user's emotional patterns over a period.

Report sections:
  1. Header + key metric cards (total detections, monitoring time,
     dominant emotion, average confidence)
  2. Emotion distribution pie chart
  3. Daily stress trend line chart
  4. Hourly stress heatmap (which hours of day are most stressful)
  5. Music intervention summary

Usage:
  from weekly_report import generate_report
  path = generate_report(days=7)   # returns path to generated PDF

Run directly to generate a demo report from synthetic data:
  python weekly_report.py
"""

import os
import io
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from stress_logger import StressLogger
from intervention_tracker import InterventionTracker, format_duration


# ── Emotion metadata ───────────────────────────────────────────────────────────
EMOTION = {
    "S": {"label": "Stressed", "color": "#F87171", "hex": colors.HexColor("#F87171")},
    "A": {"label": "Angry",    "color": "#FB923C", "hex": colors.HexColor("#FB923C")},
    "N": {"label": "Neutral",  "color": "#60A5FA", "hex": colors.HexColor("#60A5FA")},
    "H": {"label": "Happy",    "color": "#FBD152", "hex": colors.HexColor("#FBD152")},
    "C": {"label": "Calm",     "color": "#4ADE80", "hex": colors.HexColor("#4ADE80")},
}
EMOTION_ORDER = ["S", "A", "N", "H", "C"]

# Brand colours
BRAND_DARK   = colors.HexColor("#1A1A35")
BRAND_ACCENT = colors.HexColor("#7C6AF7")
TEXT_MUTED   = colors.HexColor("#6B6B8A")

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor":   "#F8F8FC",
    "axes.edgecolor":   "#CCCCDD",
    "font.family":      "DejaVu Sans",
    "font.size":        10,
})


# ── Chart builders (return PNG bytes for embedding) ────────────────────────────

def _pie_chart(entries) -> bytes:
    counts = Counter(e["code"] for e in entries)
    order  = [c for c in EMOTION_ORDER if c in counts]
    if not order:
        return None
    sizes  = [counts[c] for c in order]
    labels = [EMOTION[c]["label"] for c in order]
    cols   = [EMOTION[c]["color"] for c in order]

    fig, ax = plt.subplots(figsize=(4.2, 3.2))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=cols, autopct="%1.0f%%",
        startangle=140, wedgeprops={"linewidth": 1.5, "edgecolor": "white"},
        textprops={"fontsize": 9})
    for at in autotexts:
        at.set_fontsize(9)
        at.set_fontweight("bold")
        at.set_color("white")
    ax.set_title("Emotion Distribution", fontsize=11, fontweight="bold", pad=10)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor="white")
    plt.close()
    buf.seek(0)
    return buf.read()


def _daily_trend_chart(entries) -> bytes:
    # Stress ratio per day = (Stressed + Angry) / total that day
    by_day = defaultdict(lambda: {"stress": 0, "total": 0})
    for e in entries:
        try:
            day = datetime.fromisoformat(e["ts"]).date()
        except (ValueError, KeyError):
            continue
        by_day[day]["total"] += 1
        if e["code"] in ("S", "A"):
            by_day[day]["stress"] += 1

    if not by_day:
        return None

    days   = sorted(by_day.keys())
    ratios = [100 * by_day[d]["stress"] / max(1, by_day[d]["total"]) for d in days]
    labels = [d.strftime("%a\n%d %b") for d in days]

    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    ax.fill_between(range(len(days)), ratios, alpha=0.15, color="#F87171")
    ax.plot(range(len(days)), ratios, color="#F87171", linewidth=2,
            marker="o", markersize=6, markerfacecolor="white",
            markeredgecolor="#F87171", markeredgewidth=2)
    for i, r in enumerate(ratios):
        ax.text(i, r + 3, f"{r:.0f}%", ha="center", fontsize=8, color="#B03030")
    ax.set_xticks(range(len(days)))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Stress Ratio (%)", fontsize=9)
    ax.set_ylim(0, max(105, max(ratios) + 15) if ratios else 100)
    ax.set_title("Daily Stress Trend  (Stressed + Angry as % of detections)",
                 fontsize=11, fontweight="bold", pad=10, loc="left")
    ax.yaxis.grid(True, alpha=0.4)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor="white")
    plt.close()
    buf.seek(0)
    return buf.read()


def _hourly_heatmap(entries) -> bytes:
    # Stress count per hour of day (0-23)
    hourly_stress = np.zeros(24)
    hourly_total  = np.zeros(24)
    for e in entries:
        try:
            hr = datetime.fromisoformat(e["ts"]).hour
        except (ValueError, KeyError):
            continue
        hourly_total[hr] += 1
        if e["code"] in ("S", "A"):
            hourly_stress[hr] += 1

    if hourly_total.sum() == 0:
        return None

    ratio = np.divide(hourly_stress, hourly_total,
                      out=np.zeros_like(hourly_stress), where=hourly_total > 0)

    fig, ax = plt.subplots(figsize=(7.5, 1.6))
    data = ratio.reshape(1, 24)
    im = ax.imshow(data, cmap="YlOrRd", aspect="auto", vmin=0, vmax=1)
    ax.set_yticks([])
    ax.set_xticks(range(0, 24, 2))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 2)], fontsize=8)
    ax.set_title("Stress Intensity by Hour of Day  (darker = more stressed)",
                 fontsize=11, fontweight="bold", pad=10, loc="left")
    # Mark the peak hour
    peak = int(np.argmax(ratio))
    if ratio[peak] > 0:
        ax.text(peak, 0, "▼", ha="center", va="center", fontsize=10, color="#333")
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.ax.tick_params(labelsize=7)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor="white")
    plt.close()
    buf.seek(0)
    return buf.read()


def _recovery_histogram(episodes) -> bytes:
    """Histogram of recovery durations (minutes) for resolved episodes."""
    resolved = [e for e in episodes if e.get("resolved") and e.get("duration_seconds")]
    if not resolved:
        return None

    minutes = [e["duration_seconds"] / 60 for e in resolved]

    fig, ax = plt.subplots(figsize=(7.5, 3.0))
    bins = min(12, max(4, len(minutes) // 2))
    n, bin_edges, patches = ax.hist(minutes, bins=bins, color="#7C6AF7",
                                    edgecolor="white", alpha=0.85)
    mean_min = np.mean(minutes)
    ax.axvline(mean_min, color="#F87171", linestyle="--", linewidth=1.6,
              label=f"Mean: {mean_min:.1f} min")
    ax.set_xlabel("Recovery Time (minutes)", fontsize=9)
    ax.set_ylabel("Number of Episodes", fontsize=9)
    ax.set_title("Distribution of Stress Recovery Times",
                 fontsize=11, fontweight="bold", pad=10, loc="left")
    ax.legend(fontsize=8, framealpha=0.8)
    ax.yaxis.grid(True, alpha=0.4)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor="white")
    plt.close()
    buf.seek(0)
    return buf.read()


# ── Metric computation ─────────────────────────────────────────────────────────

def _compute_metrics(entries):
    total = len(entries)
    if total == 0:
        return None

    counts = Counter(e["code"] for e in entries)
    dominant_code = counts.most_common(1)[0][0]
    dominant = EMOTION[dominant_code]["label"]

    avg_conf = np.mean([e.get("confidence", 0) for e in entries]) * 100

    stress_events = sum(1 for e in entries if e["code"] in ("S", "A"))
    music_events  = sum(1 for e in entries if e.get("music_title"))

    # Approximate monitoring time: each detection ≈ 3s prediction interval
    est_minutes = (total * 3) / 60

    # Peak stress hour
    hourly = defaultdict(int)
    for e in entries:
        if e["code"] in ("S", "A"):
            try:
                hourly[datetime.fromisoformat(e["ts"]).hour] += 1
            except (ValueError, KeyError):
                pass
    peak_hour = max(hourly, key=hourly.get) if hourly else None

    return {
        "total":          total,
        "dominant":       dominant,
        "dominant_code":  dominant_code,
        "avg_conf":       avg_conf,
        "stress_events":  stress_events,
        "music_events":   music_events,
        "est_minutes":    est_minutes,
        "peak_hour":      peak_hour,
        "counts":         counts,
    }


# ── PDF assembly ───────────────────────────────────────────────────────────────

def generate_report(days: int = 7, output_path: str = None,
                    log_path: str = "stress_log.jsonl",
                    intervention_log_path: str = "intervention_log.jsonl") -> str | None:
    """
    Generate a PDF stress report from the last `days` days of logged data.
    Returns the path to the generated PDF, or None if there is no data.
    """
    logger  = StressLogger(log_path)
    entries = logger.read_last_days(days)

    if not entries:
        print("⚠️  No data in the selected period — cannot generate report.")
        return None

    metrics = _compute_metrics(entries)

    if output_path is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = f"StressKey_Report_{stamp}.pdf"

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title2", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=22, textColor=BRAND_DARK, spaceAfter=2)
    subtitle_style = ParagraphStyle(
        "Sub", parent=styles["Normal"], fontName="Helvetica",
        fontSize=10, textColor=TEXT_MUTED, spaceAfter=14)
    section_style = ParagraphStyle(
        "Section", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=13, textColor=BRAND_ACCENT, spaceBefore=16, spaceAfter=8)
    body_style = ParagraphStyle(
        "Body2", parent=styles["Normal"], fontName="Helvetica",
        fontSize=10, textColor=colors.HexColor("#333333"), leading=15)

    story = []

    # ── Header ──
    period_start = (datetime.now() - timedelta(days=days)).strftime("%d %b %Y")
    period_end   = datetime.now().strftime("%d %b %Y")

    story.append(Paragraph("StressKey Weekly Report", title_style))
    story.append(Paragraph(
        f"Emotional wellbeing summary &nbsp;|&nbsp; {period_start} &ndash; {period_end}",
        subtitle_style))

    # ── Metric cards (as a table) ──
    peak_str = f"{metrics['peak_hour']:02d}:00" if metrics["peak_hour"] is not None else "N/A"
    card_data = [
        ["Total Detections", "Monitoring Time", "Dominant State", "Avg Confidence"],
        [str(metrics["total"]),
         f"{metrics['est_minutes']:.0f} min",
         metrics["dominant"],
         f"{metrics['avg_conf']:.0f}%"],
    ]
    card_table = Table(card_data, colWidths=[4.2*cm]*4)
    card_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 9),
        ("FONTNAME",   (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 1), (-1, 1), 15),
        ("TEXTCOLOR",  (0, 1), (-1, 1), BRAND_ACCENT),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F0F0FA")),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("GRID",       (0, 0), (-1, -1), 2, colors.white),
    ]))
    story.append(card_table)
    story.append(Spacer(1, 6))

    # ── Insight sentence ──
    stress_pct = 100 * metrics["stress_events"] / max(1, metrics["total"])
    insight = (
        f"During this period, StressKey recorded {metrics['total']} emotion detections. "
        f"Stressed or angry states accounted for {stress_pct:.0f}% of all detections, "
        f"with peak stress occurring around {peak_str}. "
        f"The system delivered {metrics['music_events']} adaptive music interventions "
        f"in response to detected emotional states."
    )
    story.append(Paragraph(insight, body_style))

    # ── Emotion distribution + pie ──
    story.append(Paragraph("Emotion Distribution", section_style))
    pie = _pie_chart(entries)
    if pie:
        story.append(Image(io.BytesIO(pie), width=9*cm, height=6.8*cm))

    # ── Daily trend ──
    story.append(Paragraph("Daily Stress Trend", section_style))
    trend = _daily_trend_chart(entries)
    if trend:
        story.append(Image(io.BytesIO(trend), width=16*cm, height=6*cm))

    # ── Hourly heatmap ──
    story.append(Paragraph("Stress by Time of Day", section_style))
    heat = _hourly_heatmap(entries)
    if heat:
        story.append(Image(io.BytesIO(heat), width=16*cm, height=3.4*cm))

    # ── Music intervention summary ──
    story.append(Paragraph("Music Intervention Summary", section_style))
    coverage = 100 * metrics["music_events"] / max(1, metrics["stress_events"]) \
               if metrics["stress_events"] > 0 else 0
    music_text = (
        f"StressKey triggered {metrics['music_events']} music recommendations across the period. "
        f"Of the {metrics['stress_events']} stress-related events detected, the adaptive engine "
        f"provided intervention coverage of approximately {min(coverage, 100):.0f}%. "
        f"All interventions followed the Iso Principle, matching calming audio content to elevated "
        f"stress states to support emotional regulation."
    )
    story.append(Paragraph(music_text, body_style))

    # ── Recovery / Intervention Effectiveness section ──
    tracker = InterventionTracker(intervention_log_path)
    recovery_stats = tracker.get_stats(days=days)
    episodes = tracker.read_last_days(days)

    if recovery_stats.get("has_data"):
        story.append(Paragraph("Intervention Recovery Time", section_style))

        rec_card_data = [
            ["Episodes", "Resolved", "Avg Recovery", "Fastest"],
            [str(recovery_stats["total_episodes"]),
             f"{recovery_stats['resolution_rate']:.0f}%",
             format_duration(recovery_stats.get("avg_recovery_seconds")),
             format_duration(recovery_stats.get("fastest_seconds"))],
        ]
        rec_table = Table(rec_card_data, colWidths=[4.2*cm]*4)
        rec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, 0), 9),
            ("FONTNAME",   (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 1), (-1, 1), 14),
            ("TEXTCOLOR",  (0, 1), (-1, 1), BRAND_ACCENT),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F0F0FA")),
            ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("GRID",       (0, 0), (-1, -1), 2, colors.white),
        ]))
        story.append(rec_table)
        story.append(Spacer(1, 6))

        hist = _recovery_histogram(episodes)
        if hist:
            story.append(Image(io.BytesIO(hist), width=16*cm, height=6.4*cm))

        recovery_note_style = ParagraphStyle(
            "RecNote", parent=styles["Normal"], fontName="Helvetica-Oblique",
            fontSize=8.5, textColor=TEXT_MUTED, leading=12, spaceBefore=6)
        story.append(Paragraph(
            "Note: this measures the time between a stress/anger detection and the "
            "next confirmed calm, neutral, or happy state, during which a music "
            "intervention was active. It reflects observed recovery time following "
            "intervention, not a controlled measurement of the music's causal effect, "
            "as no no-intervention control condition was recorded for comparison.",
            recovery_note_style))

    # ── Footer ──
    story.append(Spacer(1, 20))
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"], fontName="Helvetica-Oblique",
        fontSize=8, textColor=TEXT_MUTED, alignment=TA_CENTER)
    story.append(Paragraph(
        f"Generated by StressKey on {datetime.now().strftime('%d %b %Y at %H:%M')} "
        f"&nbsp;|&nbsp; Keystroke-based emotion monitoring aligned with SDG 3: Good Health and Well-Being",
        footer_style))

    doc.build(story)
    print(f"✅ Report generated: {output_path}")
    return output_path


# ── Demo mode ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import random

    print("Generating demo report from synthetic data...")
    demo_logger = StressLogger("demo_stress_log.jsonl")
    demo_logger.clear()

    # Simulate a realistic week: more stress during work hours (9-17)
    now = datetime.now()
    for day_offset in range(6, -1, -1):
        day = now - timedelta(days=day_offset)
        n_detections = random.randint(20, 45)
        for _ in range(n_detections):
            hour = random.choices(
                range(24),
                weights=[1,1,1,1,1,1,2,3,5,8,9,8,7,8,9,8,7,5,3,3,2,2,1,1]
            )[0]
            ts = day.replace(hour=hour, minute=random.randint(0, 59),
                             second=random.randint(0, 59))
            # Work hours skew toward stress
            if 9 <= hour <= 17:
                code = random.choices(["S","A","N","H","C"], weights=[3,2,4,1,1])[0]
            else:
                code = random.choices(["S","A","N","H","C"], weights=[1,1,3,3,4])[0]
            # Manually build entry with custom timestamp
            import json
            entry = {
                "ts": ts.isoformat(),
                "code": code,
                "confidence": round(random.uniform(0.4, 0.95), 4),
                "dwell_ms": round(random.uniform(80, 140), 1),
                "flight_ms": round(random.uniform(250, 400), 1),
                "music_title": "Calm Piano" if code in ("S","A") else None,
            }
            with open("demo_stress_log.jsonl", "a") as f:
                f.write(json.dumps(entry) + "\n")

    # ── Simulate intervention recovery episodes ──
    import json as _json
    demo_int_path = "demo_intervention_log.jsonl"
    open(demo_int_path, "w").close()   # reset

    n_episodes = random.randint(15, 25)
    for i in range(n_episodes):
        day_offset = random.randint(0, 6)
        start = now - timedelta(days=day_offset,
                                hours=random.randint(0, 23),
                                minutes=random.randint(0, 59))
        # Recovery times skew toward 1-8 minutes, occasional slow ones
        recovery_min = max(0.3, random.gauss(3.5, 2.2))
        end = start + timedelta(minutes=recovery_min)
        trigger = random.choice(["S", "S", "S", "A"])
        resolved_to = random.choice(["C", "N", "N", "H"])
        episode = {
            "start_ts":         start.isoformat(),
            "trigger_emotion":  trigger,
            "music_title":      "Calm Piano",
            "confidence_start": round(random.uniform(0.5, 0.9), 3),
            "end_ts":           end.isoformat(),
            "resolved_to":      resolved_to,
            "duration_seconds": round(recovery_min * 60, 1),
            "resolved":         True,
            "timed_out":        False,
        }
        with open(demo_int_path, "a") as f:
            f.write(_json.dumps(episode) + "\n")

    generate_report(days=7, output_path="StressKey_Demo_Report.pdf",
                    log_path="demo_stress_log.jsonl",
                    intervention_log_path="demo_intervention_log.jsonl")
    print("✅ Demo complete — open StressKey_Demo_Report.pdf")
