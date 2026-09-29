import copy
import uuid
from pathlib import Path
from typing import Dict, List

import docx
from docx.oxml.ns import qn

from ..config import settings

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
    """
    Set nomor/huruf pada run pertama dan teks pada run kedua,
    dengan menyisipkan <w:tab/> sebelum teks (struktur sample asli).
    python-docx run.text setter menghapus elemen <w:tab/>,
    jadi tab harus disisipkan ulang secara eksplisit.
    """
    from docx.oxml import OxmlElement

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

        if text.strip().startswith('PUSAT SIBER'):
            _set_para_text(para, data['kop_utama'] + ' ')
            continue

        if 'SATUAN BAWAH' in text:
            lead = text[:len(text) - len(text.lstrip())]
            _set_para_text(para, lead + data['kop_sub'])
            continue

        if text.startswith('Nomor '):
            _set_para_text(para, 'Nomor ' + data['nomor_surat'])
            continue

        if text.startswith('Kepada Yth'):
            prefix = text[:text.rfind('\t') + 1]
            _set_para_text(para, prefix + data['kepada'])
            continue

        if text.startswith('Dari\t'):
            prefix = text[:text.rfind('\t') + 1]
            _set_para_text(para, prefix + data['dari'])
            continue

        if text.startswith('Perihal\t'):
            prefix = text[:text.rfind('\t') + 1]
            _set_para_text(para, prefix + data['perihal'])
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

    # Isi: poin 2, 3, 4, ... sesuai jumlah ringkasan; penutup bernomor berikutnya
    idx2 = idx3 = None
    for i, para in enumerate(paras):
        if para.text.startswith('2.\t'):
            idx2 = i
        elif para.text.startswith('3.\tDemikian'):
            idx3 = i

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

    _set_labeled_para(
        paras[idx3],
        '%d.' % (2 + len(isi_list)),
        'Demikian disampaikan mohon menjadi perhatian.'
    )

    # Textboxes (Choice + Fallback): tanggal & nama pejabat
    body = doc.element.body
    for txbx in body.iter(qn('w:txbxContent')):
        for p in txbx.findall(qn('w:p')):
            ts = p.findall('.//' + qn('w:t'))
            full = ''.join(t.text or '' for t in ts)
            if 'Jakarta,' in full:
                for t in ts:
                    t.text = ''
                _set_t_preserve(ts[0], data['tanggal_ttd'])
            elif 'Budi Santoso' in full:
                for t in ts:
                    t.text = ''
                _set_t_preserve(ts[0], data['nama_pejabat'] + '.')

    return doc


def _docx_to_pdf(docx_path: Path, pdf_path: Path) -> None:
    import win32com.client

    word = win32com.client.DispatchEx('Word.Application')
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        word.AutomationSecurity = 3
    except Exception:
        pass
    try:
        doc = word.Documents.Open(
            str(docx_path), ReadOnly=True, AddToRecentFiles=False,
            Visible=False, ConfirmConversions=False
        )
        doc.SaveAs(str(pdf_path), FileFormat=17)
        doc.Close(False)
    finally:
        try:
            word.Quit()
        except Exception:
            pass


def create_pdf_nota_dinas(template_data: dict, output_path: Path) -> Path:
    """
    Isi template DOCX sample (format identik dengan dokumen referensi),
    lalu konversi ke PDF melalui Microsoft Word agar layout 100% sama.
    """
    template_path = settings.TEMPLATE_DIR / 'nota_dinas_template.docx'

    doc = _fill_docx(template_path, template_data)

    tmp_docx = settings.OUTPUT_DIR / f'_tmp_{uuid.uuid4().hex}.docx'
    doc.save(str(tmp_docx))

    try:
        _docx_to_pdf(tmp_docx, output_path)
    finally:
        tmp_docx.unlink(missing_ok=True)

    return output_path
