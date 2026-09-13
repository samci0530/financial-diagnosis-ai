import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib

# ── 1. 데이터 로드 ──────────────────────────────────────────
df = pd.read_csv('/mnt/user-data/uploads/기업재무_통합데이터.CSV', encoding='utf-8-sig')

def calc_ratios(rc, rp, ni, ca, cl, tl, eq):
    dr = (tl/eq)*100 if eq > 0 else 0
    cr = (ca/cl)*100 if cl > 0 else 0
    nm = (ni/rc)*100 if rc > 0 else 0
    rg = ((rc-rp)/rp)*100 if rp > 0 else 0
    return dr, cr, nm, rg

ratios = df.apply(lambda r: calc_ratios(r['당기매출액'], r['전기매출액'], r['당기순이익'],
                                          r['유동자산'], r['유동부채'], r['부채총계'], r['자본총계']), axis=1)
df[['부채비율', '유동비율', '순이익률', '매출증가율']] = pd.DataFrame(ratios.tolist(), index=df.index)

# ── 2. 등급(A/B/C/D) 라벨링 — 가중 종합점수 기준 4분위 분류 ──
# 부채비율은 낮을수록 좋음(역방향), 나머지 3개는 높을수록 좋음
z = lambda s: (s - s.mean()) / s.std()
composite = (
    -0.45 * z(df['부채비율']) +
     0.25 * z(df['유동비율']) +
     0.20 * z(df['순이익률']) +
     0.10 * z(df['매출증가율'])
)
df['종합점수'] = composite
# 4분위: 상위 25% = 3(A), ... 하위 25% = 0(D)
df['등급라벨'] = pd.qcut(df['종합점수'], 4, labels=[0, 1, 2, 3]).astype(int)

print("등급 분포:")
print(df['등급라벨'].value_counts().sort_index())
print()

# ── 3. 모델 학습 (oob_score=True로 실제 정확도 확보) ────────
X = df[['부채비율', '유동비율', '순이익률', '매출증가율']].values
y = df['등급라벨'].values

model = RandomForestClassifier(
    n_estimators=50,
    oob_score=True,
    bootstrap=True,
    random_state=42,
    class_weight='balanced'
)
model.fit(X, y)

print(f"OOB 정확도: {model.oob_score_*100:.1f}%")
print(f"클래스: {model.classes_}")
print(f"피처 중요도: {dict(zip(['부채비율','유동비율','순이익률','매출증가율'], model.feature_importances_.round(3)))}")

joblib.dump(model, '/home/claude/model_new.pkl')
df.to_csv('/home/claude/labeled_companies.csv', index=False, encoding='utf-8-sig')
print("\n저장 완료: model_new.pkl, labeled_companies.csv")
