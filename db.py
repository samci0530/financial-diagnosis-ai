import os
import sqlite3
from sqlite3 import Error
from datetime import datetime, timezone, timedelta

# ── SQLite 파일 위치 ────────────────────────────────────────
# app.py와 같은 폴더에 data.db 파일로 저장됩니다.
# (클라우드 계정/인터넷 연결 없이 로컬 파일로 동작 — 팀원과 공유하려면
#  이 data.db 파일을 프로젝트 폴더째로 같이 전달하면 됩니다.)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.db")

KST = timezone(timedelta(hours=9))

def _now_kst():
    """한국 표준시(KST) 기준 현재 시각 문자열 (컴퓨터 시간대와 무관하게 항상 KST)"""
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

def get_conn():
    """SQLite 커넥션 반환 (파일이 없으면 자동 생성됨)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 딕셔너리처럼 컬럼명으로 접근 가능
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

# ── 테이블 생성 (최초 1회만 실행, 이후엔 있으면 그냥 통과) ─────
def init_db():
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_history (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                기업명        TEXT,
                산업군        TEXT,
                당기매출액    INTEGER,
                전기매출액    INTEGER,
                당기순이익    INTEGER,
                유동자산      INTEGER,
                유동부채      INTEGER,
                부채총계      INTEGER,
                자본총계      INTEGER,
                부채비율      REAL,
                유동비율      REAL,
                매출순이익률  REAL,
                매출증가율    REAL,
                예측등급      TEXT,
                건전성점수    INTEGER,
                분석일시      TEXT,
                UNIQUE (기업명, 당기매출액, 전기매출액, 당기순이익)
            );
        """)
        conn.commit()
    except Error as e:
        print(f"[DB] 테이블 생성 오류: {e}")
    finally:
        if conn:
            conn.close()

# ── 단건 저장 (upsert) ──────────────────────────────────────
_UPSERT_SQL = """
    INSERT INTO analysis_history
      (기업명, 산업군, 당기매출액, 전기매출액, 당기순이익,
       유동자산, 유동부채, 부채총계, 자본총계,
       부채비율, 유동비율, 매출순이익률, 매출증가율,
       예측등급, 건전성점수, 분석일시)
    VALUES
      (:기업명, :산업군, :당기매출액, :전기매출액, :당기순이익,
       :유동자산, :유동부채, :부채총계, :자본총계,
       :부채비율, :유동비율, :매출순이익률, :매출증가율,
       :예측등급, :건전성점수, :분석일시)
    ON CONFLICT(기업명, 당기매출액, 전기매출액, 당기순이익) DO UPDATE SET
      산업군       = excluded.산업군,
      유동자산     = excluded.유동자산,
      유동부채     = excluded.유동부채,
      부채총계     = excluded.부채총계,
      자본총계     = excluded.자본총계,
      부채비율     = excluded.부채비율,
      유동비율     = excluded.유동비율,
      매출순이익률 = excluded.매출순이익률,
      매출증가율   = excluded.매출증가율,
      예측등급     = excluded.예측등급,
      건전성점수   = excluded.건전성점수,
      분석일시     = excluded.분석일시
"""

def save_result(row: dict):
    """단건 upsert"""
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        payload = dict(row)
        payload["분석일시"] = _now_kst()
        cursor.execute(_UPSERT_SQL, payload)
        conn.commit()
        return True
    except Error as e:
        print(f"[DB] 저장 오류: {e}")
        return False
    finally:
        if conn:
            conn.close()

# ── 일괄 저장 ───────────────────────────────────────────────
def save_bulk(rows: list):
    """
    여러 기업을 한 번의 연결로 일괄 upsert
    반환: (성공 수, 실패 수)
    """
    if not rows:
        return 0, 0
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        now = _now_kst()
        payloads = []
        for r in rows:
            p = dict(r)
            p["분석일시"] = now
            payloads.append(p)
        cursor.executemany(_UPSERT_SQL, payloads)
        conn.commit()
        return len(rows), 0
    except Error as e:
        print(f"[DB] 일괄 저장 오류: {e}")
        return 0, len(rows)
    finally:
        if conn:
            conn.close()

# ── 이력 조회 ───────────────────────────────────────────────
def fetch_history(grade_filter=None, keyword=None):
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        conditions, params = [], []
        if grade_filter and grade_filter != "전체":
            conditions.append("예측등급 = ?"); params.append(grade_filter)
        if keyword:
            conditions.append("기업명 LIKE ?"); params.append(f"%{keyword}%")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"""
            SELECT id, 기업명, 산업군, 예측등급, 건전성점수,
                   부채비율, 유동비율, 매출순이익률, 매출증가율,
                   strftime('%Y-%m-%d %H:%M', 분석일시) AS 분석일시
            FROM analysis_history
            {where}
            ORDER BY 분석일시 DESC
            LIMIT 200
        """
        cursor.execute(sql, params)
        return [dict(r) for r in cursor.fetchall()]
    except Error as e:
        print(f"[DB] 조회 오류: {e}")
        return []
    finally:
        if conn:
            conn.close()

# ── 등급별 통계 ─────────────────────────────────────────────
def fetch_grade_stats():
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT 예측등급, COUNT(*) AS cnt FROM analysis_history GROUP BY 예측등급")
        rows = cursor.fetchall()
        stats = {"A": 0, "B": 0, "C": 0, "D": 0}
        for r in rows:
            if r["예측등급"] in stats:
                stats[r["예측등급"]] = r["cnt"]
        return stats
    except Error as e:
        print(f"[DB] 통계 조회 오류: {e}")
        return {"A": 0, "B": 0, "C": 0, "D": 0}
    finally:
        if conn:
            conn.close()

# ── 이력 삭제 ───────────────────────────────────────────────
def delete_history(record_id):
    """id로 특정 이력 1건 삭제"""
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analysis_history WHERE id = ?", (record_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Error as e:
        print(f"[DB] 삭제 오류: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_history_bulk(record_ids: list):
    """여러 건 한 번에 삭제, 반환: 삭제된 행 수"""
    if not record_ids:
        return 0
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        fmt = ",".join(["?"] * len(record_ids))
        cursor.execute(f"DELETE FROM analysis_history WHERE id IN ({fmt})", record_ids)
        conn.commit()
        return cursor.rowcount
    except Error as e:
        print(f"[DB] 일괄 삭제 오류: {e}")
        return 0
    finally:
        if conn:
            conn.close()

# ── 저장된 기업 목록 / 최신 데이터 조회 (개별진단 불러오기용) ──
def fetch_company_names():
    """DB에 저장된 기업명 목록 (중복 제거, 가나다순)"""
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT 기업명 FROM analysis_history ORDER BY 기업명")
        return [r["기업명"] for r in cursor.fetchall()]
    except Error as e:
        print(f"[DB] 기업목록 조회 오류: {e}")
        return []
    finally:
        if conn:
            conn.close()

def fetch_latest_by_name(company_name):
    """특정 기업의 가장 최근 저장 데이터 1건 (원본 재무수치 포함) 반환"""
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM analysis_history WHERE 기업명 = ? ORDER BY 분석일시 DESC LIMIT 1",
            (company_name,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    except Error as e:
        print(f"[DB] 기업 데이터 조회 오류: {e}")
        return None
    finally:
        if conn:
            conn.close()

# ── 연결 테스트 ─────────────────────────────────────────────
def test_connection():
    try:
        conn = get_conn()
        conn.close()
        return True
    except Error:
        return False
