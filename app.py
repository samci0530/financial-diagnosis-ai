import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import joblib
import numpy as np
import io
import os
import json
from datetime import datetime
from fpdf import FPDF

try:
    from db import init_db, save_result, save_bulk, fetch_history, fetch_grade_stats, test_connection
    DB_AVAILABLE = True
except ImportError:
    try:
        from db import init_db, save_result, fetch_history, fetch_grade_stats, test_connection
        DB_AVAILABLE = True
    except ImportError:
        DB_AVAILABLE = False

try:
    from db import delete_history_bulk
    DELETE_AVAILABLE = True
except ImportError:
    DELETE_AVAILABLE = False

try:
    from db import fetch_company_names, fetch_latest_by_name
    LOAD_AVAILABLE = True
except ImportError:
    LOAD_AVAILABLE = False

# 사이드바 초기 상태를 collapsed로 설정해 로딩 시 깜빡임 방지 (사이드바 숨김의 가장 깔끔한 방법)
st.set_page_config(page_title="AI 기반 기업 재무 건전성 진단 시스템", layout="wide", initial_sidebar_state="collapsed")

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700;900&display=swap');
* { font-family: 'Noto Sans KR', sans-serif !important; box-sizing: border-box; }
html, body, .stApp { background: #f0f2f5 !important; }

/* 양옆 여백 동일하게 맞추고 가운데 정렬 (max-width 지정) */
.main .block-container { 
    padding: 0 !important; 
    max-width: 1400px !important; 
    margin: 0 auto !important; 
}

#MainMenu { visibility: hidden !important; }
[data-testid="stToolbar"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; height: 0 !important; min-height:0 !important; }
footer { visibility: hidden !important; }
.stDeployButton { display: none !important; }

/* 사이드바 관련 모든 UI 강제 숨김 */
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stSidebarCollapsedControl"] { display: none !important; }
button[kind="header"] { display: none !important; }

.stButton > button { background: #3b82f6 !important; color: white !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; font-size: 13px !important; transition: all 0.2s !important; padding: 8px 18px !important; }
.stButton > button:hover { background: #2563eb !important; transform: translateY(-1px) !important; box-shadow: 0 4px 12px rgba(59,130,246,0.3) !important; }

.stTextInput input, .stNumberInput input { background: white !important; border: 1.5px solid #e2e8f0 !important; border-radius: 8px !important; font-size: 13px !important; color: #1e293b !important; transition: border-color 0.2s !important; }
.stTextInput input:focus, .stNumberInput input:focus { border-color: #3b82f6 !important; box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important; }
.stSelectbox > div > div { background: white !important; border: 1.5px solid #e2e8f0 !important; border-radius: 8px !important; color: #1e293b !important; }

.stTabs [data-baseweb="tab-list"] { background: #f1f5f9; border-radius: 10px; padding: 4px; gap: 2px; border: none; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: #64748b !important; border-radius: 7px !important; font-size: 12px !important; font-weight: 500 !important; padding: 7px 16px !important; }
.stTabs [aria-selected="true"] { background: white !important; color: #1e293b !important; font-weight: 600 !important; box-shadow: 0 1px 4px rgba(0,0,0,0.08) !important; }

[data-testid="stMetric"] { background: white; border-radius: 12px; padding: 16px !important; border: 1px solid #e8ecf0; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
[data-testid="stMetricLabel"] { color: #64748b !important; font-size: 11px !important; font-weight: 600 !important; }
[data-testid="stMetricValue"] { color: #1e293b !important; font-size: 22px !important; font-weight: 700 !important; }

/* ── 파일 업로더 CSS 수정 (빈 공간 클릭 방지 및 버튼 명확화) ── */
[data-testid="stFileUploader"] { background: white !important; border-radius: 12px !important; border: 1.5px dashed #cbd5e1 !important; }
[data-testid="stFileUploader"] section { padding: 16px !important; }
[data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }

/* dropzone: chip + 추가 버튼 가로 배치, 빈 공간 클릭 방지 */
[data-testid="stFileUploaderDropzone"] {
    background: #f8fafc !important;
    pointer-events: none !important;
    display: flex !important;
    flex-wrap: wrap !important;
    align-items: center !important;
    gap: 8px !important;
}

/* ── 1. 파일 추가 (삭제 버튼 제외한 dropzone 내 button) ── */
[data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"],
[data-testid="stFileUploaderDropzone"] button:not([data-testid="stFileChipDeleteBtn"] button):not([data-testid="stFileUploaderDeleteBtn"]) {
    pointer-events: auto !important;
    background: #3b82f6 !important;
    border: none !important;
    border-radius: 8px !important;
    color: transparent !important;
    font-size: 0 !important;
    position: relative !important;
    min-width: 90px !important;
    height: 38px !important;
    padding: 0 16px !important;
    overflow: hidden !important;
    flex-shrink: 0 !important;
}
[data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"] *,
[data-testid="stFileUploaderDropzone"] button:not([data-testid="stFileChipDeleteBtn"] button):not([data-testid="stFileUploaderDeleteBtn"]) * {
    display: none !important;
    visibility: hidden !important;
}
[data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"]::after,
[data-testid="stFileUploaderDropzone"] button:not([data-testid="stFileChipDeleteBtn"] button):not([data-testid="stFileUploaderDeleteBtn"])::after {
    content: "파일 추가" !important;
    position: absolute !important;
    inset: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    color: white !important;
    background: #3b82f6 !important;
    visibility: visible !important;
    font-family: 'Noto Sans KR', sans-serif !important;
}
[data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"]:hover::after,
[data-testid="stFileUploaderDropzone"] button:not([data-testid="stFileChipDeleteBtn"] button):not([data-testid="stFileUploaderDeleteBtn"]):hover::after {
    background: #2563eb !important;
}

/* ── 2. 파일 삭제 (chip 삭제 버튼만) ── */
[data-testid="stFileChipDeleteBtn"] button,
[data-testid="stFileUploaderDeleteBtn"] {
    pointer-events: auto !important;
    background: #fee2e2 !important;
    border: 1.5px solid #fca5a5 !important;
    border-radius: 8px !important;
    font-size: 0 !important;
    position: relative !important;
    min-width: 80px !important;
    width: 80px !important;
    height: 38px !important;
    padding: 0 !important;
    overflow: hidden !important;
    margin-left: 8px !important;
}
[data-testid="stFileChipDeleteBtn"] button svg,
[data-testid="stFileUploaderDeleteBtn"] svg {
    display: none !important;
}
[data-testid="stFileChipDeleteBtn"] button::after,
[data-testid="stFileUploaderDeleteBtn"]::after {
    content: "파일 삭제" !important;
    position: absolute !important;
    inset: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: #ef4444 !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    background: #fee2e2 !important;
    visibility: visible !important;
    font-family: 'Noto Sans KR', sans-serif !important;
}
[data-testid="stFileChipDeleteBtn"] button:hover::after,
[data-testid="stFileUploaderDeleteBtn"]:hover::after {
    background: #fecaca !important;
}

/* 파일 chip 레이아웃 */
[data-testid="stFileChip"],
[data-testid="stUploadedFile"] {
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 8px !important;
}

hr { border-color: #e2e8f0 !important; margin: 6px 0 !important; }
h1,h2,h3 { color: #1e293b !important; }
.stAlert { border-radius: 10px !important; font-size: 13px !important; }

[data-testid="stSlider"] > div > div > div > div { background: #3b82f6 !important; }

.card { background: white; border-radius: 14px; padding: 20px; border: 1px solid #e8ecf0; box-shadow: 0 1px 6px rgba(0,0,0,0.05); margin-bottom: 16px; }
.card-title { font-size: 13px; font-weight: 700; color: #1e293b; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid #f1f5f9; display: flex; align-items: center; gap: 6px; }
.kpi-card { background: white; border-radius: 14px; padding: 18px 20px; border: 1px solid #e8ecf0; box-shadow: 0 1px 6px rgba(0,0,0,0.04); }
.kpi-label { font-size: 11px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; display: flex; align-items: center; gap: 5px; }
.kpi-value { font-size: 26px; font-weight: 800; color: #1e293b; line-height: 1.1; }
.kpi-sub { font-size: 11px; color: #94a3b8; margin-top: 4px; }
[data-testid="stDataFrame"] { border-radius: 10px !important; overflow: hidden !important; border: 1px solid #e8ecf0 !important; }

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 99px; }
</style>
""", unsafe_allow_html=True)

# ── DB / 모델 ────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def init_db_once():
    if not DB_AVAILABLE:
        return False
    try:
        init_db()
        return test_connection()
    except Exception:
        return False

@st.cache_resource(show_spinner=False)
def load_model():
    try: return joblib.load('model.pkl')
    except: return None

@st.cache_resource(show_spinner=False)
def load_model_accuracy(_model):
    """
    실제 모델 정확도를 구한다.
    우선순위: 1) model_meta.json에 저장된 test accuracy
              2) 모델이 oob_score=True로 학습되어 있으면 OOB 정확도
              3) 둘 다 없으면 None (화면에는 '정보 없음'으로 표시)
    """
    # 1) 학습 스크립트가 저장한 메타 파일 우선 사용
    try:
        if os.path.exists('model_meta.json'):
            with open('model_meta.json', 'r', encoding='utf-8') as f:
                meta = json.load(f)
                if 'accuracy' in meta:
                    return round(float(meta['accuracy']) * 100, 1), meta.get('source', 'test set')
    except Exception:
        pass
    # 2) RandomForest가 oob_score=True로 학습됐다면 OOB score 사용
    if _model is not None and hasattr(_model, 'oob_score_'):
        return round(_model.oob_score_ * 100, 1), 'OOB (Out-of-Bag)'
    return None, None

db_ok    = init_db_once()
ai_model = load_model()
model_accuracy, model_accuracy_src = load_model_accuracy(ai_model)

@st.cache_data(ttl=30, show_spinner=False)
def cached_grade_stats():
    return fetch_grade_stats() if DB_AVAILABLE else {"A":0,"B":0,"C":0,"D":0}

@st.cache_data(ttl=30, show_spinner=False)
def cached_history(grade_filter=None, keyword=None):
    return fetch_history(grade_filter=grade_filter, keyword=keyword) if DB_AVAILABLE else []

REQUIRED_COLS = ['기업명','산업군','당기매출액','전기매출액','당기순이익','유동자산','유동부채','부채총계','자본총계']
GRADE_INFO = {
    3: dict(label="A등급", short="A", desc="최우수/우수 정상 기업 — 재무 구조가 매우 탄탄합니다.", color="#3b82f6", bg="#eff6ff", light="#dbeafe"),
    2: dict(label="B등급", short="B", desc="양호/보통 정상 기업 — 균형 잡힌 자산 구조를 유지합니다.", color="#10b981", bg="#ecfdf5", light="#d1fae5"),
    1: dict(label="C등급", short="C", desc="워크아웃 대상 — 부실 징후 조기 탐지, 개선이 필요합니다.", color="#f59e0b", bg="#fffbeb", light="#fde68a"),
    0: dict(label="D등급", short="D", desc="법정관리 대상 — 고위험 상태, 즉각 구조조정이 필요합니다.", color="#ef4444", bg="#fef2f2", light="#fecaca"),
}
grade_colors = {'A':'#3b82f6','B':'#10b981','C':'#f59e0b','D':'#ef4444'}
grade_bgs    = {'A':'#eff6ff','B':'#ecfdf5','C':'#fffbeb','D':'#fef2f2'}

def hex_to_rgba(hex_color, alpha=0.2):
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2],16), int(hex_color[2:4],16), int(hex_color[4:6],16)
    return f'rgba({r},{g},{b},{alpha})'

def calc_ratios(rc,rp,ni,ca,cl,tl,eq):
    return ((tl/eq)*100 if eq>0 else 0, (ca/cl)*100 if cl>0 else 0,
            (ni/rc)*100 if rc>0 else 0, ((rc-rp)/rp)*100 if rp>0 else 0)

def predict_one(model,dr,cr,nm,rg):
    X=np.array([[dr,cr,nm,rg]])
    pred=model.predict(X)[0]; prob=model.predict_proba(X)[0]
    return int(pred), int(prob[min(int(pred),len(prob)-1)]*100)

# ── PDF 리포트 생성 ──────────────────────────────────────────
FONT_REG  = os.path.join(os.path.dirname(__file__), 'fonts', 'NanumGothic-Regular.ttf')
FONT_BOLD = os.path.join(os.path.dirname(__file__), 'fonts', 'NanumGothic-Bold.ttf')

def generate_individual_report_pdf(company_name, industry, gi, score, dr, cr, nm, rg, opinion_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('Nanum', '', FONT_REG, uni=True)
    pdf.add_font('Nanum', 'B', FONT_BOLD, uni=True)

    # 헤더
    pdf.set_font('Nanum', 'B', 18)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 12, "AI 기반 기업 재무 건전성 진단 리포트", ln=True)
    pdf.set_font('Nanum', '', 10)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 8, f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.ln(4)
    pdf.set_draw_color(226, 232, 240)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)

    # 기업 정보
    pdf.set_font('Nanum', 'B', 13)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 9, f"기업명: {company_name or '미입력'}", ln=True)
    pdf.set_font('Nanum', '', 11)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 8, f"산업군: {industry or '미입력'}", ln=True)
    pdf.ln(6)

    # 등급 결과 박스
    r, g, b = tuple(int(gi['color'].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    pdf.set_fill_color(245, 247, 250)
    pdf.set_draw_color(r, g, b)
    y0 = pdf.get_y()
    pdf.rect(10, y0, 190, 30, style='DF')
    pdf.set_xy(15, y0 + 5)
    pdf.set_font('Nanum', 'B', 22)
    pdf.set_text_color(r, g, b)
    pdf.cell(40, 20, gi['short'], align='C')
    pdf.set_xy(60, y0 + 6)
    pdf.set_font('Nanum', 'B', 13)
    pdf.cell(0, 8, gi['label'], ln=True)
    pdf.set_x(60)
    pdf.set_font('Nanum', '', 10)
    pdf.set_text_color(71, 85, 105)
    pdf.multi_cell(130, 6, gi['desc'])
    pdf.set_xy(150, y0 + 6)
    pdf.set_font('Nanum', 'B', 16)
    pdf.set_text_color(r, g, b)
    pdf.cell(40, 8, f"{score}점", align='R')
    pdf.set_y(y0 + 34)
    pdf.ln(6)

    # 재무 비율 표
    pdf.set_font('Nanum', 'B', 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 8, "주요 재무 비율", ln=True)
    pdf.set_fill_color(248, 250, 252)
    pdf.set_font('Nanum', 'B', 10)
    labels = ["부채비율", "유동비율", "순이익률", "매출증가율"]
    values = [f"{dr:.1f}%", f"{cr:.1f}%", f"{nm:.1f}%", f"{rg:.1f}%"]
    col_w = 47.5
    for lab in labels:
        pdf.cell(col_w, 9, lab, border=1, align='C', fill=True)
    pdf.ln()
    pdf.set_font('Nanum', '', 11)
    for val in values:
        pdf.cell(col_w, 9, val, border=1, align='C')
    pdf.ln(14)

    # AI 의견
    pdf.set_font('Nanum', 'B', 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 8, "AI 핵심 의견", ln=True)
    pdf.set_font('Nanum', '', 10.5)
    pdf.set_text_color(55, 65, 81)
    pdf.multi_cell(0, 7, opinion_text)

    pdf.set_y(-20)
    pdf.set_font('Nanum', '', 8)
    pdf.set_text_color(180, 180, 180)
    pdf.cell(0, 10, "본 리포트는 AI 모델(RandomForest)의 예측 결과이며 참고용으로만 활용하시기 바랍니다.", align='C')

    return bytes(pdf.output())

# ── 세션 ─────────────────────────────────────────────────────
if 'page' not in st.session_state: st.session_state.page = 'home'

# ══════════════════════════════════════════════════════════════
# 공통 헤더 (상단 홈페이지 로고 영역)
# ══════════════════════════════════════════════════════════════
def render_topbar(title_ko="대시보드", subtitle_ko="신속 현황 및 빠른 진단"):
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    
    # 1. 화면 맨 위 '가운데'에 위치하는 홈버튼 (로고 스타일 적용)
    _, top_col, _ = st.columns([1, 2, 1])
    with top_col:
        if st.button("📊 AI 기반 기업 재무 건전성 진단 시스템", key=f"top_home_{title_ko}", use_container_width=True):
            st.session_state.page = 'home'
            st.rerun()

    # 2. 각 분석창의 타이틀을 보여주는 헤더 박스
    st.markdown(f"""
    <div style='background:white; border:1px solid #e8ecf0;
                padding:15px 28px; margin-top: 12px; margin-bottom: 20px;
                border-radius: 12px; box-shadow:0 1px 4px rgba(0,0,0,0.03);'>
        <div>
            <div style='font-size:17px;font-weight:800;color:#1e293b;margin-bottom:2px;'>{title_ko}</div>
            <div style='font-size:11px;color:#94a3b8;'>{subtitle_ko}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# 홈 페이지
# ══════════════════════════════════════════════════════════════
if st.session_state.page == 'home':
    # 메인화면 한 화면에 들어가도록 padding 최적화
    st.markdown("""
    <div style='background:linear-gradient(135deg,#1e3a5f 0%,#1d4ed8 50%,#1e3a5f 100%);
                padding:45px 60px 35px;text-align:center;'>
        <div style='width:60px;height:60px;background:rgba(255,255,255,0.15);
                    backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,0.2);
                    border-radius:16px;display:inline-flex;align-items:center;
                    justify-content:center;font-size:28px;margin-bottom:16px;
                    box-shadow:0 8px 24px rgba(0,0,0,0.2);'>📊</div>
        <div style='font-size:11px;font-weight:600;color:rgba(255,255,255,0.6);
                    letter-spacing:3px;margin-bottom:6px;'>AI POWERED</div>
        <div style='font-size:28px;font-weight:900;color:white;margin-bottom:10px;
                    line-height:1.2;'>AI 기반 기업<br>재무 건전성 진단 시스템</div>
        <div style='font-size:13px;color:rgba(255,255,255,0.7);line-height:1.8;max-width:520px;margin:0 auto;'>
            한국은행 표준 신용평가 기준 · RandomForest 4단계 AI 모델<br>
            A·B·C·D 4등급 건전성 자동 진단
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='padding:24px 48px 10px;'>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4, gap="medium")
    feature_cards = [
        ('dashboard', '🏠', '대시보드', '전체 현황 및 KPI', '#3b82f6', '#eff6ff', ['DB 누적 통계 확인','등급 분포 차트','빠른 진단 기능']),
        ('individual', '🔍', '개별 진단', '기업 1개 상세 분석', '#10b981', '#ecfdf5', ['재무 수치 직접 입력','AI 등급 즉시 예측','What-If 시뮬레이션']),
        ('bulk', '📂', '일괄 분석', 'CSV/Excel 다중 분석', '#f59e0b', '#fffbeb', ['파일 업로드 지원','전체 기업 일괄 분석','엑셀 결과 다운로드']),
        ('history', '📋', '분석 이력', 'DB 저장 이력 조회', '#8b5cf6', '#f5f3ff', ['등급별 필터 조회','기업명 검색','이력 엑셀 다운로드']),
    ]
    for col, (key, icon, title, subtitle, color, bg, features) in zip([c1,c2,c3,c4], feature_cards):
        with col:
            feat_html = ''.join([f"<div style='font-size:11px;color:#64748b;padding:4px 0;display:flex;align-items:center;gap:5px;border-bottom:1px solid #f1f5f9;'><span style='color:{color};font-weight:700;'>✓</span>{f}</div>" for f in features])
            st.markdown(f"""
            <div style='background:white;border:1px solid #e8ecf0;border-radius:14px;
                        padding:16px 20px;box-shadow:0 2px 8px rgba(0,0,0,0.05);margin-bottom:10px;
                        transition:all 0.2s;'>
                <div style='width:40px;height:40px;background:{bg};border-radius:10px;
                            display:flex;align-items:center;justify-content:center;
                            font-size:18px;margin-bottom:12px;'>
                    {icon}
                </div>
                <div style='font-size:15px;font-weight:800;color:#1e293b;margin-bottom:2px;'>{title}</div>
                <div style='font-size:11px;color:#94a3b8;margin-bottom:10px;'>{subtitle}</div>
                <div style='border-top:1px solid #f1f5f9;padding-top:8px;display:flex;flex-direction:column;gap:0;'>{feat_html}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"{title} 바로가기 →", key=f"home_{key}", use_container_width=True):
                st.session_state.page = key
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 대시보드
# ══════════════════════════════════════════════════════════════
elif st.session_state.page == 'dashboard':
    render_topbar("🏠 대시보드", "신속 현황 및 빠른 진단")

    st.markdown("<div style='padding:0 28px 20px 28px;'>", unsafe_allow_html=True)

    if db_ok:
        stats = cached_grade_stats()
        total = sum(stats.values())
        d_count = stats.get('D',0)
        c_count = stats.get('C',0)
    else:
        stats={'A':0,'B':0,'C':0,'D':0}; total=0; d_count=0; c_count=0

    k1,k2,k3,k4 = st.columns(4, gap="medium")
    with k1:
        st.markdown(f"<div class='kpi-card'><div class='kpi-label'><span>📊</span> 총 분석 기업</div><div class='kpi-value'>{total}<span style='font-size:14px;font-weight:400;color:#94a3b8;'>개사</span></div><div class='kpi-sub'>전체 분석 누적 건수</div></div>", unsafe_allow_html=True)
    with k2:
        st.markdown(f"<div class='kpi-card'><div class='kpi-label'><span style='color:#ef4444;'>🚨</span> 위험 기업 (D등급)</div><div class='kpi-value' style='color:#ef4444;'>{d_count}<span style='font-size:14px;font-weight:400;color:#94a3b8;'>개사</span></div><div class='kpi-sub'>즉각 구조조정 필요</div></div>", unsafe_allow_html=True)
    with k3:
        st.markdown(f"<div class='kpi-card'><div class='kpi-label'><span style='color:#f59e0b;'>⚠️</span> 주의 기업 (C등급)</div><div class='kpi-value' style='color:#f59e0b;'>{c_count}<span style='font-size:14px;font-weight:400;color:#94a3b8;'>개사</span></div><div class='kpi-sub'>부실 징후 조기 탐지</div></div>", unsafe_allow_html=True)
    with k4:
        if model_accuracy is not None:
            acc_display = f"{model_accuracy}<span style='font-size:14px;font-weight:400;'>%</span>"
            acc_sub = f"RandomForest · {model_accuracy_src} 기준"
        else:
            acc_display = "<span style='font-size:16px;color:#cbd5e1;'>N/A</span>"
            acc_sub = "정확도 정보 없음 (재학습 필요)"
        st.markdown(f"<div class='kpi-card'><div class='kpi-label'><span style='color:#3b82f6;'>🤖</span> AI 진단 정확도</div><div class='kpi-value' style='color:#3b82f6;'>{acc_display}</div><div class='kpi-sub'>{acc_sub}</div></div>", unsafe_allow_html=True)

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    left, right = st.columns([1.6, 1], gap="large")

    with left:
        st.markdown("<div class='card'><div class='card-title'>📊 DB 누적 등급 분포</div>", unsafe_allow_html=True)
        if total > 0:
            gc1,gc2,gc3,gc4 = st.columns(4, gap="small")
            for col,g in zip([gc1,gc2,gc3,gc4],['A','B','C','D']):
                cnt=stats[g]; pct=round(cnt/total*100,1)
                col.markdown(f"<div style='background:{grade_bgs[g]};border:1px solid {grade_colors[g]}30;border-radius:10px;padding:12px;text-align:center;'><div style='font-size:20px;font-weight:900;color:{grade_colors[g]};'>{g}</div><div style='font-size:18px;font-weight:800;color:#1e293b;margin:2px 0;'>{cnt}</div><div style='font-size:10px;color:#94a3b8;font-weight:600;'>{pct}%</div></div>", unsafe_allow_html=True)
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
            fig_d = px.bar(pd.DataFrame({'등급':['A','B','C','D'],'수':[stats[g] for g in ['A','B','C','D']]}), x='등급', y='수', color='등급', color_discrete_map=grade_colors, text='수')
            fig_d.update_traces(textposition='outside', marker_line_width=0)
            fig_d.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=200, showlegend=False, margin=dict(t=24,b=0,l=0,r=0), xaxis=dict(color='#94a3b8', title='', showgrid=False), yaxis=dict(color='#94a3b8', gridcolor='#f1f5f9', title=''), font=dict(color='#1e293b', size=11), bargap=0.4)
            st.plotly_chart(fig_d, use_container_width=True)
        else:
            st.markdown("<div style='text-align:center;padding:40px;color:#94a3b8;font-size:13px;'>분석 데이터가 없습니다.<br>개별 진단 또는 일괄 분석을 먼저 진행하세요.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if db_ok:
            rows = cached_history()
            if rows:
                hist_df = pd.DataFrame(rows).head(5)
                st.markdown("<div class='card'><div class='card-title'>📋 최근 분석 이력</div>", unsafe_allow_html=True)
                disp=['기업명','산업군','예측등급','건전성점수','분석일시']
                def cg(v): return f'color:{grade_colors.get(v,"#888")};font-weight:bold'
                st.dataframe(hist_df[disp].style.map(cg, subset=['예측등급']), use_container_width=True, hide_index=True)
                st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='card'><div class='card-title'><span style='background:#fef9c3;border-radius:6px;padding:2px 6px;font-size:12px;'>⚡</span> 빠른 진단</div><div style='font-size:11px;color:#94a3b8;margin-bottom:14px;'>핵심 수치 입력 후 즉시 등급 확인</div>", unsafe_allow_html=True)
        qrc=st.number_input("당기 매출액(만원)", min_value=0, value=50000, step=1000, key="qrc")
        qrp=st.number_input("전기 매출액(만원)", min_value=0, value=45000, step=1000, key="qrp")
        qni=st.number_input("당기순이익(만원)", value=5000, step=500, key="qni")
        qca=st.number_input("유동자산(만원)", min_value=0, value=30000, step=1000, key="qca")
        qcl=st.number_input("유동부채(만원)", min_value=0, value=15000, step=1000, key="qcl")
        qtl=st.number_input("부채총계(만원)", min_value=0, value=40000, step=1000, key="qtl")
        qeq=st.number_input("자본총계(만원)", min_value=1, value=60000, step=1000, key="qeq")
        if st.button("⚡ 즉시 진단", type="primary", use_container_width=True):
            if ai_model:
                qd,qcr,qnm,qrg=calc_ratios(qrc,qrp,qni,qca,qcl,qtl,qeq)
                qpred,qscore=predict_one(ai_model,qd,qcr,qnm,qrg)
                qgi=GRADE_INFO[qpred]
                st.markdown(f"<div style='background:{qgi['bg']};border:1.5px solid {qgi['color']}40;border-radius:12px;padding:18px;text-align:center;margin-top:14px;'><div style='font-size:50px;font-weight:900;color:{qgi['color']};line-height:1;'>{qgi['short']}</div><div style='font-size:12px;font-weight:700;color:{qgi['color']};margin-top:4px;'>{qgi['label']}</div><div style='font-size:22px;font-weight:800;color:#1e293b;margin-top:10px;'>{qscore}점 / 100점</div><div style='font-size:11px;color:#64748b;margin-top:6px;line-height:1.5;'>{qgi['desc']}</div></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 개별 진단
# ══════════════════════════════════════════════════════════════
elif st.session_state.page == 'individual':
    render_topbar("🔍 개별 진단", "기업 재무 수치를 입력하여 AI 등급을 분석합니다")

    st.markdown("<div style='padding:0 28px 20px 28px;'>", unsafe_allow_html=True)
    left_col, right_col = st.columns([1, 1.8], gap="large")

    def _load_saved_company():
        sel = st.session_state.get("ind_load_select")
        if not sel or sel == "직접 입력":
            return
        data = fetch_latest_by_name(sel)
        if not data:
            return
        st.session_state["ind_company_name"] = data.get("기업명") or ""
        st.session_state["ind_industry"] = data.get("산업군") or ""
        st.session_state["ind_rev_cur"] = int(data.get("당기매출액") or 0)
        st.session_state["ind_rev_prev"] = int(data.get("전기매출액") or 0)
        st.session_state["ind_net_inc"] = int(data.get("당기순이익") or 0)
        st.session_state["ind_cur_assets"] = int(data.get("유동자산") or 0)
        st.session_state["ind_cur_liab"] = int(data.get("유동부채") or 0)
        st.session_state["ind_tot_liab"] = int(data.get("부채총계") or 0)
        st.session_state["ind_equity"] = int(data.get("자본총계") or 1)

    with left_col:
        if db_ok and LOAD_AVAILABLE:
            st.markdown("<div class='card'><div class='card-title'>📂 저장된 기업 불러오기</div>", unsafe_allow_html=True)
            saved_names = fetch_company_names()
            if saved_names:
                st.selectbox(
                    "DB에 저장된 기업을 선택하면 아래 입력값이 자동으로 채워집니다",
                    ["직접 입력"] + saved_names,
                    key="ind_load_select",
                    on_change=_load_saved_company,
                )
            else:
                st.caption("아직 DB에 저장된 기업이 없습니다. 먼저 진단 후 저장해보세요.")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='card'><div class='card-title'>🏢 기업 정보</div>", unsafe_allow_html=True)
        company_name=st.text_input("기업명", placeholder="예: (주)가나제조", key="ind_company_name")
        industry=st.text_input("산업군", placeholder="예: 제조업", key="ind_industry")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='card'><div class='card-title'>💵 손익계산서</div>", unsafe_allow_html=True)
        rev_cur=st.number_input("당기 매출액(만원)", min_value=0, value=50000, step=1000, key="ind_rev_cur")
        rev_prev=st.number_input("전기 매출액(만원)", min_value=0, value=45000, step=1000, key="ind_rev_prev")
        net_inc=st.number_input("당기순이익(만원)", value=5000, step=500, key="ind_net_inc")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='card'><div class='card-title'>🛡️ 재무상태표</div>", unsafe_allow_html=True)
        cur_assets=st.number_input("유동자산(만원)", min_value=0, value=30000, step=1000, key="ind_cur_assets")
        cur_liab=st.number_input("유동부채(만원)", min_value=0, value=15000, step=1000, key="ind_cur_liab")
        tot_liab=st.number_input("부채총계(만원)", min_value=0, value=40000, step=1000, key="ind_tot_liab")
        equity=st.number_input("자본총계(만원)", min_value=1, value=60000, step=1000, key="ind_equity")
        st.markdown("</div>", unsafe_allow_html=True)

        analyze_btn=st.button("🔍 AI 재무 진단 시작", type="primary", use_container_width=True)
        if analyze_btn and ai_model:
            st.session_state.analysis_snapshot = {
                'company_name': company_name, 'industry': industry,
                'rev_cur': rev_cur, 'rev_prev': rev_prev, 'net_inc': net_inc,
                'cur_assets': cur_assets, 'cur_liab': cur_liab,
                'tot_liab': tot_liab, 'equity': equity,
            }

    with right_col:
        snap = st.session_state.get('analysis_snapshot')
        if snap and ai_model:
            company_name = snap['company_name']; industry = snap['industry']
            rev_cur = snap['rev_cur']; rev_prev = snap['rev_prev']; net_inc = snap['net_inc']
            cur_assets = snap['cur_assets']; cur_liab = snap['cur_liab']
            tot_liab = snap['tot_liab']; equity = snap['equity']
            dr,cr,nm,rg=calc_ratios(rev_cur,rev_prev,net_inc,cur_assets,cur_liab,tot_liab,equity)
            pred,score=predict_one(ai_model,dr,cr,nm,rg)
            gi=GRADE_INFO[pred]

            st.markdown(f"""
            <div style='background:{gi["bg"]};border:1.5px solid {gi["color"]}30;
                        border-radius:14px;padding:22px 24px;margin-bottom:16px;'>
                <div style='display:flex;justify-content:space-between;align-items:flex-start;'>
                    <div>
                        <div style='font-size:11px;color:#64748b;margin-bottom:5px;'>
                            {company_name or "분석 기업"} · <span style='color:#94a3b8;'>{industry or ""}</span>
                        </div>
                        <div style='font-size:11px;font-weight:600;color:#64748b;margin-bottom:6px;'>종합 재무 건전성 등급</div>
                        <div style='font-size:58px;font-weight:900;color:{gi["color"]};line-height:1;'>{gi["short"]}</div>
                        <div style='font-size:13px;font-weight:700;color:{gi["color"]};margin-top:5px;'>{gi["label"]}</div>
                    </div>
                    <div style='text-align:center;'>
                        <div style='width:90px;height:90px;background:white;
                                    border:3px solid {gi["color"]}40;border-radius:50%;
                                    display:flex;flex-direction:column;align-items:center;
                                    justify-content:center;box-shadow:0 4px 16px {gi["color"]}20;'>
                            <div style='font-size:24px;font-weight:900;color:{gi["color"]};'>{score}</div>
                            <div style='font-size:10px;color:#94a3b8;'>/ 100점</div>
                        </div>
                        <div style='font-size:10px;color:#64748b;margin-top:6px;'>건전성 점수</div>
                    </div>
                </div>
                <div style='margin-top:12px;padding-top:12px;border-top:1px solid {gi["color"]}20;
                            font-size:12px;color:#475569;line-height:1.6;'>{gi["desc"]}</div>
            </div>
            """, unsafe_allow_html=True)

            m1,m2,m3,m4=st.columns(4)
            m1.metric("🛡️ 부채비율", f"{dr:.1f}%"); m2.metric("💵 유동비율", f"{cr:.1f}%")
            m3.metric("💰 순이익률", f"{nm:.1f}%"); m4.metric("🚀 매출증가율", f"{rg:.1f}%")
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

            ch1,ch2=st.columns(2)
            with ch1:
                st.markdown("<div class='card'><div class='card-title'>📊 자산 비율</div>", unsafe_allow_html=True)
                fig_p=px.pie(pd.DataFrame({"항목":["자본","부채"],"금액":[equity,tot_liab]}), values="금액", names="항목", hole=0.55, color_discrete_sequence=[gi["color"],"#e2e8f0"])
                fig_p.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=190, margin=dict(t=0,b=0,l=0,r=0), legend=dict(font=dict(color='#1e293b',size=11)), font=dict(color='#1e293b'))
                st.plotly_chart(fig_p, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with ch2:
                st.markdown("<div class='card'><div class='card-title'>📈 주요 재무 비율</div>", unsafe_allow_html=True)
                radar_vals=[dr,cr,nm,rg]
                mn,mx=min(radar_vals),max(radar_vals)
                norm=[(v-mn)/(mx-mn)*100 if mx!=mn else 50 for v in radar_vals]
                labs=["부채비율","유동비율","순이익률","매출증가율"]
                fig_r=go.Figure()
                fig_r.add_trace(go.Scatterpolar(r=norm+[norm[0]], theta=labs+[labs[0]], fill='toself', fillcolor=hex_to_rgba(gi["color"], 0.25), line=dict(color=gi["color"], width=2)))
                fig_r.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,100],gridcolor='#e2e8f0'),bgcolor='rgba(0,0,0,0)'), paper_bgcolor='rgba(0,0,0,0)', height=190, showlegend=False, margin=dict(t=10,b=10,l=10,r=10), font=dict(color='#1e293b', size=10))
                st.plotly_chart(fig_r, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            ch3,ch4=st.columns(2)
            with ch3:
                st.markdown("<div class='card'><div class='card-title'>🤖 판단 가중치 지표</div>", unsafe_allow_html=True)
                try: imp=ai_model.feature_importances_
                except: imp=[0.45,0.25,0.20,0.10]
                imp_df=pd.DataFrame({"지표":["부채비율","유동비율","순이익률","매출증가율"],"기여도":imp}).sort_values("기여도",ascending=True)
                fig_i=px.bar(imp_df, x="기여도", y="지표", orientation='h', color="기여도", color_continuous_scale=["#dbeafe", gi["color"]])
                fig_i.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=190, showlegend=False, margin=dict(t=0,b=0,l=0,r=0), xaxis=dict(color='#94a3b8',gridcolor='#f1f5f9',title=''), yaxis=dict(color='#64748b',title=''), coloraxis_showscale=False, font=dict(color='#1e293b',size=10))
                st.plotly_chart(fig_i, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with ch4:
                opinion_map={
                    3: f"A등급으로 매우 건실한 재무 안정성을 보여주고 있습니다. 공격적인 스케일업 전략을 추진하기에 최적의 상태입니다.",
                    2: f"B등급으로 균형 잡힌 자산 구조를 유지 중입니다. 매출성장률({rg:.1f}%) 지속 관리를 권장합니다.",
                    1: f"C등급으로 부실 징후가 관측됩니다. 순이익률({nm:.1f}%) 구조 개선 및 단기 채무 상환 계획 재검토가 필요합니다.",
                    0: f"D등급으로 임계치를 초과한 고위험 상태입니다. 즉각적인 구조조정과 기업 회생 프로세스 검토를 권고합니다."
                }
                st.markdown(f"<div class='card'><div class='card-title'>💡 AI 핵심 의견</div><div style='font-size:12px;color:#374151;line-height:1.7;padding:2px 0;'>{opinion_map[pred]}</div><div style='margin-top:12px;padding-top:10px;border-top:1px solid #f1f5f9;'><div style='font-size:11px;font-weight:700;color:#94a3b8;margin-bottom:10px;'>🔮 What-If 시뮬레이션</div>", unsafe_allow_html=True)
                sr=st.slider("매출증가율 목표(%)", -30, 100, int(rg)+10, key=f"sr_{company_name}")
                sd=st.slider("부채 감축률(%)", 0, 50, 15, key=f"sd_{company_name}")
                sim_key = f"sim_result_{company_name}"
                if st.button("시뮬레이션 실행", use_container_width=True, key=f"sb_{company_name}"):
                    fp,fs=predict_one(ai_model,dr*(1-sd/100),cr,nm,float(sr))
                    st.session_state[sim_key] = (fp, fs)
                if sim_key in st.session_state:
                    fp, fs = st.session_state[sim_key]
                    fgi = GRADE_INFO[fp]
                    sf1, sf2 = st.columns(2)
                    sf1.metric("예상 점수", f"{fs}점", delta=f"{fs-score}점")
                    sf2.metric("예상 등급", fgi['short'])
                st.markdown("</div></div>", unsafe_allow_html=True)

            act1, act2 = st.columns(2)
            with act1:
                try:
                    pdf_bytes = generate_individual_report_pdf(company_name, industry, gi, score, dr, cr, nm, rg, opinion_map[pred])
                    st.download_button(
                        "📄 PDF 리포트 다운로드",
                        data=pdf_bytes,
                        file_name=f"재무진단리포트_{company_name or '기업'}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"pdf_{company_name}_{score}"
                    )
                except Exception as e:
                    st.error(f"⚠️ PDF 생성 오류: {e}")
            with act2:
                if db_ok:
                    if st.button("💾 DB 저장", use_container_width=True, key=f"btn_save_{company_name}_{score}"):
                        ok=save_result({"기업명":company_name,"산업군":industry,"당기매출액":int(rev_cur),"전기매출액":int(rev_prev),"당기순이익":int(net_inc),"유동자산":int(cur_assets),"유동부채":int(cur_liab),"부채총계":int(tot_liab),"자본총계":int(equity),"부채비율":round(dr,1),"유동비율":round(cr,1),"매출순이익률":round(nm,1),"매출증가율":round(rg,1),"예측등급":gi['short'],"건전성점수":score})
                        if ok:
                            cached_grade_stats.clear()
                            cached_history.clear()
                            st.success("✅ 저장 완료!")
                        else: st.error("❌ DB 저장 실패")
        else:
            st.markdown("""
            <div style='background:#f8fafc;border:2px dashed #e2e8f0;border-radius:14px;
                        padding:100px 40px;text-align:center;'>
                <div style='font-size:48px;'>🔍</div>
                <div style='font-size:15px;font-weight:600;color:#94a3b8;margin-top:16px;'>
                    왼쪽에서 재무 수치를 입력하고<br>진단 시작 버튼을 눌러주세요
                </div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 일괄 분석
# ══════════════════════════════════════════════════════════════
elif st.session_state.page == 'bulk':
    render_topbar("📂 일괄 분석", "CSV 또는 Excel 파일로 여러 기업을 한번에 분석합니다")

    st.markdown("<div style='padding:0 28px 20px 28px;'>", unsafe_allow_html=True)

    sample_df=pd.DataFrame([
        {"기업명":"(주)가나제조","산업군":"제조업","당기매출액":50000,"전기매출액":45000,"당기순이익":5000,"유동자산":30000,"유동부채":15000,"부채총계":40000,"자본총계":60000},
        {"기업명":"(주)나다유통","산업군":"유통도소매업","당기매출액":80000,"전기매출액":90000,"당기순이익":-2000,"유동자산":20000,"유동부채":25000,"부채총계":70000,"자본총계":30000}
    ])

    # 업로더 전체적인 너비를 좁혀 좌측으로 밀착시키면서 균형을 맞춤
    up1, up2 = st.columns([1.5, 1], gap="large")
    
    with up1:
        uploaded_file=st.file_uploader("📁 CSV/Excel 파일 업로드", type=["csv","xlsx","CSV"], label_visibility="visible")
    with up2:
        st.markdown("<div style='font-size:13px;font-weight:600;color:#1e293b;margin-bottom:6px;'>📥 양식 다운로드</div>", unsafe_allow_html=True)
        @st.cache_data
        def to_csv(df): return df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 샘플 양식", data=to_csv(sample_df), file_name="sample.csv", mime="text/csv", use_container_width=True)

    cols_info = list(zip(REQUIRED_COLS, ["기업 이름","산업군","당기 매출(만원)","전기 매출(만원)","당기순이익(만원)","유동자산(만원)","유동부채(만원)","부채총계(만원)","자본총계(만원)"]))
    rows_html = "".join([f"<tr><td style='padding:6px 12px;font-size:12px;color:#1e293b;border-bottom:1px solid #f1f5f9;font-weight:600;'>{c}</td><td style='padding:6px 12px;font-size:12px;color:#64748b;border-bottom:1px solid #f1f5f9;'>{d}</td></tr>" for c,d in cols_info])
    st.markdown(f"""
    <details style='background:white;border:1px solid #e2e8f0;border-radius:10px;padding:0;margin-bottom:16px;overflow:hidden;'>
        <summary style='padding:11px 16px;font-size:13px;font-weight:600;color:#1e293b;cursor:pointer;list-style:none;display:flex;align-items:center;gap:6px;'>
            <span>▶</span><span>📋 필수 컬럼 확인</span>
        </summary>
        <table style='width:100%;border-collapse:collapse;'>
            <thead><tr>
                <th style='padding:8px 12px;font-size:11px;color:#94a3b8;font-weight:600;text-align:left;background:#f8fafc;border-bottom:2px solid #e8ecf0;'>컬럼명</th>
                <th style='padding:8px 12px;font-size:11px;color:#94a3b8;font-weight:600;text-align:left;background:#f8fafc;border-bottom:2px solid #e8ecf0;'>설명</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </details>
    """, unsafe_allow_html=True)

    if uploaded_file is not None and ai_model is not None:
        try:
            if uploaded_file.name.lower().endswith('.csv'):
                try: df_raw=pd.read_csv(uploaded_file,encoding='utf-8-sig')
                except: df_raw=pd.read_csv(uploaded_file,encoding='euc-kr')
            else: df_raw=pd.read_excel(uploaded_file)

            df_raw.columns=df_raw.columns.str.strip()
            df_raw=df_raw.rename(columns={"회사명":"기업명","업종":"산업군"})
            for col in ['당기매출액','전기매출액','당기순이익','유동자산','유동부채','부채총계','자본총계']:
                if col in df_raw.columns:
                    df_raw[col]=df_raw[col].astype(str).str.replace('만','',regex=False).str.replace(',','',regex=False).str.strip().replace('','0').astype(float)

            missing=[c for c in REQUIRED_COLS if c not in df_raw.columns]
            if missing: st.error(f"⚠️ 컬럼 없음: {', '.join(missing)}"); st.stop()
            st.success(f"✅ {len(df_raw)}개 기업 업로드 완료!")

            results=[]
            for _,row in df_raw.iterrows():
                d,cr,nm,rg=calc_ratios(row['당기매출액'],row['전기매출액'],row['당기순이익'],row['유동자산'],row['유동부채'],row['부채총계'],row['자본총계'])
                pred,score=predict_one(ai_model,d,cr,nm,rg)
                gi=GRADE_INFO[pred]
                results.append({"기업명":row['기업명'],"산업군":row['산업군'],"등급":gi['short'],"건전성 점수":score,"부채비율":round(d,1),"유동비율":round(cr,1),"매출순이익률":round(nm,1),"매출증가율":round(rg,1),"_pred":pred,"_rev_cur":row['당기매출액'],"_rev_prev":row['전기매출액'],"_net_inc":row['당기순이익'],"_cur_assets":row['유동자산'],"_cur_liab":row['유동부채'],"_tot_liab":row['부채총계'],"_equity":row['자본총계']})

            result_df=pd.DataFrame(results)

            c_grade_df = result_df[result_df['등급'] == 'C']
            if len(c_grade_df) > 0: st.warning(f"⚠️ C등급 ({len(c_grade_df)}개사): {', '.join(c_grade_df['기업명'].tolist())}")

            d_grade_df = result_df[result_df['등급'] == 'D']
            if len(d_grade_df) > 0: st.error(f"🚨 D등급 ({len(d_grade_df)}개사): {', '.join(d_grade_df['기업명'].tolist())}")

            bl,br=st.columns([1.2,1], gap="large")
            with bl:
                st.markdown("<div class='card'><div class='card-title'>📊 등급 분포</div>", unsafe_allow_html=True)
                grade_counts=result_df['등급'].value_counts().reindex(['A','B','C','D'],fill_value=0)
                gc1,gc2,gc3,gc4=st.columns(4)
                for col,(g,cnt) in zip([gc1,gc2,gc3,gc4],grade_counts.items()):
                    pct=round(cnt/len(result_df)*100,1) if len(result_df)>0 else 0
                    col.markdown(f"<div style='background:{grade_bgs[g]};border:1px solid {grade_colors[g]}30;border-radius:10px;padding:10px;text-align:center;'><div style='font-size:18px;font-weight:900;color:{grade_colors[g]};'>{g}</div><div style='font-size:16px;font-weight:700;color:#1e293b;'>{cnt}</div><div style='font-size:10px;color:#94a3b8;'>{pct}%</div></div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with br:
                if len(result_df)>1:
                    st.markdown("<div class='card'><div class='card-title'>🕸️ 재무 지표 비교</div>", unsafe_allow_html=True)
                    rcols=['부채비율','유동비율','매출순이익률','매출증가율']
                    rdf=result_df[rcols].copy()
                    for c in rcols:
                        mn,mx=rdf[c].min(),rdf[c].max()
                        rdf[c]=(rdf[c]-mn)/(mx-mn)*100 if mx!=mn else 50
                    fig_r=go.Figure()
                    for i,r in result_df.iterrows():
                        vals=[rdf.loc[i,c] for c in rcols]+[rdf.loc[i,rcols[0]]]
                        fig_r.add_trace(go.Scatterpolar(r=vals,theta=rcols+[rcols[0]],fill='toself',name=r['기업명'],opacity=0.5))
                    fig_r.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,100],gridcolor='#e2e8f0'),bgcolor='rgba(0,0,0,0)'),paper_bgcolor='rgba(0,0,0,0)',height=260,showlegend=True,margin=dict(t=10,b=10,l=10,r=10),font=dict(color='#1e293b',size=10),legend=dict(font=dict(size=10)))
                    st.plotly_chart(fig_r, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='card'><div class='card-title'>📋 일괄 분석 결과 테이블</div>", unsafe_allow_html=True)
            dcols=['기업명','산업군','등급','건전성 점수','부채비율','유동비율','매출순이익률','매출증가율']
            def cg(v): return f'color:{grade_colors.get(v,"#888")};font-weight:bold'
            st.dataframe(result_df[dcols].style.map(cg,subset=['등급']).format({'건전성 점수':'{:.0f}점','부채비율':'{:.1f}%','유동비율':'{:.1f}%','매출순이익률':'{:.1f}%','매출증가율':'{:.1f}%'}),use_container_width=True,hide_index=True)
            dl1,dl2=st.columns(2)
            with dl1:
                out=io.BytesIO()
                with pd.ExcelWriter(out,engine='openpyxl') as w: result_df[dcols].to_excel(w,index=False,sheet_name='분석결과')
                st.download_button("📥 엑셀 다운로드",data=out.getvalue(),file_name="재무진단결과.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
            with dl2:
                if db_ok:
                    if st.button("💾 전체 DB 저장",type="primary",use_container_width=True):
                        bulk_rows=[{"기업명":r['기업명'],"산업군":r['산업군'],"당기매출액":int(r['_rev_cur']),"전기매출액":int(r['_rev_prev']),"당기순이익":int(r['_net_inc']),"유동자산":int(r['_cur_assets']),"유동부채":int(r['_cur_liab']),"부채총계":int(r['_tot_liab']),"자본총계":int(r['_equity']),"부채비율":r['부채비율'],"유동비율":r['유동비율'],"매출순이익률":r['매출순이익률'],"매출증가율":r['매출증가율'],"예측등급":r['등급'],"건전성점수":r['건전성 점수']} for _,r in result_df.iterrows()]
                        saved,failed=0,0
                        for row in bulk_rows:
                            ok=save_result(row)
                            if ok: saved+=1
                            else: failed+=1
                        if saved > 0: cached_grade_stats.clear(); cached_history.clear()
                        st.success(f"✅ {saved}개 저장"+(f" | ❌ {failed}개 실패" if failed else ""))
            st.markdown("</div>", unsafe_allow_html=True)

            # ── 추가된 기업별 상세 리포트 블록 ──
            st.markdown("<div class='card'><div class='card-title'>🔍 기업별 상세 리포트</div>",unsafe_allow_html=True)
            selected = st.selectbox("상세 분석할 기업을 선택하세요", result_df['기업명'].tolist(), label_visibility="collapsed")
            r = result_df[result_df['기업명']==selected].iloc[0]
            
            d2,cr2,nm2,rg2=calc_ratios(r['_rev_cur'],r['_rev_prev'],r['_net_inc'],r['_cur_assets'],r['_cur_liab'],r['_tot_liab'],r['_equity'])
            pred2,score2=predict_one(ai_model,d2,cr2,nm2,rg2)
            gi2=GRADE_INFO[pred2]
            
            st.markdown(f"""
            <div style='background:{gi2['bg']};border:1px solid {gi2['color']}30;border-radius:12px;padding:18px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;'>
                <div>
                    <div style='font-size:17px;font-weight:700;color:#1a2236;'>{r['기업명']}</div>
                    <div style='font-size:12px;color:#6b7a99;'>{r['산업군']}</div>
                </div>
                <div style='text-align:right;'>
                    <div style='font-size:44px;font-weight:900;color:{gi2['color']};line-height:1;'>{gi2['short']}</div>
                    <div style='font-size:12px;color:{gi2['color']};'>{score2}점 / 100점</div>
                </div>
            </div>
            """,unsafe_allow_html=True)
            
            dm1,dm2,dm3,dm4=st.columns(4)
            dm1.metric("🛡️ 부채비율",f"{d2:.1f}%")
            dm2.metric("💵 유동비율",f"{cr2:.1f}%")
            dm3.metric("💰 순이익률",f"{nm2:.1f}%")
            dm4.metric("🚀 매출증가율",f"{rg2:.1f}%")
            st.markdown("</div>",unsafe_allow_html=True)
            # ─────────────────────────────────────

        except Exception as e:
            st.error(f"⚠️ 오류: {e}")
    else:
        st.markdown("<div style='background:#f8fafc;border:2px dashed #e2e8f0;border-radius:14px;padding:60px;text-align:center;margin-top:8px;'><div style='font-size:48px;'>📂</div><div style='font-size:15px;font-weight:600;color:#94a3b8;margin-top:16px;'>CSV 또는 Excel 파일을 업로드하세요</div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# 분석 이력
# ══════════════════════════════════════════════════════════════
elif st.session_state.page == 'history':
    render_topbar("📋 분석 이력", "DB에 저장된 분석 결과를 조회합니다")

    st.markdown("<div style='padding:0 28px 20px 28px;'>", unsafe_allow_html=True)

    if not db_ok:
        st.warning("⚠️ DB 연결이 필요합니다.")
    else:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        f1,f2,f3=st.columns([1,2,1])
        with f1: gf=st.selectbox("등급 필터",["전체","A","B","C","D"])
        with f2: kw=st.text_input("기업명 검색",placeholder="기업명 입력...")
        with f3:
            st.markdown("<div style='height:26px;'></div>", unsafe_allow_html=True)
            sb=st.button("🔍 조회",use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # 조회 버튼을 눌렀을 때만 새로 검색하고, 이후 재실행(삭제/그래프 선택)에도
        # 결과가 사라지지 않도록 세션 상태에 저장해둔다.
        if sb:
            st.session_state['history_query'] = {"grade_filter": gf if gf!="전체" else None, "keyword": kw if kw else None}
            st.session_state.pop('history_rows', None)

        if 'history_query' in st.session_state:
            if 'history_rows' not in st.session_state:
                q = st.session_state['history_query']
                st.session_state['history_rows'] = cached_history(grade_filter=q["grade_filter"], keyword=q["keyword"])
            rows = st.session_state['history_rows']

            if rows:
                hist_df=pd.DataFrame(rows)
                stats2=cached_grade_stats()
                st.markdown("<div class='card'><div class='card-title'>📊 DB 누적 현황</div>", unsafe_allow_html=True)
                s1,s2,s3,s4=st.columns(4)
                for col,g in zip([s1,s2,s3,s4],['A','B','C','D']):
                    col.markdown(f"<div style='background:{grade_bgs[g]};border:1px solid {grade_colors[g]}30;border-radius:10px;padding:12px;text-align:center;'><div style='font-size:20px;font-weight:900;color:{grade_colors[g]};'>{g}</div><div style='font-size:16px;font-weight:700;color:#1e293b;'>{stats2[g]}개사</div></div>",unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown(f"<div class='card'><div class='card-title'>📋 조회 결과 ({len(hist_df)}건)</div>", unsafe_allow_html=True)
                disp=['기업명','산업군','예측등급','건전성점수','부채비율','유동비율','매출순이익률','매출증가율','분석일시']
                def cg2(v): return f'color:{grade_colors.get(v,"#888")};font-weight:bold'
                st.dataframe(hist_df[disp].style.map(cg2,subset=['예측등급']).format({'건전성점수':'{:.0f}','부채비율':'{:.1f}%','유동비율':'{:.1f}%','매출순이익률':'{:.1f}%','매출증가율':'{:.1f}%'}),use_container_width=True,hide_index=True)
                out2=io.BytesIO()
                with pd.ExcelWriter(out2,engine='openpyxl') as w: hist_df[disp].to_excel(w,index=False,sheet_name='분석이력')
                st.download_button("📥 이력 다운로드",data=out2.getvalue(),file_name="분석이력.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                st.markdown("</div>", unsafe_allow_html=True)

                # ── 기업별 등급 변동 추이 ────────────────────────
                st.markdown("<div class='card'><div class='card-title'>📈 기업별 등급 변동 추이</div>", unsafe_allow_html=True)
                company_options = sorted(hist_df['기업명'].unique().tolist())
                trend_company = st.selectbox("추이를 확인할 기업 선택", company_options, key="trend_company_select")
                trend_rows = cached_history(grade_filter=None, keyword=trend_company)
                trend_rows = [r for r in trend_rows if r['기업명'] == trend_company]
                if len(trend_rows) < 2:
                    st.info(f"'{trend_company}'은(는) 진단 이력이 {len(trend_rows)}건뿐이라 추이를 표시할 수 없습니다. (2건 이상부터 표시)")
                else:
                    trend_df = pd.DataFrame(trend_rows).sort_values('분석일시')
                    fig_t = go.Figure()
                    fig_t.add_trace(go.Scatter(
                        x=trend_df['분석일시'], y=trend_df['건전성점수'],
                        mode='lines+markers',
                        line=dict(color='#3b82f6', width=2),
                        marker=dict(size=9, color=[grade_colors.get(g,'#3b82f6') for g in trend_df['예측등급']]),
                        text=trend_df['예측등급'], hovertemplate='%{x}<br>점수: %{y}점 (%{text}등급)<extra></extra>'
                    ))
                    fig_t.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=220,
                                         margin=dict(t=10,b=0,l=0,r=0),
                                         xaxis=dict(color='#94a3b8', gridcolor='#f1f5f9', title=''),
                                         yaxis=dict(color='#94a3b8', gridcolor='#f1f5f9', title='건전성 점수', range=[0,100]),
                                         font=dict(color='#1e293b', size=11))
                    st.plotly_chart(fig_t, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

                # ── 이력 삭제 ────────────────────────────────────
                if DELETE_AVAILABLE:
                    st.markdown("<div class='card'><div class='card-title'>🗑️ 이력 삭제</div>", unsafe_allow_html=True)
                    id_label_map = {f"{r['기업명']} · {r['분석일시']} · {r['예측등급']}등급": r['id'] for r in rows}
                    selected_labels = st.multiselect("삭제할 항목을 선택하세요", list(id_label_map.keys()), key="delete_select")
                    if selected_labels:
                        if st.button(f"🗑️ 선택한 {len(selected_labels)}건 삭제", key="delete_confirm_btn"):
                            ids_to_delete = [id_label_map[lab] for lab in selected_labels]
                            deleted = delete_history_bulk(ids_to_delete)
                            if deleted > 0:
                                cached_grade_stats.clear()
                                cached_history.clear()
                                st.session_state.pop('history_rows', None)
                                st.success(f"✅ {deleted}건 삭제 완료!")
                                st.rerun()
                            else:
                                st.error("❌ 삭제 실패")
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("조회된 데이터가 없습니다.")
    st.markdown("</div>", unsafe_allow_html=True)