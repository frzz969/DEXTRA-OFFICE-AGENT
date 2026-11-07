# -*- coding: utf-8 -*-
"""Build DEXTRA 12-slide pitch PPTX (16:9, navy/white/electric purple).

Sumber materi: storyboard PPT user (12 slide). Gambar: screenshot asli dari
web DEXTRA (docs/presentation/shots/*.png), bukan gambar stock.
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(BASE, "shots")
OUT = os.path.join(os.path.expanduser("~"), "Downloads", "DEXTRA-Pitch.pptx")

NAVY = RGBColor(0x05, 0x0D, 0x2B)
NAVY2 = RGBColor(0x0A, 0x18, 0x45)
PURPLE = RGBColor(0x7C, 0x3A, 0xED)
ELECTRIC = RGBColor(0x8B, 0x5C, 0xF6)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0x94, 0xA3, 0xB8)
LIGHT = RGBColor(0xF6, 0xF7, 0xFB)
INK = RGBColor(0x0F, 0x17, 0x2A)
CARD_LINE = RGBColor(0xE2, 0xE8, 0xF0)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
W, H = 13.333, 7.5


def add_slide(bg=NAVY):
    slide = prs.slides.add_slide(BLANK)
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    shape.fill.solid(); shape.fill.fore_color.rgb = bg
    shape.line.fill.background()
    shape.shadow.inherit = False
    return slide


def rect(slide, x, y, w, h, fill=None, line=None, radius=None):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    s = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid(); s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line; s.line.width = Pt(1)
    s.shadow.inherit = False
    return s


def text(slide, x, y, w, h, s, size=18, bold=False, color=WHITE, align=PP_ALIGN.LEFT,
         italic=False, font="Inter"):
    tx = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = s; p.font.size = Pt(size); p.font.bold = bold
    p.font.color.rgb = color; p.font.italic = italic; p.font.name = font
    p.alignment = align
    return tx


def bullets(slide, x, y, w, h, items, size=16, color=None, gap=6):
    tx = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tx.text_frame; tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = item; p.font.size = Pt(size); p.font.name = "Inter"
        p.font.color.rgb = color or WHITE
        p.space_after = Pt(gap)
        p.level = 0
    return tx


def title_block(slide, kicker, title, y=0.55, color=WHITE, kcolor=ELECTRIC):
    text(slide, 0.7, y, 12, 0.4, kicker.upper(), size=13, bold=True, color=kcolor)
    text(slide, 0.7, y + 0.4, 12, 1.1, title, size=34, bold=True, color=color)


def shot(slide, name, x, y, w):
    path = os.path.join(SHOTS, name)
    if os.path.exists(path):
        slide.shapes.add_picture(path, Inches(x), Inches(y), width=Inches(w))
    else:
        rect(slide, x, y, w, w * 9 / 16, fill=NAVY2, line=CARD_LINE)


def agent_card(slide, x, name, desc, img):
    rect(slide, x, 3.0, 2.9, 3.4, fill=WHITE)
    inner = rect(slide, x + 0.15, 3.15, 2.6, 1.5, fill=NAVY2)
    if os.path.exists(os.path.join(SHOTS, img)):
        slide.shapes.add_picture(os.path.join(SHOTS, img), Inches(x + 0.15), Inches(3.15), width=Inches(2.6), height=Inches(1.5))
    text(slide, x + 0.2, 4.8, 2.5, 0.5, name, size=16, bold=True, color=NAVY)
    text(slide, x + 0.2, 5.25, 2.5, 1.0, desc, size=12.5, color=MUTED)


def flow_step(slide, x, y, w, title, sub, hero=False):
    fill = PURPLE if hero else WHITE
    tc = WHITE if hero else NAVY
    sc = RGBColor(0xE9, 0xD5, 0xFF) if hero else MUTED
    rect(slide, x, y, w, 1.25, fill=fill)
    text(slide, x + 0.15, y + 0.12, w - 0.3, 0.45, title, size=14, bold=True, color=tc, align=PP_ALIGN.CENTER)
    text(slide, x + 0.15, y + 0.58, w - 0.3, 0.6, sub, size=11, color=sc, align=PP_ALIGN.CENTER)


# ---------------- Slide 1: Cover ----------------
s = add_slide(NAVY)
rect(s, 0, 0, W, 0.12, fill=PURPLE)
text(s, 0.9, 1.0, 8, 0.5, "HACKATHON / KOMPETISI AI AGENT  ·  2026", size=13, bold=True, color=ELECTRIC)
text(s, 0.9, 1.55, 8, 1.4, "DEXTRA", size=66, bold=True, color=WHITE)
text(s, 0.9, 2.85, 8, 0.9, "Governed Enterprise AI Workforce\n& Operations Platform", size=26, bold=True, color=ELECTRIC)
text(s, 0.9, 4.15, 8, 0.6, "Your Enterprise. Your AI Workforce. Your Control.", size=18, italic=True, color=MUTED)
text(s, 0.9, 6.5, 8, 0.5, "Nama anggota / tim  ·  Nama kompetisi  ·  2026", size=14, color=MUTED)
shot(s, "overview.png", 8.0, 1.6, 4.6)

# ---------------- Slide 2: Problem ----------------
s = add_slide(LIGHT)
title_block(s, "Background & Problem", "Operasi perusahaan makin kompleks", color=NAVY, kcolor=PURPLE)
cards = [
    ("Fragmented Operations", "Data dan aktivitas bisnis tersebar di berbagai sistem."),
    ("Manual Workflows", "Banyak pekerjaan administratif dilakukan berulang kali."),
    ("Disconnected Departments", "Koordinasi antar bagian butuh banyak komunikasi."),
    ("Limited Visibility", "Manajemen kesulitan memantau aktivitas & progres menyeluruh."),
    ("AI Without Governance", "AI dipakai tanpa kontrol akses, persetujuan, dan pengawasan."),
]
for i, (t, d) in enumerate(cards):
    x = 0.7 + i * 2.52
    rect(s, x, 2.0, 2.35, 4.3, fill=WHITE, line=CARD_LINE)
    rect(s, x, 2.0, 2.35, 0.14, fill=PURPLE if i % 2 == 0 else NAVY)
    text(s, x + 0.2, 2.5, 1.95, 1.0, t, size=17, bold=True, color=NAVY)
    text(s, x + 0.2, 3.7, 1.95, 2.2, d, size=13, color=MUTED)

# ---------------- Slide 3: Solution ----------------
s = add_slide(LIGHT)
title_block(s, "Our Solution", "Introducing DEXTRA", color=NAVY, kcolor=PURPLE)
text(s, 0.7, 1.75, 12, 0.7, "Platform enterprise berbasis AI yang mengintegrasikan manajemen operasional dengan sistem multi-agent AI.",
     size=16, color=MUTED)
items = [
    "Mengelola berbagai aktivitas bisnis dalam satu platform.",
    "Mendelegasikan pekerjaan kepada AI agents spesialis.",
    "Mengotomatisasi workflow lintas departemen.",
    "Memantau proses dan hasil kerja AI secara real-time.",
    "Mempertahankan kontrol manusia melalui approval dan governance.",
]
bullets(s, 0.7, 2.6, 6.4, 4.2, ["✓  " + i for i in items], size=16, color=INK)
shot(s, "overview.png", 7.4, 2.4, 5.3)

# ---------------- Slide 4: How it works ----------------
s = add_slide(LIGHT)
title_block(s, "How DEXTRA Works", "One Command. Multiple Agents. Unified Results.", color=NAVY, kcolor=PURPLE)
steps = [
    ("Instruksi", "User → WorkBuddy"),
    ("Dekomposisi", "Pecah jadi tugas"),
    ("Delegasi", "Ke agent spesialis"),
    ("Eksekusi", "Sesuai kapabilitas & akses"),
    ("Konsolidasi", "Gabung hasil"),
    ("Approval", "Tindakan penting → manusia"),
]
for i, (t, d) in enumerate(steps):
    flow_step(s, 0.7 + i * 2.1, 2.3, 1.9, t, d, hero=(i == 0))
    if i < len(steps) - 1:
        text(s, 2.4 + i * 2.1, 2.75, 0.4, 0.4, "→", size=20, bold=True, color=PURPLE, align=PP_ALIGN.CENTER)
shot(s, "ai-workspace.png", 3.6, 4.1, 6.4)
text(s, 0.7, 4.1, 2.6, 1.0, "Hasil dikumpulkan & disajikan kepada pengguna.", size=14, italic=True, color=MUTED)

# ---------------- Slide 5: WorkBuddy ----------------
s = add_slide(NAVY)
title_block(s, "WorkBuddy: The AI Orchestrator", "Pusat koordinasi seluruh AI workforce", color=WHITE)
text(s, 0.7, 1.9, 12, 0.6, "Bukan sekadar chatbot — WorkBuddy memahami, memecah, mendelegasikan, dan mengoordinasikan pekerjaan.",
     size=16, color=MUTED)
caps = ["Natural Language Task Understanding", "Task Decomposition", "Intelligent Agent Delegation",
        "Multi-Agent Coordination", "Execution Monitoring", "Result Consolidation", "Human Approval Request"]
for i, c in enumerate(caps):
    x = 0.7 + (i % 4) * 3.05; y = 2.8 + (i // 4) * 1.05
    rect(s, x, y, 2.85, 0.85, fill=NAVY2, line=RGBColor(0x2A, 0x3A, 0x6B))
    text(s, x + 0.2, y + 0.22, 2.5, 0.5, c, size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
shot(s, "agents.png", 8.6, 4.9, 4.1)

# ---------------- Slide 6: Specialized workforce ----------------
s = add_slide(LIGHT)
title_block(s, "Specialized AI Workforce", "Empat agent spesialis", color=NAVY, kcolor=PURPLE)
agent_card(s, 0.7, "HR Agent", "Mengelola data karyawan, absensi, cuti, dan analisis SDM.", "hr.png")
agent_card(s, 3.85, "Finance Agent", "Membantu analisis keuangan, pengeluaran, anggaran, dan laporan.", "finance.png")
agent_card(s, 7.0, "Inventory Agent", "Memantau stok, deteksi persediaan rendah, rekomendasi pengadaan.", "inventory.png")
agent_card(s, 10.15, "Operations Agent", "Membantu koordinasi tugas, jadwal, dan workflow operasional.", "operations.png")

# ---------------- Slide 7: Integrated management ----------------
s = add_slide(LIGHT)
title_block(s, "Integrated Enterprise Management", "Beyond AI Assistance. Complete Business Operations.", color=NAVY, kcolor=PURPLE)
mods = ["Executive Overview", "Human Resources", "Finance", "Inventory & Procurement",
        "Operations & Tasks", "Analytics & Reporting", "Integrations"]
for i, m in enumerate(mods):
    x = 0.7 + (i % 4) * 3.05; y = 2.1 + (i // 4) * 1.0
    rect(s, x, y, 2.85, 0.8, fill=WHITE, line=CARD_LINE)
    text(s, x + 0.2, y + 0.22, 2.5, 0.5, m, size=14, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
text(s, 0.7, 4.6, 12, 0.6, "Seluruh modul terhubung dalam satu ekosistem — AI agents bekerja berdasarkan konteks operasional yang relevan.",
     size=15, color=MUTED)
shot(s, "overview.png", 3.9, 5.3, 5.5)

# ---------------- Slide 8: Governance ----------------
s = add_slide(NAVY)
title_block(s, "Governance & Human-in-the-Loop", "AI Autonomy with Human Control", color=WHITE)
gov = [
    ("Role-Based Access Control", "Akses berdasarkan peran pengguna."),
    ("Permission Management", "Setiap agent punya batas kapabilitas."),
    ("Risk Classification", "Tindakan diklasifikasikan per tingkat risiko."),
    ("Human Approval", "Tindakan sensitif butuh persetujuan manusia."),
    ("Audit Trail", "Setiap aktivitas dapat ditelusuri."),
]
for i, (t, d) in enumerate(gov):
    x = 0.7 + (i % 3) * 4.1; y = 2.1 + (i // 3) * 1.6
    rect(s, x, y, 3.9, 1.35, fill=NAVY2, line=RGBColor(0x2A, 0x3A, 0x6B))
    text(s, x + 0.25, y + 0.18, 3.4, 0.5, t, size=15, bold=True, color=WHITE)
    text(s, x + 0.25, y + 0.68, 3.4, 0.55, d, size=12.5, color=MUTED)
shot(s, "approvals.png", 8.6, 5.1, 4.0)

# ---------------- Slide 9: Use case ----------------
s = add_slide(LIGHT)
title_block(s, "Real-World Use Case", "Monthly Employee & Payroll Preparation", color=NAVY, kcolor=PURPLE)
text(s, 0.7, 1.8, 12, 0.6, '"Analyze this month\'s employee attendance, prepare payroll estimates, and generate a management report."',
     size=15, italic=True, color=MUTED)
steps = [("WorkBuddy", "Memecah pekerjaan"), ("HR Agent", "Analisis absensi & kehadiran"),
         ("Finance Agent", "Estimasi payroll"), ("WorkBuddy", "Gabung hasil → laporan"),
         ("Human Approval", "Manajer menyetujui")]
for i, (t, d) in enumerate(steps):
    flow_step(s, 0.7 + i * 2.5, 2.7, 2.3, t, d, hero=(i == 0))
    if i < 4:
        text(s, 2.85 + i * 2.5, 3.15, 0.4, 0.4, "→", size=20, bold=True, color=PURPLE, align=PP_ALIGN.CENTER)
text(s, 0.7, 4.5, 12, 0.5, "Hasil: proses lintas departemen yang lebih terkoordinasi, transparan, dan terkontrol.",
     size=15, bold=True, color=NAVY)

# ---------------- Slide 10: Differentiators ----------------
s = add_slide(LIGHT)
title_block(s, "Key Differentiators", "What Makes DEXTRA Different?", color=NAVY, kcolor=PURPLE)
rows = [
    ("Multi-Agent Collaboration", "Banyak AI agents bekerja secara terkoordinasi"),
    ("Enterprise Integration", "AI terhubung dengan modul operasional bisnis"),
    ("Governed AI Workforce", "Kapabilitas agent dibatasi oleh kebijakan"),
    ("Human-in-the-Loop", "Manusia tetap memegang kendali"),
    ("Execution Transparency", "Aktivitas dan hasil kerja dapat diaudit"),
]
for i, (t, d) in enumerate(rows):
    y = 2.0 + i * 0.92
    rect(s, 0.7, y, 12.0, 0.75, fill=WHITE, line=CARD_LINE)
    rect(s, 0.7, y, 0.14, 0.75, fill=PURPLE)
    text(s, 1.05, y + 0.12, 4.2, 0.5, t, size=16, bold=True, color=NAVY)
    text(s, 5.5, y + 0.17, 7.0, 0.5, d, size=14, color=MUTED)

# ---------------- Slide 11: Tech ----------------
s = add_slide(LIGHT)
title_block(s, "Technology & Architecture", "Built for Scalable Enterprise AI Operations", color=NAVY, kcolor=PURPLE)
tech = [
    ("Frontend", "Next.js · TypeScript · Tailwind CSS"),
    ("Backend", "FastAPI (Python) · API terpusat"),
    ("Database", "SQLite (dev) / PostgreSQL (prod) + Alembic"),
    ("AI Layer", "LLM Provider Abstraction (OpenAI, Anthropic, Google)"),
    ("Agent Runtime", "Orchestrator · task delegation · execution management"),
    ("Workflow", "Background jobs · workflow engine · audit trail"),
]
for i, (t, d) in enumerate(tech):
    x = 0.7 + (i % 3) * 4.1; y = 2.0 + (i // 3) * 1.5
    rect(s, x, y, 3.9, 1.25, fill=WHITE, line=CARD_LINE)
    text(s, x + 0.25, y + 0.16, 3.4, 0.45, t, size=15, bold=True, color=NAVY)
    text(s, x + 0.25, y + 0.62, 3.4, 0.55, d, size=12.5, color=MUTED)
rect(s, 0.7, 5.2, 12.0, 0.9, fill=RGBColor(0xFF, 0xFB, 0xEB), line=RGBColor(0xFD, 0xE6, 0x8A))
text(s, 1.0, 5.35, 11.4, 0.6, "Catatan: teknologi ini adalah rancangan arsitektur, bukan klaim bahwa seluruh komponen sudah selesai diimplementasikan.",
     size=13, color=RGBColor(0x92, 0x4A, 0x00))

# ---------------- Slide 12: Closing ----------------
s = add_slide(NAVY)
rect(s, 0, 7.38, W, 0.12, fill=PURPLE)
text(s, 0.9, 0.9, 12, 0.5, "VISION & CLOSING", size=13, bold=True, color=ELECTRIC)
text(s, 0.9, 1.5, 12, 1.0, "The Future of Enterprise Operations", size=36, bold=True, color=WHITE)
text(s, 0.9, 2.7, 11.5, 1.6, "Manusia menentukan arah dan mengambil keputusan penting. AI membantu menganalisis,\nmengoordinasikan, dan menjalankan pekerjaan sesuai batas kewenangannya.",
     size=17, color=MUTED)
text(s, 0.9, 4.4, 11.5, 0.8, "DEXTRA doesn't just give businesses an AI assistant. It gives them an entire governed AI workforce.",
     size=19, bold=True, italic=True, color=ELECTRIC)
text(s, 0.9, 5.6, 12, 0.6, "YOUR ENTERPRISE. YOUR AI WORKFORCE. YOUR CONTROL.", size=20, bold=True, color=WHITE)
text(s, 0.9, 6.4, 12, 0.5, "DEXTRA — Governed Enterprise AI Workforce & Operations Platform  ·  2026", size=14, color=MUTED)

prs.save(OUT)
print("saved:", OUT, "slides:", len(prs.slides._sldIdLst))
