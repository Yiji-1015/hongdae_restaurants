def get_user_preferences(user_input, api_key):
    """사용자 입력에서 태그와 가중치를 추출"""
    response = call_claude(
        prompt=user_input,
        system_prompt=FOOD_TAG_CLASSIFIER_SYSTEM_PROMPT,
        api_key=api_key
    )
    try:
        # 문자열 "{'A': 1}" 을 딕셔너리로 변환
        return ast.literal_eval(response)
    except:
        return {}

def calculate_final_score(menu_list, weather_tags, user_tags):
    """
    [메뉴별 최종 점수 계산]
    최종 점수 = (날씨 가중치 합) + (사용자 선호 가중치 합 * 2) 
    * 사용자의 의견이 더 중요하므로 user_tags에 2배 가중치를 줄 수도 있음
    """
    scored_menu = []

    for menu in menu_list:
        total_score = 0
        menu_tags = set(menu['tags']) # 검색 속도를 위해 set 변환

        # 1. 날씨 점수 반영
        for tag, score in weather_tags.items():
            if tag in menu_tags:
                total_score += score
        
        # 2. 사용자 선호 점수 반영 (우선순위 높음 -> 가중치 1.5배 or 2배 적용 가능)
        for tag, score in user_tags.items():
            if tag in menu_tags:
                total_score += (score * 2.0) # 사용자가 먹고 싶은 게 짱임

        scored_menu.append((menu['name'], total_score))

    # 점수 높은 순 정렬
    scored_menu.sort(key=lambda x: x[1], reverse=True)
    return scored_menu

# --- 실행 예시 ---
if __name__ == "__main__":
    # 1. 상황 가정
    # 날씨: 비옴 (RAINY) -> {"SOUP": 3, "FRIED": 2, "SPICY": 1}
    weather_score = {"SOUP": 3, "FRIED": 2, "SPICY": 1}
    
    # 사용자: "오늘 스트레스 받아서 엄청 매운 거 땡겨!"
    user_input = "오늘 스트레스 받아서 엄청 매운 거 땡겨!"
    
    # 2. LLM 호출 결과 (가정)
    # 엄청 매운 거 -> SPICY: 5
    # 스트레스 -> (보통 매운걸로 품) -> HEAVY: 3 (추론)
    user_pref_score = {"SPICY": 5, "HEAVY": 3} 
    
    print(f"🌦️ 날씨 점수: {weather_score}")
    print(f"👤 유저 점수: {user_pref_score}")
    
    # 3. 메뉴 DB (앞서 만든 menu_db 사용)
    # - 짬뽕 tags: [SOUP, SPICY, HEAVY, ...]
    # - 탕수육 tags: [FRIED, HEAVY, ...]
    
    # [짬뽕 점수 계산]
    # 날씨: SOUP(3) + SPICY(1) = 4점
    # 유저: SPICY(5*2) + HEAVY(3*2) = 16점
    # 총점: 20점
    
    # [탕수육 점수 계산]
    # 날씨: FRIED(2) = 2점
    # 유저: HEAVY(3*2) = 6점
    # 총점: 8점
    
    print("\n🏆 추천 결과: 짬뽕 승리!")