"""
Claude API 호출 모듈 (통합 버전)
"""

import anthropic
from typing import Optional


# ============================================================================
# System Prompts
# ============================================================================

FOOD_TAG_CLASSIFIER_SYSTEM_PROMPT = """
# Role
너는 사용자의 음식 선호도를 분석하여, '음식 태그'와 그 '강도(Score)'를 추출하는 AI 분류기다.

# Allowed Tags
- Temperature: HOT_SERVE, COLD_SERVE
- Texture/Type: SOUP, DRY, FRIED, CREAMY
- Base: RICE, NOODLES
- Flavor/Weight: SPICY, LIGHT, HEAVY

# Scoring Rules (1~5 Scale)
- 5 (Strong): 사용자가 명시적으로 강력하게 원함 (예: "매운 거!", "무조건 시원한 거")
- 3 (Moderate): 문맥상 자연스럽게 유추됨 (예: "해장" -> SOUP:3, SPICY:3)
- 1 (Weak): 약한 선호도 혹은 뉘앙스

# Instructions
1. 사용자의 자연어 입력을 분석하여 허용된 태그만 선택한다.
2. 각 태그에 적절한 점수(Integer)를 부여한다.
3. 상충되는 태그는 더 강한 쪽 하나만 선택한다.
4. 사용자가 '아무거나'라고 하면 빈 딕셔너리 {} 를 반환한다.
5. 출력은 오직 Python Dictionary 포맷의 문자열로만 답한다.

# Output Example
{"SOUP": 5, "SPICY": 3, "HOT_SERVE": 3}
"""


# ============================================================================
# API 호출 함수
# ============================================================================

def call_claude(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 1000,
    api_key: Optional[str] = None
) -> str:
    """
    Claude API를 호출하는 함수
    
    Args:
        prompt: Claude에게 보낼 user 메시지
        system_prompt: 시스템 프롬프트 (선택사항)
        model: 사용할 Claude 모델 (기본값: Sonnet 4)
        max_tokens: 최대 토큰 수
        api_key: API 키 (없으면 환경변수에서 가져옴)
    
    Returns:
        Claude의 응답 텍스트
    
    Example:
        # 기본 사용
        response = call_claude("안녕하세요!")
        
        # System prompt 사용
        response = call_claude(
            prompt="매운 국물 요리",
            system_prompt=FOOD_TAG_CLASSIFIER_SYSTEM_PROMPT
        )
    """
    # API 클라이언트 생성
    if api_key:
        client = anthropic.Anthropic(api_key=api_key)
    else:
        client = anthropic.Anthropic()  # 환경변수에서 자동으로 가져옴
    
    # API 호출 파라미터 설정
    params = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    # system_prompt가 있으면 추가
    if system_prompt:
        params["system"] = system_prompt
    
    # API 호출
    message = client.messages.create(**params)
    
    return message.content[0].text


# ============================================================================
# 사용 예제
# ============================================================================

if __name__ == "__main__":
    # API 키 설정
    API_KEY = ""
    
    print("=" * 60)
    print("예제 1: 기본 채팅")
    print("=" * 60)
    response = call_claude("안녕! 오늘 날씨 어때?", api_key=API_KEY)
    print("Claude:", response)
    print()
    
    print("=" * 60)
    print("예제 2: 음식 태그 분류기")
    print("=" * 60)
    test_cases = [
        "해장하고 싶어",
        "살 안 찌는 거 먹고 싶어",
        "바삭한 거 땡겨",
        "든든한 한 끼 먹고 싶다",
        "차가운 면 요리",
        "아무거나"
    ]
    
    for user_input in test_cases:
        response = call_claude(
            prompt=user_input,
            system_prompt=FOOD_TAG_CLASSIFIER_SYSTEM_PROMPT,
            api_key=API_KEY
        )
        print(f"입력: {user_input}")
        print(f"태그: {response}")
        print()