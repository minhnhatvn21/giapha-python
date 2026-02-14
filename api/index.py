from flask import Flask, render_template, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

app = Flask(__name__, template_folder='../templates')

# --- KẾT NỐI FIREBASE (Giữ nguyên như cũ) ---
if not firebase_admin._apps:
    if os.environ.get('FIREBASE_CREDENTIALS'):
        cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
        cred = credentials.Certificate(cred_dict)
    else:
        cred = credentials.Certificate('firebase_key.json') # Chạy local
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- HÀM ĐỆ QUY XÂY DỰNG CÂY VÀ TÍNH MÃ SỐ ---
def build_tree_with_code(members, parent_id=None, prefix=""):
    tree = []
    # Lấy danh sách con của parent_id hiện tại
    children = [m for m in members if m.get('parent_id') == parent_id]
    
    # Sắp xếp con theo ngày sinh hoặc thứ tự nhập (nếu có trường sort)
    # Ở đây tạm sắp xếp theo tên
    children.sort(key=lambda x: x.get('birth_date', '')) 

    for index, child in enumerate(children):
        # Tạo mã số: Nếu prefix trống (Thủy tổ) thì là "1", ngược lại là "Cha.Con"
        # index + 1 để bắt đầu từ 1
        current_code = f"{index + 1}" if prefix == "" else f"{prefix}.{index + 1}"
        
        # Gán mã vào object
        child['code'] = current_code
        
        # Đệ quy tìm con của người này
        child['children'] = build_tree_with_code(members, child['id'], current_code)
        
        tree.append(child)
    
    return tree

@app.route('/')
def home():
    # 1. Lấy hết dữ liệu từ Firebase 1 lần (đỡ tốn lượt đọc)
    try:
        docs = db.collection('thanh_vien').stream()
        all_members = []
        for doc in docs:
            m = doc.to_dict()
            m['id'] = doc.id
            all_members.append(m)

        # 2. Xử lý logic cây
        # Tìm những người không có cha (Thủy tổ)
        roots = [m for m in all_members if not m.get('parent_id')]
        
        # Xây cây hoàn chỉnh
        full_tree = build_tree_with_code(all_members, None, "")
        
        # Nếu không tìm thấy root theo kiểu parent_id=None, thử tìm theo logic khác hoặc pass all
        if not full_tree and all_members:
             # Fallback: Nếu data cũ chưa chuẩn, hiển thị list phẳng để debug
             pass 

        return render_template('home.html', tree=full_tree)
    except Exception as e:
        return f"Lỗi kết nối Database: {str(e)}"

# API nhập liệu (Giữ nguyên để bạn dùng tool nhập)
@app.route('/api/members', methods=['POST'])
def add_member():
    try:
        data = request.json
        new_member = {
            "name": data.get('name'),
            "birth_date": data.get('birth_date', ''), # Đổi tên field cho khớp logic sort
            "gender": data.get('gender', 'male'),
            "parent_id": data.get('parent_id') or None,
            "created_at": firestore.SERVER_TIMESTAMP
        }
        db.collection('thanh_vien').add(new_member)
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
