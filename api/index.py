from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# 환경변수 (ntn_ 키가 잘 들어올 거야)
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

@app.route('/api/get_tasks', methods=['GET'])
def get_tasks():
    # 키가 제대로 설정 안 됐으면 알려줌
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
                # 데이터 파싱
                title_list = props.get("To-Do", {}).get("title", [])
                title = title_list[0]["plain_text"] if title_list else "제목 없음"
                
                date_info = props.get("Date", {}).get("date", {})
                date = date_info.get("start") if date_info else None
                
                completed = props.get("Complete", {}).get("checkbox", False)
                
                if date:
                    # 캘린더용 (미완료만 점 찍기)
                    if not completed:
                        if date not in events: events[date] = []
                        events[date].append(title)
                    
                    # 리스트용 (전체)
                    list_data.append({"date": date, "task": title, "completed": completed})
            except:
                continue
        
        return jsonify({"events": events, "list": list_data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
