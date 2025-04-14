#!/usr/bin/env python
import os
import time
import csv
from tqdm import tqdm
from urlcrawler import scrape_multiple_pages
from reviewcrawler import crawl_reviews
from productcrawler_loader import get_available_crawlers, load_crawler, get_crawler_functions

def get_user_input(prompt, options=None, default=None):
    """사용자 입력을 받는 함수"""
    if options:
        option_str = '/'.join(options)
        if default:
            prompt = f"{prompt} [{option_str}] (기본값: {default}): "
        else:
            prompt = f"{prompt} [{option_str}]: "
    elif default:
        prompt = f"{prompt} (기본값: {default}): "
    else:
        prompt = f"{prompt}: "
    
    user_input = input(prompt).strip()
    
    if not user_input and default:
        return default
    
    if options and user_input not in options:
        print(f"[ERROR] 유효하지 않은 입력입니다. {options} 중에서 선택해주세요.")
        return get_user_input(prompt, options, default)
    
    return user_input

def get_yes_no_input(prompt, default="y"):
    """예/아니오 형식의 사용자 입력을 받는 함수"""
    default_prompt = "Y/n" if default.lower() == "y" else "y/N"
    user_input = input(f"{prompt} [{default_prompt}]: ").strip().lower()
    
    if not user_input:
        return default.lower() == "y"
    
    return user_input in ["y", "yes", "예"]

def main():
    """
    메인 함수: 대화형으로 사용자 입력을 받아 크롤링 실행
    """
    print("=" * 50)
    print("네이버 스마트스토어 크롤러 (대화형)")
    print("=" * 50)
    
    # 사용 가능한 크롤러 목록 가져오기
    available_crawlers = get_available_crawlers()
    
    if not available_crawlers:
        print("[ERROR] 사용 가능한 productcrawler 모듈을 찾을 수 없습니다.")
        print("최소한 productcrawler_beauty.py가 있어야 합니다.")
        return
    
    # 작업 모드 선택
    print("\n어떤 작업을 수행하시겠습니까?")
    print("1. 리뷰만 수집")
    print("2. 상품 정보만 수집")
    print("3. 리뷰와 상품 정보 모두 수집")
    print("4. 단일 상품 상세 정보만 수집")
    
    mode_choice = get_user_input("작업 번호를 선택하세요", ["1", "2", "3", "4"], "3")
    
    mode_mapping = {
        "1": "reviews",
        "2": "products",
        "3": "both",
        "4": "productinfo"
    }
    
    mode = mode_mapping[mode_choice]
    
    # 상품 크롤러 선택 (상품 정보 수집 시)
    selected_crawler = None
    if mode in ["products", "both", "productinfo"]:
        print("\n어떤 상품 카테고리를 크롤링하시겠습니까?")
        for idx, crawler in enumerate(available_crawlers, 1):
            print(f"{idx}. {crawler['category']}")
        
        crawler_options = [str(i) for i in range(1, len(available_crawlers) + 1)]
        crawler_choice = get_user_input("카테고리 번호를 선택하세요", crawler_options, "1")
        
        selected_crawler = available_crawlers[int(crawler_choice) - 1]
        print(f"[INFO] 선택한 카테고리: {selected_crawler['category']}")
        
        # 선택한 크롤러 모듈 로드
        crawler_module = load_crawler(selected_crawler['category'])
        if not crawler_module:
            print(f"[ERROR] {selected_crawler['category']} 크롤러를 로드할 수 없습니다.")
            return
        
        # 크롤러 함수 가져오기
        crawler_functions = get_crawler_functions(crawler_module)
        if not crawler_functions:
            print(f"[ERROR] {selected_crawler['category']} 크롤러에서 필요한 함수를 찾을 수 없습니다.")
            return
        
        crawl_product_detail = crawler_functions['crawl_product_detail']
        crawl_multiple_products = crawler_functions['crawl_multiple_products']
    
    # URL 입력
    url_prompt = "크롤링할 URL을 입력하세요"
    if mode == "productinfo":
        url_prompt += " (상품 상세 페이지 URL)"
    else:
        url_prompt += " (카테고리 또는 검색 결과 URL)"
    
    url = get_user_input(url_prompt)
    
    # 출력 파일명 입력
    output_prefix = get_user_input("저장할 파일명을 입력하세요 (확장자 제외)", default="navershopping_data")
    
    # 브라우저 모드 설정 (항상 브라우저 창 표시)
    headless = False
    
    # URL 저장 여부 선택
    save_urls = False
    if mode != "productinfo":
        save_urls = get_yes_no_input("수집한 URL 목록을 별도 파일로 저장할까요?", "n")
    
    print("\n입력 정보 확인:")
    print(f"- 작업 모드: {mode}")
    if mode in ["products", "both", "productinfo"]:
        print(f"- 상품 카테고리: {selected_crawler['category']}")
    print(f"- URL: {url}")
    print(f"- 파일명: {output_prefix}")
    print(f"- 브라우저 표시: 활성화")
    print(f"- URL 저장: {'예' if save_urls else '아니오'}")
    
    if not get_yes_no_input("\n위 정보로 크롤링을 시작할까요?", "y"):
        print("크롤링이 취소되었습니다.")
        return
    
    start_time = time.time()
    
    # 단일 상품 상세 정보만 크롤링하는 경우
    if mode == "productinfo":
        print("\n[STEP 1] 상품 상세 정보 수집 시작")
        crawl_product_detail(
            product_url=url,
            output_csv=f"{output_prefix}.csv",
            headless=headless
        )
        
        total_time = time.time() - start_time
        print("\n" + "=" * 50)
        print("크롤링 완료 요약")
        print("=" * 50)
        print(f"- 총 소요 시간: {total_time:.2f}초")
        print(f"- 결과 저장 위치: {output_prefix}.csv, {output_prefix}.json")
        print("=" * 50)
        return

    # STEP 1. 상품 URL 수집 (productinfo 모드가 아닐 경우)
    print("\n[STEP 1] 상품 URL 수집 시작")
    
    # 모든 상품 페이지를 수집하기 위해 아주 큰 값 설정
    max_page = 999  
    url_output = "product_urls.csv" if save_urls else "temp_urls.csv"

    scrape_multiple_pages(
        page_url=url,
        max_page=max_page,
        output_csv=url_output
    )

    # CSV 파일에서 수집한 상품 URL 읽어오기
    product_urls = []
    try:
        with open(url_output, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # 헤더 건너뛰기
            for row in reader:
                product_urls.append(row[0])
    except Exception as e:
        print(f"[ERROR] URL 파일 읽기 실패: {e}")

    if not save_urls and os.path.exists("temp_urls.csv"):
        os.remove("temp_urls.csv")

    if not product_urls:
        print("[ERROR] 상품 URL 수집에 실패했습니다.")
        return

    url_time = time.time() - start_time
    print(f"URL 수집 완료: {len(product_urls)}개 상품 URL 수집 (소요 시간: {url_time:.2f}초)")
    
    # 수집할 URL 개수 제한 옵션
    if len(product_urls) > 10:
        limit_urls = get_yes_no_input(f"\n총 {len(product_urls)}개 상품이 검색되었습니다. URL 개수를 제한하시겠습니까?", "n")
        
        if limit_urls:
            max_urls = int(get_user_input("몇 개의 URL을 처리할까요?", default="10"))
            product_urls = product_urls[:max_urls]
            print(f"URL을 {max_urls}개로 제한합니다.")

    # 리뷰 수집
    total_reviews = 0
    if mode in ['reviews', 'both']:
        # STEP 2. 각 상품별 리뷰 수집
        print(f"\n[STEP 2] 각 상품별 리뷰 수집 시작 (총 {len(product_urls)}개 상품)")
        review_start_time = time.time()

        # 리뷰 출력 파일명 설정
        reviews_output = f"{output_prefix}_reviews.csv" if mode == 'both' else f"{output_prefix}.csv"
        
        # 기존 결과 파일이 있다면 삭제 (append 모드로 실행할 것이므로)
        if os.path.exists(reviews_output):
            if get_yes_no_input(f"기존 파일 {reviews_output}이 있습니다. 덮어쓰시겠습니까?", "y"):
                os.remove(reviews_output)
                print(f"[INFO] 기존 {reviews_output} 파일을 삭제했습니다.")
            else:
                reviews_output = f"{output_prefix}_{int(time.time())}_reviews.csv"
                print(f"[INFO] 새 파일명으로 저장합니다: {reviews_output}")
                
        for idx, url in enumerate(tqdm(product_urls, desc="리뷰 수집 진행", unit="상품")):
            print(f"\n[{idx + 1}/{len(product_urls)}] 상품 리뷰 수집 중: {url}")
            try:
                df = crawl_reviews(
                    target_url=url,
                    max_pages=None,
                    output_csv=reviews_output,
                    return_df=True,
                    append_mode=True
                )
                count = len(df) if df is not None else 0
                print(f"[INFO] {url} 리뷰 수집 완료: {count}건")
                total_reviews += count
            except Exception as e:
                print(f"[ERROR] URL 처리 중 오류 발생: {url} - {str(e)}")

        review_time = time.time() - review_start_time
        print(f"\n리뷰 수집 완료: 총 {total_reviews}건 (소요 시간: {review_time:.2f}초)")

    # 상품 상세 정보 수집
    total_products = 0
    if mode in ['products', 'both']:
        # STEP 3. 각 상품별 상세 정보 수집
        print(f"\n[STEP 3] 각 상품별 상세 정보 수집 시작 (총 {len(product_urls)}개 상품)")
        product_start_time = time.time()
        
        # 상품 정보 출력 파일명 설정
        products_output = f"{output_prefix}_products.csv" if mode == 'both' else f"{output_prefix}.csv"
        
        # 기존 파일 체크
        if os.path.exists(products_output):
            if get_yes_no_input(f"기존 파일 {products_output}이 있습니다. 덮어쓰시겠습니까?", "y"):
                # 다음 단계에서 새로 생성될 것이므로 별도 삭제 불필요
                print(f"[INFO] 기존 파일을 덮어씁니다.")
            else:
                output_prefix = f"{output_prefix}_{int(time.time())}"
                products_output = f"{output_prefix}_products.csv" if mode == 'both' else f"{output_prefix}.csv"
                print(f"[INFO] 새 파일명으로 저장합니다: {products_output}")
        
        # 상품 상세 정보 수집
        products = crawl_multiple_products(
            product_urls=product_urls,
            output_prefix=output_prefix,
            headless=headless
        )
        
        total_products = len(products)
        product_time = time.time() - product_start_time
        print(f"\n상품 정보 수집 완료: 총 {total_products}건 (소요 시간: {product_time:.2f}초)")

    # 최종 결과 요약
    total_time = time.time() - start_time
    
    print("\n" + "=" * 50)
    print("크롤링 완료 요약")
    print("=" * 50)
    print(f"- 총 상품 URL 수집: {len(product_urls)}개")
    
    if mode in ['reviews', 'both']:
        print(f"- 총 리뷰 수집: {total_reviews}건")
        print(f"- 리뷰 수집 시간: {review_time:.2f}초")
        print(f"- 리뷰 저장 위치: {reviews_output}")
    
    if mode in ['products', 'both']:
        print(f"- 총 상품 상세 정보 수집: {total_products}건")
        print(f"- 상품 정보 수집 시간: {product_time:.2f}초")
        print(f"- 상품 정보 저장 위치: {products_output}")
        print(f"- JSON 저장 위치: {output_prefix}_all.json")
    
    print(f"- URL 수집 시간: {url_time:.2f}초")
    print(f"- 총 소요 시간: {total_time:.2f}초")
    print("=" * 50)
    
    print("\n크롤링이 완료되었습니다. 감사합니다!")

if __name__ == "__main__":
    main()