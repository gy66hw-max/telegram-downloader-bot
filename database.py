import sqlite3
from datetime import datetime, timedelta
from config import DB_NAME, SUB_PRICES

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. جدول المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                coins INTEGER DEFAULT 0,
                sub_expire TEXT,
                referred_by INTEGER,
                ref_activated INTEGER DEFAULT 0,
                usage_count INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        for col, col_type in [("username", "TEXT"), ("first_name", "TEXT"), ("ref_activated", "INTEGER DEFAULT 0"), ("is_banned", "INTEGER DEFAULT 0")]:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass

        # 2. جدول الكوبونات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coupons (
                code TEXT PRIMARY KEY,
                coupon_type TEXT,
                is_used INTEGER DEFAULT 0,
                used_by INTEGER
            )
        ''')

        # 3. جدول التخزين المؤقت للروابط
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_cache (
                url TEXT PRIMARY KEY,
                file_id TEXT,
                file_type TEXT
            )
        ''')

        # 4. جدول روابط المكافآت المحدودة
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gift_links (
                code TEXT PRIMARY KEY,
                reward_type TEXT,
                reward_amount INTEGER,
                max_uses INTEGER,
                current_uses INTEGER DEFAULT 0,
                custom_message TEXT
            )
        ''')

        # 5. جدول مطالبات المكافآت (لمنع التكرار)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gift_claims (
                code TEXT,
                user_id INTEGER,
                PRIMARY KEY (code, user_id)
            )
        ''')
        
        conn.commit()

# --- إدارة الحظر والوصول ---

def ban_user(target: str) -> bool:
    """حظر مستخدم بواسطة المعرف الرقمي أو اليوزرنيم"""
    clean_target = str(target).strip().lstrip("@")
    with get_db() as conn:
        cursor = conn.cursor()
        if clean_target.isdigit():
            cursor.execute(
                "UPDATE users SET is_banned = 1 WHERE user_id = ? OR LOWER(username) = LOWER(?)",
                (int(clean_target), clean_target)
            )
        else:
            cursor.execute(
                "UPDATE users SET is_banned = 0 WHERE LOWER(username) = LOWER(?)",
                (clean_target,)
            )
        conn.commit()
        return cursor.rowcount > 0

def unban_user(target: str) -> bool:
    """إلغاء حظر مستخدم بواسطة المعرف الرقمي أو اليوزرنيم"""
    clean_target = str(target).strip().lstrip("@")
    with get_db() as conn:
        cursor = conn.cursor()
        if clean_target.isdigit():
            cursor.execute(
                "UPDATE users SET is_banned = 0 WHERE user_id = ? OR LOWER(username) = LOWER(?)",
                (int(clean_target), clean_target)
            )
        else:
            cursor.execute(
                "UPDATE users SET is_banned = 0 WHERE LOWER(username) = LOWER(?)",
                (clean_target,)
            )
        conn.commit()
        return cursor.rowcount > 0

def is_user_banned(user_id: int) -> bool:
    """التحقق مما إذا كان المستخدم محظوراً"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        return bool(res and res["is_banned"] == 1)

# --- إدارة المستخدمين والإحالات ---

def get_or_create_user(user_id: int, first_name: str = None, username: str = None, referrer_id: int = None):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            referrer_info = None
            if referrer_id and referrer_id != user_id:
                cursor.execute("SELECT user_id, first_name, username FROM users WHERE user_id = ?", (referrer_id,))
                referrer_info = cursor.fetchone()

            cursor.execute(
                "INSERT INTO users (user_id, first_name, username, referred_by) VALUES (?, ?, ?, ?)",
                (user_id, first_name, username, referrer_id if referrer_id != user_id else None)
            )
            if referrer_id and referrer_id != user_id:
                # 🎁 إعطاء 2 عملة للمحيل فور دخول مستخدم جديد
                cursor.execute("UPDATE users SET coins = coins + 2 WHERE user_id = ?", (referrer_id,))
            conn.commit()
            
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            return user, True, referrer_info
        else:
            cursor.execute(
                "UPDATE users SET first_name = ?, username = ? WHERE user_id = ?",
                (first_name or user["first_name"], username or user["username"], user_id)
            )
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            return user, False, None

def get_user_ref_count(user_id: int) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
        res = cursor.fetchone()
        return res[0] if res else 0

def trigger_ref_activation_bonus(user_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT referred_by, ref_activated FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if user and user["referred_by"] and user["ref_activated"] == 0:
            referrer_id = user["referred_by"]
            # 🎁 إعطاء 3 عملات إضافية عندما يشترك المستخدم (إجمالي المكافأة 5 عملات)
            cursor.execute("UPDATE users SET coins = coins + 3 WHERE user_id = ?", (referrer_id,))
            cursor.execute("UPDATE users SET ref_activated = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            return referrer_id
    return None

def increment_usage(user_id: int):
    with get_db() as conn:
        conn.execute("UPDATE users SET usage_count = usage_count + 1 WHERE user_id = ?", (user_id,))
        conn.commit()

# --- إدارة الاشتراكات والكوبونات ---

def check_sub_status(user_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT sub_expire FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        if res and res["sub_expire"]:
            try:
                expire_dt = datetime.strptime(res["sub_expire"], "%Y-%m-%d %H:%M:%S")
                if expire_dt > datetime.now():
                    return True, expire_dt
            except ValueError:
                pass
        return False, None

def add_sub_days(user_id: int, days: int) -> str:
    """دالة مساعدة لإضافة/تمديد أيام اشتراك مستخدم"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT sub_expire FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        now = datetime.now()
        
        if user and user["sub_expire"]:
            try:
                current_exp = datetime.strptime(user["sub_expire"], "%Y-%m-%d %H:%M:%S")
                new_exp = (current_exp if current_exp > now else now) + timedelta(days=days)
            except ValueError:
                new_exp = now + timedelta(days=days)
        else:
            new_exp = now + timedelta(days=days)

        new_exp_str = new_exp.strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("UPDATE users SET sub_expire = ? WHERE user_id = ?", (new_exp_str, user_id))
        conn.commit()
        return new_exp.strftime("%Y-%m-%d %H:%M")

def buy_sub_with_coins(user_id: int, plan_type: str):
    if plan_type not in SUB_PRICES:
        return False, "❌ نوع الاشتراك غير معروف.", None
    
    cost = SUB_PRICES[plan_type]
    days = 1 if plan_type == "daily" else (7 if plan_type == "weekly" else 30)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if not user or user["coins"] < cost:
            return False, f"❌ رصيدك غير كافٍ! تحتاج إلى {cost} عملة.", None

        # خصم العملات
        conn.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (cost, user_id))
        conn.commit()

    exp_date_str = add_sub_days(user_id, days)
    referrer_id = trigger_ref_activation_bonus(user_id)
    return True, f"🎉 تم شراء الاشتراك الـ {plan_type} بنجاح حتى {exp_date_str}!", referrer_id

def create_coupon(code: str, coupon_type: str):
    with get_db() as conn:
        conn.execute("INSERT INTO coupons (code, coupon_type) VALUES (?, ?)", (code, coupon_type))
        conn.commit()

def redeem_coupon(user_id: int, code: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM coupons WHERE code = ? AND is_used = 0", (code,))
        coupon = cursor.fetchone()
        if not coupon:
            return False, "❌ الكوبون غير صالح أو تم استخدامه سابقاً.", None
        
        c_type = coupon["coupon_type"]
        days = 1 if c_type == "daily" else (7 if c_type == "weekly" else 30)
        
        conn.execute("UPDATE coupons SET is_used = 1, used_by = ? WHERE code = ?", (user_id, code))
        conn.commit()

    exp_date_str = add_sub_days(user_id, days)
    referrer_id = trigger_ref_activation_bonus(user_id)
    return True, f"🎉 تم تفعيل الكوبون الـ {c_type} بنجاح حتى {exp_date_str}!", referrer_id

# --- نظام روابط المكافآت المحدودة ---

def create_gift_link(code: str, reward_type: str, reward_amount: int, max_uses: int, custom_message: str):
    """حفظ رابط مكافأة جديد في قاعدة البيانات"""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO gift_links (code, reward_type, reward_amount, max_uses, custom_message)
            VALUES (?, ?, ?, ?, ?)
        """, (code, reward_type, reward_amount, max_uses, custom_message))
        conn.commit()

def claim_gift_link(user_id: int, code: str):
    """معالجة مطالبات وروابط الجوائز المؤقتة"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT reward_type, reward_amount, max_uses, current_uses, custom_message FROM gift_links WHERE code = ?", (code,))
        link = cursor.fetchone()

        if not link:
            return False, "NOT_FOUND", None, None

        reward_type = link["reward_type"]
        reward_amount = link["reward_amount"]
        max_uses = link["max_uses"]
        current_uses = link["current_uses"]
        custom_message = link["custom_message"]

        # 1. التحقق من اكتمال العدد
        if current_uses >= max_uses:
            return False, "EXPIRED", None, custom_message

        # 2. التحقق مما إذا كان المستخدم استلم المكافأة سابقاً
        cursor.execute("SELECT 1 FROM gift_claims WHERE code = ? AND user_id = ?", (code, user_id))
        if cursor.fetchone():
            return False, "ALREADY_CLAIMED", None, custom_message

        # 3. تسجيل المطالبة وزيادة العداد
        cursor.execute("INSERT INTO gift_claims (code, user_id) VALUES (?, ?)", (code, user_id))
        cursor.execute("UPDATE gift_links SET current_uses = current_uses + 1 WHERE code = ?", (code,))

        # 4. تسليم الجائزة حسب النوع
        if reward_type == "coins":
            cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (reward_amount, user_id))
            conn.commit()
            return True, "SUCCESS", f"🪙 +{reward_amount} عملة", custom_message
        else:
            conn.commit()
            exp_str = add_sub_days(user_id, reward_amount)
            return True, "SUCCESS", f"⭐ +{reward_amount} يوم اشتراك مجاني (حتى {exp_str})", custom_message

# --- الإحصائيات والكاش ---

def get_stats():
    with get_db() as conn:
        cursor = conn.cursor()
        total_users = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_usage = cursor.execute("SELECT SUM(usage_count) FROM users").fetchone()[0] or 0
        total_refs = cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by IS NOT NULL").fetchone()[0]
        return total_users, total_usage, total_refs

def get_top_users(limit=10):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, first_name, username, usage_count FROM users ORDER BY usage_count DESC LIMIT ?", (limit,))
        return cursor.fetchall()

def reset_competition():
    with get_db() as conn:
        conn.execute("UPDATE users SET usage_count = 0, ref_activated = 0")
        conn.commit()

def get_cached_file(url: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_id, file_type FROM file_cache WHERE url = ?", (url,))
        return cursor.fetchone()

def save_file_cache(url: str, file_id: str, file_type: str):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO file_cache (url, file_id, file_type) VALUES (?, ?, ?)", (url, file_id, file_type))
        conn.commit()
