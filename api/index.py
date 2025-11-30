from flask import Flask, request, jsonify, make_response
import requests
import os

app = Flask(__name__)

# 환경변수
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# ==========================================
# 🎨 HTML 코드 (파이썬이 직접 보관!)
# ==========================================
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yujeong Calendar</title>
    <style>
        ::-webkit-scrollbar { display: none; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
            margin: 0; padding: 0; 
            display: flex; flex-direction: column; align-items: center; 
            background: transparent;
        }
        .container { 
            width: 100%; max-width: 280px;
            background: white; border-radius: 12px; padding: 10px; box-sizing: border-box;
            border: 2px solid #FFD9E8;
        }
        .header-container {
            display: flex; justify-content: space-between; align-items: center;
            background-color: #FFD9E8; color: white; padding: 8px 12px;
            border-radius: 8px; margin-bottom: 10px;
        }
        .header-title { font-size: 0.95rem; font-weight: 700; }
        .nav-btn { cursor: pointer; padding: 0 5px; font-weight: bold; user-select: none; }
        .grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
        .day-name { text-align: center; color: #aaa; font-size: 0.6rem; font-weight: 600; margin-bottom: 4px; }
        .day { 
            aspect-ratio: 1/0.9; border-radius: 6px; 
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            cursor: pointer; transition: 0.1s; border: 1px solid transparent;
            background: #fff; color: #333; position: relative;
        }
        .day:hover { border-color: #FFD9E8; background: #fff5f8; }
        .day.today { color: #E16259; font-weight: bold; border: 1px solid #E16259; }
        .day.has-event { background-color: #FFD9E8 !important; color: white !important; font-weight: bold; border: none; }
        .day-num { font-size: 0.75rem; z-index: 2; margin-bottom: 1px; }
        .dot-box { display: flex; gap: 2px; margin-top: 1px; }
        .dot { width: 3px; height: 3px; background-color: #E16259; border-radius: 50%; }
        .day.has-event .dot { background-color: white; }
        .list-area { width: 100%; max-width: 280px; margin-top: 10px; padding: 0 5px; box-sizing: border-box; }
        .date-title { font-size: 0.8rem; font-weight: bold; color: #555; margin-bottom: 5px; }
        .task-item { 
            background: white; padding: 6px 10px; border-radius: 6px; margin-bottom: 4px;
            font-size: 0.8rem; display: flex; align-items: center; gap: 6px;
            border: 1px solid #eee; color: #333;
        }
        .check-icon { font-size: 0.7rem; }
        .empty-msg { text-align: center; color: #ccc; font-size: 0.7rem; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header-container">
            <div class="nav-btn" onclick="changeMonth(-1)">&lt;</div>
            <div class="header-title" id="month-year"></div>
            <div class="nav-btn" onclick="changeMonth(1)">&gt;</div>
        </div>
        <div class="grid" id="calendar">
            <div class="day-name">M</div><div class="day-name">T</div><div class="day-name">W</div>
            <div class="day-name">T</div><div class="day-name">F</div><div class="day-name">S</div>
            <div class="day-name" style="color:#E16259;">S</div>
        </div>
    </div>
    <div class="list-area" id="list-area"></div>
    <script>
        let eventsData = {}; 
        let fullList = [];
        let viewDate = new Date();
        const calendarEl = document.getElementById('calendar');
        const listEl = document.getElementById('list-area');
        const monthYearEl = document.getElementById('month-year');

        async function fetchData() {
            try {
                const res = await fetch('/api/get_tasks');
                const data = await res.json();
                if (data.error) throw new Error(data.error);
                eventsData = data.events || {};
                fullList = data.list || [];
                renderCalendar();
                showList(new Date().toISOString().split('T')[0]); 
            } catch (err) {
                listEl.innerHTML = `<div class='empty-msg'>로딩 실패<br>${err.message}</div>`;
            }
        }
        function changeMonth(step) {
            viewDate.setMonth(viewDate.getMonth() + step);
            renderCalendar();
        }
        function renderCalendar() {
            const viewYear = viewDate.getFullYear();
            const viewMonth = viewDate.getMonth();
            const monthNameEng = new Intl.DateTimeFormat('en-US', { month: 'long' }).format(viewDate);
            monthYearEl.innerText = `${monthNameEng} ${viewYear}`;
            while (calendarEl.children.length > 7) { calendarEl.removeChild(calendarEl.lastChild); }
            const firstDayOfWeek = new Date(viewYear, viewMonth, 1).getDay();
            const emptyCells = (firstDayOfWeek + 6) % 7;
            const lastDate = new Date(viewYear, viewMonth + 1, 0).getDate();
            for(let i=0; i<emptyCells; i++) calendarEl.innerHTML += `<div></div>`;
            for(let i=1; i<=lastDate; i++) {
                const dateKey = `${viewYear}-${String(viewMonth+1).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                const hasEvent = eventsData[dateKey];
                let dotHtml = '';
                if(hasEvent) {
                    const count = Math.min(hasEvent.length, 3);
                    dotHtml = `<div class="dot-box">${'<div class="dot"></div>'.repeat(count)}</div>`;
                }
                const today = new Date();
                const todayClass = (i === today.getDate() && viewMonth === today.getMonth() && viewYear === today.getFullYear()) ? 'today' : '';
                const eventClass = hasEvent ? 'has-event' : '';
                const dayDiv = document.createElement('div');
                dayDiv.className = `day ${todayClass} ${eventClass}`;
                dayDiv.innerHTML = `<span class="day-num">${i}</span>${dotHtml}`;
                dayDiv.onclick = () => showList(dateKey);
                calendarEl.appendChild(dayDiv);
            }
        }
        function showList(dateKey) {
            const filtered = fullList.filter(item => item.date === dateKey);
            const d = new Date(dateKey);
            const dateStr = `${d.getMonth()+1}월 ${d.getDate()}일`;
            let html = `<div class="date-title">📅 ${dateStr}</div>`;
            if (filtered.length === 0) {
                html += `<div class="empty-msg">일정이 없어요</div>`;
            } else {
                filtered.forEach(item => {
                    const check = item.completed ? "✅" : "▫️";
                    html += `<div class="task-item"><span class="check-icon">${check}</span><span>${item.task}</span></div>`;
                });
            }
            listEl.innerHTML = html;
        }
        fetchData();
    </script>
</body>
</html>
"""

# ==========================================
# 🧠 메인 라우트 (HTML + 헤더 강제 주입!)
# ==========================================
@app.route('/')
def home():
    response = make_response(HTML_CONTENT)
    # ⭐ 여기가 핵심! 노션 입장을 강제로 허용하는 헤더
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    response.headers['Content-Security-Policy'] = "frame-ancestors *"
    return response

# API 라우트 (데이터 가져오기)
@app.route('/api/get_tasks', methods=['GET', 'POST'])
def get_tasks():
    if not NOTION_TOKEN or not DATABASE_ID:
        return jsonify({"error": "Vercel 환경변수 미설정"}), 500

    try:
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        payload = {"sorts": [{"property": "Date", "direction": "ascending"}]}
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            return jsonify({"error": f"노션 응답 오류: {response.status_code}"}), 500
        
        data = response.json()
        events = {}
        list_data = []

        for result in data.get("results", []):
            try:
                props = result["properties"]
                title_list = props.get("To-Do", {}).get("title", [])
                title = title_list[0]["plain_text"] if title_list else "제목 없음"
                date_info = props.get("Date", {}).get("date", {})
                date = date_info.get("start") if date_info else None
                completed = props.get("Complete", {}).get("checkbox", False)
                
                if date:
                    if not completed:
                        if date not in events: events[date] = []
                        events[date].append(title)
                    list_data.append({"date": date, "task": title, "completed": completed})
            except:
                continue
        
        return jsonify({"events": events, "list": list_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
