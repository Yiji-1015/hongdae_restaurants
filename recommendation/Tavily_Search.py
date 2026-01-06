import requests
import json

def tavily_search(query, api_key):
    """
    Tavily Search API를 사용하여 검색을 수행합니다.
    
    Args:
        query (str): 검색할 쿼리
        api_key (str): Tavily API 키
    
    Returns:
        dict: 검색 결과
    """
    url = "https://api.tavily.com/search"
    
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",  # "basic" 또는 "advanced"
        "include_answer": True,
        "max_results": 5
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"에러 발생: {e}")
        return None


# 사용 예시
if __name__ == "__main__":
    # API 키를 여기에 입력하세요
    API_KEY = ""
    
    # 검색 쿼리
    search_query = "요즘 유행하는 음식"
    
    # 검색 실행
    results = tavily_search(search_query, API_KEY)
    
    if results:
        print(f"검색 쿼리: {search_query}\n")
        
        # 답변이 있으면 출력
        if "answer" in results:
            print(f"요약 답변: {results['answer']}\n")
        
        # 검색 결과 출력
        print("검색 결과:")
        for i, result in enumerate(results.get("results", []), 1):
            print(f"\n{i}. {result.get('title', 'N/A')}")
            print(f"   URL: {result.get('url', 'N/A')}")
            print(f"   내용: {result.get('content', 'N/A')[:200]}...")
    else:
        print("검색 결과를 가져오지 못했습니다.")