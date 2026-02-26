"""
crawler.py - 3대 뉴스 사이트 통합 크롤러
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

공통 인터페이스(BaseCrawler) → 사이트별 구현체 → 통합 매니저 구조

  BaseCrawler (추상 클래스)
    ├── NaverCrawler     네이버 뉴스
    ├── DaumCrawler      다음 뉴스
    └── HankyungCrawler  한국경제

  MultiSiteCrawler      세 크롤러를 묶어 한 번에 실행
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import time
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  데이터 클래스
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@dataclass
class NewsItem:
    title:      str
    press:      str
    pub_time:   str
    url:        str
    source:     str
    crawled_at: str = field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    def to_dict(self) -> dict:
        return {
            "title":      self.title,
            "press":      self.press,
            "pub_time":   self.pub_time,
            "url":        self.url,
            "source":     self.source,
            "crawled_at": self.crawled_at,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  공통 드라이버 팩토리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def build_driver(headless: bool = True) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  공통 인터페이스 (추상 베이스 클래스)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class BaseCrawler(ABC):
    """
    모든 사이트별 크롤러가 반드시 구현해야 하는 공통 인터페이스.

    ┌──────────────────────────────────────────────────────┐
    │  구현 의무 메서드 (추상)                              │
    │  ├── build_url(keyword, page)  → 검색 URL 생성       │
    │  ├── wait_selector()           → 로딩 대기 CSS 셀렉터│
    │  └── parse_page(driver)        → 항목 파싱 로직      │
    │                                                      │
    │  공통 제공 메서드 (재사용)                            │
    │  └── crawl(keyword, pages)     → 전체 크롤링 실행    │
    └──────────────────────────────────────────────────────┘
    """

    SITE_NAME: str = ""
    SITE_KEY:  str = ""

    def __init__(self, headless: bool = True, wait_sec: int = 8,
                 delay_range: tuple = (1.2, 2.5)):
        self.headless    = headless
        self.wait_sec    = wait_sec
        self.delay_range = delay_range
        self._driver = None

    # ── 추상 메서드 ────────────────────────────────────────────────
    @abstractmethod
    def build_url(self, keyword: str, page: int) -> str:
        """키워드 + 페이지 번호로 검색 URL을 생성합니다."""

    @abstractmethod
    def wait_selector(self) -> str:
        """페이지 로딩 완료를 판단할 CSS 셀렉터를 반환합니다."""

    @abstractmethod
    def parse_page(self, driver: webdriver.Chrome) -> list:
        """현재 페이지에서 NewsItem 리스트를 파싱하여 반환합니다."""

    # ── 공통 실행 엔진 ─────────────────────────────────────────────
    def crawl(self, keyword: str, pages: int = 5) -> list:
        """지정 키워드로 pages 수만큼 뉴스를 수집합니다."""
        results = []
        self._driver = build_driver(self.headless)
        wait = WebDriverWait(self._driver, self.wait_sec)

        try:
            for page in range(1, pages + 1):
                url = self.build_url(keyword, page)
                print(f"      [{self.SITE_NAME}] {page}/{pages}p → {url}")
                self._driver.get(url)

                try:
                    wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, self.wait_selector())
                    ))
                except TimeoutException:
                    print(f"      ⚠️  타임아웃 - {page}p 건너뜀")
                    continue

                try:
                    items = self.parse_page(self._driver)
                except Exception as e:
                    print(f"      ⚠️  파싱 오류: {e}")
                    items = []

                results.extend(items)
                print(f"      ✓ {len(items)}건 수집 (누적 {len(results)}건)")
                time.sleep(random.uniform(*self.delay_range))

        except Exception as e:
            print(f"      ❌ [{self.SITE_NAME}] 크롤링 중단: {e}")
        finally:
            if self._driver:
                self._driver.quit()
                self._driver = None

        return results

    # ── 공통 헬퍼 ─────────────────────────────────────────────────
    @staticmethod
    def safe_text(element, selector: str, default: str = "") -> str:
        """CSS 셀렉터로 텍스트를 안전하게 추출합니다."""
        try:
            return element.find_element(By.CSS_SELECTOR, selector).text.strip()
        except NoSuchElementException:
            return default

    @staticmethod
    def safe_attr(element, selector: str, attr: str, default: str = "") -> str:
        """CSS 셀렉터로 속성값을 안전하게 추출합니다."""
        try:
            return element.find_element(By.CSS_SELECTOR, selector).get_attribute(attr) or default
        except NoSuchElementException:
            return default


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  구현체 1 — 네이버 뉴스
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class NaverCrawler(BaseCrawler):
    """
    네이버 뉴스 검색 크롤러

    URL 패턴:
      search.naver.com/search.naver?where=news&query={kw}&start={start}&sort=1
      └── start: 1페이지=1, 2페이지=11, 3페이지=21 ... (×10 오프셋)

    수집 셀렉터:
      목록  ul.list_news > li.bx
      제목  a.news_tit
      언론사 a.info.press
      시간  span.info (날짜 패턴 포함 요소)
    """
    SITE_NAME = "네이버"
    SITE_KEY  = "naver"

    _BASE = ("https://search.naver.com/search.naver"
             "?where=news&query={kw}&start={start}&sort=1")

    def build_url(self, keyword: str, page: int) -> str:
        start = (page - 1) * 10 + 1
        return self._BASE.format(kw=quote_plus(keyword), start=start)

    def wait_selector(self) -> str:
        return "ul.list_news > li"

    def parse_page(self, driver) -> list:
        items = []
        cards = driver.find_elements(By.CSS_SELECTOR, "ul.list_news > li.bx")
        for card in cards:
            title = self.safe_text(card, "a.news_tit")
            if not title:
                continue
            press    = self.safe_text(card, "a.info.press") or self.safe_text(card, "a.press")
            pub_time = self._extract_time(card)
            url      = self.safe_attr(card, "a.news_tit", "href")
            items.append(NewsItem(title=title, press=press or "알 수 없음",
                                  pub_time=pub_time, url=url, source=self.SITE_KEY))
        return items

    @staticmethod
    def _extract_time(card) -> str:
        spans = card.find_elements(By.CSS_SELECTOR, "span.info")
        for span in spans:
            text = span.text.strip()
            if any(k in text for k in ["전", ".", "시간", "일"]):
                return text
        return spans[-1].text.strip() if spans else ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  구현체 2 — 다음 뉴스
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class DaumCrawler(BaseCrawler):
    """
    다음(Daum) 뉴스 검색 크롤러

    URL 패턴:
      search.daum.net/search?w=news&q={kw}&p={page}&sort=recency
      └── p: 1페이지=1, 2페이지=2 ... (그대로 페이지 번호)

    수집 셀렉터:
      목록  li.g_item  /  div.cont_inner
      제목  a.tit_main  /  a.link_txt  /  a.item-title
      언론사 span.name_cp  /  span.txt_cp
      시간  span.num_date  /  span.date_txt
    """
    SITE_NAME = "다음"
    SITE_KEY  = "daum"

    _BASE = ("https://search.daum.net/search"
             "?w=news&q={kw}&p={page}&spacing=0&sort=recency")

    def build_url(self, keyword: str, page: int) -> str:
        return self._BASE.format(kw=quote_plus(keyword), page=page)

    def wait_selector(self) -> str:
        return "div#newsSearchMainList, ul.list_news, div.wrap_g"

    def parse_page(self, driver) -> list:
        items = []
        cards = []
        for sel in ["li.g_item", "div.cont_inner", "li[data-docid]"]:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if cards:
                break

        for card in cards:
            title = (self.safe_text(card, "a.tit_main")
                     or self.safe_text(card, "a.link_txt")
                     or self.safe_text(card, "a.item-title")
                     or self.safe_text(card, "a.tit_g"))
            if not title:
                continue

            url = (self.safe_attr(card, "a.tit_main", "href")
                   or self.safe_attr(card, "a.link_txt", "href")
                   or self.safe_attr(card, "a.item-title", "href"))
            press = (self.safe_text(card, "span.name_cp")
                     or self.safe_text(card, "span.txt_cp")
                     or self.safe_text(card, "span.info_txt"))
            pub_time = (self.safe_text(card, "span.num_date")
                        or self.safe_text(card, "span.date_txt")
                        or self.safe_text(card, "span.info_date"))
            items.append(NewsItem(title=title, press=press or "알 수 없음",
                                  pub_time=pub_time, url=url, source=self.SITE_KEY))
        return items


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  구현체 3 — 한국경제
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class HankyungCrawler(BaseCrawler):
    """
    한국경제(hankyung.com) 뉴스 검색 크롤러

    URL 패턴:
      www.hankyung.com/search?search_str={kw}&page={page}&type=news&sort=date
      └── page: 1페이지=1, 2페이지=2 ...
    수집 셀렉터:
      목록  li.item  /  article.list-item
      제목  .news-tit  /  h3.title a  /  a.tit
      언론사 span.author  (자사 기사 많음 → 기자명 대체)
      시간  span.date  /  time

    특징:
      경제/산업 전문 용어 다수 → 감성 사전 가중치 분석에 유리
      상대 경로 URL → https://www.hankyung.com 자동 prefix 처리
    """
    SITE_NAME = "한국경제"
    SITE_KEY  = "hankyung"

    _BASE = ("https://www.hankyung.com/search"
             "?search_str={kw}&page={page}&type=news&sort=date")

    def build_url(self, keyword: str, page: int) -> str:
        return self._BASE.format(kw=quote_plus(keyword), page=page)

    def wait_selector(self) -> str:
        return "ul.list-news, div.news-list, article.news-item"

    def parse_page(self, driver) -> list:
        items = []
        cards = []
        for sel in ["li.item", "li.news-item", "article.list-item"]:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if cards:
                break

        for card in cards:
            title = (self.safe_text(card, ".news-tit")
                     or self.safe_text(card, "h3.title a")
                     or self.safe_text(card, "a.tit")
                     or self.safe_text(card, ".tit"))
            if not title:
                continue

            url = (self.safe_attr(card, ".news-tit", "href")
                   or self.safe_attr(card, "h3.title a", "href")
                   or self.safe_attr(card, "a.tit", "href"))
            if url and url.startswith("/"):
                url = "https://www.hankyung.com" + url

            press    = self.safe_text(card, "span.author") or self.safe_text(card, "span.reporter") or "한국경제"
            pub_time = (self.safe_text(card, "span.date")
                        or self.safe_text(card, "time")
                        or self.safe_attr(card, "time", "datetime"))

            items.append(NewsItem(title=title, press=press,
                                  pub_time=pub_time, url=url, source=self.SITE_KEY))
        return items


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  통합 크롤러 매니저
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class MultiSiteCrawler:
    """
    3대 뉴스 사이트를 하나의 인터페이스로 통합 실행하는 매니저.

    사용 예시:
        crawler = MultiSiteCrawler(sites=["naver", "daum", "hankyung"])
        results = crawler.crawl(keyword="삼성전자", pages_per_site=3)
        df = crawler.to_dataframe(results)

    레지스트리 구조:
        _REGISTRY 딕셔너리에만 추가하면 새 사이트를 바로 지원합니다.

    중복 제거:
        URL 기준 → URL 없으면 제목 기준으로 중복 제거합니다.
    """

    # ✏️ 새 사이트 추가 시 여기에만 등록
    _REGISTRY: dict[str, type] = {
        "naver":    NaverCrawler,
        "daum":     DaumCrawler,
        "hankyung": HankyungCrawler,
    }

    def __init__(self, sites=None, headless: bool = True, wait_sec: int = 8):
        target_keys = sites or list(self._REGISTRY.keys())
        invalid = set(target_keys) - set(self._REGISTRY)
        if invalid:
            raise ValueError(f"지원하지 않는 사이트: {invalid} | 사용 가능: {list(self._REGISTRY)}")
        self.crawlers = [
            self._REGISTRY[k](headless=headless, wait_sec=wait_sec)
            for k in target_keys
        ]

    def crawl(self, keyword: str, pages_per_site: int = 3) -> list:
        """등록된 모든 사이트에서 순차적으로 뉴스를 수집합니다."""
        all_items = []
        print(f"\n  🌐 멀티사이트 크롤링 시작")
        print(f"  키워드: [{keyword}] | 사이트당 {pages_per_site}페이지")
        print(f"  대상: {[c.SITE_NAME for c in self.crawlers]}")

        for crawler in self.crawlers:
            print(f"\n  ─── {crawler.SITE_NAME} ───")
            items = crawler.crawl(keyword=keyword, pages=pages_per_site)
            all_items.extend(items)
            print(f"  ✅ {crawler.SITE_NAME}: {len(items)}건")

        all_items = self._deduplicate(all_items)
        print(f"\n  📦 총 수집: {len(all_items)}건 (중복 제거 후)")
        return all_items

    def to_dataframe(self, items: list):
        import pandas as pd
        return pd.DataFrame([i.to_dict() for i in items])

    def crawl_to_df(self, keyword: str, pages_per_site: int = 3):
        """crawl() + to_dataframe() 편의 메서드."""
        return self.to_dataframe(self.crawl(keyword=keyword, pages_per_site=pages_per_site))

    @staticmethod
    def _deduplicate(items: list) -> list:
        seen = set()
        unique = []
        for item in items:
            key = item.url.strip() if item.url.strip() else item.title.strip()
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    @classmethod
    def list_sites(cls) -> list:
        return list(cls._REGISTRY.keys())
