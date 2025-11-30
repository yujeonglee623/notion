import streamlit as st
import requests
import json
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime

# ==========================================
# 🔐 유정이의 비밀 열쇠
# ==========================================
try:
    NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
    DATABASE_ID = st.secrets["DATABASE_ID"]
except:
    st.error("Secrets 설정을 확인해주세요!")
    st.stop()

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# ==========================================
# 🧠 파이썬 백엔드 (읽기 전용)
# ==========================================
def get_data():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {"sorts": [{"property": "Date", "direction": "ascending"}]}
    res = requests.post(url, headers=headers, json=payload)
    
    if res.status_code != 200:
        return "{}", pd.DataFrame()

    results = res.json().get("results", [])
    calendar_events = {}
    df_list = []
    
    for result in results:
        try:
            props = result["properties"]
            page_id = result["id"]
            
            title_list = props.get("To-Do", {}).get("title", [])
            title = title_list[0]["plain_text"] if title_list else "제목 없음"
            date_info = props.get("Date", {}).get("date", {})
            date = date_info.get("start") if date_info else None
            completed = props.get("Complete", {}).get("checkbox", False)
            
            if not date: continue

            if not completed:
                if date not in calendar_events:
                    calendar_events[date] = []
                calendar_events[date].append(title)
            
            df_list.append({"ID": page_id, "날짜": date, "할일": title, "완료": completed})
        except:
            continue
            
    return json.dumps(calendar_events, ensure_ascii=False), pd.DataFrame(df_list)

# ==========================================
# 💅 UI 디자인 (컴팩트 모드)
# ==========================================
st.set_page_config(page_title="유정이의 캘린더", layout="centered") # layout을 centered로 변경해서 더 오밀조밀하게

# 여백 완전 제거 스타일
st.markdown("""
    <style>
        .block-container { padding-top: 0rem; padding-bottom: 0rem; padding-left: 1rem; padding-right: 1rem; } 
        header, footer { visibility: hidden; }
        .stApp { margin-top: -30px; } /* 강제로 위로 끌어올리기 */
        
        /* 리스트 카드 스타일 (작게) */
        .task-card {
            background-color: white;
            padding: 8px;
            border-radius: 6px;
            border: 1px solid #eee;
            margin-bottom: 5px;
            font-size: 0.9rem;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        }
    </style>
""", unsafe_allow_html=True)

events_json, df = get_data()

# 1. 캘린더 (HTML - Mini Ver.)
html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        ::-webkit-scrollbar {{ display: none; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 0; display: flex; justify-content: center; }}
        .container {{ width: 100%; max-width: 600px; padding-bottom: 5px; }} /* 너비 제한 */
        
        /* 헤더 크기 축소 */
        .header {{ font-size: 1.1rem; font-weight: 800; margin: 10px 0; color: #333; text-align: center; }}
        
        .calendar-grid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }}
        .day-name {{ text-align: center; color: #999; font-size: 0.7rem; margin-bottom: 3px; font-weight: 600; }}
        
        .day {{ 
            aspect-ratio: 1/0.8; 
            border-radius: 8px; /* 둥글기 축소 */
            background: #fff; 
            border: 1px solid #eee;
            padding: 2px; /* 패딩 축소 */
            font-size: 0.8rem; /* 폰트 축소 */
            display: flex; 
            flex-direction: column;
            align-items: center; 
            justify-content: center; 
            position: relative; 
            cursor: pointer; 
            color: #333;
        }}
        
        .day:hover {{ border-color: #FFD9E8; transform: translateY(-1px); }}
        .day.today {{ border: 1.5px solid #FFD9E8; color: #E16259; font-weight: bold; }}
        .day.has-event {{ background-color: #FFD9E8 !important; color: white !important; font-weight: bold; border: none; }}
        
        .day-num {{ font-size: 0.9rem; margin-bottom: 2px; z-index: 10; }}
        
        /* 점 크기 축소 */
        .dot-container {{ display: flex; gap: 3px; margin-top: 2px; }}
        .dot {{ width: 4px; height: 4px; background-color: #E16259; border-radius: 50%; }}
        .day.has-event .dot {{ background-color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header" id="month-year"></div>
        <div class="calendar-grid" id="calendar">
            <div class="day-name">SUN</div><div class="day-name">MON</div><div class="day-name">TUE</div>
            <div class="day-name">WED</div><div class="day-name">THU</div><div class="day-name">FRI</div><div class="day-name">SAT</div>
        </div>
    </div>
    <script>
        const events = {events_json}; 
        const calendarEl = document.getElementById('calendar');
        const monthYearEl = document.getElementById('month-year');
        const date = new Date();
        const currentYear = date.getFullYear();
        const currentMonth = date.getMonth();
        function render() {{
            monthYearEl.innerText = `${{currentYear}}. ${{String(currentMonth + 1).padStart(2, '0')}}`;
            while (calendarEl.children.length > 7) {{ calendarEl.removeChild(calendarEl.lastChild); }}
            const firstDay = new Date(currentYear, currentMonth, 1).getDay();
            const lastDate = new Date(currentYear, currentMonth + 1, 0).getDate();
            for(let i=0; i<firstDay; i++) calendarEl.appendChild(document.createElement('div'));
            for(let i=1; i<=lastDate; i++) {{
                const day = document.createElement('div');
                day.className = 'day';
                const dateKey = `${{currentYear}}-${{String(currentMonth+1).padStart(2,'0')}}-${{String(i).padStart(2,'0')}}`;
                const numDiv = document.createElement('div');
                numDiv.className = 'day-num';
                numDiv.innerText = i;
                day.appendChild(numDiv);
                const today = new Date();
                if(i === today.getDate() && currentMonth === today.getMonth()) day.classList.add('today');
                if(events[dateKey]) {{
                    const tasks = events[dateKey];
                    day.classList.add('has-event');
                    day.title = tasks.join('\\n');
                    const dotContainer = document.createElement('div');
                    dotContainer.className = 'dot-container';
                    const limit = Math.min(tasks.length, 3);
                    for(let d=0; d<limit; d++) {{
                        const dot = document.createElement('div');
                        dot.className = 'dot';
                        dotContainer.appendChild(dot);
                    }}
                    day.appendChild(dotContainer);
                }}
                calendarEl.appendChild(day);
            }}
        }}
        render();
    </script>
</body>
</html>
"""
# 높이를 550으로 대폭 축소! (컴팩트)
components.html(html_code, height=550, scrolling=False)

# 2. 상세 조회 (작게)
c1, c2 = st.columns([1, 1.5])

with c1:
    st.markdown("##### 📅 날짜 선택")
    selected_date = st.date_input("확인할 날짜", datetime.now(), label_visibility="collapsed")

with c2:
    st.markdown(f"##### 📋 {selected_date.strftime('%m/%d')} 일정")
    if not df.empty:
        filtered_df = df[df["날짜"] == str(selected_date)]
        if not filtered_df.empty:
            for index, row in filtered_df.iterrows():
                check = "✅" if row['완료'] else "▫️"
                st.markdown(
                    f"""<div class="task-card"><b>{check} {row['할일']}</b></div>""", 
                    unsafe_allow_html=True
                )
        else:
            st.caption("일정 없음")
    else:
        st.caption("데이터 없음")
