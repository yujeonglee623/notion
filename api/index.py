from flask import Flask

app = Flask(__name__)

@app.route('/api/get_tasks')
def home():
    return {"status": "Alive!", "message": "서버가 살아있습니다!"}

# Vercel은 이 app 객체를 찾아서 실행함
