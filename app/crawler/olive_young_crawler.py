# -*- coding: utf-8 -*-
# [FIX] Refactored Olive Young Review Crawler with Enhanced Wait & Click Logic
import time
import re
import sys
import os
import json
import random
import hashlib
import argparse
import pandas as pd
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

sys.stdout.reconfigure(encoding='utf-8')

# ==============================================================================
# CONFIGURATION
# ==============================================================================
EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

SKIN_TYPES = {
    "skin_oily": "지성",
    "skin_dry": "건성",
    "skin_combination": "복합성",
    "skin_sensitive": "민감성",
    "skin_slightly_dry": "약건성",
    "skin_trouble": "트러블성",
    "skin_normal": "중성"
}

# [ADD] 정렬 타입 상수 (실제 올리브영 UI 텍스트와 일치)
SORT_TYPES = {
    "latest": "최신순",
    "helpful": "도움순",
    "high_rating": "평점 높은순",
    "low_rating": "평점 낮은순",
}

TARGET_PADS = {
    "아스파라거스 패드": {"keywords": ["아스파라거스", "asparagus"],                     "default_goods": "A000000166709"},
    "복숭아 패드":       {"keywords": ["복숭아", "피치", "peach"],                       "default_goods": "A000000231714"},
    "블루 캐모마일 패드": {"keywords": ["캐모마일", "chamomile", "카모마일", "블루캐모마일"], "default_goods": "A000000166709"},
    "라이스 패드":       {"keywords": ["라이스", "rice", "쌀"],                          "default_goods": "A000000166709"},
    "레몬그라스 패드":   {"keywords": ["레몬그라스", "lemongrass"],                      "default_goods": "A000000166709"},
    "샤인머스캣 패드":   {"keywords": ["샤인머스캣", "shine", "머스캣"],                 "default_goods": "A000000166709"},
    "핑크자몽 패드":     {"keywords": ["자몽", "grapefruit", "핑크자몽"],                "default_goods": "A000000166709"},
    "미나리 패드":       {"keywords": ["미나리", "파슬리", "parsley", "판토텐산"],        "default_goods": "A000000185135"},
    "당근 패드":         {"keywords": ["당근", "캐롯", "carrot"],                        "default_goods": "A000000248098"},
    "감자 패드":         {"keywords": ["감자", "포테이토", "potato"],                    "default_goods": "A000000200396"},
    "도토리 패드":       {"keywords": ["도토리", "에이콘", "acorn"],                     "default_goods": "A000000157075"},
}

PRODUCT_PAGES = {
    "A000000166709": {"name": "11종 통합 기획전 페이지", "max_scroll_steps": 600, "target_reviews": 1500, "delay": 1.0},
    "A000000206889": {"name": "스킨푸드 패드 레시피 3종 페이지", "max_scroll_steps": 300, "target_reviews": 500, "delay": 1.0},
    "A000000231714": {"name": "복숭아 패드 전용 페이지",  "max_scroll_steps": 200, "target_reviews": 250,  "delay": 0.9},
    "A000000185135": {"name": "미나리 패드 전용 페이지",  "max_scroll_steps": 200, "target_reviews": 250,  "delay": 0.9},
    "A000000248098": {"name": "당근 패드 기획전 페이지",  "max_scroll_steps": 200, "target_reviews": 250,  "delay": 0.9},
    "A000000200396": {"name": "감자 패드 전용 페이지",    "max_scroll_steps": 200, "target_reviews": 250,  "delay": 0.9},
    "A000000157075": {"name": "도토리 패드 전용 페이지",  "max_scroll_steps": 200, "target_reviews": 250,  "delay": 0.9},
}

SUSPECT_KEYWORDS = ["가글", "구강", "치약", "칫솔", "마우스워시", "구취", "잇몸"]

# ==============================================================================
# JavaScript: XHR + fetch 인터셉터
# ==============================================================================
_INTERCEPTOR_JS = """
if (!window.__oyIntercepted) {
    window.__oyIntercepted = true;
    window.__oyBatches    = [];

    // ── XHR ─────────────────────────────────────────────────────────
    const _xOpen = XMLHttpRequest.prototype.open;
    const _xSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(m, u) {
        this._oy_url = String(u || '');
        return _xOpen.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function() {
        this.addEventListener('load', function() {
            if ((this._oy_url || '').includes('/review/api/')) {
                window.__oyBatches.push({
                    src: 'xhr', url: this._oy_url,
                    status: this.status, body: this.responseText || ''
                });
            }
        });
        return _xSend.apply(this, arguments);
    };

    // ── fetch ────────────────────────────────────────────────────────
    const _origFetch = window.fetch;
    window.fetch = async function(input, init) {
        const url = typeof input === 'string' ? input : ((input && input.url) || '');
        const res = await _origFetch.apply(this, arguments);
        if (url.includes('/review/api/')) {
            try {
                const text = await res.clone().text();
                window.__oyBatches.push({
                    src: 'fetch', url: url,
                    status: res.status, body: text || ''
                });
            } catch(e) {}
        }
        return res;
    };
}
"""

_COLLECT_BATCHES_JS = """
const b = (window.__oyBatches || []).slice();
window.__oyBatches = [];
return JSON.stringify(b);
"""

# [FIX] 태그에 구애받지 않고 공백 제거 및 포함 관계(contains)로 매칭하는 유연한 Shadow DOM 클릭 JS
_JS_CLICK_BY_TEXT = r"""
return (function(targetText) {
    console.warn("=== CLICK_BY_TEXT START ===", targetText);
    function findAndClick(root, depth = 0) {
        if (!root) return false;
        const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
        const target = targetText.replace(/\s+/g, '');
        console.warn("Depth:", depth, "Elements count:", all.length, "Target:", target);
        
        for (let i = all.length - 1; i >= 0; i--) {
            const el = all[i];
            const txt = el.textContent.replace(/\s+/g, '');
            if (txt.includes(target)) {
                console.warn("Found match candidate:", el.tagName, "offsetWidth:", el.offsetWidth, "text:", txt.substring(0, 30));
                if (el.offsetWidth > 0) {
                    try {
                        let clickTarget = el;
                        let curr = el;
                        while (curr && curr !== document.body) {
                            if (curr.tagName && curr.tagName.toLowerCase() === 'button') {
                                clickTarget = curr;
                                break;
                            }
                            if (curr.shadowRoot) {
                                const btn = curr.shadowRoot.querySelector('button');
                                if (btn) {
                                    clickTarget = btn;
                                    break;
                                }
                            }
                            curr = curr.parentElement || (curr.parentNode && curr.parentNode.host ? curr.parentNode.host : null);
                        }
                        console.warn("Clicking target element:", clickTarget.tagName);
                        clickTarget.click();
                        return true;
                    } catch(e) {
                        console.error("Click execution failed:", e);
                    }
                }
            }
        }
        for (const el of all) {
            if (el.shadowRoot) {
                if (findAndClick(el.shadowRoot, depth + 1)) return true;
            }
        }
        return false;
    }
    const res = findAndClick(document);
    console.warn("=== CLICK_BY_TEXT END ===", res);
    return res;
})(arguments[0]);
"""

# [FIX] Shadow DOM 관통 클래스 셀렉터 클릭 JS
_JS_CLICK_BY_CLASS = """
(function(selector) {
    function findAndClick(root) {
        if (!root) return false;
        const el = root.querySelector ? root.querySelector(selector) : null;
        if (el) {
            if (el.offsetWidth > 0 && el.offsetHeight > 0) {
                el.click();
                return true;
            }
        }
        const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
        for (const sub of all) {
            if (sub.shadowRoot) {
                if (findAndClick(sub.shadowRoot)) return true;
            }
        }
        return false;
    }
    return findAndClick(document);
})(arguments[0]);
"""

# ==============================================================================
# JavaScript: Shadow DOM 직접 추출
# ==============================================================================
_EXTRACT_JS = """
return (function(goodsNo) {
    const reviews = [];
    const seen    = new Set();

    function findAll(root, tagLower, depth) {
        if (!root || depth > 9) return [];
        let found = [];
        try {
            const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
            for (const el of all) {
                if (el.tagName && el.tagName.toLowerCase() === tagLower) found.push(el);
                if (el.shadowRoot) found = found.concat(findAll(el.shadowRoot, tagLower, depth + 1));
            }
        } catch(e) {}
        return found;
    }

    const items = findAll(document, 'oy-review-review-item', 0);

    for (const item of items) {
        if (!item.shadowRoot) continue;
        const sr = item.shadowRoot;

        const dateEl = sr.querySelector('span.date')
                    || sr.querySelector('.date')
                    || sr.querySelector('[class*="date"]')
                    || sr.querySelector('[class*="Date"]');
        const date = dateEl ? dateEl.textContent.trim() : '';

        const optEl = sr.querySelector('div.goods-option');
        let option  = optEl ? optEl.textContent.trim() : '단품';
        option = option.replace(/^\\s*\\[옵션\\]\\s*/, '').trim() || '단품';

        const ratingDiv = sr.querySelector('div.rating');
        let rating = 5;
        if (ratingDiv) {
            const stars = Array.from(ratingDiv.querySelectorAll('oy-review-star-icon'));
            const filledCount = stars.filter(s => {
                if (s.hasAttribute('empty'))            return false;
                if (s.getAttribute('type') === 'empty') return false;
                if (s.shadowRoot) {
                    const paths = Array.from(s.shadowRoot.querySelectorAll('path[fill], circle[fill]'));
                    for (const p of paths) {
                        const f = (p.getAttribute('fill') || '').toLowerCase();
                        if (f === '#d9d9d9' || f === 'gray' || f === '#ccc' || f === '#cccccc') return false;
                    }
                }
                return true;
            }).length;
            rating = filledCount > 0 ? filledCount : stars.length;
            if (rating < 1 || rating > 5) rating = 5;
        }

        let content = '';
        const contentComp = sr.querySelector('oy-review-review-content');
        if (contentComp && contentComp.shadowRoot) {
            const csr = contentComp.shadowRoot;
            const cEl = csr.querySelector('.review-content-container')
                     || csr.querySelector('[class*="content-container"]')
                     || csr.querySelector('[class*="review-content"]');
            content = cEl ? cEl.textContent.trim() : csr.textContent.trim();
            content = content.replace(/해당 리뷰는 성분과 내용물이 동일한[\\s\\S]*?있습니다\\./, '').trim();
        }
        if (!content || content.length < 5) continue;

        let username = '익명';
        let skinTypes = '';
        const userComp = sr.querySelector('oy-review-review-user');
        if (userComp && userComp.shadowRoot) {
            const uEl = userComp.shadowRoot.querySelector('.name')
                     || userComp.shadowRoot.querySelector('[class*="nickname"]')
                     || userComp.shadowRoot.querySelector('[class*="user-id"]')
                     || userComp.shadowRoot.querySelector('[class*="author"]');
            if (uEl) username = uEl.textContent.trim() || '익명';

            const skinEl = userComp.shadowRoot.querySelector('.skin-types');
            if (skinEl) {
                skinTypes = Array.from(skinEl.querySelectorAll('.skin-type'))
                                 .map(el => el.textContent.trim())
                                 .filter(Boolean)
                                 .join(', ');
            }
        }

        let reviewId = '';
        try {
            reviewId = item.getAttribute('review-id') || item.getAttribute('id') || '';
        } catch(e) {}

        const key = date + '::' + content.substring(0, 40);
        if (!seen.has(key)) {
            seen.add(key);
            reviews.push({
                review_id:   reviewId,
                goods_no:    goodsNo,
                username:    username,
                skin_types:  skinTypes,
                rating:      rating,
                date:        date,
                content:     content,
                option_name: option,
            });
        }
    }
    return JSON.stringify(reviews);
})(arguments[0]);
"""

# ==============================================================================
# API Decoding
# ==============================================================================
SKIN_TYPE_MAP = {"A01": "지성", "A02": "건성", "A03": "복합성", "A04": "중성", "A05": "약건성"}
SKIN_TONE_MAP = {"B01": "웜톤", "B02": "쿨톤", "B03": "봄웜톤", "B04": "여름쿨톤", "B05": "가을웜톤", "B06": "겨울쿨톤"}
SKIN_TROUBLE_MAP = {"C01": "민감성", "C02": "잡티", "C03": "모공", "C04": "각질", "C05": "트러블", "C06": "블랙헤드", "C07": "주름", "C08": "미백"}

def decode_skin_types(profile_dto):
    if not profile_dto or not isinstance(profile_dto, dict):
        return ""
    parts = []
    st = profile_dto.get("skinType")
    if st: parts.append(SKIN_TYPE_MAP.get(st, st))
    stone = profile_dto.get("skinTone")
    if stone: parts.append(SKIN_TONE_MAP.get(stone, stone))
    troubles = profile_dto.get("skinTrouble") or []
    for tr in troubles:
        if tr: parts.append(SKIN_TROUBLE_MAP.get(tr, tr))
    return ", ".join(filter(None, parts))

# ==============================================================================
# Helper Functions
# ==============================================================================
def check_login_required(driver):
    current_url = driver.current_url.lower()
    if "login" in current_url or "sso" in current_url:
        print("[!] 로그인 요구 페이지로 리다이렉트됨.")
        return True
    
    has_login_popup = driver.execute_script("""
        function checkLoginPopup(root) {
            if (!root) return false;
            const elements = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
            for (const el of elements) {
                const txt = (el.textContent || '').trim();
                if (txt === "로그인" && (el.tagName === 'BUTTON' || el.tagName === 'A') && el.offsetWidth > 0) {
                    if (el.closest && el.closest('[class*="popup"], [class*="modal"]')) {
                        return true;
                    }
                }
            }
            for (const sub of elements) {
                if (sub.shadowRoot) {
                    if (checkLoginPopup(sub.shadowRoot)) return true;
                }
            }
            return false;
        }
        return checkLoginPopup(document);
    """)
    if has_login_popup:
        print("[!] 로그인 팝업 또는 폼 감지됨.")
        return True
    return False

def wait_for_review_list_update(driver, prev_first_review_key, timeout=8):
    get_first_review_js = """
        function findFirstReview(root) {
            if (!root) return null;
            const item = root.querySelector ? root.querySelector('oy-review-review-item') : null;
            if (item) return item;
            const elements = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
            for (const sub of elements) {
                if (sub.shadowRoot) {
                    const found = findFirstReview(sub.shadowRoot);
                    if (found) return found;
                }
            }
            return null;
        }
        return findFirstReview(document);
    """
    try:
        prev_el = driver.execute_script(get_first_review_js)
    except Exception:
        prev_el = None
        
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            current_el = driver.execute_script(get_first_review_js)
            if prev_el is None:
                if current_el is not None:
                    time.sleep(0.5)
                    return True
            else:
                try:
                    _ = prev_el.is_enabled()
                    if current_el != prev_el:
                        time.sleep(0.5)
                        return True
                except StaleElementReferenceException:
                    time.sleep(0.5)
                    return True
        except Exception:
            pass
        time.sleep(0.2)
    return False

def normalize_whitespace(text):
    if not text:
        return ""
    text = str(text).replace('\r', '').replace('\n', ' ').replace('\t', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def build_review_key(review):
    r_id = review.get('review_id')
    if r_id:
        return str(r_id).strip()
    goods_no = str(review.get('goods_no', '')).strip()
    rating = str(review.get('rating', '5')).strip()
    content = normalize_whitespace(review.get('content', ''))
    raw_str = f"{goods_no}_{rating}_{content}"
    h = hashlib.sha256(raw_str.encode('utf-8'))
    return h.hexdigest()

def verify_suspect_keywords(goods_no, review):
    content = review.get('content', '')
    for kw in SUSPECT_KEYWORDS:
        if kw in content:
            print(f"[SUSPECT] product_code={goods_no} keyword={kw} review_text={content[:100]}...")
            break

# ==============================================================================
# API Ingestion
# ==============================================================================
def parse_api_batch(body_text, goods_no):
    reviews = []
    try:
        data = json.loads(body_text)
    except Exception:
        return reviews

    _d = data.get('data')
    _r = data.get('result')
    review_list = (
        data.get('goodsReviewList') or
        data.get('reviewList') or
        (_d.get('goodsReviewList') if isinstance(_d, dict) else None) or
        (_d.get('reviewList')      if isinstance(_d, dict) else None) or
        (_r.get('goodsReviewList') if isinstance(_r, dict) else None) or
        (_r.get('reviewList')      if isinstance(_r, dict) else None) or
        (_d if isinstance(_d, list) else None) or
        []
    )
    if not isinstance(review_list, list):
        return reviews

    # [FIX] 진단 로그 출력
    print(f"[DEBUG_API] review_list_count={len(review_list)}")

    for r in review_list:
        if not isinstance(r, dict):
            continue

        # [FIX] 묶음 상품에서 옵션별 goods_no가 부모와 다를 수 있으므로 로그만 남기고 건너뛰지 않음
        resp_goods_no = r.get('goodsNo') or r.get('goodsDto', {}).get('goodsNo')
        if resp_goods_no and str(resp_goods_no) != str(goods_no):
            print(f"[DEBUG_API] response_goods_no={resp_goods_no} (parent={goods_no}, 묶음상품 허용)")

        content = (r.get('content') or r.get('reviewContents') or
                   r.get('reviewContent') or r.get('contents') or '').strip()
        if not content or len(content) < 5:
            continue

        date = (r.get('createdDateTime') or r.get('reviewDt') or r.get('regDt') or r.get('date') or
                r.get('createDt') or r.get('writeDate') or r.get('createDate') or '').strip()
        if not date:
            photos = r.get('photoReviewList') or []
            if photos and isinstance(photos[0], dict):
                m = re.match(r'(\d{4})/(\d{2})/(\d{2})/', photos[0].get('imagePath', ''))
                if m:
                    date = f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
        if not date:
            date = str(r.get('reviewId', ''))

        profile_dto = r.get('profileDto') or {}
        username = (profile_dto.get('memberNickname') or r.get('memberNickNm') or r.get('nickName') or
                    r.get('nickname') or r.get('writerNm') or r.get('memberName') or '익명').strip() or '익명'

        try:
            rating = int(r.get('reviewScore') or r.get('score') or
                         r.get('rating') or r.get('starScore') or r.get('pointScore') or 5)
        except Exception:
            rating = 5

        goods_dto = r.get('goodsDto') or {}
        option = (r.get('goodsOptionNm') or r.get('optionNm') or r.get('optionName') or
                  goods_dto.get('optionName') or goods_dto.get('goodsName') or '단품').strip()
        option = re.sub(r'^\\s*\\[옵션\\]\\s*', '', option).strip() or '단품'

        review_id = str(r.get('reviewId', ''))
        skin_types = decode_skin_types(profile_dto)

        reviews.append({
            'review_id':   review_id,
            'goods_no':    goods_no,
            'username':    username,
            'skin_types':  skin_types,
            'rating':      max(1, min(5, rating)),
            'date':        date,
            'content':     content,
            'option_name': option,
        })

    return reviews

def collect_api_reviews(driver, goods_no):
    raw = driver.execute_script(_COLLECT_BATCHES_JS)
    batches = json.loads(raw or '[]')
    print(f"[DEBUG_API] batch_count={len(batches)}")
    reviews = []
    for b in batches:
        url  = b.get('url', '')
        body = b.get('body', '')
        parsed = parse_api_batch(body, goods_no)
        reviews.extend(parsed)
    print(f"[DEBUG_API] parsed_review_count={len(reviews)}")
    return reviews, len(batches)

def extract_reviews_from_shadow_dom(driver, goods_no):
    try:
        # [ADD] Shadow DOM 태그명 진단
        tag_check = driver.execute_script(r"""
            function findTags(root, depth) {
                if (!root || depth > 5) return [];
                const tags = [];
                const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
                for (const el of all) {
                    const tag = el.tagName ? el.tagName.toLowerCase() : '';
                    if (tag.startsWith('oy-review')) tags.push(tag);
                    if (el.shadowRoot) {
                        tags.push(...findTags(el.shadowRoot, depth + 1));
                    }
                }
                return [...new Set(tags)];
            }
            return JSON.stringify(findTags(document, 0));
        """)
        print(f"[DEBUG_DOM] oy-review 태그 목록: {tag_check}")

        result = driver.execute_script(_EXTRACT_JS, goods_no)
        if isinstance(result, str):
            parsed = json.loads(result)
            print(f"[DEBUG_DOM] shadow DOM 추출 리뷰 수: {len(parsed)}")
            return parsed
        print(f"[DEBUG_DOM] shadow DOM 추출 결과 타입: {type(result)}, 값: {result}")
        return result if result else []
    except Exception as e:
        print(f"[!] shadow DOM 추출 에러: {e}")
        return []

# ==============================================================================
# Edge Driver Init
# ==============================================================================
def init_driver(args):
    print("\n[*] Edge 모바일 에뮬레이션 드라이버를 초기화하는 중...")
    options = Options()
    if args.headless.lower() == "true":
        options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=375,812")
    options.binary_location = EDGE_BINARY_PATH
    options.add_argument(
        "user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
    )
    
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    try:
        driver = webdriver.Edge(options=options)
        print("[*] 드라이버 초기화 완료.")
        return driver
    except Exception as e:
        print(f"[!] 드라이버 초기화 실패: {e}")
        sys.exit(1)

def _dismiss_popups(driver):
    driver.execute_script("""
        ['닫기','그만보기','웹으로','웹에서','close'].forEach(kw => {
            document.querySelectorAll('button,a,span').forEach(el => {
                if (el.textContent.trim().toLowerCase().includes(kw) && el.offsetWidth > 0)
                    try { el.click(); } catch(e) {}
            });
        });
        ['[class*="popup"]','[class*="modal"]','[class*="dimmed"]',
         '[class*="overlay"]','[class*="layer"]','[class*="banner"]'].forEach(sel =>
            document.querySelectorAll(sel).forEach(el => {
                const c = (el.className||'').toLowerCase(), id = (el.id||'').toLowerCase();
                if (!c.includes('review') && !c.includes('gdas') && !id.includes('review'))
                    el.style.display = 'none';
            })
        );
        document.documentElement.style.overflow = 'auto';
        document.body.style.overflow  = 'auto';
        document.body.style.position  = 'static';
    """)

def _activate_review_tab(driver):
    _SKIP_CLS = ("ReviewArea_btn-review", "ReviewArea_review-thumbs", "review-count", "review-score")

    def _try_click(el):
        try:
            txt = el.text.strip()
            cls = el.get_attribute("class") or ""
            tag = el.tag_name.lower()
            if ('리뷰' in txt and 1 <= len(txt) <= 40
                    and tag in ('li', 'button', 'a', 'span', 'div', 'em')
                    and not any(s in cls for s in _SKIP_CLS)):
                driver.execute_script("arguments[0].click();", el)
                print(f"[*] 탭 클릭 시도: <{tag}> cls='{cls[:40]}' txt='{txt[:30]}'")
                return True
        except Exception:
            pass
        return False

    clicked = False
    for selector in ["[class*='GoodsDetailTabs'] li", "[class*='GoodsDetailTabs'] button", "li[role='tab']", "button[role='tab']"]:
        for el in driver.find_elements(By.CSS_SELECTOR, selector):
            if _try_click(el):
                clicked = True
                break
        if clicked:
            break

    if not clicked:
        for el in driver.find_elements(By.XPATH, "//*[contains(text(), '리뷰')]"):
            if _try_click(el):
                break

    for i in range(15):
        time.sleep(1.0)
        mounted = driver.execute_script("return !!document.querySelector('oy-review-review-in-product');")
        if mounted:
            return True
    return False

def _scroll_to_review_component(driver):
    driver.execute_script("""
        const comp = document.querySelector('oy-review-review-in-product');
        if (comp) comp.scrollIntoView({behavior: 'instant', block: 'start'});
        else window.scrollTo(0, document.body.scrollHeight * 0.4);
    """)

# ==============================================================================
# [FIX] 정렬 적용 일반화 함수
# ==============================================================================
def apply_sort(driver, opt_name, sort_key):
    """sort_key: 'latest', 'helpful', 'high_rating', 'low_rating'"""
    sort_label = SORT_TYPES.get(sort_key, sort_key)

    # 현재 정렬 상태 확인
    current_sort = driver.execute_script(r"""
        function checkSort(root) {
            if (!root) return '';
            const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
            for (const el of all) {
                const tag = el.tagName ? el.tagName.toLowerCase() : '';
                if ((tag === 'oy-review-sort-select' || tag === 'oy-review-review-sort') && el.shadowRoot) {
                    const label = el.shadowRoot.querySelector('.select-label, [class*="label"], [class*="selected"]');
                    if (label) return label.textContent.trim();
                }
                if (el.shadowRoot) {
                    const found = checkSort(el.shadowRoot);
                    if (found) return found;
                }
            }
            return '';
        }
        return checkSort(document);
    """)
    print(f"[DEBUG_SORT] current_sort='{current_sort}' target='{sort_label}'")

    if sort_label in (current_sort or ''):
        print(f"[SORT] option_name='{opt_name}' sort_type={sort_key} status=already_applied")
        return True

    # 정렬 드롭다운 열기 — 여러 가지 시도
    clicked = False
    # 1) 현재 정렬 라벨 텍스트로 클릭
    if current_sort:
        clicked = driver.execute_script(_JS_CLICK_BY_TEXT, current_sort)
    # 2) 알려진 정렬 라벨들로 순서대로 시도
    if not clicked:
        for try_label in ["추천순", "최신순", "도움순", "유용한순", "평점높은순", "평점낮은순"]:
            clicked = driver.execute_script(_JS_CLICK_BY_TEXT, try_label)
            if clicked:
                break
    # 3) Shadow DOM 내부 정렬 컴포넌트 직접 클릭
    if not clicked:
        clicked = driver.execute_script(r"""
            function clickSortSelect(root) {
                if (!root) return false;
                const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
                for (const el of all) {
                    const tag = el.tagName ? el.tagName.toLowerCase() : '';
                    if ((tag === 'oy-review-sort-select' || tag === 'oy-review-review-sort') && el.shadowRoot) {
                        const btn = el.shadowRoot.querySelector('.select-container, button, .select-label, [class*="label"]');
                        if (btn) { btn.click(); return true; }
                    }
                    if (el.shadowRoot) {
                        if (clickSortSelect(el.shadowRoot)) return true;
                    }
                }
                return false;
            }
            return clickSortSelect(document);
        """)

    time.sleep(1.5)

    selected = driver.execute_script(_JS_CLICK_BY_TEXT, sort_label)
    if selected:
        print(f"[SORT] option_name='{opt_name}' sort_type={sort_key} status=applied")
        wait_for_review_list_update(driver, None)
        time.sleep(2.0)
        return True
    else:
        print(f"[SKIP] option_name='{opt_name}' sort_type={sort_key} reason=button_not_found")
        return False

# ==============================================================================
# 다음 페이지 이동 (페이징 버튼 클릭 또는 무한 스크롤 다운 fallback)
# ==============================================================================
def click_next_page(driver):
    # 1. 페이징 버튼 클릭 시도 (하위 호환성 유지)
    clicked = driver.execute_script("""
        function clickNextPageDeep(root) {
            if (!root) return false;
            const pagination = root.querySelector ? root.querySelector('oy-review-pagination') : null;
            if (pagination && pagination.shadowRoot) {
                const nextBtn = pagination.shadowRoot.querySelector('button.next, [class*="next"]');
                if (nextBtn && nextBtn.offsetWidth > 0 && !nextBtn.disabled) {
                    nextBtn.click();
                    return true;
                }
                const pages = Array.from(pagination.shadowRoot.querySelectorAll('button.page, [class*="page"]'));
                let activeIdx = -1;
                for (let i = 0; i < pages.length; i++) {
                    if (pages[i].classList.contains('active') || pages[i].getAttribute('aria-current') === 'true') {
                        activeIdx = i;
                        break;
                    }
                }
                if (activeIdx !== -1 && activeIdx + 1 < pages.length) {
                    pages[activeIdx + 1].click();
                    return true;
                }
            }
            const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
            for (const sub of all) {
                if (sub.shadowRoot) {
                    if (clickNextPageDeep(sub.shadowRoot)) return true;
                }
            }
            return false;
        }
        return clickNextPageDeep(document);
    """)
    if clicked:
        return True

    # 2. 모바일 에뮬레이션(무한 스크롤) 환경 대응
    # 스크롤 전 리뷰 개수 측정
    prev_count = driver.execute_script("""
        function countReviews(root) {
            if (!root) return 0;
            let count = 0;
            const items = root.querySelectorAll ? root.querySelectorAll('oy-review-review-item') : [];
            count += items.length;
            const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
            for (const el of all) {
                if (el.shadowRoot) {
                    count += countReviews(el.shadowRoot);
                }
            }
            return count;
        }
        return countReviews(document);
    """)

    # 아래로 스크롤하여 추가 로드 트리거
    driver.execute_script("window.scrollBy(0, 1200);")
    time.sleep(1.8)

    # 스크롤 후 리뷰 개수 측정
    new_count = driver.execute_script("""
        function countReviews(root) {
            if (!root) return 0;
            let count = 0;
            const items = root.querySelectorAll ? root.querySelectorAll('oy-review-review-item') : [];
            count += items.length;
            const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
            for (const el of all) {
                if (el.shadowRoot) {
                    count += countReviews(el.shadowRoot);
                }
            }
            return count;
        }
        return countReviews(document);
    """)

    # 변화가 없다면 조금 더 강하게 스크롤 시도
    if new_count == prev_count:
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(1.5)
        new_count = driver.execute_script("""
            function countReviews(root) {
                if (!root) return 0;
                let count = 0;
                const items = root.querySelectorAll ? root.querySelectorAll('oy-review-review-item') : [];
                count += items.length;
                const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
                for (const el of all) {
                    if (el.shadowRoot) {
                        count += countReviews(el.shadowRoot);
                    }
                }
                return count;
            }
            return countReviews(document);
        """)

    # API 배치 응답 수신 여부 확인
    has_batches = driver.execute_script("return (window.__oyBatches || []).length > 0;")
    
    # 리뷰 개수가 증가했거나 새로 가로챈 API 배치가 존재하면 계속 진행 가능
    return (new_count > prev_count) or has_batches

# [ADD] 전역 기존 수집된 리뷰 키 세트
ALREADY_COLLECTED_KEYS = set()
DB_STATS = {}
TOTAL_COLLECTED_TEMP_COUNT = 0
GLOBAL_CRAWLED_REVIEWS = []

def collect_reviews_for_condition(driver, goods_no, filter_type, option_name, skin_type, sort_type, args):
    global ALREADY_COLLECTED_KEYS, TOTAL_COLLECTED_TEMP_COUNT, GLOBAL_CRAWLED_REVIEWS
    limit_revs = args.limit_reviews
    max_pages = args.max_pages
    delay = 1.2
    
    collected_reviews = {}
    # [FIX] __oyBatches 초기화를 여기서 하지 않음 — 옵션 선택/정렬 직후 API 응답이 이미 쌓여 있음
    
    for page in range(1, max_pages + 1):
        # [ADD] 전체 수집량 1500개 목표 도달 시 조기 종료
        if (len(ALREADY_COLLECTED_KEYS) + TOTAL_COLLECTED_TEMP_COUNT + len(collected_reviews)) >= 1500:
            print("[*] 목표 수집 수 1500개에 도달하여 조건 내 수집을 중단합니다.")
            break

        api_reviews, batch_count = collect_api_reviews(driver, goods_no)
        dom_reviews = extract_reviews_from_shadow_dom(driver, goods_no)
        
        new_count_in_page = 0
        dup_count_in_page = 0
        
        for r in api_reviews + dom_reviews:
            r['filter_type'] = filter_type
            r['option_name'] = option_name
            r['skin_type'] = skin_type
            r['sort_type'] = sort_type
            r['review_key'] = build_review_key(r)
            
            verify_suspect_keywords(goods_no, r)
            
            key = r['review_key']
            
            # [ADD] 구글 시트에 이미 존재하는 리뷰면 수집 제외
            if key in ALREADY_COLLECTED_KEYS:
                dup_count_in_page += 1
                continue

            if key not in collected_reviews:
                collected_reviews[key] = r
                new_count_in_page += 1
            else:
                dup_count_in_page += 1
                
        current = len(collected_reviews)
        print(f"[PAGE] option_name='{option_name}' filter_type={filter_type} page={page} found={new_count_in_page+dup_count_in_page} new_unique={new_count_in_page} duplicated={dup_count_in_page}")
        
        # [ADD] 해당 페이지에서 수집한 리뷰 중 신규 고유 리뷰가 하나도 없고 리뷰 목록 자체는 비어있지 않다면,
        # 이미 과거에 크롤링한 구글 시트 적재 범위에 닿은 것이므로 다음 페이지 이동 중단
        if new_count_in_page == 0 and len(api_reviews + dom_reviews) > 0:
            print(f"[PAGE] 신규 수집된 리뷰가 없어 다음 페이지 이동을 중단합니다.")
            break

        if current >= limit_revs:
            break
            
        has_next = click_next_page(driver)
        if not has_next:
            break
            
        wait_for_review_list_update(driver, None)
        time.sleep(delay + random.uniform(0.1, 0.3))
        
    # 수집 완료 후 전역 카운터 임시 누적
    TOTAL_COLLECTED_TEMP_COUNT += len(collected_reviews)
    return list(collected_reviews.values())

# ==============================================================================
# [FIX] 묶음 옵션 필터링 기반 크롤링 함수 (대기/폴링 보완)
# ==============================================================================
def crawl_with_options_filtering(driver, goods_no, page_info, args):
    global GLOBAL_CRAWLED_REVIEWS
    url = f"https://m.oliveyoung.co.kr/m/goods/getGoodsDetail.do?goodsNo={goods_no}"
    print(f"\n{'='*60}")
    print(f"[PRODUCT] product_code={goods_no} product_name={page_info['name']}")
    print(f"[*] URL: {url}")

    driver.get(url)
    time.sleep(5.5)

    if check_login_required(driver):
        print(f"[SKIP] product_code={goods_no} reason=login_required")
        return []

    driver.execute_script(_INTERCEPTOR_JS)
    time.sleep(0.3)
    
    _dismiss_popups(driver)
    time.sleep(1.0)

    mounted = _activate_review_tab(driver)
    if not mounted:
        print(f"[SKIP] product_code={goods_no} reason=review_tab_mount_failed")
        return []

    _scroll_to_review_component(driver)
    time.sleep(2.0)

    # [ADD] 상품 옵션 칩/버튼 로드 완료 대기
    start_wait = time.time()
    found_option_btn = False
    while time.time() - start_wait < 12:
        exists = driver.execute_script("""
            function checkExists(root) {
                if (!root) return false;
                const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
                for (const el of all) {
                    const txt = el.textContent.replace(/\\s+/g, '');
                    if (txt.includes("상품옵션") && el.offsetWidth > 0) return true;
                }
                for (const sub of all) {
                    if (sub.shadowRoot) {
                        if (checkExists(sub.shadowRoot)) return true;
                    }
                }
                return false;
            }
            return checkExists(document);
        """)
        if exists:
            found_option_btn = True
            break
        time.sleep(0.5)

    if not found_option_btn:
        print(f"[SKIP] product_code={goods_no} filter_type=option_modal reason=option_btn_not_loaded")
        return []

    # 1. '상품 옵션' 버튼 클릭하여 모달 열기
    open_success = driver.execute_script(_JS_CLICK_BY_TEXT, "상품 옵션")
    if not open_success:
        print(f"[SKIP] product_code={goods_no} filter_type=option_modal reason=option_btn_click_failed")
        return []
    
    # [ADD] 옵션 모달 및 옵션 목록 렌더링 폴링 대기
    options_list = None
    start_wait = time.time()
    while time.time() - start_wait < 10:
        options_list = driver.execute_script("""
            function findDeepOptions(root) {
                if (!root) return null;
                const sheet = root.querySelector ? root.querySelector('oy-review-goods-option-sheet') : null;
                if (sheet && sheet.shadowRoot) {
                    const options = Array.from(sheet.shadowRoot.querySelectorAll('li.option'));
                    if (options.length > 0) {
                        return options.map((opt, idx) => {
                            const nameEl = opt.querySelector('.option-name');
                            const name = nameEl ? nameEl.textContent.trim() : '';
                            const countEl = opt.querySelector('.review-count');
                            const count = countEl ? countEl.textContent.trim() : '';
                            return { index: idx, name: name, count: count };
                        });
                    }
                }
                const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
                for (const sub of all) {
                    if (sub.shadowRoot) {
                        const found = findDeepOptions(sub.shadowRoot);
                        if (found) return found;
                    }
                }
                return null;
            }
            return findDeepOptions(document);
        """)
        if options_list:
            break
        time.sleep(0.5)

    if not options_list:
        print(f"[SKIP] product_code={goods_no} filter_type=options reason=options_not_found")
        driver.execute_script(_JS_CLICK_BY_CLASS, ".close-button, [class*='close']")
        return []

    print(f"[*] 총 {len(options_list)}개의 옵션을 탐지했습니다.")
    limit_options = 2 if args.limit_reviews <= 20 else len(options_list)
    options_list = options_list[:limit_options]

    all_collected_reviews = []

    for opt in options_list:
        opt_idx = opt['index']
        opt_name = opt['name']
        print(f"\n[OPTION] option_name='{opt_name}' status=selected")

        is_open = driver.execute_script("""
            function findDeepSheet(root) {
                if (!root) return false;
                const comp = root.querySelector ? root.querySelector('oy-review-bottom-sheet') : null;
                if (comp && comp.shadowRoot) {
                    const container = comp.shadowRoot.querySelector('.bottom-sheet-container');
                    return container ? container.classList.contains('is-open') : false;
                }
                const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
                for (const sub of all) {
                    if (sub.shadowRoot) {
                        const found = findDeepSheet(sub.shadowRoot);
                        if (found) return found;
                    }
                }
                return false;
            }
            return findDeepSheet(document);
        """)
        if not is_open:
            driver.execute_script(_JS_CLICK_BY_TEXT, "상품 옵션")
            time.sleep(2.0)

        # [FIX] 옵션 선택 이전에 배치 초기화 — 옵션 선택/정렬 후 API 응답을 수집하기 위함
        driver.execute_script("window.__oyBatches = [];")

        # 옵션 하나 선택 후 조회
        driver.execute_script("""
            const targetIndex = arguments[0];
            function selectOptionDeep(root) {
                if (!root) return false;
                const sheet = root.querySelector ? root.querySelector('oy-review-goods-option-sheet') : null;
                if (sheet && sheet.shadowRoot) {
                    const resetBtn = sheet.shadowRoot.querySelector('.reset-button');
                    if (resetBtn) resetBtn.click();
                    
                    const options = Array.from(sheet.shadowRoot.querySelectorAll('li.option'));
                    if (options[targetIndex]) {
                        options[targetIndex].click();
                    }
                    
                    const viewBtn = sheet.shadowRoot.querySelector('.review-button');
                    if (viewBtn) {
                        viewBtn.click();
                        return true;
                    }
                }
                const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
                for (const sub of all) {
                    if (sub.shadowRoot) {
                        if (selectOptionDeep(sub.shadowRoot)) return true;
                    }
                }
                return false;
            }
            return selectOptionDeep(document);
        """, opt_idx)
        
        wait_for_review_list_update(driver, None)
        time.sleep(2.0)

        if check_login_required(driver):
            print(f"[SKIP] product_code={goods_no} reason=login_required")
            break

        # [FIX] 옵션 선택 후 리뷰 영역으로 스크롤 + 정렬 컨트롤 로드 대기
        _scroll_to_review_component(driver)
        time.sleep(1.5)

        # [FIX] 정렬별 수집 루프
        for sort_key, sort_label in SORT_TYPES.items():
            # 배치 초기화 → 정렬 적용 → 수집
            driver.execute_script("window.__oyBatches = [];")
            sort_ok = apply_sort(driver, opt_name, sort_key)
            if not sort_ok:
                continue

            filter_type = f"sort_{sort_key}"
            collected = collect_reviews_for_condition(
                driver, goods_no, filter_type, opt_name, "None", sort_key, args
            )
            all_collected_reviews.extend(collected)

            if check_login_required(driver):
                print(f"[SKIP] product_code={goods_no} reason=login_required")
                break

        # [FIX] 피부 타입별 수집 (최신순 고정)
        # 첫 반복에서만 필터 칩 텍스트 진단
        if True:
            chip_texts = driver.execute_script(r"""
                function findChips(root, depth) {
                    if (!root || depth > 6) return [];
                    const texts = [];
                    const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
                    for (const el of all) {
                        const tag = el.tagName ? el.tagName.toLowerCase() : '';
                        if (tag.includes('filter') || tag.includes('chip')) {
                            if (el.shadowRoot) {
                                const inner = Array.from(el.shadowRoot.querySelectorAll('button, span, div, label'));
                                for (const i of inner) {
                                    const t = i.textContent.trim();
                                    if (t && t.length < 30 && i.offsetWidth > 0) texts.push(tag + ': ' + t);
                                }
                            }
                            const t = el.textContent.trim();
                            if (t && t.length < 30 && el.offsetWidth > 0) texts.push(tag + ': ' + t);
                        }
                        if (el.shadowRoot) texts.push(...findChips(el.shadowRoot, depth + 1));
                    }
                    return [...new Set(texts)];
                }
                return JSON.stringify(findChips(document, 0));
            """)
            print(f"[DEBUG_FILTER] 필터 칩 텍스트: {chip_texts}")

        for skin_key in list(SKIN_TYPES.keys()):
            skin_name = SKIN_TYPES[skin_key]
            filter_type = f"{skin_key}_sort_latest"

            # 배치 초기화
            driver.execute_script("window.__oyBatches = [];")

            opened = driver.execute_script(_JS_CLICK_BY_TEXT, "피부 필터")
            if not opened:
                opened = driver.execute_script(_JS_CLICK_BY_TEXT, "피부타입")
            if not opened:
                opened = driver.execute_script(_JS_CLICK_BY_TEXT, "피부필터")
            if not opened:
                opened = driver.execute_script(_JS_CLICK_BY_TEXT, "피부 타입")
            if not opened:
                print(f"[SKIP] option_name='{opt_name}' skin_type={skin_name} reason=skin_filter_btn_not_found")
                continue
            time.sleep(2.0)

            # [ADD] 피부 필터 시트 내부 구조 진단
            sheet_info = driver.execute_script(r"""
                function dumpSkinSheet(root, depth) {
                    if (!root || depth > 6) return [];
                    const info = [];
                    const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
                    for (const el of all) {
                        const tag = el.tagName ? el.tagName.toLowerCase() : '';
                        if (el.shadowRoot) {
                            const sr = el.shadowRoot;
                            const inner = Array.from(sr.querySelectorAll('*'));
                            for (const i of inner) {
                                const itag = i.tagName ? i.tagName.toLowerCase() : '';
                                const txt = i.textContent.trim().substring(0, 40);
                                const cls = i.className && typeof i.className === 'string' ? i.className.substring(0, 40) : '';
                                if (txt && i.offsetWidth > 0 && txt.length < 30) {
                                    info.push(tag + ' > ' + itag + ' cls=' + cls + ' txt=' + txt);
                                }
                            }
                            info.push(...dumpSkinSheet(sr, depth + 1));
                        }
                    }
                    return info;
                }
                return JSON.stringify(dumpSkinSheet(document, 0).slice(0, 50));
            """)
            print(f"[DEBUG_SKIN_SHEET] 시트 내부: {sheet_info}")

            # [FIX] 피부 타입 클릭 선택 및 적용 — 실제 DOM 구조 반영
            selected = driver.execute_script(r"""
                const targetText = arguments[0];
                function findSkinSheet(root, depth) {
                    if (!root || depth > 8) return null;
                    const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
                    for (const el of all) {
                        const tag = el.tagName ? el.tagName.toLowerCase() : '';
                        if (tag === 'oy-review-skin-fit-sheet' && el.shadowRoot) return el;
                        if (el.shadowRoot) {
                            const found = findSkinSheet(el.shadowRoot, depth + 1);
                            if (found) return found;
                        }
                    }
                    return null;
                }
                function findBottomSheet(root, depth) {
                    if (!root || depth > 8) return null;
                    const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
                    for (const el of all) {
                        const tag = el.tagName ? el.tagName.toLowerCase() : '';
                        if (tag === 'oy-review-bottom-sheet' && el.shadowRoot) {
                            const container = el.shadowRoot.querySelector('.bottom-sheet-container.is-open');
                            if (container) return el;
                        }
                        if (el.shadowRoot) {
                            const found = findBottomSheet(el.shadowRoot, depth + 1);
                            if (found) return found;
                        }
                    }
                    return null;
                }

                const skinSheet = findSkinSheet(document, 0);
                if (!skinSheet || !skinSheet.shadowRoot) return false;

                const sr = skinSheet.shadowRoot;
                const bottomSheet = findBottomSheet(document, 0);

                // [ADD] 초기화 버튼 클릭 시도 (기존 필터 해제)
                let resetDone = false;
                const resetBtn = sr.querySelector('.reset-button, [class*="reset"], [class*="clear"]');
                if (resetBtn) {
                    resetBtn.click();
                    resetDone = true;
                } else if (bottomSheet && bottomSheet.shadowRoot) {
                    const bsr = bottomSheet.shadowRoot;
                    const bResetBtn = bsr.querySelector('.reset-button, [class*="reset"], [class*="clear"]');
                    if (bResetBtn) {
                        bResetBtn.click();
                        resetDone = true;
                    }
                }
                if (!resetDone) {
                    const allCandidates = Array.from(sr.querySelectorAll('button, span, a'));
                    if (bottomSheet && bottomSheet.shadowRoot) {
                        allCandidates.push(...Array.from(bottomSheet.shadowRoot.querySelectorAll('button, span, a')));
                    }
                    for (const el of allCandidates) {
                        const txt = el.textContent.trim();
                        if ((txt === '초기화' || txt === '재설정') && el.offsetWidth > 0) {
                            el.click();
                            resetDone = true;
                            break;
                        }
                    }
                }

                const chips = Array.from(sr.querySelectorAll('button.chip'));
                let clicked = false;
                for (const chip of chips) {
                    if (chip.textContent.trim() === targetText && chip.offsetWidth > 0) {
                        chip.click();
                        clicked = true;
                        break;
                    }
                }
                if (!clicked) return false;

                // 적용 버튼 클릭 — bottom-sheet footer 안의 버튼
                if (bottomSheet && bottomSheet.shadowRoot) {
                    const bsr = bottomSheet.shadowRoot;
                    const applyBtn = bsr.querySelector('.foot button, .footer button, button.apply, button.submit, .review-button');
                    if (applyBtn) {
                        applyBtn.click();
                        return true;
                    }
                    // foot 영역의 모든 버튼 중 텍스트에 '리뷰' 또는 '적용' 포함하는 것 클릭
                    const allBtns = Array.from(bsr.querySelectorAll('button'));
                    for (const btn of allBtns) {
                        const t = btn.textContent.trim();
                        if ((t.includes('리뷰') || t.includes('적용') || t.includes('확인')) && btn.offsetWidth > 0) {
                            btn.click();
                            return true;
                        }
                    }
                }
                return clicked;
            """, skin_name)

            if not selected:
                print(f"[SKIP] option_name='{opt_name}' skin_type={skin_name} reason=skin_option_not_found")
                driver.execute_script(_JS_CLICK_BY_CLASS, ".close-button, [class*='close']")
                continue

            wait_for_review_list_update(driver, None)
            time.sleep(2.0)

            if check_login_required(driver):
                print(f"[SKIP] product_code={goods_no} reason=login_required")
                break

            # 최신순 적용
            apply_sort(driver, opt_name, "latest")

            collected = collect_reviews_for_condition(
                driver, goods_no, filter_type, opt_name, skin_name, "latest", args
            )
            all_collected_reviews.extend(collected)
            GLOBAL_CRAWLED_REVIEWS.extend(collected)

        # 상품 옵션 초기화 후 닫기
        driver.execute_script(_JS_CLICK_BY_TEXT, "상품 옵션")
        time.sleep(2.0)
        driver.execute_script("""
            function resetOptionDeep(root) {
                if (!root) return false;
                const sheet = root.querySelector ? root.querySelector('oy-review-goods-option-sheet') : null;
                if (sheet && sheet.shadowRoot) {
                    const resetBtn = sheet.shadowRoot.querySelector('.reset-button');
                    if (resetBtn) resetBtn.click();
                    const viewBtn = sheet.shadowRoot.querySelector('.review-button');
                    if (viewBtn) { viewBtn.click(); return true; }
                }
                const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
                for (const sub of all) {
                    if (sub.shadowRoot) {
                        if (resetOptionDeep(sub.shadowRoot)) return true;
                    }
                }
                return false;
            }
            resetOptionDeep(document);
        """)
        wait_for_review_list_update(driver, None)
        time.sleep(2.0)

    return all_collected_reviews

# ==============================================================================
# 단품 상품 수집
# ==============================================================================
def crawl_raw_reviews_from_page(driver, goods_no, page_info, args):
    global GLOBAL_CRAWLED_REVIEWS
    if goods_no in ["A000000166709", "A000000206889"]:
        return crawl_with_options_filtering(driver, goods_no, page_info, args)

    url = f"https://m.oliveyoung.co.kr/m/goods/getGoodsDetail.do?goodsNo={goods_no}"
    print(f"\n{'='*60}")
    print(f"[PRODUCT] product_code={goods_no} product_name={page_info['name']}")
    print(f"[*] URL: {url}")

    driver.get(url)
    time.sleep(5.5)

    if check_login_required(driver):
        print(f"[SKIP] product_code={goods_no} reason=login_required")
        return []

    driver.execute_script(_INTERCEPTOR_JS)
    time.sleep(0.3)
    
    _dismiss_popups(driver)
    time.sleep(1.0)

    mounted = _activate_review_tab(driver)
    if not mounted:
        print(f"[SKIP] product_code={goods_no} reason=review_tab_mount_failed")
        return []

    _scroll_to_review_component(driver)
    time.sleep(2.0)

    # 1. '피부필터' 칩 로드 완료 대기
    start_wait = time.time()
    found_skin_btn = False
    while time.time() - start_wait < 12:
        exists = driver.execute_script("""
            function checkExists(root) {
                if (!root) return false;
                const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
                for (const el of all) {
                    const txt = el.textContent.replace(/\\s+/g, '');
                    if (txt.includes("피부필터") && el.offsetWidth > 0) return true;
                }
                for (const sub of all) {
                    if (sub.shadowRoot) {
                        if (checkExists(sub.shadowRoot)) return true;
                    }
                }
                return false;
            }
            return checkExists(document);
        """)
        if exists:
            found_skin_btn = True
            break
        time.sleep(0.5)

    if not found_skin_btn:
        print(f"[SKIP] product_code={goods_no} filter_type=skin_filter reason=button_not_found")
        return []

    all_collected_reviews = []
    opt_name = "단품"

    # [FIX] 정렬별 수집 루프
    for sort_key, sort_label in SORT_TYPES.items():
        driver.execute_script("window.__oyBatches = [];")
        sort_ok = apply_sort(driver, opt_name, sort_key)
        if not sort_ok:
            continue

        filter_type = f"sort_{sort_key}"
        collected = collect_reviews_for_condition(
            driver, goods_no, filter_type, opt_name, "None", sort_key, args
        )
        all_collected_reviews.extend(collected)
        GLOBAL_CRAWLED_REVIEWS.extend(collected)

        if check_login_required(driver):
            print(f"[SKIP] product_code={goods_no} reason=login_required")
            break

    # [FIX] 피부 타입별 수집 (최신순 고정)
    for skin_key in list(SKIN_TYPES.keys()):
        skin_name = SKIN_TYPES[skin_key]
        filter_type = f"{skin_key}_sort_latest"

        driver.execute_script("window.__oyBatches = [];")

        opened = driver.execute_script(_JS_CLICK_BY_TEXT, "피부 필터")
        if not opened:
            opened = driver.execute_script(_JS_CLICK_BY_TEXT, "피부타입")
        if not opened:
            opened = driver.execute_script(_JS_CLICK_BY_TEXT, "피부필터")
        if not opened:
            opened = driver.execute_script(_JS_CLICK_BY_TEXT, "피부 타입")
        if not opened:
            print(f"[SKIP] option_name='{opt_name}' skin_type={skin_name} reason=skin_filter_btn_not_found")
            continue
        time.sleep(2.0)

        # [FIX] 피부 타입 클릭 선택 및 적용 — 실제 DOM 구조 반영
        selected = driver.execute_script(r"""
            const targetText = arguments[0];
            function findSkinSheet(root, depth) {
                if (!root || depth > 8) return null;
                const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
                for (const el of all) {
                    const tag = el.tagName ? el.tagName.toLowerCase() : '';
                    if (tag === 'oy-review-skin-fit-sheet' && el.shadowRoot) return el;
                    if (el.shadowRoot) {
                        const found = findSkinSheet(el.shadowRoot, depth + 1);
                        if (found) return found;
                    }
                }
                return null;
            }
            function findBottomSheet(root, depth) {
                if (!root || depth > 8) return null;
                const all = Array.from(root.querySelectorAll ? root.querySelectorAll('*') : []);
                for (const el of all) {
                    const tag = el.tagName ? el.tagName.toLowerCase() : '';
                    if (tag === 'oy-review-bottom-sheet' && el.shadowRoot) {
                        const container = el.shadowRoot.querySelector('.bottom-sheet-container.is-open');
                        if (container) return el;
                    }
                    if (el.shadowRoot) {
                        const found = findBottomSheet(el.shadowRoot, depth + 1);
                        if (found) return found;
                    }
                }
                return null;
            }

            const skinSheet = findSkinSheet(document, 0);
            if (!skinSheet || !skinSheet.shadowRoot) return false;

            const sr = skinSheet.shadowRoot;
            const bottomSheet = findBottomSheet(document, 0);

            // [ADD] 초기화 버튼 클릭 시도 (기존 필터 해제)
            let resetDone = false;
            const resetBtn = sr.querySelector('.reset-button, [class*="reset"], [class*="clear"]');
            if (resetBtn) {
                resetBtn.click();
                resetDone = true;
            } else if (bottomSheet && bottomSheet.shadowRoot) {
                const bsr = bottomSheet.shadowRoot;
                const bResetBtn = bsr.querySelector('.reset-button, [class*="reset"], [class*="clear"]');
                if (bResetBtn) {
                    bResetBtn.click();
                    resetDone = true;
                }
            }
            if (!resetDone) {
                const allCandidates = Array.from(sr.querySelectorAll('button, span, a'));
                if (bottomSheet && bottomSheet.shadowRoot) {
                    allCandidates.push(...Array.from(bottomSheet.shadowRoot.querySelectorAll('button, span, a')));
                }
                for (const el of allCandidates) {
                    const txt = el.textContent.trim();
                    if ((txt === '초기화' || txt === '재설정') && el.offsetWidth > 0) {
                        el.click();
                        resetDone = true;
                        break;
                    }
                }
            }

            const chips = Array.from(sr.querySelectorAll('button.chip'));
            let clicked = false;
            for (const chip of chips) {
                if (chip.textContent.trim() === targetText && chip.offsetWidth > 0) {
                    chip.click();
                    clicked = true;
                    break;
                }
            }
            if (!clicked) return false;

            // 적용 버튼 클릭 — bottom-sheet footer 안의 버튼
            if (bottomSheet && bottomSheet.shadowRoot) {
                const bsr = bottomSheet.shadowRoot;
                const applyBtn = bsr.querySelector('.foot button, .footer button, button.apply, button.submit, .review-button');
                if (applyBtn) {
                    applyBtn.click();
                    return true;
                }
                // foot 영역의 모든 버튼 중 텍스트에 '리뷰' 또는 '적용' 포함하는 것 클릭
                const allBtns = Array.from(bsr.querySelectorAll('button'));
                for (const btn of allBtns) {
                    const t = btn.textContent.trim();
                    if ((t.includes('리뷰') || t.includes('적용') || t.includes('확인')) && btn.offsetWidth > 0) {
                        btn.click();
                        return true;
                    }
                }
            }
            return clicked;
        """, skin_name)

        if not selected:
            print(f"[SKIP] option_name='{opt_name}' skin_type={skin_name} reason=skin_option_not_found")
            driver.execute_script(_JS_CLICK_BY_CLASS, ".close-button, [class*='close']")
            continue

        wait_for_review_list_update(driver, None)
        time.sleep(2.0)

        if check_login_required(driver):
            print(f"[SKIP] product_code={goods_no} reason=login_required")
            break

        apply_sort(driver, opt_name, "latest")

        collected = collect_reviews_for_condition(
            driver, goods_no, filter_type, opt_name, skin_name, "latest", args
        )
        all_collected_reviews.extend(collected)
        GLOBAL_CRAWLED_REVIEWS.extend(collected)

    return all_collected_reviews

# ==============================================================================
# Entry Point
# ==============================================================================
def parse_args():
    parser = argparse.ArgumentParser(description="올리브영 11종 패드 리뷰 수집기")
    parser.add_argument("--limit-products", type=int, default=None, help="크롤링할 상품 개수 제한")
    # [FIX] 1500개 목표 수집을 위해 조건당 리뷰 수 기본값 200, 최대 페이지 20으로 상향
    parser.add_argument("--limit-reviews", type=int, default=200, help="조건당 수집할 최대 리뷰 수")
    parser.add_argument("--max-pages", type=int, default=20, help="조건당 최대 페이지 수")
    parser.add_argument("--headless", type=str, default="True", help="Headless 모드 사용 여부 (True/False)")
    parser.add_argument("--dry-run", action="store_true", help="드라이 런 모드")
    return parser.parse_args()

def main():
    global ALREADY_COLLECTED_KEYS, TOTAL_COLLECTED_TEMP_COUNT
    args = parse_args()
    print("="*60)
    print("  올리브영 스킨푸드 11종 패드 균등 평점 리뷰 수집기")
    print("  방식: API 인터셉터 + Shadow DOM 추출 + 묶음 상품 정렬/필터 루프")
    print("="*60)

    ALREADY_COLLECTED_KEYS = set()
    
    # 1. DB에서 기존 수집된 리뷰 키 로드
    try:
        from app.database.connection import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT review_id FROM reviews WHERE review_id IS NOT NULL;")
        db_keys = [r[0] for r in cursor.fetchall() if r[0]]
        ALREADY_COLLECTED_KEYS.update(db_keys)
        print(f"[DB] 이미 존재하여 제외할 리뷰 키 개수: {len(db_keys)}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[DB_ERROR] DB 연동 실패로 기존 키 로드 불가: {e}")

    # 2. CSV 파일에서 기존 수집된 리뷰 키 로드
    csv_path = "review_crawler/data/olive_young_reviews.csv"
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            if "review_key" in df.columns:
                csv_keys = df["review_key"].dropna().astype(str).tolist()
                ALREADY_COLLECTED_KEYS.update(csv_keys)
                print(f"[CSV] 파일({csv_path})에서 로드된 리뷰 키 개수: {len(csv_keys)}")
        except Exception as e:
            print(f"[CSV_ERROR] CSV 파일 로드 실패: {e}")

    driver = init_driver(args)
    global GLOBAL_CRAWLED_REVIEWS
    GLOBAL_CRAWLED_REVIEWS = []
    TOTAL_COLLECTED_TEMP_COUNT = 0

    try:
        product_list = list(PRODUCT_PAGES.items())
        if args.limit_products:
            product_list = product_list[:args.limit_products]

        total_goal = 4500
        for idx, (goods_no, page_info) in enumerate(product_list):
            current_total = len(ALREADY_COLLECTED_KEYS) + TOTAL_COLLECTED_TEMP_COUNT
            if current_total >= total_goal:
                print(f"\n[*] 기존 수집 데이터 + 신규 수집 데이터 총합이 {total_goal}개 목표를 달성하여 크롤링을 최종 종료합니다.")
                break

            print(f"\n[PRODUCT] index={idx+1}/{len(product_list)} product_code={goods_no} product_name={page_info['name']}")
            try:
                page_reviews = crawl_raw_reviews_from_page(driver, goods_no, page_info, args)
                print(f"[PRODUCT_DONE] product_code={goods_no} unique_saved={len(page_reviews)}")
            except Exception as e:
                print(f"[ERROR] product_code={goods_no} filter_type=all type=crawl_error reason={e}")

            if idx < len(product_list) - 1:
                print("[*] 다음 페이지 이동 전 4초 쿨다운...")
                time.sleep(4)
    except KeyboardInterrupt:
        print("\n[!] 사용자에 의해 크롤링이 중단되었습니다. 현재까지 수집된 데이터를 저장합니다.")
    finally:
        print("\n[*] Selenium 드라이버 종료.")
        driver.quit()

    rows = []
    for r in GLOBAL_CRAWLED_REVIEWS:
        rows.append({
            "goods_no":     r["goods_no"],
            "option_name":  r["option_name"] or "단품",
            "username":     r["username"],
            "skin_types":   r["skin_types"],
            "rating":       r["rating"],
            "date":         r["date"],
            "content":      r["content"],
            "filter_type":  r.get("filter_type", "sort_latest"),
            "review_key":   r.get("review_key", ""),
            "skin_type":    r.get("skin_type", "None"),
            "sort_type":    r.get("sort_type", "latest")
        })

    df = pd.DataFrame(rows)

    # 데이터 검증
    valid_rows = []
    skipped_count = 0
    for idx, row in df.iterrows():
        r_key = str(row.get("review_key", "")).strip() if pd.notna(row.get("review_key")) else ""
        content = str(row.get("content", "")).strip() if pd.notna(row.get("content")) else ""
        rating = row.get("rating")
        goods_no = str(row.get("goods_no", "")).strip() if pd.notna(row.get("goods_no")) else ""

        try:
            rating_val = int(rating)
            rating_ok = 1 <= rating_val <= 5
        except Exception:
            rating_ok = False

        if not r_key or len(content) < 10 or not rating_ok or not goods_no:
            skipped_count += 1
            continue
        valid_rows.append(row)

    df = pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=df.columns)
    print(f"[VALIDATE] valid={len(df)} skipped={skipped_count}")

    # 중복 제거
    df = df.drop_duplicates(subset=["review_key"], keep="first")

    # CSV 저장
    csv_path = os.getenv("REVIEW_CSV_PATH", "review_crawler/data/olive_young_reviews.csv")
    try:
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        df.to_csv(
            csv_path,
            index=False,
            encoding="utf-8-sig"
        )
        print(f"[CSV] path={csv_path} rows_written={len(df)}")
    except Exception as e:
        print(f"[ERROR] type=csv_save_error reason={e}")

    print("\n" + "="*60)
    print("  모든 작업 완료!")
    print("="*60)


if __name__ == "__main__":
    main()
