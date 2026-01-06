import json
import ast
import os
from weather_utils import get_weather_info
from claude_api import call_claude, FOOD_TAG_CLASSIFIER_SYSTEM_PROMPT

# ============================================================================
# 1. 설정 및 상수
# ============================================================================

# API 키 (여기에 입력하세요)
MY_API_KEY = "" 

# 위치 (성남시)
LAT, LON = 37.4201, 127.1262

# 날씨/기온에 따른 가중치 점수표
WEATHER_TO_FOOD_SCORE = {
    # 날씨
    "RAINY":  {"SOUP": 3, "FRIED": 3, "NOODLES": 2, "SPICY": 1},
    "SNOWY":  {"HOT_SERVE": 5, "SOUP": 3, "HEAVY": 2, "CREAMY": 2},
    "SUNNY":  {"LIGHT": 3, "DRY": 2, "COLD_SERVE": 1},
    "CLOUDY": {"NOODLES": 3, "SPICY": 2, "CREAMY": 1},
    
    # 기온
    "HOT":    {"COLD_SERVE": 5, "LIGHT": 3, "SPICY": 2},
    "COLD":   {"HOT_SERVE": 5, "SOUP": 4, "HEAVY": 2, "RICE": 2},
    "NORMAL": {} 
}

# 기본 데이터 (파일 오류 시 사용)
DEFAULT_MENU = [
    {"name": "김치찌개", "tags": ["SOUP", "SPICY", "HOT_SERVE", "HEAVY", "RICE"]},
    {"name": "삼겹살", "tags": ["HEAVY", "HOT_SERVE", "FRIED", "DRY"]},
    {"name": "냉면", "tags": ["NOODLES", "COLD_SERVE", "LIGHT", "SOUP"]},
    {"name": "치킨", "tags": ["FRIED", "HOT_SERVE", "HEAVY", "DRY"]}
]

# ============================================================================
# 2. 유틸리티 함수
# ============================================================================

def load_menu_db(filename="menus.json"):
    """JSON 파일을 읽고 중복을 제거하여 반환합니다."""
    data = []
    
    # 1. 파일 읽기
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"📂 '{filename}' 로드 성공!")
        except Exception as e:
            print(f"⚠️ 파일 읽기 실패 ({e}). 기본 데이터를 사용합니다.")
            data = DEFAULT_MENU
    else:
        print("⚠️ 파일이 없습니다. 기본 데이터를 사용합니다.")
        data = DEFAULT_MENU

    # 2. 중복 제거 (이름 기준)
    unique_menus = []
    seen_names = set()
    
    for menu in data:
        if menu["name"] not in seen_names:
            unique_menus.append(menu)
            seen_names.add(menu["name"])
    
    print(f"📊 총 {len(unique_menus)}개의 메뉴 준비 완료 (중복 제거됨)")
    return unique_menus


def get_user_intent_tags(user_input, api_key):
    """Claude API를 호출하여 사용자 의도를 파악합니다."""
    if not user_input.strip():
        return {}
        
    try:
        response = call_claude(
            prompt=user_input,
            system_prompt=FOOD_TAG_CLASSIFIER_SYSTEM_PROMPT,
            api_key=api_key
        )
        return ast.literal_eval(response)
    except Exception as e:
        print(f"⚠️ 의도 분석 실패: {e}")
        return {}


def calculate_recommendations(menu_list, weather_desc, temp_flag, user_tags):
    """
    메뉴별 점수를 계산하고, 점수 내역(reason)을 포함하여 반환합니다.
    """
    # 1. 날씨 점수표 미리 만들기
    weather_pref = {}
    if weather_desc in WEATHER_TO_FOOD_SCORE:
        for tag, score in WEATHER_TO_FOOD_SCORE[weather_desc].items():
            weather_pref[tag] = weather_pref.get(tag, 0) + score
    if temp_flag in WEATHER_TO_FOOD_SCORE:
        for tag, score in WEATHER_TO_FOOD_SCORE[temp_flag].items():
            weather_pref[tag] = weather_pref.get(tag, 0) + score

    scored_results = []
    
    # 2. 각 메뉴 점수 계산
    for menu in menu_list:
        total_score = 0
        reasons = [] # 점수 획득 사유 저장용
        menu_tags = set(menu['tags'])
        
        # (A) 날씨 점수 계산
        for tag, score in weather_pref.items():
            if tag in menu_tags:
                total_score += score
                reasons.append(f"날씨({tag} +{score})")
        
        # (B) 사용자 취향 점수 계산 (가중치 2배)
        for tag, score in user_tags.items():
            if tag in menu_tags:
                weighted_score = score * 2.0
                total_score += weighted_score
                reasons.append(f"취향({tag} +{weighted_score:.0f})")
                
        scored_results.append({
            "name": menu["name"],
            "score": total_score,
            "reasons": reasons, # 상세 내역 추가
            "tags": menu["tags"]
        })
    
    # 점수 높은 순 정렬
    return sorted(scored_results, key=lambda x: x["score"], reverse=True)


# ============================================================================
# 3. 메인 실행
# ============================================================================

if __name__ == "__main__":
    # 1. 메뉴 로드
    MENU_DB = load_menu_db("menus.json")

    # 2. 날씨 확인
    print("\n🌤️ [시스템] 현재 날씨 정보를 조회합니다...")
    weather_desc, temp_flag = get_weather_info(LAT, LON)
    
    if not weather_desc:
        weather_desc, temp_flag = "SUNNY", "NORMAL"
        print("   (날씨 조회 실패로 기본값 사용)")
    
    print(f"   👉 상태: {weather_desc} / 기온: {temp_flag}")

    # 3. 사용자 입력
    print("\n🍽️ [시스템] 드시고 싶은 메뉴 스타일이 있나요?")
    print("   (예: '비오는데 따뜻한 국물 먹고 싶어', '스트레스 받아서 매운거!')")
    user_input = input("   입력 >> ")
    
    # 4. 의도 분석
    print("\n🧠 [시스템] 사용자의 의도를 분석 중입니다...")
    user_tags = get_user_intent_tags(user_input, MY_API_KEY)
    print(f"   👉 분석 결과: {user_tags}")
    
    # 5. 추천 결과 계산
    results = calculate_recommendations(MENU_DB, weather_desc, temp_flag, user_tags)
    
    # 6. 최종 출력 (상세 내역 포함)
    print("\n" + "="*50)
    print(f"🏆 오늘의 추천 메뉴 (Top 3)")
    print("="*50)
    
    if not results:
        print("😭 추천할 메뉴가 없습니다.")
    else:
        for i, item in enumerate(results[:3]):
            print(f"\n🥇 {i+1}위: [{item['name']}] (총점: {item['score']}점)")
            
            # 상세 점수 이유 출력
            if item['reasons']:
                print(f"   └─ 🔍 점수 요인: {', '.join(item['reasons'])}")
            else:
                print(f"   └─ (특별한 가중치 없음)")
    
    print("\n" + "="*50)