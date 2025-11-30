import streamlit as st
import requests
import json
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime

# ==========================================
# 🔐 유정이의 비밀 열쇠 (Streamlit Secrets에서 가져오기)
# ==========================================
# 깃허브에는 키를 올리지 않고, 나중에 배포 사이트(Streamlit Cloud)에 따로 입력할 거야!
try:
    NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
    DATABASE_ID = st.secrets["DATABASE_ID"]
except:
    # 혹시 로컬에서 실행할 때 에러 방지용 (임시)
    st.error("비밀키가 설정되지 않았어! 배포할 때 Secrets에 입력해야 해.")
    st.stop()

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# ... (이 밑으로는 아까 그 코드 그대로 유지!) ...

# ==========================================
# 🧠 파이썬 백엔드
# ==========================================
def add_task_to_notion(task, date):
    url = "https://api.notion.com/v1/pages"
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "To-Do": {"title": [{"text": {"content": task}}]},
            "Date": {"date": {"start": str(date)}},
            "Complete": {"checkbox": False}
        }
    }
    requests.post(url, headers=headers, json=data)

def delete_page(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {"archived": True}
    res = requests.patch(url, headers=headers, json=data)
    return res.status_code == 200

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
# 💅 UI 디자인
# ==========================================
st.set_page_config(page_title="유정이의 핑크 캘린더", layout="wide")
st.markdown("""<style>.block-container { padding-top: 1rem; } header, footer { visibility: hidden; }</style>""", unsafe_allow_html=True)

# 1. 입력창
st.markdown("### ✏️ 일정 추가")
with st.form("input_form", clear_on_submit=True):
    c1, c2, c3 = st.columns([3, 2, 1])
    with c1: task_input = st.text_input("할 일", label_visibility="collapsed")
    with c2: date_input = st.date_input("날짜", label_visibility="collapsed")
    with c3: submitted = st.form_submit_button("저장")
    if submitted and task_input:
        add_task_to_notion(task_input, date_input)
        st.rerun()

events_json, df = get_data()

# 2. 캘린더 (HTML) - 시각화용
st.markdown("---")
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

# 3. 👇 여기가 핵심! 날짜별 상세 보기 (필터링 기능)
st.markdown("---")

# 레이아웃: 왼쪽(날짜 선택) | 오른쪽(그 날짜의 일정 리스트)
c1, c2 = st.columns([1, 2])

with c1:
    st.markdown("### 🔍 날짜 선택")
    st.info("캘린더에서 확인한 날짜를\n여기서 선택해주세요!")
    # 기본값을 오늘 날짜로 설정
    selected_date = st.date_input("확인할 날짜", datetime.now(), label_visibility="collapsed")

with c2:
    st.markdown(f"### 📋 {selected_date.strftime('%m월 %d일')}의 일정")
    
    if not df.empty:
        # 1. 내가 선택한 날짜의 데이터만 걸러내기 (Filtering)
        # 데이터프레임의 '날짜' 컬럼은 문자열(String)이거나 날짜형일 수 있으니 맞춰줘야 해
        filtered_df = df[df["날짜"] == str(selected_date)]
        
        if not filtered_df.empty:
            # 일정이 있으면 보여주기
            for index, row in filtered_df.iterrows():
                # 카드 형태로 예쁘게 보여주기
                with st.container():
                    col_text, col_del = st.columns([4, 1])
                    with col_text:
                        # 체크박스로 완료 여부 보여주기 (노션엔 반영 안되지만 시각적으로)
                        st.markdown(f"**▫️ {row['할일']}**")
                    with col_del:
                        # 삭제 버튼 (고유 키를 써서 버튼끼리 안 겹치게)
                        if st.button("삭제", key=f"del_{row['ID']}"):
                            if delete_page(row['ID']):
                                st.toast("삭제 완료!")
                                st.rerun()
                    st.markdown("---") # 구분선
        else:
            st.success("이 날은 일정이 없어요! 자유시간 😆")
    else:
        st.warning("등록된 전체 일정이 하나도 없어요.")