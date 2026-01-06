import streamlit as st
import json
import ast
import os
from weather_utils import get_weather_info
from claude_api import call_claude, FOOD_TAG_CLASSIFIER_SYSTEM_PROMPT

# ============================================================================
# 페이지 설정
# ============================================================================
st.set_page_config(
    page_title="🍽️ 오늘 뭐 먹지?",
    page_icon="🍽️",
    layout="wide"
)

# ============================================================================
# 설정 및 상수
# ============================================================================

# API 키
MY_API_KEY = ""

# 위치 (성남시)
LAT, LON = 37.4201, 127.1262

# 날씨/기온에 따른 가중치 점수표
WEATHER_TO_FOOD_SCORE = {
    "RAINY":  {"SOUP": 3, "FRIED": 3, "NOODLES": 2, "SPICY": 1},
    "SNOWY":  {"HOT_SERVE": 5, "SOUP": 3, "HEAVY": 2, "CREAMY": 2},
    "SUNNY":  {"LIGHT": 3, "DRY": 2, "COLD_SERVE": 1},
    "CLOUDY": {"NOODLES": 3, "SPICY": 2, "CREAMY": 1},
    "HOT":    {"COLD_SERVE": 5, "LIGHT": 3, "SPICY": 2},
    "COLD":   {"HOT_SERVE": 5, "SOUP": 4, "HEAVY": 2, "RICE": 2},
    "NORMAL": {} 
}

# 기본 데이터
DEFAULT_MENU = [
    {"name": "김치찌개", "tags": ["SOUP", "SPICY", "HOT_SERVE", "HEAVY", "RICE"]},
    {"name": "삼겹살", "tags": ["HEAVY", "HOT_SERVE", "FRIED", "DRY"]},
    {"name": "냉면", "tags": ["NOODLES", "COLD_SERVE", "LIGHT", "SOUP"]},
    {"name": "치킨", "tags": ["FRIED", "HOT_SERVE", "HEAVY", "DRY"]}
]

# ============================================================================
# 유틸리티 함수
# ============================================================================

@st.cache_data
def load_menu_db(filename="menus.json"):
    """JSON 파일을 읽고 중복을 제거하여 반환합니다."""
    data = []
    
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            st.warning(f"파일 읽기 실패. 기본 데이터를 사용합니다.")
            data = DEFAULT_MENU
    else:
        data = DEFAULT_MENU

    # 중복 제거
    unique_menus = []
    seen_names = set()
    
    for menu in data:
        if menu["name"] not in seen_names:
            unique_menus.append(menu)
            seen_names.add(menu["name"])
    
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
        st.error(f"의도 분석 실패: {e}")
        return {}


def calculate_recommendations(menu_list, weather_desc, temp_flag, user_tags):
    """메뉴별 점수를 계산하고, 점수 내역을 포함하여 반환합니다."""
    weather_pref = {}
    if weather_desc in WEATHER_TO_FOOD_SCORE:
        for tag, score in WEATHER_TO_FOOD_SCORE[weather_desc].items():
            weather_pref[tag] = weather_pref.get(tag, 0) + score
    if temp_flag in WEATHER_TO_FOOD_SCORE:
        for tag, score in WEATHER_TO_FOOD_SCORE[temp_flag].items():
            weather_pref[tag] = weather_pref.get(tag, 0) + score

    scored_results = []
    
    for menu in menu_list:
        total_score = 0
        reasons = []
        menu_tags = set(menu['tags'])
        
        # 날씨 점수
        for tag, score in weather_pref.items():
            if tag in menu_tags:
                total_score += score
                reasons.append(f"날씨({tag} +{score})")
        
        # 사용자 취향 점수 (2배 가중치)
        for tag, score in user_tags.items():
            if tag in menu_tags:
                weighted_score = score * 2.0
                total_score += weighted_score
                reasons.append(f"취향({tag} +{weighted_score:.0f})")
                
        scored_results.append({
            "name": menu["name"],
            "score": total_score,
            "reasons": reasons,
            "tags": menu["tags"]
        })
    
    return sorted(scored_results, key=lambda x: x["score"], reverse=True)


# ============================================================================
# 메인 UI
# ============================================================================

st.title("🍽️ 오늘 뭐 먹지?")
st.markdown("### AI가 날씨와 당신의 기분을 고려해 메뉴를 추천해드립니다!")

# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
    st.info(f"📍 위치: 성남시\n🗓️ 날짜: {st.session_state.get('today', '오늘')}")
    
    if st.button("🔄 날씨 새로고침"):
        st.cache_data.clear()
        st.rerun()

# 메뉴 로드
MENU_DB = load_menu_db("menus.json")
st.sidebar.success(f"✅ {len(MENU_DB)}개 메뉴 로드됨")

# 날씨 정보
st.subheader("🌤️ 현재 날씨")
with st.spinner("날씨 정보를 가져오는 중..."):
    weather_desc, temp_flag = get_weather_info(LAT, LON)
    
    if not weather_desc:
        weather_desc, temp_flag = "SUNNY", "NORMAL"
        st.warning("날씨 조회 실패. 기본값을 사용합니다.")

# 날씨 정보 표시
col1, col2, col3 = st.columns(3)
with col1:
    weather_emoji = {
        "RAINY": "🌧️", "SNOWY": "❄️", 
        "SUNNY": "☀️", "CLOUDY": "☁️"
    }
    st.metric("날씨", weather_desc, delta=None)
    st.markdown(f"### {weather_emoji.get(weather_desc, '🌤️')}")

with col2:
    temp_emoji = {"HOT": "🔥", "COLD": "🧊", "NORMAL": "🌡️"}
    st.metric("기온", temp_flag, delta=None)
    st.markdown(f"### {temp_emoji.get(temp_flag, '🌡️')}")

with col3:
    st.metric("총 메뉴", f"{len(MENU_DB)}개", delta=None)

st.divider()

# 사용자 입력
st.subheader("💬 오늘 어떤 걸 먹고 싶으세요?")
st.caption("예: '비오는데 따뜻한 국물 먹고 싶어', '스트레스 받아서 매운거!', '가볍게 먹고 싶어'")

user_input = st.text_input(
    "입력하세요:",
    placeholder="원하는 메뉴 스타일을 자유롭게 말씀해주세요...",
    key="user_input"
)

if st.button("🔍 메뉴 추천받기", type="primary", use_container_width=True):
    if user_input.strip():
        with st.spinner("🧠 AI가 당신의 취향을 분석하는 중..."):
            user_tags = get_user_intent_tags(user_input, MY_API_KEY)
        
        if user_tags:
            st.success(f"✅ 분석 완료: {user_tags}")
        
        # 추천 계산
        with st.spinner("🎯 최적의 메뉴를 찾는 중..."):
            results = calculate_recommendations(MENU_DB, weather_desc, temp_flag, user_tags)
        
        st.divider()
        st.subheader("🏆 오늘의 추천 메뉴 TOP 3")
        
        if not results:
            st.error("😭 추천할 메뉴가 없습니다.")
        else:
            # TOP 3 표시
            medals = ["🥇", "🥈", "🥉"]
            for i, item in enumerate(results[:3]):
                with st.container():
                    col_a, col_b = st.columns([1, 3])
                    
                    with col_a:
                        st.markdown(f"## {medals[i]}")
                    
                    with col_b:
                        st.markdown(f"### {item['name']}")
                        st.metric("총점", f"{item['score']}점")
                        
                        if item['reasons']:
                            st.caption(f"🔍 점수 요인: {', '.join(item['reasons'])}")
                        else:
                            st.caption("(특별한 가중치 없음)")
                        
                        st.caption(f"🏷️ 태그: {', '.join(item['tags'])}")
                    
                    st.divider()
            
            # 전체 결과 (접기)
            with st.expander("📋 전체 추천 목록 보기"):
                for i, item in enumerate(results[3:], start=4):
                    st.write(f"{i}. **{item['name']}** ({item['score']}점)")
                    if item['reasons']:
                        st.caption(f"   └ {', '.join(item['reasons'])}")
    else:
        st.warning("⚠️ 원하는 메뉴 스타일을 입력해주세요!")

# 푸터
st.divider()
st.caption("Made with ❤️ using Streamlit & Claude AI")