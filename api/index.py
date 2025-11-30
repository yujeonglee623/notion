from flask import Flask, request, jsonify
import requests
import os

# Vercel이 찾는 게 바로 이 'app' 변수야!
app = Flask(__name__)

# 환경변수 가져오기
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

@app.route('/', methods=['GET'])
def home():
    return "API is running!"

@app.route('/api/get_tasks', methods=['GET'])
def get_tasks():
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
                title = props["To-Do"]["title"][0]["plain_text"]
                date = props["Date"]["date"]["start"]
                completed = props["Complete"]["checkbox"]
                
                if not completed:
                    if date not in events: events[date] = []
                    events[date].append(title)
                
                list_data.append({"id": page_id, "date": date, "task": title, "completed": completed})
            except:
                continue
        
        return jsonify({"events": events, "list": list_data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/delete_task', methods=['POST'])
def delete_task():
    try:
        data = request.json
        page_id = data.get("page_id")
        url = f"https://api.notion.com/v1/pages/{page_id}"
        payload = {"archived": True}
        requests.patch(url, headers=headers, json=payload)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 이 부분은 Vercel에서는 무시되지만, 로컬 테스트용으로 남겨둠
if __name__ == '__main__':
    app.run()
