import requests
from datetime import datetime

SEASON_AVG_TEMP = {
    "winter": 2,
    "spring": 13,
    "summer": 26,
    "fall": 14,
}

def get_season(month: int) -> str:
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "fall"

def classify_temp_now(temp_c: float, delta: float = 5.0):
    month = datetime.now().month
    season = get_season(month)
    avg = SEASON_AVG_TEMP[season]

    return {
        "season": season,
        "COLD": temp_c <= avg - delta,
        "HOT":  temp_c >= avg + delta,
    }

def get_weather_description(code):
    if code in [0, 1]: return "SUNNY"
    elif code in [2, 3, 45, 48]: return "CLOUDY"
    elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99]: return "RAINY"
    elif code in [71, 73, 75, 77, 85, 86]: return "SNOWY"
    else: return "UNKNOWN"

def get_weather_info(latitude, longitude):
    """
    날씨 정보를 가져와서 (상태, 온도플래그) 튜플을 반환합니다.
    예: ("SUNNY", "HOT") 또는 ("RAINY", "NORMAL")
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,weather_code",
        "timezone": "Asia/Seoul",
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        current = data['current']
        
        # 1. 날씨 상태 (SUNNY, RAINY 등)
        weather_desc = get_weather_description(current['weather_code'])
        
        # 2. 온도 플래그 (HOT, COLD, NORMAL)
        temp_analysis = classify_temp_now(current['temperature_2m'])
        active_flags = [k for k, v in temp_analysis.items() if v is True]
        
        # HOT이나 COLD가 아니면 NORMAL 반환 (IndexError 방지)
        temp_flag = active_flags[0] if active_flags else "NORMAL"
        
        return weather_desc, temp_flag

    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None, None

# 이 파일 자체를 실행했을 때만 테스트 코드가 돌아가게 함
if __name__ == "__main__":
    desc, temp = get_weather_info(37.4201, 127.1262)
    print(f"결과: {desc}, {temp}")