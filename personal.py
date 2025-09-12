import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

def save_user(user):
    # foydalanuvchi ma'lumotlarini tayyorlash
    user_data = {
        "id": user.id,
        "full_name": user.full_name,
        "username": f"@{user.username}" if user.username else "yo‘q",
        "phone": user.phone if hasattr(user, "phone") and user.phone else "❌ Telefon raqam yo‘q",
        "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # JSON faylga saqlash
    file_path = Path("users.json")
    
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            users_list = json.load(f)
    else:
        users_list = []

    users_list.append(user_data)
    
    # vaqt bo‘yicha tartiblash
    users_list.sort(key=lambda x: x["joined_at"])
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(users_list, f, ensure_ascii=False, indent=4)

    # 🗂 Haftalar va oylarga ajratish
    weekly_data = defaultdict(list)
    monthly_data = defaultdict(list)
    
    for u in users_list:
        dt = datetime.strptime(u["joined_at"], "%Y-%m-%d %H:%M:%S")
        
        # Hafta (ISO format)
        year, week, _ = dt.isocalendar()
        weekly_data[f"{year}-week{week}"].append(u)
        
        # Oy
        monthly_data[f"{dt.year}-{dt.month:02}"].append(u)

    # JSON fayllarga alohida saqlash
    with open("weekly_users.json", "w", encoding="utf-8") as f:
        json.dump(weekly_data, f, ensure_ascii=False, indent=4)
        
    with open("monthly_users.json", "w", encoding="utf-8") as f:
        json.dump(monthly_data, f, ensure_ascii=False, indent=4)

    print(f"✅ Yangi foydalanuvchi saqlandi: {user.full_name}")

# Misol uchun: foydalanuvchi obyektini yaratish
class User:
    def __init__(self, id, full_name, username=None, phone=None):
        self.id = id
        self.full_name = full_name
        self.username = username
        self.phone = phone

# test
user = User(6460533244, "Samandar", "Master_Dragon_1")
save_user(user)
