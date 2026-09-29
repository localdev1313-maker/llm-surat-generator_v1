import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_presentation(output_path: Path):
    prs = Presentation()
    # 16:9 Widescreen dimensions
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_slide_layout = prs.slide_layouts[6]

    # Color Palette
    NAVY_DARK = RGBColor(15, 30, 54)        # #0F1E36
    NAVY_CARD = RGBColor(26, 58, 92)        # #1A3A5C
    NAVY_LIGHT = RGBColor(37, 99, 235)      # #2563EB
    BG_LIGHT = RGBColor(245, 247, 250)      # #F5F7FA
    WHITE = RGBColor(255, 255, 255)
    TEXT_DARK = RGBColor(15, 23, 42)        # #0F172A
    TEXT_MUTED = RGBColor(71, 85, 105)      # #475569
    ACCENT_GOLD = RGBColor(245, 158, 11)    # #F59E0B
    ACCENT_CYBER = RGBColor(14, 165, 233)   # #0EA5E9
    CARD_BG = RGBColor(255, 255, 255)
    BORDER_COLOR = RGBColor(203, 213, 225)

    logo_path = Path(r"d:\DEV_OPS\llm-surat-generator_android_version_v1\backend\static\logo_utama.jpg")

    def add_header(slide, title_text, category_text="SISTEM SURAT ELEKTRONIK BERBASIS AI (SSEB AI)"):
        # Top banner background
        top_bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(1.15))
        top_bg.fill.solid()
        top_bg.fill.fore_color.rgb = NAVY_DARK
        top_bg.line.fill.background()

        # Category text
        txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.12), Inches(11.5), Inches(0.3))
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = category_text.upper()
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = ACCENT_CYBER

        # Main Title text
        txBox2 = slide.shapes.add_textbox(Inches(0.8), Inches(0.42), Inches(11.5), Inches(0.6))
        tf2 = txBox2.text_frame
        tf2.word_wrap = True
        p2 = tf2.paragraphs[0]
        p2.text = title_text
        p2.font.size = Pt(22)
        p2.font.bold = True
        p2.font.color.rgb = WHITE

        # Bottom Footer
        ftBox = slide.shapes.add_textbox(Inches(0.8), Inches(7.1), Inches(11.733), Inches(0.3))
        ft_tf = ftBox.text_frame
        p_ft = ft_tf.paragraphs[0]
        p_ft.text = "SSEB AI v2.0 • Standar Kepatuhan KEP/868/2022 TNI • On-Premises Sovereign Architecture"
        p_ft.font.size = Pt(10)
        p_ft.font.color.rgb = TEXT_MUTED

    # ----------------------------------------------------
    # SLIDE 1: COVER SLIDE
    # ----------------------------------------------------
    s1 = prs.slides.add_slide(blank_slide_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = NAVY_DARK
    bg1.line.fill.background()

    # Decorative Accent Strip
    strip = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(7.2), Inches(13.333), Inches(0.3))
    strip.fill.solid()
    strip.fill.fore_color.rgb = NAVY_LIGHT
    strip.line.fill.background()

    # Add Logo
    if logo_path.exists():
        s1.shapes.add_picture(str(logo_path), Inches(1.2), Inches(1.6), width=Inches(3.2), height=Inches(3.2))

    # Title Box
    tbox = s1.shapes.add_textbox(Inches(4.8), Inches(1.5), Inches(7.8), Inches(4.5))
    tf = tbox.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "PAPARAN SISTEM"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYBER
    p.space_after = Pt(8)

    p2 = tf.add_paragraph()
    p2.text = "SISTEM SURAT ELEKTRONIK\nBERBASIS AI (SSEB AI)"
    p2.font.size = Pt(30)
    p2.font.bold = True
    p2.font.color.rgb = WHITE
    p2.space_after = Pt(14)

    p3 = tf.add_paragraph()
    p3.text = "Layanan Penyusunan Naskah Dinas & Nota Dinas Otomatis\nTerintegrasi Sovereign AI Sesuai Standar KEP/868/2022 TNI"
    p3.font.size = Pt(15)
    p3.font.color.rgb = RGBColor(226, 232, 240)
    p3.space_after = Pt(24)

    p4 = tf.add_paragraph()
    p4.text = "Disusun untuk: Sosialisasi & Implementasi Operasional • 2026"
    p4.font.size = Pt(12)
    p4.font.italic = True
    p4.font.color.rgb = ACCENT_GOLD

    # ----------------------------------------------------
    # SLIDE 2: LATAR BELAKANG & URGENSI
    # ----------------------------------------------------
    s2 = prs.slides.add_slide(blank_slide_layout)
    add_header(s2, "Latar Belakang & Urgensi Platform")

    # 3 Cards Layout
    card_data_2 = [
        ("Kebutuhan Kecepatan Administrasi", 
         "Dinamika operasi militer & birokrasi modern menuntut kecepatan pengambilan keputusan yang bertumpu pada kelancaran naskah dinas resmi tanpa mengorbankan ketepatan."),
        ("Ketatnya Regulasi KEP/868/2022", 
         "Tata tulis militer memiliki aturan ketat mengenai struktur, margin presisi milimeter, hirarki kalimat penutup, susunan sub-poin, dan pangkat/korps/NRP pejabat penandatangan."),
        ("Tuntutan Kedaulatan & Keamanan Data", 
         "Penggunaan AI komersial publik berbasis cloud membawa resiko kebocoran data intelijen. Diperlukan sistem On-Premises mandiri yang berjalan 100% di jaringan intranet lokal.")
    ]

    for i, (title, desc) in enumerate(card_data_2):
        left = Inches(0.8 + i * 4.0)
        card = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(1.6), Inches(3.7), Inches(5.1))
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = BORDER_COLOR
        card.line.width = Pt(1.5)

        # Header bar on card
        c_hdr = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(1.6), Inches(3.7), Inches(0.9))
        c_hdr.fill.solid()
        c_hdr.fill.fore_color.rgb = NAVY_CARD
        c_hdr.line.fill.background()

        tx = s2.shapes.add_textbox(left + Inches(0.2), Inches(1.7), Inches(3.3), Inches(0.7))
        p = tx.text_frame.paragraphs[0]
        p.text = f"{i+1}. {title}"
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = WHITE

        tx_body = s2.shapes.add_textbox(left + Inches(0.2), Inches(2.7), Inches(3.3), Inches(3.8))
        tx_body.text_frame.word_wrap = True
        p_b = tx_body.text_frame.paragraphs[0]
        p_b.text = desc
        p_b.font.size = Pt(13)
        p_b.font.color.rgb = TEXT_DARK
        p_b.line_spacing = 1.3

    # ----------------------------------------------------
    # SLIDE 3: PERMASALAHAN UTAMA (PAIN POINTS)
    # ----------------------------------------------------
    s3 = prs.slides.add_slide(blank_slide_layout)
    add_header(s3, "Tantangan & Permasalahan Administrasi Konvensional")

    pains = [
        ("Waktu Penyusunan yang Lambat", "Penyusunan manual draf nota dinas membutuhkan 30–90 menit per dokumen untuk merangkai kalimat formal dan mencari dasar regulasi."),
        ("Inkonsistensi Format & Tata Tulis", "Sering terjadi kesalahan format margin, penomoran, penulisan nama pejabat, dan tanda baca sub-poin yang tidak sesuai standar KEP-868."),
        ("Resiko Kebocoran Dokumen Rahasia", "Ketergantungan staf pada tools AI publik (ChatGPT/Gemini online) membahayakan kerahasiaan dokumen internal satuan."),
        ("Keterbatasan Aksesibilitas Mobile", "Pejabat dan staf dinas luar kesulitan membuat konsep dan memverifikasi nota dinas dengan cepat tanpa membuka komputer kantor.")
    ]

    for i, (title, desc) in enumerate(pains):
        row = i // 2
        col = i % 2
        left = Inches(0.8 + col * 5.9)
        top = Inches(1.6 + row * 2.6)

        card = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, Inches(5.6), Inches(2.3))
        card.fill.solid()
        card.fill.fore_color.rgb = WHITE
        card.line.color.rgb = RGBColor(239, 68, 68) if i==2 else BORDER_COLOR
        card.line.width = Pt(1.5)

        tx = s3.shapes.add_textbox(left + Inches(0.3), top + Inches(0.2), Inches(5.0), Inches(1.9))
        tf = tx.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"⚠️  {title}"
        p.font.size = Pt(15)
        p.font.bold = True
        p.font.color.rgb = NAVY_CARD
        p.space_after = Pt(8)

        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(12)
        p2.font.color.rgb = TEXT_MUTED

    # ----------------------------------------------------
    # SLIDE 4: VISI & TUJUAN PLATFORM
    # ----------------------------------------------------
    s4 = prs.slides.add_slide(blank_slide_layout)
    add_header(s4, "Visi & Tujuan Strategis SSEB AI")

    goals = [
        ("Otomatisasi Penuh Redaksi", "Mengubah poin-poin singkat menjadi naskah dinas formal dalam waktu < 5 detik menggunakan Local AI."),
        ("Kepatuhan Mutlak KEP/868/2022", "Mengunci otomatis seluruh parameter tata naskah militer, margin presisi, dan hierarki tanda tangan."),
        ("Kedaulatan & Keamanan Data (Air-Gapped)", "100% pemrosesan data lokal di server intranet mandiri tanpa ketergantungan internet luar."),
        ("Ekosistem Multi-Platform Terpadu", "Kemudahan akses via Android Mobile Native, Portal Web Intranet, dan Telegram Bot Terenkripsi.")
    ]

    for i, (title, desc) in enumerate(goals):
        top = Inches(1.6 + i * 1.3)
        bar = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), top, Inches(11.733), Inches(1.15))
        bar.fill.solid()
        bar.fill.fore_color.rgb = WHITE
        bar.line.color.rgb = NAVY_LIGHT
        bar.line.width = Pt(1.5)

        # Icon number pill
        pill = s4.shapes.add_shape(MSO_SHAPE.OVAL, Inches(1.0), top + Inches(0.2), Inches(0.75), Inches(0.75))
        pill.fill.solid()
        pill.fill.fore_color.rgb = NAVY_CARD
        pill.line.fill.background()
        p_pill = pill.text_frame.paragraphs[0]
        p_pill.text = str(i+1)
        p_pill.font.size = Pt(14)
        p_pill.font.bold = True
        p_pill.font.color.rgb = WHITE
        p_pill.alignment = PP_ALIGN.CENTER

        tx = s4.shapes.add_textbox(Inches(2.0), top + Inches(0.12), Inches(10.3), Inches(0.9))
        tf = tx.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(15)
        p.font.bold = True
        p.font.color.rgb = NAVY_DARK

        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(12)
        p2.font.color.rgb = TEXT_MUTED

    # ----------------------------------------------------
    # SLIDE 5: FITUR UTAMA & INOVASI
    # ----------------------------------------------------
    s5 = prs.slides.add_slide(blank_slide_layout)
    add_header(s5, "Fitur Unggulan & Kapabilitas Sistem")

    features = [
        ("RAG Grounding KEP-868", "Injeksi aturan wajib naskah militer langsung ke prompt model untuk menjaga integritas bahasa baku."),
        ("Isolated Point Generator", "Generasi redaksi per butir naskah independen, mencegah pengulangan kalimat pembuka dan duplikasi teks."),
        ("Hierarki Penutup Adaptif", "Pilihan instan Atasan ('mohon menjadi periksa') vs Sejajar/Bawahan ('mohon menjadi perhatian')."),
        ("Sub-Poin Berjenjang Otomatis", "Pemberian penomoran sub-poin (a., b., c.) dan pungtuasi baku militer (';', '; dan', '.') otomatis."),
        ("Identitas Pejabat Militer Lengkap", "Pencantuman otomatis Jabatan, Nama Pejabat berakhiran titik, dan Pangkat/Korps/NRP."),
        ("Distribusi Tembusan Dinamis", "Penambahan daftar pejabat tembusan fleksibel di pojok kiri bawah naskah.")
    ]

    for i, (title, desc) in enumerate(features):
        row = i // 3
        col = i % 3
        left = Inches(0.8 + col * 3.95)
        top = Inches(1.6 + row * 2.6)

        card = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, Inches(3.75), Inches(2.35))
        card.fill.solid()
        card.fill.fore_color.rgb = WHITE
        card.line.color.rgb = BORDER_COLOR
        card.line.width = Pt(1.5)

        tx = s5.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15), Inches(3.35), Inches(2.0))
        tf = tx.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"✨ {title}"
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = NAVY_CARD
        p.space_after = Pt(6)

        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(11.5)
        p2.font.color.rgb = TEXT_DARK

    # ----------------------------------------------------
    # SLIDE 6: KEPATUHAN STANDAR KEP/868/2022
    # ----------------------------------------------------
    s6 = prs.slides.add_slide(blank_slide_layout)
    add_header(s6, "Kepatuhan Spesifikasi Format Militer KEP/868/2022")

    specs = [
        ("Ukuran Kertas & Margin Baku", "Kertas A4 standar militer\n• Atas: 20.3 mm (0.8\")\n• Kiri: 25.4 mm (1.0\")\n• Bawah: 12.7 mm (0.5\")\n• Kanan: 15.2 mm (0.6\")"),
        ("Tipografi & Perataan", "• Font: Arial 12pt\n• Spasi Baris: 1.25\n• Perataan: Justified (Rata Kiri-Kanan)\n• Kop Naskah: Center"),
        ("Tata Letak Tanda Tangan", "• Rata kanan simetris\n• Tempat & tanggal (Jakarta, 22 Agustus 2026)\n• Jabatan penandatangan\n• Nama pejabat tebal berakhiran titik\n• Pangkat/Korps/NRP di bawah nama"),
        ("Struktur Penomoran & Tembusan", "• Format: B/ND-01/VIII/2026/Unit\n• Tembusan di sudut kiri bawah sejajar/bawah TTD\n• Urutan butir: 1., 2., dst.")
    ]

    for i, (title, desc) in enumerate(specs):
        row = i // 2
        col = i % 2
        left = Inches(0.8 + col * 5.9)
        top = Inches(1.6 + row * 2.6)

        card = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, Inches(5.6), Inches(2.35))
        card.fill.solid()
        card.fill.fore_color.rgb = WHITE
        card.line.color.rgb = NAVY_LIGHT
        card.line.width = Pt(1.5)

        tx = s6.shapes.add_textbox(left + Inches(0.3), top + Inches(0.15), Inches(5.0), Inches(2.0))
        tf = tx.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"📐 {title}"
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = NAVY_DARK
        p.space_after = Pt(6)

        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(12)
        p2.font.color.rgb = TEXT_DARK

    # ----------------------------------------------------
    # SLIDE 7: ARSITEKTUR TEKNOLOGI
    # ----------------------------------------------------
    s7 = prs.slides.add_slide(blank_slide_layout)
    add_header(s7, "Arsitektur Sistem & Keamanan Data (On-Premises)")

    tiers = [
        ("1. CLIENT TIER", "• Android Mobile App (Jetpack Compose)\n• Intranet Web Portal (HTML5/Vanilla CSS)\n• Telegram Bot Interface"),
        ("2. BACKEND GATEWAY", "• FastAPI Asynchronous Engine\n• Jinja2 Military Template Engine\n• WeasyPrint / PyMuPDF PDF Engine"),
        ("3. AI & RAG CORE", "• Ollama On-Premises Local LLM\n• Vector Knowledge Base KEP-868\n• Isolated Prompting Pipeline"),
        ("4. SECURITY PERIMETER", "• 100% Air-Gapped Local Network\n• Android FileProvider Sandboxing\n• User Authentication Barrier")
    ]

    for i, (title, desc) in enumerate(tiers):
        left = Inches(0.8 + i * 3.0)
        card = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(1.6), Inches(2.8), Inches(5.1))
        card.fill.solid()
        card.fill.fore_color.rgb = WHITE
        card.line.color.rgb = NAVY_CARD
        card.line.width = Pt(1.5)

        # Header
        hdr = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(1.6), Inches(2.8), Inches(0.7))
        hdr.fill.solid()
        hdr.fill.fore_color.rgb = NAVY_CARD
        hdr.line.fill.background()
        p = hdr.text_frame.paragraphs[0]
        p.text = title
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = WHITE
        p.alignment = PP_ALIGN.CENTER

        tx = s7.shapes.add_textbox(left + Inches(0.15), Inches(2.4), Inches(2.5), Inches(4.0))
        tf = tx.text_frame
        tf.word_wrap = True
        p_desc = tf.paragraphs[0]
        p_desc.text = desc
        p_desc.font.size = Pt(12)
        p_desc.font.color.rgb = TEXT_DARK
        p_desc.line_spacing = 1.3

    # ----------------------------------------------------
    # SLIDE 8: ALUR PENGGUNA (USER JOURNEY)
    # ----------------------------------------------------
    s8 = prs.slides.add_slide(blank_slide_layout)
    add_header(s8, "Alur Operasional Pengguna (User Flow)")

    steps = [
        ("Langkah 1: Login", "Autentikasi akun pengguna (ujiakun/admin123) untuk membuka akses sistem."),
        ("Langkah 2: Input Ringkas", "Isi nomor surat, perihal, dasar, poin pokok isi, sub-poin, dan data penandatangan."),
        ("Langkah 3: Pilih Hierarki", "Tentukan tujuan surat (Atasan vs Sejajar/Bawahan) untuk kalimat penutup otomatis."),
        ("Langkah 4: AI Generate", "Tekan tombol generate, AI merangkai naskah formal baku dalam < 5 detik."),
        ("Langkah 5: Preview & Share", "Tinjau PDF resolusi tinggi via Android Native PdfRenderer, bagikan atau cetak langsung.")
    ]

    for i, (title, desc) in enumerate(steps):
        top = Inches(1.6 + i * 1.05)
        box = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), top, Inches(11.733), Inches(0.9))
        box.fill.solid()
        box.fill.fore_color.rgb = WHITE
        box.line.color.rgb = BORDER_COLOR
        box.line.width = Pt(1.2)

        # Step tag
        tag = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), top + Inches(0.15), Inches(2.2), Inches(0.6))
        tag.fill.solid()
        tag.fill.fore_color.rgb = NAVY_LIGHT
        tag.line.fill.background()
        p_tag = tag.text_frame.paragraphs[0]
        p_tag.text = title
        p_tag.font.size = Pt(12)
        p_tag.font.bold = True
        p_tag.font.color.rgb = WHITE
        p_tag.alignment = PP_ALIGN.CENTER

        tx = s8.shapes.add_textbox(Inches(3.4), top + Inches(0.1), Inches(8.9), Inches(0.7))
        tf = tx.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = desc
        p.font.size = Pt(12)
        p.font.color.rgb = TEXT_DARK

    # ----------------------------------------------------
    # SLIDE 9: DAMPAK & MANFAAT OPERASIONAL
    # ----------------------------------------------------
    s9 = prs.slides.add_slide(blank_slide_layout)
    add_header(s9, "Dampak & Manfaat Operasional Satuan")

    benefits = [
        ("Efisiensi Waktu 90%", "Penyusunan naskah dinas terpangkas dari 60 menit menjadi hanya 1-2 menit secara menyeluruh."),
        ("Zero Data Leak Risk", "Menjamin kerahasiaan dokumen militer 100% terjaga di server lokal tanpa transmisi keluar."),
        ("Standardisasi Format 100%", "Menghilangkan kesalahan margin, format penomoran, dan tanda baca di seluruh satuan kerja."),
        ("Aksesibilitas Komando Tinggi", "Pimpinan dan staf dapat memproses dan menyetujui konsep naskah dinas di mana saja via smartphone.")
    ]

    for i, (title, desc) in enumerate(benefits):
        row = i // 2
        col = i % 2
        left = Inches(0.8 + col * 5.9)
        top = Inches(1.6 + row * 2.6)

        card = s9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, Inches(5.6), Inches(2.35))
        card.fill.solid()
        card.fill.fore_color.rgb = WHITE
        card.line.color.rgb = ACCENT_GOLD if (i==0 or i==1) else NAVY_LIGHT
        card.line.width = Pt(2.0)

        tx = s9.shapes.add_textbox(left + Inches(0.3), top + Inches(0.2), Inches(5.0), Inches(1.9))
        tf = tx.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"🚀  {title}"
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = NAVY_CARD
        p.space_after = Pt(8)

        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(13)
        p2.font.color.rgb = TEXT_DARK

    # ----------------------------------------------------
    # SLIDE 10: PENUTUP & ROADMAP PENGEMBANGAN
    # ----------------------------------------------------
    s10 = prs.slides.add_slide(blank_slide_layout)
    bg10 = s10.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg10.fill.solid()
    bg10.fill.fore_color.rgb = NAVY_DARK
    bg10.line.fill.background()

    # Logo on closing slide
    if logo_path.exists():
        s10.shapes.add_picture(str(logo_path), Inches(1.5), Inches(1.8), width=Inches(3.0), height=Inches(3.0))

    tx10 = s10.shapes.add_textbox(Inches(5.0), Inches(1.5), Inches(7.5), Inches(4.5))
    tf10 = tx10.text_frame
    tf10.word_wrap = True

    p = tf10.paragraphs[0]
    p.text = "KESIMPULAN & ROADMAP"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYBER
    p.space_after = Pt(8)

    p2 = tf10.add_paragraph()
    p2.text = "Sistem Surat Elektronik Berbasis AI (SSEB AI) siap diimplementasikan sebagai platform standar naskah dinas mandiri."
    p2.font.size = Pt(16)
    p2.font.bold = True
    p2.font.color.rgb = WHITE
    p2.space_after = Pt(16)

    p3 = tf10.add_paragraph()
    p3.text = "Roadmap Pengembangan Lanjutan:\n• Integrasi Tanda Tangan Elektronik (TTE / Sertifikat Digital Militer)\n• Integrasi Dikte Suara (Voice-to-Text) Bahasa Indonesia Mandiri\n• Sinkronisasi Ekosistem E-Office Satuan Terpadu"
    p3.font.size = Pt(13)
    p3.font.color.rgb = RGBColor(226, 232, 240)
    p3.space_after = Pt(20)

    p4 = tf10.add_paragraph()
    p4.text = "TERIMA KASIH • SESI TANYA JAWAB"
    p4.font.size = Pt(16)
    p4.font.bold = True
    p4.font.color.rgb = ACCENT_GOLD

    prs.save(str(output_path))
    print(f"[SUCCESS] Presentation successfully generated at: {output_path}")

if __name__ == "__main__":
    out_file = Path(r"d:\DEV_OPS\llm-surat-generator_android_version_v1\PAPARAN_SISTEM_SURAT_ELEKTRONIK_AI.pptx")
    create_presentation(out_file)
