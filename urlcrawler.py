import time
import csv

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

def scrape_multiple_pages(page_url: str, max_page: int, output_csv: str):
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # 필요시 헤드리스 모드
    driver = webdriver.Chrome(service=service, options=options)

    all_urls = set()

    try:
        driver.get(page_url)
        time.sleep(3)  # 페이지 로딩 대기

        for page in range(1, max_page + 1):
            # ---- (A) 현재 페이지의 상품 URL 수집 ----
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            # 수정된 부분: 선택자를 현재 HTML 구조에 맞게 변경
            # 여러 선택자를 시도하여 더 견고하게 만듦
            cards = []
            selectors = [
                'a._2id8yXpK_k[data-shp-area="list.pd"]',  # 새로운 구조 기반
                'li[class*="flu7YgFW2k"] a[data-shp-area="list.pd"]',  # 리스트 아이템 기반
                'a[data-shp-contents-type="chnl_prod_no"]',  # 콘텐츠 타입 기반
                'a._nlog_click._nlog_impression_element[data-shp-area="list.pd"]'  # 기존 선택자
            ]
            
            # 여러 선택자 시도
            for selector in selectors:
                cards = soup.select(selector)
                if cards:
                    print(f"선택자 '{selector}'로 {len(cards)}개 카드 발견")
                    break
            
            for card in cards:
                href = card.get('href')
                if href:
                    # 상대 URL인 경우 절대 URL로 변환
                    if href.startswith('/'):
                        href = 'https://brand.naver.com' + href
                    all_urls.add(href)

            print(f"[페이지 {page}] 상품 {len(cards)}개 수집 (누적 {len(all_urls)}개)")

            if page == max_page:
                break  # 원하는 페이지 수만큼 돌았다면 종료

            # ---- (C) 페이지네이션에서 다음 페이지 클릭 ----
            # 수정된 페이지네이션 처리
            next_page_found = False
            
            # 1. 숫자 기반 페이지네이션 시도
            next_page_str = str(page + 1)
            pagination_selectors = [
                'div[role="menubar"] a.UWN4IvaQza._nlog_click',  # 기존 선택자
                'a[style*="page"], span[style*="page"]',  # 페이지 스타일 속성
                'a[aria-current="false"]',  # aria 속성
                'div._1MhlCIscR5 span._3c7D-iuXGW'  # 페이지 표시 요소
            ]
            
            for selector in pagination_selectors:
                pagination_links = driver.find_elements(By.CSS_SELECTOR, selector)
                for link in pagination_links:
                    if link.text.strip() == next_page_str:
                        try:
                            link.click()
                            next_page_found = True
                            print(f"페이지 {next_page_str}로 이동 성공")
                            break
                        except Exception as e:
                            print(f"페이지 {next_page_str} 클릭 시도 실패: {e}")
                if next_page_found:
                    break
            
            # 2. '다음' 버튼 시도 (숫자 기반 네비게이션이 실패한 경우)
            if not next_page_found:
                next_button_selectors = [
                    'a:contains("다음")', 
                    'a[aria-label="다음"]', 
                    'a.pagination_next',
                    'a[class*="next"]'
                ]
                
                for selector in next_button_selectors:
                    try:
                        # XPath로 텍스트 포함 요소 찾기 (CSS 선택자에서는 :contains 지원 안 함)
                        if selector == 'a:contains("다음")':
                            next_buttons = driver.find_elements(By.XPATH, "//a[contains(text(), '다음')]")
                        else:
                            next_buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        for btn in next_buttons:
                            try:
                                btn.click()
                                next_page_found = True
                                print("'다음' 버튼으로 이동 성공")
                                break
                            except:
                                continue
                        
                        if next_page_found:
                            break
                    except:
                        continue
            
            if not next_page_found:
                print(f"{page}페이지 이후로 더 이상 페이지 링크를 찾지 못했습니다.")
                break

            time.sleep(3)  # 다음 페이지 로딩 대기

    finally:
        driver.quit()

    # --- 수집된 URL CSV 저장 ---
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["URL"])
        for url in all_urls:
            writer.writerow([url])

    print(f"\n총 {len(all_urls)}개의 상품 URL을 수집했고, {output_csv}에 저장했습니다.")


if __name__ == "__main__":
    start_url = "https://brand.naver.com/lucky567/category/50000803"  # 예시 URL
    scrape_multiple_pages(
        page_url=start_url,
        max_page=3,
        output_csv="product_urls_pagination.csv"
    )