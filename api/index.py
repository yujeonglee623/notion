from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# 환경변수 가져오기
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

@app.route('/api/get_tasks', methods=['GET'])
def get_tasks():
    # 1. 비밀키 검사 (여기가 제일 중요!)
    if not NOTION_TOKEN or not DATABASE_ID:
        return jsonify({"error": "Vercel 환경변수(NOTION_TOKEN, DATABASE_ID)가 설정되지 않았습니다!"}), 500

    try:
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        payload = {"sorts": [{"property": "Date", "direction": "ascending"}]}
        response = requests.post(url, headers=headers, json=payload)
        
        # 2. 노션 응답 검사
        if response.status_code != 200:
            return jsonify({"error": f"노션 연결 실패: {response.text}"}), 500
        
        data = response.json()
        events = {}
        list_data = []

        for result in data.get("results", []):
            try:
                props = result["properties"]
                page_id = result["id"]
                
                # 데이터가 없으면 빈 문자열 처리 (에러 방지)
                title_list = props.get("To-Do", {}).get("title", [])
                title = title_list[0]["plain_text"] if title_list else "제목 없음"
                
                date_info = props.get("Date", {}).get("date", {})
                date = date_info.get("start") if date_info else None
                
                completed = props.get("Complete", {}).get("checkbox", False)
                
                if not completed and date:
                    if date not in events: events[date] = []
                    events[date].append(title)
                
                if date:
                    list_data.append({"id": page_id, "date": date, "task": title, "completed": completed})
            except Exception as e:
                continue # 데이터 하나가 이상해도 무시하고 계속 진행
        
        # 성공적으로 데이터 반환
        return jsonify({"events": events, "list": list_data})

    except Exception as e:
        # 파이썬 내부 에러 발생 시
        return jsonify({"error": f"파이썬 코드 에러: {str(e)}"}), 500

@app.route('/api/delete_task', methods=['POST'])
def delete_task():
    try:
        data = request.json
        page_id = data.get("page_id")
        url = f"https://api.notion.com/v1/pages/{page_id}"
        payload = {"archived": True}
        response = requests.patch(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            return jsonify({"error": "삭제 실패"}), 500
            
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run()
