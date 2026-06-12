from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables" / "MoveValue_참가신청서_기획서_초안.docx"


TOKENS = {
    "font": "Malgun Gothic",
    "body_size": 10.5,
    "heading_blue": "2E74B5",
    "heading_dark": "1F4D78",
    "border": "D8DDE2",
    "header_fill": "F2F4F7",
    "muted_fill": "F7F9FB",
}


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=120, bottom=80, end=120):
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in [("top", top), ("start", start), ("bottom", bottom), ("end", end)]:
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color=None):
    color = color or TOKENS["border"]
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_table_width(table, widths):
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False
    for row in table.rows:
        for idx, width in enumerate(widths):
            if idx < len(row.cells):
                row.cells[idx].width = Inches(width)
                set_cell_margins(row.cells[idx])


def set_run_font(run, size=None, bold=False, color=None):
    run.font.name = TOKENS["font"]
    run._element.rPr.rFonts.set(qn("w:eastAsia"), TOKENS["font"])
    if size:
        run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def add_paragraph(doc, text="", style=None, bold=False):
    paragraph = doc.add_paragraph(style=style)
    if text:
        run = paragraph.add_run(text)
        set_run_font(run, TOKENS["body_size"], bold=bold)
    return paragraph


def add_heading(doc, text, level=1):
    style = f"Heading {level}"
    paragraph = doc.add_paragraph(style=style)
    run = paragraph.add_run(text)
    set_run_font(run, 16 if level == 1 else 13 if level == 2 else 12, bold=True, color=TOKENS["heading_blue"] if level < 3 else TOKENS["heading_dark"])
    return paragraph


def add_kv_table(doc, rows):
    table = doc.add_table(rows=0, cols=2)
    set_table_borders(table)
    set_table_width(table, [1.75, 4.75])
    for label, value in rows:
        cells = table.add_row().cells
        cells[0].text = ""
        cells[1].text = ""
        set_cell_shading(cells[0], TOKENS["header_fill"])
        for cell in cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
        label_run = cells[0].paragraphs[0].add_run(label)
        set_run_font(label_run, 9.5, bold=True, color="17212B")
        value_run = cells[1].paragraphs[0].add_run(value)
        set_run_font(value_run, 10.0)
    doc.add_paragraph()
    return table


def add_budget_table(doc):
    rows = [
        ("데이터 수집·정제", "5,000천원", "실거래가·공시가격·건축물대장·SOC API 연계, 데이터 정규화, 품질 점검"),
        ("프로토타입 개발", "8,000천원", "웹 UI, 점수 엔진, 통근·가격 API 어댑터, AI Agent 근거 구조화"),
        ("지도·분석 고도화", "3,000천원", "부동산 지도 라벨, 생활 SOC 반경, 단지 비교, 위험 신호 대시보드"),
        ("실증·사용자 테스트", "2,000천원", "시민 테스트, 인터뷰, 피드백 반영"),
        ("문서화·발표", "2,000천원", "기획서, 리포트, 발표자료"),
    ]
    for item, amount, detail in rows:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.left_indent = Inches(0.18)
        paragraph.paragraph_format.first_line_indent = Inches(-0.18)
        paragraph.paragraph_format.space_after = Pt(4)
        run = paragraph.add_run(f"{item}: ")
        set_run_font(run, 10, bold=True)
        run = paragraph.add_run(f"{amount} - {detail}")
        set_run_font(run, 10)
    doc.add_paragraph()


def build():
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    styles = doc.styles
    styles["Normal"].font.name = TOKENS["font"]
    styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), TOKENS["font"])
    styles["Normal"].font.size = Pt(TOKENS["body_size"])
    styles["Normal"].paragraph_format.line_spacing = 1.1
    styles["Normal"].paragraph_format.space_after = Pt(6)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("2026 국토교통 서비스 발굴 경연 참가신청서 작성 초안")
    set_run_font(run, 18, bold=True, color="17212B")

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("MoveValue: 주거-이동 통합 생활권 매칭 서비스")
    set_run_font(run, 11, bold=True, color=TOKENS["heading_blue"])

    add_paragraph(
        doc,
        "주의: 연락처, 서명, 개인정보 수집·이용 동의는 제출 전 신청자가 직접 확인하고 기재해야 합니다.",
        bold=True,
    )

    add_heading(doc, "1. 참가 신청서", 1)
    add_kv_table(
        doc,
        [
            ("신청 기관명", "이승보 / MoveValue 프로젝트팀(개인 참가, 예비창업)"),
            ("사업 분야", "국토교통 데이터 기반 생활권 추천·부동산·교통 연계 서비스"),
            ("신청 담당자명", "이승보"),
            ("담당자 연락처", "제출 전 기재"),
            ("담당자 이메일", "knightpen@icloud.com"),
            ("서비스 모델명", "MoveValue: 주거-이동 통합 생활권 매칭 서비스"),
            ("서비스 사업 분야", "부동산·교통·MaaS·생활 SOC 데이터 융합 서비스"),
            ("산출물", "웹 기반 생활권 추천·통근검증·부동산 지도 대시보드, 점수 산정 API, live API 어댑터, 데이터 연계 설계서, 서비스 기획서"),
            ("소요 예산", "20,000천원"),
            ("소요 기간", "2026.06.20 ~ 2026.08.31(약 2.5개월)"),
            ("주관 기업", "MoveValue 프로젝트팀: 서비스 기획, 프로토타입 개발, 데이터 결합·스코어링"),
            ("협력 기업", "협력 후보: 국토교통 데이터 보유기관, 부동산 플랫폼, MaaS/교통 데이터 사업자"),
        ],
    )

    add_heading(doc, "2. 실증서비스 모델 구현 기획서", 1)
    sections = [
        (
            "서비스 모델명 및 분야",
            "MoveValue: 주거-이동 통합 생활권 매칭 서비스. 분야는 국토교통 데이터 융합, 생활권 추천, 부동산·교통 연계 서비스입니다.",
        ),
        (
            "서비스 제공 대상",
            "공공 및 민간 모두 해당합니다. 공공은 지자체·정책 부서·공공 데이터 활용 사업을 대상으로 하고, 민간은 부동산 플랫폼·MaaS 플랫폼·기업 이주 지원 서비스·일반 시민을 대상으로 합니다.",
        ),
        (
            "실증서비스 아이디어 모델 개요",
            "MoveValue는 사용자의 월 주거 예산, 출퇴근 목적지, 가구 유형, 생활 인프라 우선순위를 입력받아 후보 생활권을 추천하는 서비스입니다. 단순 월세나 매매가가 아니라 주거비, 이동시간, 환승 편의, 생활 SOC 접근성, 안전·환경 지표를 함께 계산합니다. 핵심 기능은 생활권 랭킹, 실제 주소 기반 통근 루트 검증, 지도 기반 아파트 단지 대시보드, 전세 위험 신호 점검, AI Agent 질의응답, 정책·플랫폼용 API 제공입니다.",
        ),
        (
            "배경 및 필요성",
            "주거 선택 과정에서 시민은 가격, 직장 접근성, 대중교통, 생활시설을 각각 따로 검색해야 합니다. 이 때문에 월세는 낮지만 통근시간과 교통비가 높아지는 선택, 환승 부담이 큰 선택, 생활 인프라 접근성이 떨어지는 선택이 발생합니다. 국토교통 분야에는 실거래가, 지오코딩, 도시철도 역사, 교통 데이터 오픈마켓 등 활용 가능한 데이터가 이미 존재하지만 시민의 실제 의사결정 화면까지 연결되는 서비스는 제한적입니다.",
        ),
        (
            "차별성",
            "기존 부동산 서비스는 매물 가격과 위치 검색 중심입니다. MoveValue는 거주 후 매월 발생하는 이동 부담과 생활 접근성을 비용화·점수화하고, 단지 단위 가격·전세 위험 신호·생활 SOC 반경을 같은 지도에서 확인하게 합니다. 추천 결과를 블랙박스로 제시하지 않고 주거비·통근·생활 SOC·안전환경·확인 필요 서류를 근거 그룹으로 함께 보여줍니다. 공공데이터만으로 최소 기능을 구현할 수 있고, Kakao·ODsay·TMAP·서울 OpenAptInfo·국토교통부 실거래가 API 키가 연결되면 live 검증과 가격 정밀도가 올라가는 단계형 구조입니다.",
        ),
        (
            "현황 및 구체화 방안",
            "현재 작업공간에는 서울시 2025 전월세 실데이터 114,319건을 집계한 API 기반 웹 프로토타입이 구현되어 있습니다. 지도 화면에서는 서울시 공동주택 아파트 단지를 표시하고, 라벨을 매매가·전세가율·위험도·통근시간으로 전환할 수 있습니다. 단지 클릭 시 기본 정보, 가격 정보, 가격 API 연계 상태, 거래 추이, 전세 위험 신호, 계약 전 체크리스트, 생활권 정보, AI 요약이 열리는 대시보드가 동작합니다. 현재 구조는 Kakao 주소 검색, ODsay/TMAP 대중교통 경로, 서울 OpenAptInfo 전체 단지, 국토교통부 아파트 매매·전월세 실거래가 API를 환경변수 키 기반으로 호출하고, 키가 없으면 폴백합니다. 선정 후에는 공시가격 PNU 매핑, 건축물대장, VWorld 지오코더·용도지역, 전국도시철도 역사정보, 국가교통 데이터 오픈마켓 데이터를 추가 어댑터로 연결합니다.",
        ),
        (
            "서비스 구현을 위한 협력 방안",
            "협력 후보는 공공데이터 제공기관과 국토교통 데이터 오픈마켓, 부동산 플랫폼 또는 지역 중개 네트워크, 지자체·교통 데이터 사업자입니다. MoveValue가 데이터 결합, 점수 산정, 화면/API 개발을 맡고, 데이터 공급자는 원천 데이터 및 품질 정보를 제공하며, 수요처는 서비스 실증과 사용자 피드백을 제공하는 구조입니다.",
        ),
        (
            "기대효과",
            "시민은 주거비만 보고 결정할 때 놓치기 쉬운 통근시간, 교통비, 생활 인프라 접근성을 한 화면에서 비교할 수 있습니다. 지자체는 생활권별 교통·주거 부담을 시민 관점으로 파악해 정책 우선순위를 정할 수 있고, 민간 플랫폼은 국토교통 데이터 기반 부가 서비스를 붙여 차별화할 수 있습니다.",
        ),
        (
            "소요 기간",
            "2026.06.20 ~ 2026.08.31(약 2.5개월)",
        ),
    ]

    for heading, body in sections:
        add_heading(doc, heading, 2)
        add_paragraph(doc, body)

    add_heading(doc, "소요 예산", 2)
    add_paragraph(doc, "총 20,000천원")
    add_budget_table(doc)

    add_heading(doc, "3. 서약서 및 개인정보 동의서 확인 항목", 1)
    add_kv_table(
        doc,
        [
            ("서약서 기관명", "이승보 / MoveValue 프로젝트팀"),
            ("신청자(대표) 성명", "이승보"),
            ("서명", "제출 전 직접 서명"),
            ("개인정보 수집·이용 동의", "제출 전 본인이 직접 확인 후 체크"),
        ],
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
