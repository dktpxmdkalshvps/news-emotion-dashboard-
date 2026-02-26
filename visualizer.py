"""
visualizer.py - 감성 분석 결과 대시보드 시각화
Matplotlib / Seaborn 기반 4-패널 대시보드 생성
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from collections import Counter

warnings.filterwarnings("ignore")

# ── 한글 폰트 자동 설정 ───────────────────────────────────────────────────────
def _set_korean_font():
    """OS별로 사용 가능한 한글 폰트를 자동으로 설정합니다."""
    font_candidates = [
        # macOS
        "AppleGothic", "Apple SD Gothic Neo",
        # Windows
        "Malgun Gothic", "맑은 고딕",
        # Linux
        "NanumGothic", "NanumBarunGothic", "Noto Sans CJK KR",
        "Noto Sans KR", "UnDotum",
        # Fallback / Common Linux
        "WenQuanYi Zen Hei", "Unifont", "Baekmuk Dotum",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for font in font_candidates:
        if font in available:
            matplotlib.rc("font", family=font)
            matplotlib.rcParams["axes.unicode_minus"] = False
            return font

    # 폴백: 기본 폰트 사용 (한글이 깨질 수 있음)
    matplotlib.rcParams["axes.unicode_minus"] = False
    return None

_set_korean_font()

# ── 색상 팔레트 ───────────────────────────────────────────────────────────────
COLORS = {
    "긍정": "#2ECC71",   # 초록
    "중립": "#95A5A6",   # 회색
    "부정": "#E74C3C",   # 빨강
    "bg":   "#1A1A2E",   # 다크 배경
    "card": "#16213E",   # 카드 배경
    "text": "#EAEAEA",   # 텍스트
    "accent": "#E94560", # 포인트 컬러
}

SENTIMENT_ORDER = ["긍정", "중립", "부정"]
PALETTE = [COLORS[s] for s in SENTIMENT_ORDER]


class DashboardVisualizer:
    """
    4-패널 감성 대시보드 생성기
    
    패널 구성:
      [1] 감성 비율 파이 차트
      [2] 감성별 뉴스 건수 막대 그래프
      [3] 감성 점수 분포 히스토그램
      [4] 상위 키워드 Word Frequency 차트
    """

    def __init__(self, keyword: str, output_dir: str = "output"):
        self.keyword = keyword
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def create_dashboard(self, df: pd.DataFrame) -> str:
        """
        전체 대시보드를 생성하고 파일로 저장합니다.
        
        Returns:
            저장된 파일 경로
        """
        fig = plt.figure(figsize=(18, 13), facecolor=COLORS["bg"])
        fig.suptitle(
            f"📰 [{self.keyword}] 뉴스 감성 분석 대시보드",
            fontsize=22, fontweight="bold",
            color=COLORS["text"], y=0.97,
        )

        # 서브플롯 그리드: 2행 × 3열 (상단은 파이+막대+점수분포, 하단은 키워드 전체)
        gs = fig.add_gridspec(
            2, 3, hspace=0.45, wspace=0.4,
            left=0.07, right=0.95, top=0.90, bottom=0.08
        )

        ax_pie    = fig.add_subplot(gs[0, 0])
        ax_bar    = fig.add_subplot(gs[0, 1])
        ax_hist   = fig.add_subplot(gs[0, 2])
        ax_kw     = fig.add_subplot(gs[1, :])   # 하단 전체 폭

        self._plot_pie(ax_pie, df)
        self._plot_bar(ax_bar, df)
        self._plot_histogram(ax_hist, df)
        self._plot_keyword_freq(ax_kw, df)

        # 하단 통계 요약 텍스트
        self._add_summary_text(fig, df)

        output_path = os.path.join(self.output_dir, "dashboard.png")
        plt.savefig(output_path, dpi=150, bbox_inches="tight",
                    facecolor=COLORS["bg"])
        plt.close()
        return output_path

    # ── 패널 1: 파이 차트 ────────────────────────────────────────
    def _plot_pie(self, ax, df: pd.DataFrame):
        counts = df["sentiment"].value_counts()
        # 순서 통일
        labels = [s for s in SENTIMENT_ORDER if s in counts.index]
        sizes  = [counts[s] for s in labels]
        colors = [COLORS[s] for s in labels]

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            startangle=140,
            pctdistance=0.75,
            wedgeprops=dict(width=0.6, edgecolor=COLORS["bg"], linewidth=2),
        )
        for text in texts:
            text.set_color(COLORS["text"])
            text.set_fontsize(11)
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontsize(10)
            autotext.set_fontweight("bold")

        ax.set_facecolor(COLORS["card"])
        ax.set_title("감성 비율", color=COLORS["text"],
                     fontsize=13, fontweight="bold", pad=12)

    # ── 패널 2: 막대 그래프 ───────────────────────────────────────
    def _plot_bar(self, ax, df: pd.DataFrame):
        counts = df["sentiment"].value_counts().reindex(SENTIMENT_ORDER, fill_value=0)

        bars = ax.bar(
            counts.index, counts.values,
            color=PALETTE, edgecolor=COLORS["bg"],
            linewidth=1.5, width=0.6,
        )

        # 막대 위에 수치 표시
        for bar, val in zip(bars, counts.values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.3,
                str(val),
                ha="center", va="bottom",
                color=COLORS["text"], fontsize=12, fontweight="bold",
            )

        ax.set_facecolor(COLORS["card"])
        ax.set_title("감성별 기사 수", color=COLORS["text"],
                     fontsize=13, fontweight="bold")
        ax.set_ylabel("건수", color=COLORS["text"], fontsize=10)
        ax.tick_params(colors=COLORS["text"])
        for spine in ax.spines.values():
            spine.set_edgecolor("#444")
        ax.set_ylim(0, counts.max() * 1.2)

    # ── 패널 3: 감성 점수 분포 히스토그램 ───────────────────────
    def _plot_histogram(self, ax, df: pd.DataFrame):
        # 감성별로 색 구분하여 stacked 히스토그램
        for sentiment, color in zip(SENTIMENT_ORDER, PALETTE):
            subset = df[df["sentiment"] == sentiment]["score"]
            if subset.empty:
                continue
            ax.hist(
                subset, bins=15, color=color, alpha=0.75,
                edgecolor=COLORS["bg"], linewidth=0.8,
                label=sentiment,
            )

        # 평균선 표시
        mean_score = df["score"].mean()
        ax.axvline(mean_score, color=COLORS["accent"],
                   linestyle="--", linewidth=1.5,
                   label=f"평균: {mean_score:.2f}")

        ax.set_facecolor(COLORS["card"])
        ax.set_title("감성 점수 분포", color=COLORS["text"],
                     fontsize=13, fontweight="bold")
        ax.set_xlabel("점수", color=COLORS["text"], fontsize=10)
        ax.set_ylabel("빈도", color=COLORS["text"], fontsize=10)
        ax.tick_params(colors=COLORS["text"])
        for spine in ax.spines.values():
            spine.set_edgecolor("#444")

        legend = ax.legend(facecolor=COLORS["card"],
                           labelcolor=COLORS["text"], fontsize=9)

    # ── 패널 4: 키워드 빈도 차트 ─────────────────────────────────
    def _plot_keyword_freq(self, ax, df: pd.DataFrame):
        # 감성 사전의 매칭 단어를 집계
        pos_words = []
        neg_words = []

        for _, row in df.iterrows():
            if pd.notna(row.get("matched_pos")) and row["matched_pos"]:
                pos_words.extend(row["matched_pos"].split(", "))
            if pd.notna(row.get("matched_neg")) and row["matched_neg"]:
                neg_words.extend(row["matched_neg"].split(", "))

        # 상위 10개씩 추출
        top_pos = Counter(pos_words).most_common(10)
        top_neg = Counter(neg_words).most_common(10)
        top_neg_inv = [(w, -c) for w, c in top_neg]  # 음수 방향으로 표시

        all_words = [w for w, _ in top_neg_inv[::-1]] + [w for w, _ in top_pos]
        all_scores = [-c for _, c in top_neg_inv[::-1]] + [c for _, c in top_pos]
        bar_colors = [COLORS["부정"]] * len(top_neg) + [COLORS["긍정"]] * len(top_pos)

        if not all_words:
            ax.text(0.5, 0.5, "매칭된 키워드가 없습니다",
                    ha="center", va="center",
                    color=COLORS["text"], fontsize=14,
                    transform=ax.transAxes)
            ax.set_facecolor(COLORS["card"])
            return

        y_pos = range(len(all_words))
        bars = ax.barh(list(y_pos), all_scores,
                       color=bar_colors, edgecolor=COLORS["bg"],
                       linewidth=0.8, height=0.7)

        # 수치 레이블
        for bar, score in zip(bars, all_scores):
            x_offset = 0.15 if score >= 0 else -0.15
            ha = "left" if score >= 0 else "right"
            ax.text(
                score + x_offset, bar.get_y() + bar.get_height() / 2,
                str(abs(int(score))),
                va="center", ha=ha,
                color=COLORS["text"], fontsize=9,
            )

        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(all_words, color=COLORS["text"], fontsize=10)
        ax.axvline(0, color="#555", linewidth=1)
        ax.set_facecolor(COLORS["card"])
        ax.set_title("감성 키워드 빈도 (←부정 | 긍정→)",
                     color=COLORS["text"], fontsize=13, fontweight="bold")
        ax.tick_params(axis="x", colors=COLORS["text"])
        for spine in ax.spines.values():
            spine.set_edgecolor("#444")

    # ── 하단 요약 텍스트 ──────────────────────────────────────────
    def _add_summary_text(self, fig, df: pd.DataFrame):
        total = len(df)
        counts = df["sentiment"].value_counts()
        pos_r = counts.get("긍정", 0) / total * 100
        neg_r = counts.get("부정", 0) / total * 100
        avg   = df["score"].mean()

        summary = (
            f"총 분석 기사: {total}건  |  "
            f"긍정 {pos_r:.1f}%  |  부정 {neg_r:.1f}%  |  "
            f"평균 감성 점수: {avg:+.2f}"
        )
        fig.text(
            0.5, 0.01, summary,
            ha="center", va="bottom",
            color=COLORS["text"], fontsize=11,
            bbox=dict(boxstyle="round,pad=0.4",
                      facecolor=COLORS["card"], edgecolor="#555"),
        )
