"""
main.py - 전체 파이프라인 진입점
Selenium 기반 3대 뉴스 사이트 통합 크롤링 → 감성 분석 → 시각화 → 엑셀 저장
"""

from crawler import MultiSiteCrawler
from sentiment import SentimentAnalyzer
from visualizer import DashboardVisualizer
from exporter import DataExporter
from datetime import datetime


def run_pipeline(keyword: str, pages_per_site: int = 3,
                 sites: list = None):
    """
    Args:
        keyword:        검색 키워드
        pages_per_site: 사이트당 수집 페이지 수
        sites:          수집 사이트 목록 (None=전체)
                        예: ["naver", "hankyung"]
    """
    print("=" * 60)
    print(f"  📰 News Sentiment Insight Dashboard")
    print(f"  키워드: [{keyword}] | 사이트당 {pages_per_site}p")
    print(f"  시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # STEP 1: 멀티사이트 크롤링
    print("\n[STEP 1] 🔍 3대 뉴스 사이트 크롤링 중...")
    crawler = MultiSiteCrawler(sites=sites)
    df = crawler.crawl_to_df(keyword=keyword, pages_per_site=pages_per_site)

    if df.empty:
        print("  ❌ 수집된 데이터가 없습니다.")
        return

    print(f"\n  📊 사이트별 수집 현황:")
    for site, count in df["source"].value_counts().items():
        print(f"     {site}: {count}건")
    print(f"  합계: {len(df)}건")

    # STEP 2: 감성 분석
    print("\n[STEP 2] 🧠 감성 점수 산출 중...")
    analyzer = SentimentAnalyzer()
    df = analyzer.analyze(df)
    stats = analyzer.get_statistics(df)
    print(f"  긍정: {stats['positive']}건({stats['pos_ratio']}%)"
          f" | 부정: {stats['negative']}건({stats['neg_ratio']}%)"
          f" | 평균점수: {stats['avg_score']:+}")

    # STEP 3: 대시보드 시각화
    print("\n[STEP 3] 📊 대시보드 생성 중...")
    viz = DashboardVisualizer(keyword=keyword)
    viz.create_dashboard(df)
    print("  ✅ output/dashboard.png 저장 완료")

    # STEP 4: 엑셀 저장
    print("\n[STEP 4] 📂 엑셀 저장 중...")
    exporter = DataExporter(keyword=keyword)
    path = exporter.export(df)
    print(f"  ✅ {path} 저장 완료")

    print("\n" + "=" * 60)
    print("  🎉 파이프라인 완료!")
    print("=" * 60)
    return df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="News Sentiment Insight Dashboard")
    parser.add_argument("--keyword", "-k", type=str, default="삼성전자", help="Search keyword (default: 삼성전자)")
    parser.add_argument("--pages", "-p", type=int, default=3, help="Pages per site (default: 3)")
    parser.add_argument("--sites", "-s", nargs="+", default=None, help="Specific sites to crawl (e.g., naver hankyung)")

    args = parser.parse_args()

    run_pipeline(args.keyword, args.pages, args.sites)
