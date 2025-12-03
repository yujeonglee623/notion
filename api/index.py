from flask import Flask, jsonify, request, render_template, make_response
import requests
import os
from datetime import datetime, timedelta # <-- 이거 추가!

# templates 폴더와 static 폴더 위치 지정
app = Flask(__name__, template_folder='../templates', static_folder='../static')

# 환경변수 가져오기
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID") # 캘린더/리스트용 DB
MANDALART_ID = os.environ.get("MANDALART_ID") # 만다라트용 DB

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

# 1. 캘린더 (기본 주소 / )
@app.route('/')
def calendar_page():
    return allow_iframe(render_template('calendar.html'))

# 2. 리스트 ( /list )
@app.route('/list')
def list_page():
    return allow_iframe(render_template('list.html'))

# 3. 음악 플레이어 ( /music )
@app.route('/music')
def music_page():
    return allow_iframe(render_template('music.html'))

# 4. 디데이 ( /dday )
@app.route('/dday')
def dday_page():
    return allow_iframe(render_template('dday.html'))

# 5. 유튜브 플레이리스트 ( /playlist )
@app.route('/playlist')
def playlist_page():
    return allow_iframe(render_template('playlist.html'))

# 6. 만다라트 ( /mandalart )
@app.route('/mandalart')
def mandalart_page():
    return allow_iframe(render_template('mandalart.html'))

# 7. 날씨 위젯 페이지 ( /weather )
@app.route('/weather')
def weather_page():
    return allow_iframe(render_template('weather.html'))

# 날씨 데이터 가져오기 API
@app.route('/api/get_weather', methods=['GET'])
def get_weather():
    try:
        api_key = os.environ.get("OWM_API_KEY")
        lat = os.environ.get("LAT")
        lon = os.environ.get("LON")

        if not api_key or not lat or not lon:
             return jsonify({"error": "환경변수(OWM_API_KEY, LAT, LON)가 설정되지 않았습니다."}), 500

        # OpenWeatherMap One Call API 호출 (현재, 일일, 시간별 데이터 모두 포함)
        url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=minutely,alerts&units=metric&lang=kr&appid={api_key}"
        
        response = requests.get(url)
        data = response.json()

        if response.status_code != 200:
             return jsonify({"error": f"날씨 API 오류: {data.get('message')}"}), response.status_code

        # 필요한 데이터만 정리해서 보내기
        weather_data = {
            "current": {
                "temp": round(data["current"]["temp"]),
                "desc": data["current"]["weather"][0]["description"],
                "icon": data["current"]["weather"][0]["icon"],
                "code": data["current"]["weather"][0]["id"], # 날씨 상태 코드 (배경화면용)
                "high": round(data["daily"][0]["temp"]["max"]), # 오늘 최고
                "low": round(data["daily"][0]["temp"]["min"])   # 오늘 최저
            },
            # 향후 12시간 데이터만 추림
            "hourly": []
        }

        for i in range(1, 13): # 1시간 뒤부터 12시간 뒤까지
            hour_data = data["hourly"][i]
            weather_data["hourly"].append({
                # 시간을 "오후 3시" 형태로 변환 (UTC 기준이라 9시간 더해줌 - 한국 기준)
                # 실제 서버 시간대에 따라 다를 수 있으나 Vercel 기본 기준으로 계산
                 "time": (datetime.utcfromtimestamp(hour_data["dt"]) + timedelta(hours=9)).strftime("%p %I시").replace("AM", "오전").replace("PM", "오후"),
                 "temp": round(hour_data["temp"]),
                 "icon": hour_data["weather"][0]["icon"],
                 "pop": round(hour_data["pop"] * 100) # 강수확률 (0~1 -> 0~100%)
            })
            
        return jsonify(weather_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# (맨 아래 if __name__ == '__main__': app.run() 이부분은 그대로 유지)


# ==========================================
# 📡 데이터 통신 API
# ==========================================

# 1. 캘린더/리스트 데이터 가져오기 (정렬 적용!)
@app.route('/api/get_tasks', methods=['GET'])
def get_tasks():
    if not NOTION_TOKEN or not DATABASE_ID: return jsonify({"error": "Env Var Error (캘린더 DB)"}), 500
    try:
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        
        # ⭐ [수정됨] 1순위: 날짜순, 2순위: 가나다순
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
                
                # 데이터 안전하게 꺼내기
                title_list = props.get("To-Do", {}).get("title", [])
                title = title_list[0]["plain_text"] if title_list else "제목 없음"
                
                date_info = props.get("Date", {}).get("date", {})
                date = date_info.get("start") if date_info else None
                
                completed = props.get("Complete", {}).get("checkbox", False)
                
                if date:
                    # 캘린더용 (완료 안 된 것만 점 표시)
                    if not completed:
                        if date not in events: events[date] = []
                        events[date].append(title)
                    
                    # 리스트용 (전체 다)
                    list_data.append({"id": page_id, "date": date, "task": title, "completed": completed})
            except: continue
            
        return jsonify({"events": events, "list": list_data})
    except Exception as e: return jsonify({"error": str(e)}), 500

# 2. 리스트 체크박스 업데이트
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

# 3. 만다라트 데이터 가져오기
@app.route('/api/get_mandalart', methods=['GET'])
def get_mandalart():
    # 만다라트용 환경변수 확인
    if not MANDALART_ID: return jsonify({"error": "Env Var Error (MANDALART_ID)"}), 500
    
    try:
        url = f"https://api.notion.com/v1/databases/{MANDALART_ID}/query"
        response = requests.post(url, headers=headers)
        data = response.json()
        
        mandalart_data = {}
        
        for result in data.get("results", []):
            try:
                props = result["properties"]
                # 주제
                topic = props.get("주제", {}).get("title", [])
                topic_text = topic[0]["plain_text"] if topic else "빈 칸"
                # 위치
                pos = props.get("위치", {}).get("select", {})
                pos_text = pos.get("name") if pos else None
                # 실천계획
                plans = props.get("실천계획", {}).get("rich_text", [])
                plan_text = plans[0]["plain_text"] if plans else ""
                plan_list = plan_text.split('\n')
                
                if pos_text:
                    mandalart_data[pos_text] = {
                        "topic": topic_text,
                        "plans": plan_list
                    }
            except: continue
            
        return jsonify(mandalart_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()

