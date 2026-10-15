import copy
import uuid
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from jinja2 import Template
import docx
from docx import Document
from docx.shared import Mm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION, WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from bs4 import BeautifulSoup
from htmldocx import HtmlToDocx

from ..config import settings

logger = logging.getLogger(__name__)

BULAN_ID = [
    'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
    'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
]


def _set_para_text(para, text: str) -> None:
    runs = para.runs
    if not runs:
        para.add_run(text)
        return
    runs[0].text = text
    for r in runs[1:]:
        r.text = ''


def _set_labeled_para(para, label: str, content: str) -> None:
    runs = para.runs
    runs[0].text = label
    if len(runs) > 1:
        r1_el = runs[1]._r
        ts = r1_el.findall(qn('w:t'))
        for t in ts[1:]:
            r1_el.remove(t)
        if not ts:
            t = OxmlElement('w:t')
            r1_el.append(t)
            ts = [t]
        first_t = ts[0]
        prev = first_t.getprevious()
        if prev is None or prev.tag != qn('w:tab'):
            tab = OxmlElement('w:tab')
            first_t.addprevious(tab)
        first_t.text = content
        first_t.set(qn('xml:space'), 'preserve')
    for r in runs[2:]:
        r.text = ''


def _collect_wts(p_el):
    wts = []
    for r in p_el.findall(qn('w:r')):
        wts.extend(r.findall(qn('w:t')))
    return wts


def _set_t_preserve(t_el, text: str) -> None:
    t_el.text = text
    t_el.set(qn('xml:space'), 'preserve')


def _fill_docx(template_path: Path, data: Dict) -> docx.Document:
    doc = docx.Document(str(template_path))
    paras = doc.paragraphs

    isi_list: List[str] = data.get('isi_list') or ['']
    if not isi_list:
        isi_list = ['']

    for para in paras:
        text = para.text

        if text.strip().startswith('PUSAT SIBER') or text.strip().startswith('PUSAT KOMANDO') or text.strip().startswith('KOP UTAMA'):
            _set_para_text(para, data.get('kop_utama', '') + ' ')
            continue

        if 'SATUAN BAWAH' in text:
            lead = text[:len(text) - len(text.lstrip())]
            _set_para_text(para, lead + data.get('kop_sub', ''))
            continue

        if text.startswith('Nomor '):
            _set_para_text(para, 'Nomor ' + data.get('nomor_surat', ''))
            continue

        if text.startswith('Kepada Yth'):
            prefix = text[:text.rfind('\t') + 1]
            _set_para_text(para, prefix + data.get('kepada', ''))
            continue

        if text.startswith('Dari\t'):
            prefix = text[:text.rfind('\t') + 1]
            _set_para_text(para, prefix + data.get('dari', ''))
            continue

        if text.startswith('Perihal\t'):
            prefix = text[:text.rfind('\t') + 1]
            _set_para_text(para, prefix + data.get('perihal', ''))
            continue

    # Dasar list
    dasar_list: List[str] = data.get('dasar_list') or ['']
    a_idx = b_idx = None
    for i, para in enumerate(paras):
        if para.text.startswith('a.\t'):
            a_idx = i
        elif para.text.startswith('b.\t'):
            b_idx = i

    if a_idx is not None:
        _set_labeled_para(paras[a_idx], 'a.', dasar_list[0])

    if b_idx is not None:
        if len(dasar_list) == 1:
            b_el = paras[b_idx]._p
            prev_el = paras[b_idx - 1]._p
            b_el.getparent().remove(prev_el)
            b_el.getparent().remove(b_el)
        else:
            _set_labeled_para(paras[b_idx], 'b.', dasar_list[1])
            empty_el = paras[b_idx - 1]._p
            b_el = paras[b_idx]._p
            anchor = b_el
            for extra_idx in range(2, len(dasar_list)):
                letter = chr(97 + extra_idx)
                new_empty = copy.deepcopy(empty_el)
                new_item = copy.deepcopy(b_el)
                anchor.addnext(new_empty)
                new_empty.addnext(new_item)
                anchor = new_item
                wts = _collect_wts(new_item)
                for t in wts[2:]:
                    t.text = ''
                _set_t_preserve(wts[0], letter + '.')
                _set_t_preserve(wts[1], dasar_list[extra_idx])

    # Isi
    idx2 = idx3 = None
    for i, para in enumerate(paras):
        if para.text.startswith('2.\t'):
            idx2 = i
        elif para.text.startswith('3.\tDemikian'):
            idx3 = i

    if idx2 is not None:
        _set_labeled_para(paras[idx2], '2.', isi_list[0])

        if len(isi_list) > 1:
            item_el = paras[idx2]._p
            empty_el = paras[idx2 + 1]._p
            anchor = empty_el
            for i in range(1, len(isi_list)):
                new_item = copy.deepcopy(item_el)
                new_empty = copy.deepcopy(empty_el)
                anchor.addnext(new_item)
                new_item.addnext(new_empty)
                anchor = new_empty
                wts = _collect_wts(new_item)
                for t in wts[2:]:
                    t.text = ''
                _set_t_preserve(wts[0], '%d.' % (2 + i))
                _set_t_preserve(wts[1], isi_list[i])

    if idx3 is not None:
        _set_labeled_para(
            paras[idx3],
            '%d.' % (2 + len(isi_list)),
            'Demikian disampaikan mohon menjadi perhatian.'
        )

    # Textboxes: tanggal & nama pejabat
    body = doc.element.body
    for txbx in body.iter(qn('w:txbxContent')):
        for p in txbx.findall(qn('w:p')):
            ts = p.findall('.//' + qn('w:t'))
            full = ''.join(t.text or '' for t in ts)
            if 'Jakarta,' in full and 'tanggal_ttd' in data:
                for t in ts:
                    t.text = ''
                _set_t_preserve(ts[0], data['tanggal_ttd'])
            elif 'Budi Santoso' in full and 'nama_pejabat' in data:
                for t in ts:
                    t.text = ''
                _set_t_preserve(ts[0], data['nama_pejabat'] + '.')

    return doc


def preprocess_html_for_docx(html: str) -> str:
    """
    Bersihkan HTML sebelum diparsing oleh htmldocx agar tidak error pada tabel bersarang
    atau tag-tag kompleks.
    """
    soup = BeautifulSoup(html, 'html.parser')

    for tag in soup(['style', 'script']):
        tag.decompose()

    # Ratakan tabel bertingkat / bersarang (nested tables)
    for table in soup.find_all('table'):
        for nested in table.find_all('table'):
            div = soup.new_tag('div')
            for row in nested.find_all('tr'):
                p = soup.new_tag('p')
                cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
                p.string = '    '.join(cells)
                div.append(p)
            nested.replace_with(div)

    return str(soup)


def _convert_complex_tables(soup_body, doc):
    """
    Konversi tabel HTML dengan colspan/rowspan menjadi tabel python-docx langsung.
    """
    tables = soup_body.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        if not rows:
            continue
        max_cols = 0
        for r in rows:
            cells = r.find_all(['td', 'th'])
            col_count = sum(int(c.get('colspan', 1)) for c in cells)
            if col_count > max_cols:
                max_cols = col_count

        if max_cols == 0:
            continue

        docx_tbl = doc.add_table(rows=len(rows), cols=max_cols)
        docx_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        for r_idx, r in enumerate(rows):
            cells = r.find_all(['td', 'th'])
            c_idx = 0
            for cell in cells:
                colspan = int(cell.get('colspan', 1))
                text = cell.get_text(separator=' ', strip=True)
                if c_idx < max_cols:
                    docx_cell = docx_tbl.cell(r_idx, c_idx)
                    docx_cell.text = text
                    for p in docx_cell.paragraphs:
                        for run in p.runs:
                            run.font.name = 'Arial'
                            run.font.size = Pt(8.5 if cell.name == 'th' else 8)
                            if cell.name == 'th':
                                run.font.bold = True
                c_idx += colspan
        table.decompose()


def create_docx_from_html(html_content: str, output_path: Path, landscape: bool = False) -> Path:
    """
    Render dokumen DOCX dari HTML dengan standar margin KEP/868/2022 Mabes TNI.
    """
    clean_html = preprocess_html_for_docx(html_content)
    doc = Document()

    for section in doc.sections:
        if landscape:
            section.orientation = WD_ORIENT.LANDSCAPE
            section.page_width = Mm(297)
            section.page_height = Mm(210)
            section.top_margin = Mm(15)
            section.right_margin = Mm(15)
            section.bottom_margin = Mm(15)
            section.left_margin = Mm(15)
        else:
            section.orientation = WD_ORIENT.PORTRAIT
            section.page_width = Mm(210)
            section.page_height = Mm(297)
            section.top_margin = Mm(20.3)
            section.right_margin = Mm(18)
            section.bottom_margin = Mm(12.7)
            section.left_margin = Mm(25.4)

    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Arial'
    normal_style.font.size = Pt(11)

    parser = HtmlToDocx()
    parser.add_html_to_document(clean_html, doc)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path


def create_docx_nota_dinas(template_data: dict, output_path: Path) -> Path:
    """
    Buat file DOCX untuk Nota Dinas sesuai format baku KEP/868/2022.
    Menggunakan template DOCX resmi jika tersedia, fallback ke HTML render.
    """
    template_path = settings.TEMPLATE_DIR / 'nota_dinas_template.docx'
    if template_path.exists():
        try:
            doc = _fill_docx(template_path, template_data)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path))
            return output_path
        except Exception as e:
            logger.warning(f"Gagal generate DOCX via template asli: {e}, fallback ke HTML render")

    template_file = settings.TEMPLATE_DIR / "nota_dinas_template.html"
    with open(template_file, "r", encoding="utf-8") as f:
        tmpl = Template(f.read())
    html_content = tmpl.render(**template_data)
    return create_docx_from_html(html_content, output_path, landscape=False)


def create_docx_telaahan_staf(template_data: dict, output_path: Path) -> Path:
    """
    Generate DOCX untuk telaahan staf baku TNI (KEP/868 Contoh 26).
    """
    data = dict(template_data)
    if "sections" in data and "pasal" not in data:
        data["pasal"] = data["sections"]
    elif "pasal" in data and "sections" not in data:
        data["sections"] = data["pasal"]

    nama = data.get("nama_pejabat") or data.get("nama_pejabat_atau_pasis") or "Budi Santoso"
    jabatan = data.get("jabatan_pejabat") or data.get("jabatan") or "Perwira Staf"
    pangkat = data.get("pangkat_pejabat") or data.get("pangkat_korps_nrp") or ""

    data["nama_pejabat"] = nama
    data["nama_pejabat_atau_pasis"] = nama
    data["jabatan_pejabat"] = jabatan
    data["jabatan"] = jabatan
    data["pangkat_pejabat"] = pangkat
    data["pangkat_korps_nrp"] = pangkat

    template_file = settings.TEMPLATE_DIR / "telaahan_staf_template.html"
    with open(template_file, "r", encoding="utf-8") as f:
        tmpl = Template(f.read())
    html_content = tmpl.render(**data)
    return create_docx_from_html(html_content, output_path, landscape=False)


def create_docx_kajian(kategori: str, kka_model: str, template_data: dict, output_path: Path) -> Path:
    """
    Generate DOCX untuk Modul Kajian Dual-Mode:
    - TELAAHAN_STAF: KEP/868/IX/2022 Contoh 26
    - KKA_SESKOAL: STUDI_KASUS, ANALISIS_MOE, PEMECAHAN_MASALAH
    """
    data = dict(template_data)
    if "sections" in data and "pasal" not in data:
        data["pasal"] = data["sections"]
    elif "pasal" in data and "sections" not in data:
        data["sections"] = data["pasal"]

    nama = data.get("nama_pejabat") or data.get("nama_pejabat_atau_pasis") or "Budi Santoso"
    jabatan = data.get("jabatan_pejabat") or data.get("jabatan") or "Perwira Staf"
    pangkat = data.get("pangkat_pejabat") or data.get("pangkat_korps_nrp") or ""

    data["nama_pejabat"] = nama
    data["nama_pejabat_atau_pasis"] = nama
    data["jabatan_pejabat"] = jabatan
    data["jabatan"] = jabatan
    data["pangkat_pejabat"] = pangkat
    data["pangkat_korps_nrp"] = pangkat

    kat_upper = str(kategori).upper()
    if kat_upper == "TELAAHAN_STAF" or "TELAAHAN" in kat_upper:
        template_file = settings.TEMPLATE_DIR / "telaahan_staf_template.html"
    else:
        model_upper = str(kka_model).upper()
        if "STUDI_KASUS" in model_upper or "KASUS" in model_upper:
            template_file = settings.TEMPLATE_DIR / "kka_studi_kasus_template.html"
        elif "ANALISIS" in model_upper or "MOE" in model_upper:
            template_file = settings.TEMPLATE_DIR / "kka_analisis_moe_template.html"
        elif "MASALAH" in model_upper or "SOM" in model_upper:
            template_file = settings.TEMPLATE_DIR / "kka_pemecahan_masalah_template.html"
        else:
            template_file = settings.TEMPLATE_DIR / "kka_studi_kasus_template.html"

    with open(template_file, "r", encoding="utf-8") as f:
        tmpl = Template(f.read())
    html_content = tmpl.render(**data)
    return create_docx_from_html(html_content, output_path, landscape=False)


def create_docx_surat(template_data: dict, output_path: Path) -> Path:
    """
    Generate DOCX untuk surat dinas resmi.
    """
    template_file = settings.TEMPLATE_DIR / "surat_template.html"
    with open(template_file, "r", encoding="utf-8") as f:
        tmpl = Template(f.read())
    html_content = tmpl.render(**template_data)
    return create_docx_from_html(html_content, output_path, landscape=False)


def create_docx_lapju(template_data: dict, output_path: Path) -> Path:
    """
    Generate DOCX resmi terpadu Laporan Kemajuan (LAPJU) Belanja Modal:
    Bagian 1: Portrait A4 Surat Pengantar resmi
    Bagian 2: Landscape A4 Matriks Tabel Realisasi
    """
    with open(settings.TEMPLATE_DIR / "lapju_surat_pengantar_template.html", "r", encoding="utf-8") as f:
        tmpl_p = Template(f.read())
    html_p = tmpl_p.render(**template_data)

    with open(settings.TEMPLATE_DIR / "lapju_lampiran_tabel_template.html", "r", encoding="utf-8") as f:
        tmpl_l = Template(f.read())
    html_l = tmpl_l.render(**template_data)

    doc = Document()

    # Section 1: Portrait
    sec1 = doc.sections[0]
    sec1.orientation = WD_ORIENT.PORTRAIT
    sec1.page_width = Mm(210)
    sec1.page_height = Mm(297)
    sec1.top_margin = Mm(20.3)
    sec1.right_margin = Mm(18)
    sec1.bottom_margin = Mm(12.7)
    sec1.left_margin = Mm(25.4)

    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Arial'
    normal_style.font.size = Pt(11)

    clean_p = preprocess_html_for_docx(html_p)
    parser = HtmlToDocx()
    parser.add_html_to_document(clean_p, doc)

    # Section 2: Landscape
    sec2 = doc.add_section(WD_SECTION.NEW_PAGE)
    sec2.orientation = WD_ORIENT.LANDSCAPE
    sec2.page_width = Mm(297)
    sec2.page_height = Mm(210)
    sec2.top_margin = Mm(15)
    sec2.right_margin = Mm(15)
    sec2.bottom_margin = Mm(15)
    sec2.left_margin = Mm(15)

    soup_l = BeautifulSoup(html_l, 'html.parser')
    for tag in soup_l(['style', 'script']):
        tag.decompose()

    # Render non-table header texts first
    table_tag = soup_l.find('table')
    if table_tag:
        # Extra tags before table
        _convert_complex_tables(soup_l, doc)
    
    clean_l = str(soup_l)
    if clean_l.strip():
        parser.add_html_to_document(clean_l, doc)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path
