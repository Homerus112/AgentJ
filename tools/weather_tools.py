"""
tools/weather_tools.py
OpenWeatherMap API로 날씨 정보 가져오기
무료 API: https://openweathermap.org/api
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
CITY = os.getenv("OPENWEATHER_CITY", "Seoul")
BASE_URL = "https://api.openweathermap.org/data/2.5"

# 날씨 아이콘 매핑
WEATHER_ICONS = {
    "Clear": "☀️", "Clouds": "☁️", "Rain": "🌧️",
    "Drizzle": "🌦️", "Snow": "❄️", "Thunderstorm": "⛈️",
    "Mist": "🌫️", "Fog": "🌫️", "Haze": "🌫️",
}


def get_current_weather(city: str = None) -> dict:
    """현재 날씨 조회"""
    if not API_KEY:
        return {"error": "OPENWEATHER_API_KEY 미설정"}

    target = city or CITY
    try:
        resp = requests.get(
            f"{BASE_URL}/weather",
            params={"q": target, "appid": API_KEY, "units": "metric", "lang": "kr"},
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()

        main_weather = data["weather"][0]["main"]
        icon = WEATHER_ICONS.get(main_weather, "🌡️")

        return {
            "city": data["name"],
            "temp": round(data["main"]["temp"]),
            "feels_like": round(data["main"]["feels_like"]),
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"],
            "main": main_weather,
            "icon": icon,
            "wind_speed": round(data["wind"]["speed"] * 3.6),  # m/s → km/h
        }
    except Exception as e:
        return {"error": str(e), "city": target}


def get_weather_summary(city: str = None) -> str:
    """날씨 한 줄 요약 (이메일 브리핑용)"""
    w = get_current_weather(city)
    if "error" in w:
        return f"날씨 정보 불러오기 실패: {w['error']}"

    advice = ""
    if w["main"] == "Rain" or w["main"] == "Drizzle":
        advice = " ☂️ 우산 챙기세요!"
    elif w["temp"] >= 30:
        advice = " 💧 더운 날, 수분 보충!"
    elif w["temp"] <= 5:
        advice = " 🧥 따뜻하게 입으세요!"

    return (
        f"{w['icon']} {w['city']} {w['temp']}°C "
        f"(체감 {w['feels_like']}°C) · {w['description']} "
        f"· 습도 {w['humidity']}% · 바람 {w['wind_speed']}km/h{advice}"
    )


def format_weather_for_email(city: str = None) -> str:
    """이메일 HTML 섹션용 날씨 포맷"""
    w = get_current_weather(city)
    if "error" in w:
        return f"<p>날씨 정보 불러오기 실패</p>"

    advice = ""
    if w["main"] in ("Rain", "Drizzle"):
        advice = "<strong>☂️ 우산 챙기세요!</strong>"
    elif w["temp"] >= 30:
        advice = "<strong>💧 더운 날씨, 수분 보충!</strong>"
    elif w["temp"] <= 5:
        advice = "<strong>🧥 따뜻하게 입으세요!</strong>"

    return f"""
<div style="background:#f0f4ff;border-radius:8px;padding:12px 16px;margin:12px 0;">
  <b>{w['icon']} 오늘의 날씨 — {w['city']}</b><br>
  🌡️ 기온 <b>{w['temp']}°C</b> (체감 {w['feels_like']}°C) &nbsp;
  💧 습도 {w['humidity']}% &nbsp;
  💨 바람 {w['wind_speed']}km/h<br>
  {w['description'].capitalize()} {advice}
</div>"""
