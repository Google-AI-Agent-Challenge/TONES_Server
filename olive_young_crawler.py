import time
import re
import sys
import os
import random
import pandas as pd
from bs4 import BeautifulSoup
from curl_cffi import requests
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By

# 콘솔 출력 인코딩을 UTF-8로 강제 설정하여 한글 및 이모지 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

# ==============================================================================
# CONFIGURATION BLOCK (설정 영역)
# ==============================================================================
OUTPUT_FILENAME = "스킨푸드_패드_고객리뷰.xlsx"
EDGE_BINARY_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
# ==============================================================================

# 스킨푸드 11종 패드 상품 정의 및 옵션 매핑 키워드 규칙
TARGET_PADS = {
    "아스파라거스 패드": {
        "keywords": ["아스파라거스", "asparagus"],
        "default_goods": "A000000166709"
    },
    "복숭아 패드": {
        "keywords": ["복숭아", "피치", "peach"],
        "default_goods": "A000000231714"
    },
    "블루 캐모마일 패드": {
        "keywords": ["캐모마일", "chamomile", "카모마일", "블루캐모마일"],
        "default_goods": "A000000166709"
    },
    "라이스 패드": {
        "keywords": ["라이스", "rice", "쌀"],
        "default_goods": "A000000166709"
    },
    "레몬그라스 패드": {
        "keywords": ["레몬그라스", "lemongrass"],
        "default_goods": "A000000166709"
    },
    "샤인머스캣 패드": {
        "keywords": ["샤인머스캣", "shine", "머스캣"],
        "default_goods": "A000000166709"
    },
    "핑크자몽 패드": {
        "keywords": ["자몽", "grapefruit", "핑크자몽"],
        "default_goods": "A000000166709"
    },
    "미나리 패드": {
        "keywords": ["미나리", "파슬리", "parsley", "판토텐산"],
        "default_goods": "A000000185135"
    },
    "당근 패드": {
        "keywords": ["당근", "캐롯", "carrot"],
        "default_goods": "A000000248098"
    },
    "감자 패드": {
        "keywords": ["감자", "포테이토", "potato"],
        "default_goods": "A000000200396"
    },
    "도토리 패드": {
        "keywords": ["도토리", "에이콘", "acorn"],
        "default_goods": "A000000157075"
    }
}

# 고유 상품 페이지 정의 및 수집할 스크롤 스텝 분기
# 통합 기획전 페이지일수록 더 많은 리뷰 풀을 모으기 위해 스크롤을 길게 줍니다.
PRODUCT_PAGES = {
    "A000000166709": {"name": "11종 통합 기획전 페이지 (아스파라거스/라이스/도토리 등)", "scroll_steps": 160, "delay": 1.3},
    "A000000231714": {"name": "복숭아 패드 전용/기획 페이지", "scroll_steps": 40, "delay": 1.0},
    "A000000185135": {"name": "미나리 패드 전용 페이지", "scroll_steps": 45, "delay": 1.0},
    "A000000248098": {"name": "당근 패드 기획전 페이지", "scroll_steps": 45, "delay": 1.0},
    "A000000200396": {"name": "감자 패드 전용 페이지", "scroll_steps": 40, "delay": 1.0},
    "A000000157075": {"name": "도토리 패드 전용 페이지", "scroll_steps": 40, "delay": 1.0}
}

# 중첩된 웹 컴포넌트(Shadow Root) 내부에 숨겨진 리뷰 데이터를 깊이 탐색하여 추출하는 핵심 JavaScript 코드
JS_DEEP_EXTRACT = """
let inProd = document.querySelector('oy-review-review-in-product');
if (!inProd) return [];
let root1 = inProd.shadowRoot;
if (!root1) return [];

let listProvider = root1.querySelector('oy-review-review-list-provider');
if (!listProvider) return [];
let reviewList = listProvider.querySelector('oy-review-review-list');
if (!reviewList) return [];
let root2 = reviewList.shadowRoot;
if (!root2) return [];

let items = root2.querySelectorAll('oy-review-review-item');
let reviews = [];

items.forEach(item => {
    let itemRoot = item.shadowRoot;
    if (!itemRoot) return;
    
    // 1. 작성자 닉네임 및 피부정보 추출
    let username = "익명";
    let skinTypes = [];
    let userEl = itemRoot.querySelector('oy-review-review-user');
    if (userEl && userEl.shadowRoot) {
        let nameEl = userEl.shadowRoot.querySelector('.name');
        if (nameEl) username = nameEl.textContent.trim();
        
        let skinEls = userEl.shadowRoot.querySelectorAll('.skin-type');
        skinEls.forEach(s => skinTypes.push(s.textContent.trim()));
    }
    
    // 2. 별점 추출 (별 아이콘 컴포넌트 갯수 세기)
    let rating = 0;
    let ratingEl = itemRoot.querySelector('.rating');
    if (ratingEl) {
        rating = ratingEl.querySelectorAll('oy-review-star-icon').length;
    }
    
    // 3. 작성일 추출
    let date = "";
    let dateEl = itemRoot.querySelector('.common-info .date');
    if (dateEl) date = dateEl.textContent.trim();
    
    // 4. 리뷰 상세 본문 추출
    let content = "";
    let contentEl = itemRoot.querySelector('oy-review-review-content');
    if (contentEl && contentEl.shadowRoot) {
        let pEl = contentEl.shadowRoot.querySelector('.content p');
        if (pEl) content = pEl.textContent.trim();
    }
    
    // 5. 구매 옵션명 추출
    let optionName = "";
    let optionEl = itemRoot.querySelector('.goods-option');
    if (optionEl) {
        optionName = optionEl.textContent.trim();
    } else {
        let optEl = itemRoot.querySelector('.option') || itemRoot.querySelector('[class*="option"]');
        if (optEl) optionName = optEl.textContent.trim();
    }
    
    if (username || content) {
        reviews.push({
            username: username,
            skin_types: skinTypes.join(', '),
            rating: rating,
            date: date,
            content: content,
            option_name: optionName
        });
    }
});

return reviews;
"""

def init_driver():
    """Selenium Edge 헤드리스 드라이버 초기화 (창 크기 1920x1080 강제 설정)"""
    print("\n[*] Selenium Edge 드라이버를 초기화하는 중입니다...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080") # 스크롤 차단 방지를 위한 넓은 뷰포트 강제 설정!
    options.binary_location = EDGE_BINARY_PATH
    # 자동화 차단 방지 헤더 설정
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    try:
        driver = webdriver.Edge(options=options)
        print("[*] Edge 드라이버 초기화 및 뷰포트 설정(1920x1080) 완료.")
        return driver
    except Exception as e:
        print(f"[!] 드라이버 초기화 실패: {e}")
        sys.exit(1)

def crawl_raw_reviews_from_page(driver, goods_no, page_info):
    """각 고유 상품 상세 페이지에서 가능한 많은 로우(Raw) 리뷰 데이터를 스크롤하며 수집"""
    url = f"https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo={goods_no}"
    print(f"\n" + "="*60)
    print(f"[*] 크롤링 타겟 페이지: [{goods_no}] {page_info['name']}")
    print(f"[*] URL: {url}")
    print(f"[*] 상세 페이지 이동 중...")
    
    driver.get(url)
    time.sleep(5) # 로딩 안정화 대기
    
    # 1. 리뷰 탭 클릭을 통해 리뷰 동적 컴포넌트 마운트
    print("[*] '리뷰&셔터' 탭 활성화 시도 중...")
    buttons = driver.find_elements(By.TAG_NAME, "button")
    clicked = False
    for btn in buttons:
        try:
            txt = btn.text
            if "리뷰&셔터" in txt or "리뷰 " in txt:
                driver.execute_script("arguments[0].click();", btn)
                clicked = True
                print(f"[*] 리뷰 탭 클릭 성공! (버튼 텍스트: '{txt}')")
                break
        except Exception:
            continue
            
    if not clicked:
        print("[!] 리뷰 탭 활성화 버튼을 직접 클릭하지 못했습니다. 디폴트로 열려있는지 확인합니다.")
        
    time.sleep(3)
    
    # 2. 가상 스크롤 및 수집 루프
    raw_reviews = {}
    steps = page_info["scroll_steps"]
    delay = page_info["delay"]
    
    print(f"[*] 가상 스크롤 수집 루프 시작 (총 {steps}단계 진행)")
    
    for step in range(steps):
        # 쉐도우 루트 내부 깊숙이 파싱하는 JS 코드 실행
        step_reviews = driver.execute_script(JS_DEEP_EXTRACT)
        if step_reviews:
            for r in step_reviews:
                # 닉네임, 날짜, 리뷰 본문 첫 50글자를 조합해 중복 제거용 고유 키 생성
                key = (r['username'], r['date'], r['content'][:50])
                if key not in raw_reviews:
                    raw_reviews[key] = {
                        "goods_no": goods_no,
                        "username": r['username'],
                        "skin_types": r['skin_types'],
                        "rating": r['rating'],
                        "date": r['date'],
                        "content": r['content'],
                        "option_name": r['option_name']
                    }
                    
        # 단순히 scrollBy가 아니라, 하단 높이에 이벤트를 명확히 주기 위해scrollTo를 교차 병합 사용
        if step % 2 == 0:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        else:
            driver.execute_script("window.scrollBy(0, 750);")
            
        if (step + 1) % 15 == 0 or (step + 1) == steps:
            print(f"    - [{step+1}/{steps}] 단계 스크롤 완료 | 현재 페이지 누적 고유 리뷰 수: {len(raw_reviews)}개")
        
        # 딜레이 조절 (약간의 변동성을 주어 봇 탐지 회피)
        time.sleep(delay + random.uniform(0.0, 0.2))
        
    print(f"[*] 수집 종료. [{goods_no}] 페이지에서 총 {len(raw_reviews)}개의 고유 리뷰를 획득했습니다.")
    return list(raw_reviews.values())

def map_reviews_to_target_pads(all_raw_reviews):
    """수집된 대량의 리뷰 풀에 대해 옵션명 및 상품명을 분석하여 스킨푸드 11종 패드로 분류"""
    print("\n" + "="*60)
    print("[*] 11종 스킨푸드 패드로 리뷰 매핑 및 분류를 시작합니다...")
    print("="*60)
    
    # 11종 각 패드별 리뷰 수집소 생성
    categorized_reviews = {pad_name: [] for pad_name in TARGET_PADS.keys()}
    unmapped_count = 0
    
    for r in all_raw_reviews:
        mapped = False
        opt = (r['option_name'] or "").lower()
        g_no = r['goods_no']
        
        # 1. 1차 매핑: 리뷰 카드 내부의 옵션명(option_name) 분석
        for pad_name, info in TARGET_PADS.items():
            for kw in info["keywords"]:
                if kw in opt:
                    categorized_reviews[pad_name].append(r)
                    mapped = True
                    break
            if mapped:
                break
                
        # 2. 2차 매핑 (단품 전용 페이지 대응): 
        # 옵션명이 비어있거나 매핑에 실패한 경우, 해당 리뷰를 긁어온 상품 코드의 디폴트 타겟 패드로 분류
        if not mapped:
            for pad_name, info in TARGET_PADS.items():
                if g_no == info["default_goods"]:
                    categorized_reviews[pad_name].append(r)
                    mapped = True
                    break
                
        if not mapped:
            unmapped_count += 1
            
    print("[*] 매핑 결과 분류 통계:")
    for pad, revs in categorized_reviews.items():
        print(f"    - {pad}: {len(revs)}개 분류 완료")
    print(f"    - 분류되지 않은 기타 옵션 리뷰: {unmapped_count}개")
    
    return categorized_reviews

def balance_reviews(pad_name, reviews, target_total=50):
    """
    평점 균등 분배 샘플링 알고리즘 (Recursive Rating Balancing Algorithm)
    1~5점의 별점을 최대한 10개씩 골고루 섞되, 특정 저평가 리뷰가 부족할 경우 
    남는 목표 수량을 다른 평점 그룹에 균등하게 재귀 재배분하여 정확히 50개를 채움.
    """
    print(f"\n[*] [{pad_name}] 평점 균등 샘플링 진행 중...")
    
    # 평점 그룹별(1점~5점) 리뷰 분류
    reviews_by_rating = {1: [], 2: [], 3: [], 4: [], 5: []}
    for r in reviews:
        score = r["rating"]
        if score in reviews_by_rating:
            reviews_by_rating[score].append(r)
            
    ratings = [1, 2, 3, 4, 5]
    available = {r: len(reviews_by_rating[r]) for r in ratings}
    allocated = {r: 0 for r in ratings}
    
    total_available = sum(available.values())
    if total_available <= target_total:
        print(f"    [!] 가용 리뷰 수({total_available})가 목표량({target_total}) 이하입니다. 전체를 선택합니다.")
        return reviews
        
    remaining_target = target_total
    active_ratings = list(ratings)
    
    # 재귀 배분 루프
    while remaining_target > 0 and active_ratings:
        num_groups = len(active_ratings)
        base_share = remaining_target // num_groups
        if base_share == 0:
            base_share = 1
            
        next_active = []
        for r in active_ratings:
            needed = base_share
            av = available[r] - allocated[r]
            
            if av <= needed:
                allocated[r] += av
                remaining_target -= av
            else:
                allocated[r] += needed
                remaining_target -= needed
                next_active.append(r)
                
        # 한 라운드를 마친 뒤 분배가 교착상태인 경우 비례 추가 분배
        if len(next_active) == len(active_ratings) and remaining_target > 0:
            for r in sorted(next_active, key=lambda x: available[x] - allocated[x], reverse=True):
                if remaining_target > 0 and (available[r] - allocated[r]) > 0:
                    allocated[r] += 1
                    remaining_target -= 1
            break
            
        active_ratings = next_active
        
    # 최종 선택 및 셔플링
    selected_reviews = []
    for r in ratings:
        count = allocated[r]
        revs = reviews_by_rating[r]
        random.shuffle(revs)
        selected_reviews.extend(revs[:count])
        print(f"    - 평점 {r}점: 총 {available[r]}개 중 {count}개 선택")
        
    print(f"    -> 최종 선정 완료: {len(selected_reviews)}개")
    return selected_reviews

def save_to_premium_excel(final_reviews_dict):
    """최종 선별된 11종 패드의 균등 평점 리뷰 데이터를 프리미엄 디자인이 적용된 단일 XLSX 시트로 저장"""
    print(f"\n[*] 엑셀 파일 생성을 준비 중입니다... (파일명: {OUTPUT_FILENAME})")
    
    flat_data = []
    for pad_name, revs in final_reviews_dict.items():
        for r in revs:
            flat_data.append({
                "타겟상품명": pad_name,
                "올리브영 상품코드": r["goods_no"],
                "구매 옵션명": r["option_name"] if r["option_name"] else "단품",
                "작성자": r["username"],
                "피부타입": r["skin_types"],
                "별점": f"{r['rating']}점",
                "작성일": r["date"],
                "리뷰 내용": r["content"]
            })
            
    df = pd.DataFrame(flat_data)
    if df.empty:
        print("[!] 최종 수집 데이터가 존재하지 않아 엑셀 파일을 생성할 수 없습니다.")
        return
        
    columns_order = ["타겟상품명", "올리브영 상품코드", "구매 옵션명", "작성자", "피부타입", "별점", "작성일", "리뷰 내용"]
    df = df[columns_order]
    
    try:
        with pd.ExcelWriter(OUTPUT_FILENAME, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='스킨푸드 패드 리뷰')
            
            workbook = writer.book
            worksheet = writer.sheets['스킨푸드 패드 리뷰']
            
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            
            # 프리미엄 뷰티 올리브 그린 칼라 팔레트 디자인 적용
            header_fill = PatternFill(start_color="33691E", end_color="33691E", fill_type="solid") # 깊은 올리브 그린 헤더
            header_font = Font(name="Malgun Gothic", size=11, bold=True, color="FFFFFF")
            data_font = Font(name="Malgun Gothic", size=10)
            
            thin_border = Border(
                left=Side(style='thin', color='EAEAEA'),
                right=Side(style='thin', color='EAEAEA'),
                top=Side(style='thin', color='EAEAEA'),
                bottom=Side(style='thin', color='EAEAEA')
            )
            
            # 헤더 디자인 반영
            for col_idx in range(1, len(columns_order) + 1):
                cell = worksheet.cell(row=1, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = thin_border
                
            # 데이터 로우 스타일링 및 정렬 처리
            for row in range(2, len(df) + 2):
                for col in range(1, len(columns_order) + 1):
                    cell = worksheet.cell(row=row, column=col)
                    cell.font = data_font
                    cell.border = thin_border
                    
                    # 칼럼별 정렬 최적화
                    # 타겟상품명, 상품코드, 작성자, 별점, 작성일은 정가운데 정렬하여 시각화 효과 극대화
                    if col in [1, 2, 4, 6, 7]:
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    # 리뷰 내용은 왼쪽 정렬 및 자동 개행 (텍스트 랩핑)
                    elif col == 8:
                        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                    else:
                        cell.alignment = Alignment(horizontal="left", vertical="center")
                        
            # 행의 높이 증대
            worksheet.row_dimensions[1].height = 32
            for r in range(2, len(df) + 2):
                worksheet.row_dimensions[r].height = 25
                
            # 열 너비 자동 최적화 맞춤
            for col in worksheet.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    val = str(cell.value or '')
                    # 한글 보정 글자 수 계산
                    byte_len = len(val.encode('utf-8'))
                    visual_len = (byte_len + len(val)) // 2
                    if visual_len > max_len:
                        max_len = visual_len
                # 너무 과도하게 긴 칼럼(리뷰 내용 등) 방지를 위한 적정 한도 제어
                worksheet.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 70)
                
        print(f"\n[+] 프리미엄 엑셀 파일 저장 성공: {os.path.abspath(OUTPUT_FILENAME)}")
        print(f"[+] 최종 저장된 데이터 수: {len(df)}개 행 (11개 제품군 x 최대 50개씩)")
    except Exception as e:
        print(f"[!] 엑셀 저장 도중 에러가 발생했습니다: {e}")

def main():
    print("="*60)
    print("      올리브영 스킨푸드 11종 패드 균등 평점 리뷰 수집기")
    print("="*60)
    
    # 1. Selenium 헤드리스 Edge 드라이버 구동
    driver = init_driver()
    
    all_pages_reviews = []
    
    try:
        # 2. 고유 상품 페이지 6개 목록을 돌며 각각 Raw 리뷰 덩어리 수집
        for idx, (goods_no, page_info) in enumerate(PRODUCT_PAGES.items()):
            print(f"\n[*] [페이지 진행도: {idx+1}/{len(PRODUCT_PAGES)}]")
            page_reviews = crawl_raw_reviews_from_page(driver, goods_no, page_info)
            all_pages_reviews.extend(page_reviews)
            
            # 서버 부하 조절용 세션 전환 쿨타임 대기
            if idx < len(PRODUCT_PAGES) - 1:
                print("[*] 다음 상품 페이지로 이동하기 전 4초간 쿨다운 대기합니다...")
                time.sleep(4)
                
    finally:
        print("\n[*] Selenium 드라이버를 정상 종료합니다.")
        driver.quit()
        
    # 3. 수집된 전체 로우 리뷰를 스킨푸드 11종 패드로 라우팅 분류
    categorized_reviews = map_reviews_to_target_pads(all_pages_reviews)
    
    # 4. 각 패드별 평점 균등 배분 샘플링 실행
    final_selected_reviews = {}
    for pad_name, rev_pool in categorized_reviews.items():
        balanced = balance_reviews(pad_name, rev_pool, target_total=50)
        final_selected_reviews[pad_name] = balanced
        
    # 5. 스타일링된 완성도 높은 프리미엄 엑셀 파일로 출력
    save_to_premium_excel(final_selected_reviews)
    
    print("\n" + "="*60)
    print("      모든 크롤링 및 균등 평점 리뷰 데이터 수집 작업 완료!")
    print("="*60)

if __name__ == "__main__":
    main()
