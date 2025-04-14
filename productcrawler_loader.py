import importlib
import os
import re

def get_available_crawlers():
    """
    폴더 내 사용 가능한 모든 productcrawler 모듈을 찾아 반환
    """
    crawlers = []
    
    # 디버깅을 위한 정보 출력
    print("[DEBUG] 현재 디렉토리:", os.getcwd())
    print("[DEBUG] 디렉토리 내 파일:", os.listdir('.'))
    
    # 현재 디렉토리의 모든 파일 탐색
    for file in os.listdir('.'):
        # productcrawler_xxx.py 패턴의 파일 찾기
        if re.match(r'productcrawler_[a-zA-Z0-9_]+\.py$', file):
            # 파일 이름에서 확장자 제거
            module_name = file[:-3]
            # 카테고리 이름 추출 (productcrawler_ 이후 부분)
            category = module_name.split('productcrawler_')[1]
            crawlers.append({
                'module': module_name,
                'category': category
            })
            print(f"[DEBUG] 크롤러 발견: {module_name}, 카테고리: {category}")
    
    return crawlers

def load_crawler(category):
    """
    지정된 카테고리의 크롤러 모듈을 동적으로 로드
    
    Args:
        category (str): 크롤러 카테고리 이름 (예: beauty, fashion)
    
    Returns:
        module: 로드된 크롤러 모듈
    """
    module_name = f"productcrawler_{category}"
    
    try:
        print(f"[DEBUG] 모듈 로드 시도: {module_name}")
        # 동적으로 모듈 임포트
        crawler_module = importlib.import_module(module_name)
        print(f"[DEBUG] 모듈 로드 성공: {module_name}")
        # 모듈에 있는 모든 함수 출력
        print(f"[DEBUG] 모듈 내 함수들: {dir(crawler_module)}")
        return crawler_module
    except ImportError as e:
        print(f"[ERROR] {module_name} 모듈을 찾을 수 없습니다: {e}")
        return None

def get_crawler_functions(module):
    """
    크롤러 모듈에서 필요한 함수들을 추출
    
    Args:
        module: 크롤러 모듈
    
    Returns:
        dict: 크롤러 함수 사전
    """
    if not module:
        return None
    
    try:
        # 필수 함수 확인
        required_functions = [
            'crawl_product_detail', 
            'crawl_multiple_products'
        ]
        
        functions = {}
        for func_name in required_functions:
            if hasattr(module, func_name):
                print(f"[DEBUG] 함수 발견: {func_name}")
                functions[func_name] = getattr(module, func_name)
            else:
                print(f"[ERROR] 모듈에 필요한 함수 {func_name}이(가) 없습니다.")
                return None
        
        return functions
    except Exception as e:
        print(f"[ERROR] 크롤러 함수 추출 중 오류: {e}")
        return None