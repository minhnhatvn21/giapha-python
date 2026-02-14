# api/index.py
from flask import Flask, render_template, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

app = Flask(__name__, template_folder='../templates')

# --- KẾT NỐI FIREBASE ---
# Kiểm tra xem đã kết nối chưa để tránh lỗi khi deploy Vercel
if not firebase_admin._apps:
    # Trên Vercel, ta sẽ dùng biến môi trường (Environment Variable) để bảo mật
    # Trên máy cá nhân, ta dùng file firebase_key.json
    if os.environ.get('FIREBASE_CREDENTIALS'):
        cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
        cred = credentials.Certificate(cred_dict)
    else:
        # Đường dẫn file json tải về từ bước 1
        cred = credentials.Certificate('firebase_key.json')
    
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('home.html')

# API: Lấy danh sách thành viên
@app.route('/api/members', methods=['GET'])
def get_members():
    try:
        members_ref = db.collection('thanh_vien')
        docs = members_ref.stream()
        members = []
        for doc in docs:
            member = doc.to_dict()
            member['id'] = doc.id
            members.append(member)
        return jsonify(members), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API: Thêm thành viên mới
@app.route('/api/members', methods=['POST'])
def add_member():
    try:
        data = request.json
        # Dữ liệu cơ bản
        new_member = {
            "name": data.get('name'),
            "birth_name": data.get('birth_name', ''),
            "gender": data.get('gender', 'male'),
            "dates": data.get('dates', ''),
            "parent_id": data.get('parent_id', None), # ID cha để nối cây
            "spouse": data.get('spouse', ''),
            "bio": data.get('bio', ''),
            "created_at": firestore.SERVER_TIMESTAMP
        }
        
        # Lưu vào Firestore
        update_time, member_ref = db.collection('thanh_vien').add(new_member)
        
        return jsonify({"success": True, "id": member_ref.id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Để chạy dưới dạng serverless function trên Vercel
# app này được gọi bởi Vercel, không cần if __name__ == '__main__'