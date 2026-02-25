"""
sentiment.py - 한국어 감성 분석 모듈
사전 기반(Lexicon-based) 감성 점수 산출 + 가중치 적용
"""

import re
import pandas as pd
from dataclasses import dataclass, field


# ── 감성 사전 정의 ────────────────────────────────────────────────────────────
# 형식: { "단어": 점수 }  (양수=긍정, 음수=부정)
# 점수 범위: -3(매우부정) ~ +3(매우긍정)

POSITIVE_DICT: dict[str, float] = {
    # 📈 주가/실적 상승 관련
    "급등":       3.0,
    "상한가":     3.0,
    "최고가":     2.5,
    "신고가":     2.5,
    "강세":       2.0,
    "상승":       1.5,
    "올랐":       1.5,
    "오름":       1.5,
    "반등":       2.0,
    "돌파":       2.0,
    "호조":       2.0,
    "증가":       1.5,
    "성장":       2.0,
    "확대":       1.5,
    "개선":       1.5,
    "흑자":       2.0,
    "수익":       1.0,
    "흥행":       2.0,
    "흥행성공":   2.5,
    "초과달성":   2.5,
    # 👍 긍정적 평가
    "호평":       2.0,
    "선두":       1.5,
    "1위":        2.0,
    "압도적":     2.0,
    "획기적":     2.0,
    "혁신":       1.5,
    "성공":       2.0,
    "기대":       1.0,
    "긍정적":     1.5,
    "유망":       1.5,
    "수혜":       1.5,
    "호재":       2.5,
    "낙관":       1.5,
    "회복":       1.5,
    "개최":       0.5,
    "합의":       1.0,
    "타결":       1.5,
    "승인":       1.5,
    "선정":       1.0,
    "수주":       2.0,
    "계약":       1.5,
    "투자":       1.0,
}

NEGATIVE_DICT: dict[str, float] = {
    # 📉 주가/실적 하락 관련
    "급락":       -3.0,
    "하한가":     -3.0,
    "최저가":     -2.5,
    "신저가":     -2.5,
    "약세":       -2.0,
    "하락":       -1.5,
    "내렸":       -1.5,
    "내림":       -1.5,
    "폭락":       -3.0,
    "추락":       -2.5,
    "부진":       -2.0,
    "감소":       -1.5,
    "축소":       -1.5,
    "악화":       -2.0,
    "적자":       -2.0,
    "손실":       -2.0,
    "손해":       -2.0,
    # ⚠️ 부정적 사건
    "위기":       -2.5,
    "리스크":     -2.0,
    "충격":       -2.0,
    "붕괴":       -3.0,
    "파산":       -3.0,
    "실패":       -2.0,
    "취소":       -1.5,
    "중단":       -1.5,
    "제재":       -2.0,
    "규제":       -1.5,
    "벌금":       -2.0,
    "과징금":     -2.0,
    "소송":       -1.5,
    "리콜":       -2.0,
    "결함":       -2.0,
    "논란":       -1.5,
    "비판":       -1.5,
    "우려":       -1.5,
    "경고":       -1.5,
    "부정적":     -1.5,
    "침체":       -2.0,
    "불황":       -2.5,
    "하향":       -1.5,
    "불안":       -1.5,
    "갈등":       -1.5,
    "분쟁":       -2.0,
    "결렬":       -2.0,
    "의혹":       -1.5,
    "고발":       -2.0,
}

# 부정어 - 의미를 반전시키는 단어
NEGATION_WORDS = ["안", "못", "없", "아니", "부", "비", "불", "미"]


@dataclass
class SentimentResult:
    score: float
    sentiment: str          # '긍정' / '부정' / '중립'
    matched_pos: list[str] = field(default_factory=list)
    matched_neg: list[str] = field(default_factory=list)


class SentimentAnalyzer:
    """
    한국어 뉴스 제목 감성 분석기
    
    알고리즘:
      1. 사전의 각 단어가 제목에 포함되는지 확인
      2. 부정어(안, 못, 없...) 앞에 있는 단어는 점수를 반전
      3. 최종 합산 점수로 긍정/부정/중립 분류
    
    임계값:
      score > +0.5  → 긍정
      score < -0.5  → 부정
      otherwise     → 중립
    """

    POS_THRESHOLD = 0.5
    NEG_THRESHOLD = -0.5

    def __init__(
        self,
        pos_dict: dict = None,
        neg_dict: dict = None,
    ):
        self.pos_dict = pos_dict or POSITIVE_DICT
        self.neg_dict = neg_dict or NEGATIVE_DICT
        self.all_dict = {**self.pos_dict, **self.neg_dict}

    # ── 공개 API ─────────────────────────────────────────────────
    def analyze(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        DataFrame의 'title' 컬럼을 분석하여 감성 관련 컬럼을 추가합니다.
        
        추가되는 컬럼:
          - score       : 감성 점수 (float)
          - sentiment   : 긍정 / 부정 / 중립
          - matched_pos : 매칭된 긍정 단어 목록
          - matched_neg : 매칭된 부정 단어 목록
        """
        results = df["title"].apply(self._score_title)

        df = df.copy()
        df["score"]       = results.apply(lambda r: r.score)
        df["sentiment"]   = results.apply(lambda r: r.sentiment)
        df["matched_pos"] = results.apply(lambda r: ", ".join(r.matched_pos))
        df["matched_neg"] = results.apply(lambda r: ", ".join(r.matched_neg))
        return df

    def score_single(self, text: str) -> SentimentResult:
        """단일 텍스트의 감성 점수를 반환합니다."""
        return self._score_title(text)

    # ── 내부 로직 ────────────────────────────────────────────────
    def _score_title(self, title: str) -> SentimentResult:
        """
        제목 하나의 감성 점수를 계산합니다.
        
        부정어 처리:
          '하락 없는' → '하락'이 부정어 뒤에 있으므로 점수 반전 (+1.5)
        """
        if not isinstance(title, str) or not title.strip():
            return SentimentResult(score=0.0, sentiment="중립")

        total_score = 0.0
        matched_pos = []
        matched_neg = []

        for word, base_score in self.all_dict.items():
            if word not in title:
                continue

            # 해당 단어 위치 파악 후 앞쪽 5글자 내 부정어 여부 확인
            idx = title.find(word)
            context_before = title[max(0, idx - 5): idx]
            has_negation = any(neg in context_before for neg in NEGATION_WORDS)

            actual_score = -base_score if has_negation else base_score

            if actual_score > 0:
                matched_pos.append(word)
            elif actual_score < 0:
                matched_neg.append(word)

            total_score += actual_score

        # 감성 레이블 분류
        if total_score > self.POS_THRESHOLD:
            sentiment = "긍정"
        elif total_score < self.NEG_THRESHOLD:
            sentiment = "부정"
        else:
            sentiment = "중립"

        return SentimentResult(
            score=round(total_score, 2),
            sentiment=sentiment,
            matched_pos=matched_pos,
            matched_neg=matched_neg,
        )

    # ── 유틸리티 ─────────────────────────────────────────────────
    def get_statistics(self, df: pd.DataFrame) -> dict:
        """분석 결과 요약 통계를 반환합니다."""
        counts = df["sentiment"].value_counts()
        total = len(df)
        return {
            "total":       total,
            "positive":    counts.get("긍정", 0),
            "negative":    counts.get("부정", 0),
            "neutral":     counts.get("중립", 0),
            "pos_ratio":   round(counts.get("긍정", 0) / total * 100, 1),
            "neg_ratio":   round(counts.get("부정", 0) / total * 100, 1),
            "avg_score":   round(df["score"].mean(), 3),
            "max_score":   df["score"].max(),
            "min_score":   df["score"].min(),
        }
