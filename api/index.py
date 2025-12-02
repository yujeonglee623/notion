from flask import Flask, jsonify, request, render_template, make_response
import requests
import os

# 템플릿과 스태틱 폴더 위치 지정
app = Flask(__name__, template_folder='../templates', static_folder='../static')

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# ⭐⭐⭐ [핵심] 모든 응답에 강제로 '문 열어' 헤더를 붙이는 마법의 코드
@app.after_request
def add_header(response):
    # 노션이 내 사이트를 액자(iframe)에 넣을 수 있게 허락함
    response.headers['Content-Security-Policy'] = "frame-ancestors https://www.notion.so https://notion.so *;"
    # 일부 브라우저 호환성을 위해 추가
    response.headers['X-Frame-Options'] = 'ALLOWALL' 
    return response

# 1. 캘린더 페이지 (기본 주소)
@app.route('/')
def calendar_page():
    return render_template('calendar.html')

# 2. 리스트 페이지
@app.route('/list')
def list_page():
    return render_template('list.html')

# 3. 음악 페이지
@app.route('/music')
def music_page():
    return render_template('music.html')

# 4. ⭐ 디데이 페이지
@app.route('/dday')
def dday_page():
    return allow_iframe(render_template('dday.html'))

# 5. ⭐ 유튜브 플레이리스트
@app.route('/playlist')
def playlist_page():
    return allow_iframe(render_template('playlist.html'))

# --- API (데이터 통신) ---
@app.route('/api/get_tasks', methods=['GET'])
def get_tasks():
    if not NOTION_TOKEN or not DATABASE_ID: return jsonify({"error": "Env Var Error"}), 500
    try:
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        payload = {"sorts": [{"property": "Date", "direction": "ascending"}]}
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

if __name__ == '__main__':
    app.run()


