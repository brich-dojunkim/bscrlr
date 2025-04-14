import re
import time
import json
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver(headless=True):
    """Chrome 웹드라이버 설정"""
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("window-size=1920x1080")
    options.add_argument("disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(3)
    return driver

def safe_find_element(driver, by, selector, wait_time=5):
    """안전하게 요소 찾기 (명시적 대기 사용)"""
    try:
        element = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((by, selector))
        )
        return element
    except (TimeoutException, NoSuchElementException):
        return None

def safe_find_elements(driver, by, selector, wait_time=5):
    """안전하게 요소들 찾기 (명시적 대기 사용)"""
    try:
        elements = WebDriverWait(driver, wait_time).until(
            EC.presence_of_all_elements_located((by, selector))
        )
        return elements
    except (TimeoutException, NoSuchElementException):
        return []

def safe_click(driver, element, retry=3, scroll_first=True):
    """안전하게 요소를 클릭하는 함수"""
    for attempt in range(retry):
        try:
            if scroll_first:
                # 요소로 스크롤
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.5)
            
            # 클릭 시도
            element.click()
            time.sleep(1)
            return True
        except (ElementNotInteractableException, TimeoutException) as e:
            print(f"클릭 시도 {attempt+1}/{retry} 실패: {e}")
            time.sleep(1)
            
            if attempt == retry - 1:
                # 마지막 시도에서 JavaScript로 클릭 시도
                try:
                    driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception as js_e:
                    print(f"JavaScript 클릭도 실패: {js_e}")
                    return False
        except Exception as e:
            print(f"기타 오류 발생: {e}")
            return False
    
    return False

def extract_text(element):
    """요소에서 텍스트 추출 (None 처리)"""
    return element.text.strip() if element else ""

def extract_product_basic_info(soup):
    """상품 기본 정보 추출"""
    basic_info = {}
    
    # 상품명 추출
    title_tag = soup.find('h3', {'class': '_22kNQuEXmb'})
    basic_info['product_title'] = extract_text(title_tag)
    
    # 상품 번호, 상태, 브랜드 등 추출
    try:
        table = soup.find('table', {'class': '_1_UiXWHt__'})
        if table:
            rows = table.find_all('tr')
            for row in rows:
                headers = row.find_all('th')
                data_cells = row.find_all('td')
                
                for i, header in enumerate(headers):
                    if i < len(data_cells):
                        header_text = header.text.strip()
                        value_text = data_cells[i].text.strip()
                        
                        if header_text == "상품번호":
                            basic_info['product_id'] = value_text
                        elif header_text == "상품상태":
                            basic_info['product_status'] = value_text
                        elif header_text == "제조사":
                            basic_info['manufacturer'] = value_text
                        elif header_text == "브랜드":
                            basic_info['brand'] = value_text
                        elif header_text == "원산지":
                            basic_info['origin'] = value_text
    except Exception as e:
        print(f"기본 정보 추출 중 오류: {e}")
    
    return basic_info

def extract_product_specs(soup):
    """상품 상세 스펙 추출 - 뷰티 제품 특화"""
    specs = {}
    
    try:
        # 상세 스펙이 있는 테이블 (두 번째 테이블)
        tables = soup.find_all('table', {'class': '_1_UiXWHt__'})
        if len(tables) >= 2:
            detail_table = tables[1]
            rows = detail_table.find_all('tr')
            
            for row in rows:
                headers = row.find_all('th')
                data_cells = row.find_all('td')
                
                for i, header in enumerate(headers):
                    if i < len(data_cells):
                        header_text = header.text.strip()
                        value_text = data_cells[i].text.strip()
                        
                        # 주요 스펙 정보 추출 - 뷰티 제품 특화 필드
                        specs[header_text] = value_text
    except Exception as e:
        print(f"상세 스펙 추출 중 오류: {e}")
    
    # 뷰티 제품 특화 필드 확인
    beauty_fields = [
        "사용부위", "피부타입", "종류", "자외선차단지수", 
        "주요제품특징", "효능", "용량", "성분"
    ]
    
    # 누락된 필드에 빈 값 추가
    for field in beauty_fields:
        if field not in specs:
            specs[field] = ""
    
    return specs

def extract_price_info(soup):
    """가격 정보 추출"""
    price_info = {}
    
    try:
        # 판매가 추출
        price_elem = soup.find('span', {'class': '_1LY7DqCnwR'})
        if price_elem:
            price_text = price_elem.text.strip()
            # 숫자만 추출
            price = re.sub(r'[^\d]', '', price_text)
            price_info['price'] = price
        
        # 할인 정보 추출
        discount_elem = soup.find('span', {'class': 'discount'})
        if discount_elem:
            discount_text = discount_elem.text.strip()
            price_info['discount'] = discount_text
    except Exception as e:
        print(f"가격 정보 추출 중 오류: {e}")
    
    return price_info

def extract_shipping_info(soup):
    """배송 정보 추출"""
    shipping_info = {}
    
    try:
        # 배송 정보 테이블 (페이지 하단 부분)
        trade_terms_table = soup.find('div', {'class': 'trade_terms_info'})
        if trade_terms_table:
            table = trade_terms_table.find('table')
            if table:
                rows = table.find_all('tr')
                
                for row in rows:
                    header = row.find('th')
                    data_cell = row.find('td')
                    
                    if header and data_cell:
                        header_text = header.text.strip()
                        value_text = data_cell.text.strip()
                        
                        if "배송방법" in header_text:
                            shipping_info['shipping_method'] = value_text
                        elif "주문 이후 예상되는 배송기간" in header_text:
                            shipping_info['shipping_period'] = value_text
                        elif "소비자가 부담하는 반품비용" in header_text:
                            shipping_info['return_cost'] = value_text
    except Exception as e:
        print(f"배송 정보 추출 중 오류: {e}")
    
    return shipping_info

def extract_product_tags(soup):
    """관련 태그 추출"""
    tags = []
    
    try:
        tag_links = soup.find_all('a', {'class': '_3SMi-TrYq2'})
        for tag_link in tag_links:
            tag_text = tag_link.text.strip()
            if tag_text.startswith('#'):
                tags.append(tag_text)
    except Exception as e:
        print(f"태그 정보 추출 중 오류: {e}")
    
    return tags

def extract_preference_analysis(soup):
    """구매 선호도 분석 추출 - 뷰티 제품 특화"""
    preference = {}
    
    try:
        # 구매 선호도 영역
        preference_div = soup.find('div', {'class': 'bd_3GILa'})
        if preference_div:
            # 피부 타입별 선호도
            items = preference_div.find_all('li', {'class': 'bd_WRUDg'})
            for item in items:
                try:
                    type_elem = item.find('div', {'class': 'bd_3Kurp'})
                    score_elem = item.find('div', {'class': 'bd_LIZeW'})
                    
                    if type_elem and score_elem:
                        skin_type = type_elem.text.strip()
                        # 높이 값에서 퍼센트 추출
                        style = score_elem.get('style', '')
                        percent_match = re.search(r'height:\s*([0-9.]+)%', style)
                        if percent_match:
                            score = percent_match.group(1)
                            preference[skin_type] = score
                except Exception as item_e:
                    print(f"선호도 항목 추출 중 오류: {item_e}")
    except Exception as e:
        print(f"구매 선호도 추출 중 오류: {e}")
    
    return preference

def extract_product_images(soup):
    """상품 이미지 URL 추출"""
    images = []
    
    try:
        # 상품 썸네일 이미지
        thumb_img = soup.find('img', {'class': '_25CKxIKjAk'})
        if thumb_img and 'src' in thumb_img.attrs:
            images.append(thumb_img['src'])
        
        # 상세 설명 이미지
        detail_imgs = soup.find_all('img', {'class': 'se-image-resource'})
        for img in detail_imgs:
            if 'src' in img.attrs:
                images.append(img['src'])
    except Exception as e:
        print(f"이미지 URL 추출 중 오류: {e}")
    
    return images

def extract_promotion_info(soup):
    """프로모션 정보 추출"""
    promotion = {}
    
    try:
        # 쿠폰 정보
        coupon_div = soup.find('div', {'class': '_3l8UUYnfmI'})
        if coupon_div:
            # 쿠폰 타이틀
            title_elem = coupon_div.find('div', {'class': '_6m0rQkziLj'})
            if title_elem:
                promotion['coupon_title'] = title_elem.text.strip()
            
            # 할인 금액
            discount_elem = coupon_div.find('span', {'class': '_2SuxywSpjf'})
            if discount_elem:
                promotion['discount_amount'] = discount_elem.text.strip()
            
            # 최소 주문 금액
            min_order_elem = coupon_div.find('div', {'class': '_2DIMjdlZpO'})
            if min_order_elem:
                promotion['min_order_amount'] = min_order_elem.text.strip()
    except Exception as e:
        print(f"프로모션 정보 추출 중 오류: {e}")
    
    return promotion

def extract_related_products(soup):
    """관련 상품 정보 추출"""
    related_products = []
    
    try:
        product_items = soup.find_all('li', {'class': '_1rY1-Sog8x'})
        for item in product_items:
            product = {}
            
            # 상품명
            title_elem = item.find('p', {'class': '_33pMQzgHDp'})
            if title_elem:
                product['title'] = title_elem.text.strip()
            
            # 가격
            price_elem = item.find('span', {'class': '_3A6Qt4xeM6'})
            if price_elem:
                product['price'] = price_elem.text.strip()
            
            # 판매자
            seller_elem = item.find('p', {'class': '_3XPfyP0knm'})
            if seller_elem:
                product['seller'] = seller_elem.text.strip()
            
            # 이미지 URL
            img_elem = item.find('img', {'class': '_25CKxIKjAk'})
            if img_elem and 'src' in img_elem.attrs:
                product['image_url'] = img_elem['src']
            
            # 원본 상품 정보 추가
            product['source_product_id'] = ""  # 후에 채워질 필드
            
            if product:
                related_products.append(product)
    except Exception as e:
        print(f"관련 상품 정보 추출 중 오류: {e}")
    
    return related_products

def extract_beauty_specific_info(soup):
    """뷰티 제품 특화 정보 추출"""
    beauty_info = {}
    
    try:
        # 화장품 성분 정보 (성분 목록)
        ingredient_section = soup.find(string=lambda text: text and '화장품법에 따라 기재' in text)
        if ingredient_section:
            parent = ingredient_section.parent
            if parent:
                ingredients_text = parent.text.strip()
                beauty_info['ingredients'] = ingredients_text
        
        # 기능성 화장품 정보
        functional_section = soup.find(string=lambda text: text and '기능성 화장품' in text)
        if functional_section:
            parent = functional_section.parent
            if parent:
                functional_text = parent.text.strip()
                beauty_info['functional_info'] = functional_text
                
        # 사용 시 주의사항
        caution_section = soup.find(string=lambda text: text and '사용할 때의 주의사항' in text)
        if caution_section:
            parent = caution_section.parent
            if parent:
                caution_text = parent.text.strip()
                beauty_info['caution'] = caution_text
    except Exception as e:
        print(f"뷰티 특화 정보 추출 중 오류: {e}")
    
    return beauty_info

def crawl_product_detail(product_url, output_csv=None, headless=True):
    """상품 상세 페이지 크롤링 - 뷰티 제품 특화"""
    if product_url.startswith('/'):
        product_url = 'https://brand.naver.com' + product_url
    
    driver = setup_driver(headless=headless)
    product_data = {}
    
    try:
        # 상품 페이지 로드
        print(f"[INFO] 상품 URL 열기: {product_url}")
        driver.get(product_url)
        time.sleep(3)
        
        # 페이지 소스 가져오기
        html_source = driver.page_source
        soup = BeautifulSoup(html_source, 'html.parser')
        
        # 필요한 정보 추출
        product_data['url'] = product_url
        product_data['crawled_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
        product_data['category'] = 'beauty'  # 뷰티 카테고리 명시
        
        # 상품 기본 정보
        basic_info = extract_product_basic_info(soup)
        product_data.update(basic_info)
        
        # 상품 상세 스펙 (뷰티 제품 특화)
        specs = extract_product_specs(soup)
        product_data['specifications'] = specs
        
        # 가격 정보
        price_info = extract_price_info(soup)
        product_data.update(price_info)
        
        # 배송 정보
        shipping_info = extract_shipping_info(soup)
        product_data['shipping_info'] = shipping_info
        
        # 관련 태그
        tags = extract_product_tags(soup)
        product_data['tags'] = tags
        
        # 구매 선호도 분석 (피부 타입별)
        preference = extract_preference_analysis(soup)
        product_data['preference_analysis'] = preference
        
        # 이미지 URL
        images = extract_product_images(soup)
        product_data['image_urls'] = images
        
        # 프로모션 정보
        promotion = extract_promotion_info(soup)
        product_data['promotion'] = promotion
        
        # 관련 상품 정보
        related_products = extract_related_products(soup)
        # 원본 상품 ID 추가
        for product in related_products:
            product['source_product_id'] = product_data.get('product_id', '')
        
        product_data['related_products'] = related_products
        
        # 뷰티 제품 특화 정보
        beauty_info = extract_beauty_specific_info(soup)
        product_data['beauty_info'] = beauty_info
        
        # 상세 정보 펼치기 버튼 클릭 시도
        try:
            more_button = safe_find_element(driver, By.CSS_SELECTOR, '._1gG8JHE9Zc')
            if more_button and more_button.is_displayed():
                safe_click(driver, more_button)
                time.sleep(2)
                
                # 펼쳐진 정보 추가 크롤링
                html_source = driver.page_source
                soup = BeautifulSoup(html_source, 'html.parser')
                
                # 추가 뷰티 정보 크롤링
                additional_beauty_info = extract_beauty_specific_info(soup)
                product_data['beauty_info'].update(additional_beauty_info)
        except Exception as e:
            print(f"[WARN] 상세 정보 펼치기 버튼 클릭 중 오류: {e}")
        
        # 결과 출력
        print(f"[INFO] 상품 '{product_data.get('product_title', '알 수 없음')}' 정보 수집 완료")
        
        # CSV로 저장 (옵션) - 단일 상품 크롤링 시에만
        if output_csv and not isinstance(output_csv, bool):
            # 중첩된 딕셔너리와 리스트를 일차원 데이터로 변환
            flat_data = {}
            for key, value in product_data.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        flat_data[f"{key}_{sub_key}"] = sub_value
                elif isinstance(value, list) and key != "related_products":
                    flat_data[key] = "|".join(str(item) for item in value)
                else:
                    flat_data[key] = value
            
            # 관련 상품은 별도 CSV로 저장
            if "related_products" in product_data and product_data["related_products"]:
                related_df = pd.DataFrame(product_data["related_products"])
                related_csv = output_csv.replace(".csv", "_related_products.csv")
                related_df.to_csv(related_csv, index=False, encoding='utf-8-sig')
                print(f"[INFO] 관련 상품 정보 CSV 저장 완료: {related_csv}")
            
            # 메인 데이터 저장
            df = pd.DataFrame([flat_data])
            df.to_csv(output_csv, index=False, encoding='utf-8-sig')
            print(f"[INFO] 상품 정보 CSV 저장 완료: {output_csv}")
            
            # JSON 파일로도 저장
            json_file = output_csv.replace(".csv", ".json")
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(product_data, f, ensure_ascii=False, indent=4)
            print(f"[INFO] 상품 정보 JSON 저장 완료: {json_file}")
        
        return product_data
        
    except Exception as e:
        print(f"[ERROR] 상품 정보 크롤링 중 오류 발생: {e}")
        return {}
    
    finally:
        driver.quit()

def crawl_multiple_products(product_urls, output_prefix="product_detail", headless=True):
    """여러 상품 페이지 크롤링 - 뷰티 제품 특화 (단일 CSV 파일로 저장)"""
    all_products = []
    all_related_products = []
    
    for idx, url in enumerate(product_urls):
        print(f"\n[{idx+1}/{len(product_urls)}] 상품 정보 수집 중: {url}")
        try:
            # 상품 정보 크롤링 (CSV 저장 비활성화)
            product_data = crawl_product_detail(
                product_url=url,
                output_csv=False,  # 개별 CSV 저장 안 함
                headless=headless
            )
            
            if product_data:
                # 상품 데이터 추가
                all_products.append(product_data)
                
                # 관련 상품 데이터 추가
                if "related_products" in product_data and product_data["related_products"]:
                    all_related_products.extend(product_data["related_products"])
            
            # 서버 부하를 줄이기 위해 대기
            time.sleep(2)
            
        except Exception as e:
            print(f"[ERROR] URL 처리 중 오류 발생: {url} - {str(e)}")
    
    # 처리된 상품이 없으면 빈 리스트 반환
    if not all_products:
        print("[WARN] 수집된 상품 정보가 없습니다.")
        return []
    
    # 중첩된 딕셔너리와 리스트를 일차원 데이터로 변환
    flat_products = []
    for product in all_products:
        flat_data = {}
        for key, value in product.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flat_data[f"{key}_{sub_key}"] = sub_value
            elif isinstance(value, list) and key != "related_products":
                flat_data[key] = "|".join(str(item) for item in value)
            elif key != "related_products":  # 관련 상품은 별도 처리
                flat_data[key] = value
        flat_products.append(flat_data)
    
    # 전체 상품 정보를 하나의 CSV 파일로 저장
    products_df = pd.DataFrame(flat_products)
    products_csv = f"{output_prefix}.csv"
    products_df.to_csv(products_csv, index=False, encoding='utf-8-sig')
    print(f"[INFO] 전체 상품 정보 CSV 저장 완료: {products_csv} (총 {len(flat_products)}개 상품)")
    
    # 관련 상품 정보를 하나의 CSV 파일로 저장
    if all_related_products:
        related_df = pd.DataFrame(all_related_products)
        related_csv = f"{output_prefix}_related_products.csv"
        related_df.to_csv(related_csv, index=False, encoding='utf-8-sig')
        print(f"[INFO] 관련 상품 정보 CSV 저장 완료: {related_csv} (총 {len(all_related_products)}개 관련 상품)")
    
    # 전체 결과를 하나의 JSON으로 저장
    with open(f"{output_prefix}_all.json", 'w', encoding='utf-8') as f:
        json.dump(all_products, f, ensure_ascii=False, indent=4)
    print(f"[INFO] 전체 상품 정보 JSON 저장 완료: {output_prefix}_all.json")
    
    return all_products


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='네이버 스마트스토어 뷰티 제품 상세 정보 크롤러')
    parser.add_argument('--url', type=str, help='크롤링할 상품 URL')
    parser.add_argument('--urls_file', type=str, help='크롤링할 상품 URL 목록 파일 (.txt 또는 .csv)')
    parser.add_argument('--output', type=str, default='beauty_product_detail.csv', help='결과를 저장할 CSV 파일명')
    parser.add_argument('--no-headless', action='store_true', help='헤드리스 모드 비활성화 (브라우저 표시)')
    
    args = parser.parse_args()
    
    # URL이 직접 제공된 경우
    if args.url:
        crawl_product_detail(
            product_url=args.url,
            output_csv=args.output,
            headless=(not args.no_headless)
        )
    
    # URL 목록 파일이 제공된 경우
    elif args.urls_file:
        product_urls = []
        
        # 파일 확장자에 따라 처리
        if args.urls_file.endswith('.csv'):
            # CSV 파일에서 URL 목록 읽기
            df = pd.read_csv(args.urls_file)
            # 첫 번째 열에 URL이 있다고 가정
            product_urls = df.iloc[:, 0].tolist()
        else:
            # 텍스트 파일에서 URL 목록 읽기
            with open(args.urls_file, 'r', encoding='utf-8') as f:
                product_urls = [line.strip() for line in f if line.strip()]
        
        if not product_urls:
            print("[ERROR] URL 목록이 비어 있습니다.")
        else:
            print(f"[INFO] 총 {len(product_urls)}개의 URL을 크롤링합니다.")
            output_prefix = args.output.replace(".csv", "")
            crawl_multiple_products(
                product_urls=product_urls,
                output_prefix=output_prefix,
                headless=(not args.no_headless)
            )
    
    else:
        print("[ERROR] --url 또는 --urls_file 인자가 필요합니다.")
        parser.print_help()