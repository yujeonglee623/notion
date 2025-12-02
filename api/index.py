from flask import Flask, jsonify, request, render_template, make_response
import requests
import os

app = Flask(__name__, template_folder='../templates', static_folder='../static')

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def allow_iframe(content):
    response = make_response(content)
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    response.headers['Content-Security-Policy'] = "frame-ancestors *"
    return response

# === 페이지 라우트 ===
@app.route('/')
def calendar_page(): return allow_iframe(render_template('calendar.html'))

@app.route('/list')
def list_page(): return allow_iframe(render_template('list.html'))

@app.route('/music')
def music_page(): return allow_iframe(render_template('music.html'))

@app.route('/dday')
def dday_page(): return allow_iframe(render_template('dday.html'))

# 5. ⭐ 만다라트 페이지 (새로 추가!)
@app.route('/mandalart')
def mandalart_page():
    return allow_iframe(render_template('mandalart.html'))

@app.route('/playlist')
def playlist_page(): return allow_iframe(render_template('playlist.html'))


# === 데이터 API ===
# 기존 캘린더용 API
@app.route('/api/get_tasks', methods=['GET'])
def get_tasks():
    # ... (기존 코드 생략 - 그대로 둬도 됨) ...
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
    # ... (기존 코드 생략) ...
    return jsonify({"status": "success"}) # (생략함, 기존 코드 유지)

# ⭐ 만다라트 데이터 가져오기 API (새로 추가!)
@app.route('/api/get_mandalart', methods=['GET'])
def get_mandalart():
    try:
        # 만다라트 DB ID는 환경변수 MANDALART_ID로 따로 빼거나, 
        # 귀찮으면 그냥 여기에 문자열로 박아도 돼! (하지만 환경변수 추천)
        # 일단은 기존 DATABASE_ID 말고, 만다라트용 ID를 써야 해!
        # 유정아, Vercel 환경변수에 'MANDALART_ID'를 추가해줘!
        M_ID = os.environ.get("MANDALART_ID") 
        
        if not M_ID: return jsonify({"error": "MANDALART_ID 환경변수 없음"}), 500

        url = f"https://api.notion.com/v1/databases/{M_ID}/query"
        response = requests.post(url, headers=headers)
        data = response.json()
        
        mandalart_data = {}
        
        for result in data.get("results", []):
            try:
                props = result["properties"]
                # 주제 (Name)
                topic = props.get("주제", {}).get("title", [])
                topic_text = topic[0]["plain_text"] if topic else "빈 칸"
                
                # 위치 (Select)
                pos = props.get("위치", {}).get("select", {})
                pos_text = pos.get("name") if pos else None
                
                # 실천계획 (Text -> 줄바꿈으로 분리)
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
