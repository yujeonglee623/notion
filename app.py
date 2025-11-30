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
    st.error("Secrets 설정 필요")
    st.stop()

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# ==========================================
# 🧠 파이썬 백엔드
# ==========================================
def get_data():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    payload = {"sorts": [{"property": "Date", "direction": "ascending"}]}
    res = requests.post(url, headers=headers, json=payload)
    
    if res.status_code != 200: return "{}", pd.DataFrame()

    results = res.json().get("results", [])
    calendar_events = {}
    df_list = []
    
    for result in results:
        try:
            props = result["properties"]
            page_id = result["id"]
            title = props["To-Do"]["title"][0]["plain_text"] if props["To-Do"]["title"] else ""
            date = props["Date"]["date"]["start"] if props["Date"]["date"] else None
            completed = props.get("Complete", {}).get("checkbox", False)
            
            if not date: continue
            if not completed:
                if date not in calendar_events: calendar_events[date] = []
                calendar_events[date].append(title)
            df_list.append({"ID": page_id, "날짜": date, "할일": title, "완료": completed})
        except: continue
            
    return json.dumps(calendar_events, ensure_ascii=False), pd.DataFrame(df_list)

# ==========================================
# 💅 UI 디자인 (초미니 버전)
# ==========================================
st.set_page_config(page_title="Mini Cal", layout="centered")

# Streamlit 여백 강제 삭제 (상하좌우 꽉 채우기)
st.markdown("""
    <style>
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            max-width: 100% !important;
        }
        header, footer { visibility: hidden; }
        
        /* 아래쪽 리스트 폰트 줄이기 */
        .stMarkdown p { font-size: 0.8rem !important; }
        .stDateInput label { display: none; } /* 날짜 라벨 숨기기 */
        div[data-testid="stDateInput"] { transform: scale(0.9); transform-origin: left top; }
    </style>
""", unsafe_allow_html=True)

events_json, df = get_data()

# 1. 캘린더 (HTML - Ultra Mini Size)
html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        ::-webkit-scrollbar {{ display: none; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
            margin: 0; padding: 0; 
            display: flex; justify-content: center; 
        }}
        .container {{ 
            width: 100%; 
            max-width: 280px; /* ⭐ 여기가 핵심! 최대폭 280px */
            padding-bottom: 0px; 
        }}
        
        .header {{ 
            font-size: 0.9rem; /* 헤더 폰트 작게 */
            font-weight: 800; 
            margin: 5px 0 10px 0; /* 여백 축소 */
            color: #333; 
            text-align: center; 
        }}
        
        .calendar-grid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }} /* 간격 2px */
        .day-name {{ text-align: center; color: #999; font-size: 0.6rem; margin-bottom: 2px; font-weight: 600; }}
        
        .day {{ 
            aspect-ratio: 1/0.85; 
            border-radius: 6px; 
            background: #fff; 
            border: 1px solid #eee;
            padding: 0px; 
            display: flex; flex-direction: column; align-items: center; justify-content: center; 
            position: relative; cursor: pointer; color: #333;
        }}
        
        .day:hover {{ border-color: #FFD9E8; }}
        .day.today {{ border: 1px solid #E16259; color: #E16259; font-weight: bold; }}
        .day.has-event {{ background-color: #FFD9E8 !important; color: white !important; font-weight: bold; border: none; }}
        
        .day-num {{ font-size: 0.75rem; margin-bottom: 1px; z-index: 10; }} /* 숫자 크기 12px 정도 */
        
        .dot-container {{ display: flex; gap: 2px; margin-top: 1px; }}
        .dot {{ width: 3px; height: 3px; background-color: #E16259; border-radius: 50%; }} /* 점 크기 3px */
        .day.has-event .dot {{ background-color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header" id="month-year"></div>
        <div class="calendar-grid" id="calendar">
            <div class="day-name">S</div><div class="day-name">M</div><div class="day-name">T</div>
            <div class="day-name">W</div><div class="day-name">T</div><div class="day-name">F</div><div class="day-name">S</div>
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
# 높이를 320으로 확 줄임 (진짜 작음!)
components.html(html_code, height=320, scrolling=False)

# 2. 리스트 (미니)
c1, c2 = st.columns([1.5, 2])
with c1:
    selected_date = st.date_input("날짜", datetime.now(), label_visibility="collapsed")
with c2:
    if not df.empty:
        filtered_df = df[df["날짜"] == str(selected_date)]
        if not filtered_df.empty:
            for index, row in filtered_df.iterrows():
                check = "✅" if row['완료'] else "▫️"
                # 아주 작은 폰트로 리스트 표시
                st.markdown(f"<div style='font-size:0.8rem; margin-bottom:2px;'>{check} {row['할일']}</div>", unsafe_allow_html=True)
        else:
            st.caption("일정 없음")
    else:
        st.caption("No Data")
