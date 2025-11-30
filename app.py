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
    st.error("비밀키가 설정되지 않았어! 배포할 때 Secrets에 입력해야 해.")
    st.stop()

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# ==========================================
# 🧠 파이썬 백엔드 (Only Reading!)
# ==========================================
# 쓰기/삭제 함수는 다 지웠어! 오직 읽기만!

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
            # Page ID는 이제 필요 없지만, 나중을 위해 남겨둠
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
# 💅 UI 디자인 (깔끔 그 자체 ✨)
# ==========================================
st.set_page_config(page_title="유정이의 핑크 캘린더", layout="wide")

# 여백 최소화 스타일
st.markdown("""
    <style>
        .block-container { padding-top: 0rem; padding-bottom: 0rem; } 
        header, footer { visibility: hidden; }
        
        /* 카드 스타일 */
        .task-card {
            background-color: white;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #eee;
            margin-bottom: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)

# 데이터 가져오기
events_json, df = get_data()

# 1. 캘린더 (HTML)
html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        ::-webkit-scrollbar {{ display: none; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 5px; display: flex; justify-content: center; }}
        .container {{ width: 100%; max-width: 900px; padding-bottom: 10px; }}
        .header {{ font-size: 1.4rem; font-weight: 800; margin: 15px 0; color: #333; text-align: center; }}
        .calendar-grid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; }}
        .day-name {{ text-align: center; color: #999; font-size: 0.8rem; margin-bottom: 5px; font-weight: 600; }}
        
        .day {{ 
            aspect-ratio: 1/0.8; border-radius: 12px; background: #fff; border: 1px solid #eee;
            padding: 6px; font-size: 1rem; display: flex; flex-direction: column;
            align-items: center; justify-content: center; position: relative; cursor: pointer; color: #333;
        }}
        .day:hover {{ border-color: #FFD9E8; transform: translateY(-2px); }}
        .day.today {{ border: 2px solid #FFD9E8; color: #E16259; font-weight: bold; }}
        
        .day.has-event {{ background-color: #FFD9E8 !important; color: white !important; font-weight: bold; border: none; }}
        
        .day-num {{ font-size: 1.1rem; margin-bottom: 4px; z-index: 10; }}
        .dot-container {{ display: flex; gap: 4px; margin-top: 2px; }}
        .dot {{ width: 5px; height: 5px; background-color: #E16259; border-radius: 50%; }}
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
components.html(html_code, height=950, scrolling=True)

# 2. 상세 조회 (삭제 버튼 없이 깔끔하게 보여주기만 함)
st.markdown("---")
c1, c2 = st.columns([1, 2])

with c1:
    st.markdown("### 🔍 날짜 선택")
    st.caption("노션 DB에서 일정을 관리하세요.")
    selected_date = st.date_input("확인할 날짜", datetime.now(), label_visibility="collapsed")

with c2:
    st.markdown(f"### 📋 {selected_date.strftime('%m월 %d일')}의 일정")
    if not df.empty:
        filtered_df = df[df["날짜"] == str(selected_date)]
        if not filtered_df.empty:
            for index, row in filtered_df.iterrows():
                # 삭제 버튼 없이 그냥 텍스트만 깔끔하게 보여줌
                check = "✅" if row['완료'] else "▫️"
                st.markdown(
                    f"""
                    <div class="task-card">
                        <b>{check} {row['할일']}</b>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
        else:
            st.info("이 날은 일정이 없어요!")
    else:
        st.warning("등록된 전체 일정이 없습니다.")
