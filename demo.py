"""
demo.py - 샘플 데이터로 전체 파이프라인 테스트
Selenium/Chrome 없이도 3대 사이트 통합 구조의 결과물을 확인할 수 있습니다.
"""

import pandas as pd
import random
from datetime import datetime, timedelta
from sentiment import SentimentAnalyzer
from visualizer import DashboardVisualizer
from exporter import DataExporter

SAMPLE_TITLES = [
    # 긍정
    "삼성전자, 2분기 영업이익 급등…반도체 흑자 전환 성공",
    "코스피 2600 돌파…외국인 매수세 강세 지속",
    "현대차, 글로벌 전기차 판매 1위 달성…성장세 가속",
    "네이버 AI 신사업 수주 잇달아…주가 상한가",
    "LG에너지솔루션 신고가 경신…수주 잔고 급증",
    "삼성 반도체 수출 30% 증가…무역수지 개선",
    "SK하이닉스, HBM 독점 공급 계약 타결",
    "현대重, 친환경 선박 수주 잇따라 성장 가속화",
    "포스코, 2차전지 소재 투자 확대로 유망주 선정",
    "카카오 콘텐츠 부문 호조…연간 흑자 전환 기대",
    # 부정
    "삼성전자 주가 급락…미중 갈등 여파 충격",
    "코스피 3% 하락…글로벌 긴축 공포 재부각",
    "부동산 PF 위기…건설사 파산 우려 현실화",
    "원달러 환율 폭등…외환시장 불안 심화",
    "국내 수출 감소세 지속…제조업 침체 우려",
    "가계부채 급증…금융당국 규제 강화 경고",
    "대기업 실적 쇼크…3분기 영업이익 대폭 감소",
    "IT 기업 대규모 구조조정…고용 불안 확대",
    "반도체 수요 부진 지속…업황 악화 우려 증가",
    "테슬라 대규모 리콜…전기차 결함 논란 확대",
    # 중립
    "한국은행, 기준금리 동결 결정",
    "금융위, 내년 금융정책 방향 발표",
    "삼성전자, 3분기 실적 발표 예정",
    "현대차, 신모델 출시 계획 공개",
    "LG전자 신사업 전략 설명회 개최",
]

SOURCES = ["naver", "daum", "hankyung"]
PRESS_BY_SOURCE = {
    "naver":    ["조선일보", "중앙일보", "동아일보", "한국경제", "연합뉴스", "MBC"],
    "daum":     ["이데일리", "머니투데이", "헤럴드경제", "뉴시스", "뉴스1"],
    "hankyung": ["한국경제", "한경닷컴"],
}


def generate_sample_data(keyword: str, n_per_site: int = 10) -> pd.DataFrame:
    random.seed(42)
    rows = []
    base = datetime.now()

    for source in SOURCES:
        for i in range(n_per_site):
            title = random.choice(SAMPLE_TITLES)
            if keyword not in title and random.random() > 0.4:
                title = title.replace("삼성전자", keyword)
            rows.append({
                "title":      title,
                "press":      random.choice(PRESS_BY_SOURCE[source]),
                "pub_time":   (base - timedelta(hours=random.randint(1, 48))).strftime("%Y.%m.%d %H:%M"),
                "url":        f"https://{source}.example.com/article/{i+1000}",
                "source":     source,
                "crawled_at": base.strftime("%Y-%m-%d %H:%M:%S"),
            })
    return pd.DataFrame(rows)


def run_demo(keyword: str = "삼성전자"):
    print("=" * 60)
    print("  🧪 데모 모드 — 샘플 데이터로 전체 파이프라인 실행")
    print(f"  키워드: [{keyword}]")
    print("=" * 60)

    # STEP 1
    print("\n[STEP 1] 📦 샘플 데이터 생성 (사이트별 10건 × 3)")
    df = generate_sample_data(keyword, n_per_site=10)
    print(f"  ✅ 총 {len(df)}건 생성")
    for src, cnt in df["source"].value_counts().items():
        label = {"naver": "네이버", "daum": "다음", "hankyung": "한국경제"}[src]
        print(f"     {label:6s}: {cnt}건")

    # STEP 2
    print("\n[STEP 2] 🧠 감성 분석")
    analyzer = SentimentAnalyzer()
    df = analyzer.analyze(df)
    stats = analyzer.get_statistics(df)
    print(f"  긍정: {stats['positive']}건 | 부정: {stats['negative']}건 | 중립: {stats['neutral']}건")
    print(f"  평균 감성 점수: {stats['avg_score']:+.3f}")

    # 사이트별 감성 분포
    print("\n  📊 사이트별 감성 분포:")
    site_labels = {"naver": "네이버", "daum": "다음", "hankyung": "한국경제"}
    for src in SOURCES:
        sub = df[df["source"] == src]["sentiment"].value_counts()
        pos = sub.get("긍정", 0)
        neg = sub.get("부정", 0)
        neu = sub.get("중립", 0)
        avg = df[df["source"] == src]["score"].mean()
        print(f"     {site_labels[src]:6s} | 긍정:{pos} 부정:{neg} 중립:{neu} | 평균:{avg:+.2f}")

    # STEP 3
    print("\n[STEP 3] 📊 대시보드 생성")
    viz = DashboardVisualizer(keyword=keyword)
    img = viz.create_dashboard(df)
    print(f"  ✅ {img}")

    # STEP 4
    print("\n[STEP 4] 📂 엑셀 저장")
    exp = DataExporter(keyword=keyword)
    xlsx = exp.export(df)
    print(f"  ✅ {xlsx}")

    print("\n" + "=" * 60)
    print("  🎉 데모 완료! output/ 폴더를 확인하세요.")
    print("=" * 60)
    return df


if __name__ == "__main__":
    KEYWORD = "삼성전자"
    df = run_demo(keyword=KEYWORD)

    print("\n📋 분석 결과 미리보기 (상위 6건):")
    cols = ["source", "title", "score", "sentiment"]
    print(df[cols].head(6).to_string(index=False))
