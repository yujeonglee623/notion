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
# 📅 1. 캘린더 전용 HTML (리스트 없음)
# ==========================================
HTML_CALENDAR = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yujeong Calendar Only</title>
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
        /* hover 효과 제거하거나 약하게 (클릭 기능이 없으므로) */
        .day:hover { background: #fff5f8; }
        .day.today { color: #E16259; font-weight: bold; border: 1px solid #E16259; }
        .day.has-event { background-color: #FFD9E8 !important; color: white !important; font-weight: bold; border: none; }
        .day-num { font-size: 0.75rem; z-index: 2; margin-bottom: 1px; }
        .dot-box { display: flex; gap: 2px; margin-top: 1px; }
        .dot { width: 3px; height: 3px; background-color: #E16259; border-radius: 50%; }
        .day.has-event .dot { background-color: white; }
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
    <script>
        let eventsData = {}; 
        let viewDate = new Date();
        const calendarEl = document.getElementById('calendar');
        const monthYearEl = document.getElementById('month-year');

        async function fetchData() {
            try {
                const res = await fetch('/api/get_tasks');
                const data = await res.json();
                eventsData = data.events || {};
                renderCalendar();
            } catch (err) { console.log(err); }
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
                calendarEl.appendChild(dayDiv);
            }
        }
        fetchData();
    </script>
</body>
</html>
"""

# ==========================================
# 📝 2. 리스트 전용 HTML (날짜 선택기 포함)
# ==========================================
HTML_LIST = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yujeong List Only</title>
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
            background: white; border-radius: 12px; padding: 15px; box-sizing: border-box;
            border: 2px solid #FFD9E8;
            min-height: 200px;
        }
        
        /* 날짜 선택 헤더 */
        .date-header {
            display: flex; align-items: center; justify-content: space-between;
            margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px;
        }
        .date-display { font-size: 1rem; font-weight: 800; color: #333; }
        
        /* 날짜 입력기 숨기고 예쁜 버튼으로 대체할 수도 있지만, 심플하게 기본 input 사용 */
        input[type="date"] {
            border: 1px solid #ddd; border-radius: 6px; padding: 4px;
            font-family: inherit; color: #555; outline: none; font-size: 0.8rem;
        }
        input[type="date"]:focus { border-color: #FFD9E8; }

        .task-item { 
            background: white; padding: 8px 10px; border-radius: 6px; margin-bottom: 6px;
            font-size: 0.85rem; display: flex; align-items: center; gap: 8px;
            border: 1px solid #eee; color: #333; transition: 0.2s;
        }
        input[type="checkbox"] { accent-color: #E16259; width: 14px; height: 14px; cursor: pointer; }
        .completed-task { text-decoration: line-through; color: #aaa; }
        .empty-msg { text-align: center; color: #ccc; font-size: 0.8rem; margin-top: 30px; }
        
        .loader { border: 2px solid #f3f3f3; border-top: 2px solid #FFD9E8; border-radius: 50%; width: 15px; height: 15px; animation: spin 1s linear infinite; margin: 20px auto; display:none;}
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <div class="date-header">
            <span class="date-display">Today's List</span>
            <input type="date" id="date-picker">
        </div>

        <div id="loader" class="loader"></div>
        <div id="list-area"></div>
    </div>
    
    <script>
        let fullList = [];
        const listEl = document.getElementById('list-area');
        const datePicker = document.getElementById('date-picker');
        const loader = document.getElementById('loader');

        // 오늘 날짜로 초기화
        datePicker.valueAsDate = new Date();

        async function fetchData() {
            loader.style.display = 'block';
            listEl.innerHTML = '';
            try {
                const res = await fetch('/api/get_tasks');
                const data = await res.json();
                fullList = data.list || [];
                renderList();
            } catch (err) {
                listEl.innerHTML = `<div class='empty-msg'>로딩 실패</div>`;
            } finally {
                loader.style.display = 'none';
            }
        }

        function renderList() {
            const selectedDate = datePicker.value; // YYYY-MM-DD
            const filtered = fullList.filter(item => item.date === selectedDate);
            
            if (filtered.length === 0) {
                listEl.innerHTML = `<div class="empty-msg">일정이 없어요 🏝️</div>`;
            } else {
                let html = '';
                filtered.forEach(item => {
                    const checkedAttr = item.completed ? "checked" : "";
                    const completedClass = item.completed ? "completed-task" : "";
                    html += `
                        <div class="task-item">
                            <input type="checkbox" ${checkedAttr} onchange="toggleTask('${item.id}', this.checked)">
                            <span id="text-${item.id}" class="${completedClass}">${item.task}</span>
                        </div>
                    `;
                });
                listEl.innerHTML = html;
            }
        }

        async function toggleTask(pageId, isChecked) {
            const textSpan = document.getElementById(`text-${pageId}`);
            if(isChecked) textSpan.classList.add('completed-task');
            else textSpan.classList.remove('completed-task');
            try {
                await fetch('/api/update_task', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ page_id: pageId, completed: isChecked })
                });
                fetchData(); // 데이터 갱신
            } catch (e) { alert("오류 발생"); }
        }

        // 날짜 바꾸면 리스트 갱신
        datePicker.addEventListener('change', renderList);

        fetchData();
    </script>
</body>
</html>
"""

# ==========================================
# 🚀 라우팅 설정 (주소 나누기!)
# ==========================================
@app.route('/')
def calendar_page():
    # 기본 주소( / )로 들어오면 캘린더만 보여줌
    response = make_response(HTML_CALENDAR)
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    response.headers['Content-Security-Policy'] = "frame-ancestors *"
    return response

@app.route('/list')
def list_page():
    # ( /list ) 주소로 들어오면 리스트만 보여줌
    response = make_response(HTML_LIST)
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    response.headers['Content-Security-Policy'] = "frame-ancestors *"
    return response

# API는 공통으로 사용
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
