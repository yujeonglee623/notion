from flask import Flask, jsonify, request, render_template, make_response
import requests
import os
from datetime import datetime

# templates 폴더와 static 폴더 위치 지정
app = Flask(__name__, template_folder='../templates', static_folder='../static')

# 환경변수 가져오기
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID") # 캘린더용
MANDALART_ID = os.environ.get("MANDALART_ID") # 만다라트용

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# 공통 헤더 설정 함수 (노션 임베드 허용)
def allow_iframe(content):
    response = make_response(content)
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    response.headers['Content-Security-Policy'] = "frame-ancestors *"
    return response

# ==========================================
# 🌐 화면 보여주는 라우트 (페이지)
# ==========================================

# 1. 캘린더
@app.route('/')
def calendar_page():
    return allow_iframe(render_template('calendar.html'))

# 2. 리스트
@app.route('/list')
def list_page():
    return allow_iframe(render_template('list.html'))

# 3. 음악 플레이어
@app.route('/music')
def music_page():
    return allow_iframe(render_template('music.html'))

# 4. 디데이
@app.route('/dday')
def dday_page():
    return allow_iframe(render_template('dday.html'))

# 5. 유튜브 플레이리스트
@app.route('/playlist')
def playlist_page():
    return allow_iframe(render_template('playlist.html'))

# 6. 만다라트
@app.route('/mandalart')
def mandalart_page():
    return allow_iframe(render_template('mandalart.html'))

# 7. ⭐ 날씨 (이게 있어야 함!)
@app.route('/weather')
def weather_page():
    return allow_iframe(render_template('weather.html'))


# ==========================================
# 📡 데이터 통신 API
# ==========================================

# 1. 캘린더/리스트 데이터
@app.route('/api/get_tasks', methods=['GET'])
def get_tasks():
    if not NOTION_TOKEN or not DATABASE_ID: return jsonify({"error": "Env Var Error"}), 500
    try:
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        payload = {
            "sorts": [
                {"property": "Date", "direction": "ascending"},
                {"property": "To-Do", "direction": "ascending"}
            ]
        }
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        events = {}
        list_data = []
        for result in data.get("results", []):
            try:
                props = result["properties"]
                page_id = result["id"]
                title = props.get("To-Do", {}).get("title", [])[0]["plain_text"] if props.get("To-Do", {}).get("title") else ""
                date = props.get("Date", {}).get("date", {}).get("start") if props.get("Date", {}).get("date") else None
                completed = props.get("Complete", {}).get("checkbox", False)
                if date:
                    if not completed:
                        if date not in events: events[date] = []
                        events[date].append(title)
                    list_data.append({"id": page_id, "date": date, "task": title, "completed": completed})
            except: continue
        return jsonify({"events": events, "list": list_data})
    except Exception as e: return jsonify({"error": str(e)}), 500

# 2. 리스트 업데이트
@app.route('/api/update_task', methods=['POST'])
def update_task():
    try:
        data = request.json
        page_id = data.get("page_id")
        completed = data.get("completed")
        url = f"https://api.notion.com/v1/pages/{page_id}"
        payload = { "properties": { "Complete": { "checkbox": completed } } }
        requests.patch(url, headers=headers, json=payload)
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"error": str(e)}), 500

# 3. 만다라트 데이터
@app.route('/api/get_mandalart', methods=['GET'])
def get_mandalart():
    if not MANDALART_ID: return jsonify({"error": "MANDALART_ID 미설정"}), 500
    try:
        url = f"https://api.notion.com/v1/databases/{MANDALART_ID}/query"
        response = requests.post(url, headers=headers)
        data = response.json()
        mandalart_data = {}
        for result in data.get("results", []):
            try:
                props = result["properties"]
                topic = props.get("주제", {}).get("title", [])[0]["plain_text"] if props.get("주제", {}).get("title") else ""
                pos = props.get("위치", {}).get("select", {}).get("name")
                plans = props.get("실천계획", {}).get("rich_text", [])
                plan_text = plans[0]["plain_text"] if plans else ""
                plan_list = plan_text.split('\n')
                if pos:
                    mandalart_data[pos] = {"topic": topic, "plans": plan_list}
            except: continue
        return jsonify(mandalart_data)
    except Exception as e: return jsonify({"error": str(e)}), 500

# 4. ⭐ 날씨 데이터 (무료 2.5 버전)
@app.route('/api/get_weather', methods=['GET'])
def get_weather():
    try:
        api_key = os.environ.get("OWM_API_KEY")
        lat = os.environ.get("LAT")
        lon = os.environ.get("LON")

        if not api_key or not lat or not lon:
             return jsonify({"error": "환경변수(OWM_API_KEY, LAT, LON) 미설정"}), 500

        # 현재 날씨
        current_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&lang=kr&appid={api_key}"
        res_cur = requests.get(current_url).json()

        # 5일/3시간 예보
        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&units=metric&lang=kr&appid={api_key}"
        res_for = requests.get(forecast_url).json()

        if str(res_cur.get("cod")) != "200":
             return jsonify({"error": f"API Error: {res_cur.get('message')}"}), 500

        # 오늘 최고/최저 (향후 24시간 기준)
        temps = [item['main']['temp'] for item in res_for['list'][:8]]
        today_high = max(temps)
        today_low = min(temps)

        weather_data = {
            "current": {
                "temp": round(res_cur["main"]["temp"]),
                "desc": res_cur["weather"][0]["description"],
                "icon": res_cur["weather"][0]["icon"],
                "code": res_cur["weather"][0]["id"],
                "high": round(today_high),
                "low": round(today_low)
            },
            "hourly": []
        }

        # 3시간 간격 예보 (5개)
        for item in res_for['list'][:5]:
            dt_object = datetime.fromtimestamp(item["dt"])
            time_str = dt_object.strftime("%p %I시").replace("AM", "오전").replace("PM", "오후")
            
            weather_data["hourly"].append({
                "time": time_str,
                "temp": round(item["main"]["temp"]),
                "icon": item["weather"][0]["icon"],
                "pop": round(item.get("pop", 0) * 100)
            })
            
        return jsonify(weather_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
