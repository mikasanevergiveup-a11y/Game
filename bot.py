import os
import telebot
import psycopg2
from flask import Flask

# Bot Token ကို ဤနေရာတွင် ထည့်ပါ
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DATABASE_URL = "postgresql://postgres.oziuwtfvqalrndxrlhfu:5MsTXrMV6foC4FGS@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres"

# ⚠️ ဤနေရာတွင် သင်၏ ADMIN ID ကို အတိအကျ ထည့်ပါ (ဥပမာ - 123456789)
ADMIN_ID = 6673230697 

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_states = {}

def get_db_connection():
    if "6543" in DATABASE_URL:
        db_url = DATABASE_URL.replace("6543", "5432")
    else:
        db_url = DATABASE_URL
    conn = psycopg2.connect(db_url, sslmode='require')
    return conn

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                email TEXT,
                password TEXT,
                coins REAL DEFAULT 0,
                mining_level INT DEFAULT 0,
                machine_status TEXT DEFAULT 'None'
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database initialization error: {e}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    text = f"မင်္ဂလာပါ @{username}\nGame ဆော့ရန် အောက်ပါ gp များကို join ပေးပါနော်"
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("Join Group 1", url="https://t.me/candyhubass"))
    markup.add(telebot.types.InlineKeyboardButton("Join Group 2", url="https://t.me/CandyHub_Ch"))
    markup.add(telebot.types.InlineKeyboardButton("Join Group 3", url="https://t.me/CandyHub_Chat"))
    markup.add(telebot.types.InlineKeyboardButton("✅ Check Join", callback_data="check_join"))
    
    bot.send_message(user_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    user_id = call.from_user.id
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("📝 Sign up (အကောင့်သစ်ဖွင့်ရန်)", callback_data="auth_signup"),
        telebot.types.InlineKeyboardButton("🔑 Log in (အကောင့်ဝင်ရန်)", callback_data="auth_login")
    )
    bot.send_message(user_id, "ကျေးဇူးပြု၍ အောက်ပါတို့မှ တစ်ခုကို ရွေးချယ်ပါ:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["auth_signup", "auth_login"])
def handle_auth_mode(call):
    user_id = call.from_user.id
    mode = "signup" if call.data == "auth_signup" else "login"
    user_states[user_id] = {'mode': mode, 'step': 'waiting_email'}
    
    action_text = "အကောင့်သစ်ဖွင့်ရန်" if mode == "signup" else "အကောင့်ဝင်ရန်"
    bot.send_message(user_id, f"{action_text} သင့်ရဲ့ Email ကို ရိုက်ထည့်ပေးပါ:")

# ပုံ(Screenshot) လက်ခံရန် သီးသန့် Handler
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    state_data = user_states.get(user_id)
    
    if state_data and state_data.get('step') == 'waiting_payment_proof':
        level = state_data.get('level')
        # အကောင်းဆုံး Resolution ရှိတဲ့ ပုံကို ယူမည်
        photo_id = message.photo[-1].file_id 
        username = message.from_user.username or "User"
        
        # User ကို အကြောင်းကြားခြင်း
        bot.send_message(user_id, "✅ ငွေလွှဲပြေစာ (Screenshot) ပေးပို့မှု အောင်မြင်ပါသည်။ Admin အတည်ပြုချက်ကို စောင့်ဆိုင်းပေးပါ။")
        
        # Admin ဆီသို့ ပုံပို့ခြင်း
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(
            telebot.types.InlineKeyboardButton("✅ Confirm", callback_data=f"adm_conf_{user_id}_{level}"),
            telebot.types.InlineKeyboardButton("❌ Decline", callback_data=f"adm_decl_{user_id}")
        )
        caption = f"🧾 **New Machine Request**\n\n👤 User: @{username} (ID: `{user_id}`)\n🎮 Requested Level: {level}"
        
        try:
            bot.send_photo(ADMIN_ID, photo_id, caption=caption, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            bot.send_message(user_id, "⚠️ Admin ထံသို့ ပေးပို့ရာတွင် အမှားအယွင်းရှိနေပါသည်။ (Admin ID မှားနေနိုင်ပါသည်)")
            print(f"Error sending to admin: {e}")
            
        user_states.pop(user_id, None)

# စာသား(Text) များ လက်ခံရန် Handler
@bot.message_handler(content_types=['text'], func=lambda message: message.from_user.id in user_states)
def handle_user_input(message):
    user_id = message.from_user.id
    state_data = user_states[user_id]
    step = state_data.get('step')
    
    if step == 'waiting_email':
        state_data['email'] = message.text.strip()
        state_data['step'] = 'waiting_password'
        bot.send_message(user_id, "ကျေးဇူးပြု၍ Password (စကားဝှက်) ကို ရိုက်ထည့်ပေးပါ:")
        
    elif step == 'waiting_password':
        state_data['password'] = message.text.strip()
        email = state_data['email']
        password = state_data['password']
        mode = state_data['mode']
        
        if mode == "signup":
            state_data['step'] = 'confirm_signup'
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(
                telebot.types.InlineKeyboardButton("Yes", callback_data="signup_yes"),
                telebot.types.InlineKeyboardButton("No", callback_data="signup_no")
            )
            bot.send_message(
                user_id, 
                f"အကောင့်အချက်အလက်များ မှန်ကန်ပါသလား?\n\nEmail: {email}\nPassword: {password}", 
                reply_markup=markup
            )
        else:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT password FROM users WHERE user_id = %s AND email = %s", (user_id, email))
                row = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if row and row[0] == password:
                    bot.send_message(user_id, "✅ Log in ဝင်ရောက်ခြင်း အောင်မြင်ပါသည်။\n/buy ဟု ရိုက်၍ Mining Machine ဝယ်ယူနိုင်ပါသည်။")
                else:
                    bot.send_message(user_id, "❌ Email သို့မဟုတ် Password အမှားအယွင်းရှိနေပါသည်။ /start ဖြင့် ပြန်လည်ကြိုးစားပါ။")
            except Exception as e:
                bot.send_message(user_id, f"Error: {e}")
            finally:
                user_states.pop(user_id, None)

@bot.callback_query_handler(func=lambda call: call.data in ["signup_yes", "signup_no"])
def confirm_signup(call):
    user_id = call.from_user.id
    if user_id not in user_states:
        bot.send_message(user_id, "အချိန်ကုန်သွားပါပြီ။ /start ဖြင့် အစမှပြန်စပါ။")
        return
        
    if call.data == "signup_yes":
        state_data = user_states[user_id]
        email = state_data.get('email')
        password = state_data.get('password')
        username = call.from_user.username or "User"
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, username, email, password, coins, mining_level, machine_status) 
                VALUES (%s, %s, %s, %s, 0, 0, 'None')
                ON CONFLICT (user_id) 
                DO UPDATE SET email = EXCLUDED.email, password = EXCLUDED.password, username = EXCLUDED.username
            """, (user_id, username, email, password))
            conn.commit()
            cursor.close()
            conn.close()
            bot.send_message(user_id, "✅ အကောင့်ဖွင့်ခြင်း (Sign up) အောင်မြင်ပါသည်။\nMining Machine ဝယ်ယူရန် /buy ဟု ရိုက်ပါ။")
        except Exception as e:
            bot.send_message(user_id, f"❌ အမှားအယွင်းဖြစ်ပေါ်ခဲ့သည်: {e}")
        finally:
            user_states.pop(user_id, None)
    else:
        user_states.pop(user_id, None)
        bot.send_message(user_id, "❌ အကောင့်ဖွင့်ခြင်းကို ပယ်ဖျက်လိုက်ပါသည်။ ပြန်စရန် /start ကိုနှိပ်ပါ။")

@bot.message_handler(commands=['buy'])
def buy_machine(message):
    user_id = message.from_user.id
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("Level 1 (1hr) - 10000 coin", callback_data="buy_lvl1"))
    markup.add(telebot.types.InlineKeyboardButton("Level 2 (3hr) - 15000 coin", callback_data="buy_lvl2"))
    markup.add(telebot.types.InlineKeyboardButton("Level 3 (5hr) - 30000 coin", callback_data="buy_lvl3"))
    markup.add(telebot.types.InlineKeyboardButton("Level 4 (10hr) - 40000 coin", callback_data="buy_lvl4"))
    markup.add(telebot.types.InlineKeyboardButton("Level 5 (24hr) - 50000 coin", callback_data="buy_lvl5"))
    
    bot.send_message(user_id, "Mining machine ရွေးချယ်ပါ:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_lvl"))
def process_buy_level(call):
    user_id = call.from_user.id
    level = call.data.replace("buy_lvl", "")
    
    costs = {"1": 10000, "2": 15000, "3": 30000, "4": 40000, "5": 50000}
    cost = costs.get(level, 0)
    
    text = (
        f"Payment လုပ်ရန်:\n"
        f"Email: adm@adm.com သို့ candyhub ထဲတွင် coin {cost} လွှဲပေးပါ။\n\n"
        f"ငွေလွှဲပြီးပါက ပုံ (Screenshot) ပို့ပေးရန် Yes ကိုနှိပ်ပါ၊ မပို့လိုလျှင် No ကိုနှိပ်ပါ။"
    )
    
    user_states[user_id] = {'step': 'waiting_payment_proof', 'level': level}
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("Yes (ပုံပို့မည်)", callback_data="pay_yes"),
        telebot.types.InlineKeyboardButton("No (ပယ်ဖျက်မည်)", callback_data="pay_no")
    )
    bot.send_message(user_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["pay_yes", "pay_no"])
def payment_prompt_handler(call):
    user_id = call.from_user.id
    if call.data == "pay_yes":
        bot.send_message(user_id, "ကျေးဇူးပြု၍ ငွေလွှဲထားသော ပုံ (Screenshot) ကို ပို့ပေးပါ။")
    else:
        user_states.pop(user_id, None)
        bot.send_message(user_id, "ဝယ်ယူမှုကို ပယ်ဖျက်လိုက်ပါသည်။")

# Admin မှ Confirm (သို့) Decline လုပ်ခြင်းကို လက်ခံမည့် အပိုင်း
@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_conf_") or call.data.startswith("adm_decl_"))
def admin_verification_handler(call):
    data = call.data.split('_')
    action = data[1]
    target_user_id = int(data[2])
    
    if action == "conf":
        level = int(data[3])
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET mining_level = %s, machine_status = 'Active' WHERE user_id = %s", (level, target_user_id))
            conn.commit()
            cursor.close()
            conn.close()
            
            bot.send_message(target_user_id, f"🎉 Admin မှ သင့်ငွေလွှဲမှုကို အတည်ပြုလိုက်ပါသည်။ Level {level} Mining Machine စတင်အလုပ်လုပ်နေပါပြီ။ /profile တွင်စစ်ဆေးပါ။")
            bot.edit_message_caption("✅ **အတည်ပြုပြီးပါပြီ (Confirmed)**", chat_id=call.message.chat.id, message_id=call.message.message_id)
        except Exception as e:
            bot.send_message(call.message.chat.id, f"DB Error: {e}")
            
    elif action == "decl":
        bot.send_message(target_user_id, "❌ သင့်ငွေလွှဲမှုကို Admin မှ ငြင်းပယ်လိုက်ပါသည်။ ကျေးဇူးပြု၍ အချက်အလက်များ မှန်ကန်စွာ ပြန်လည်ပေးပို့ပါ။")
        bot.edit_message_caption("❌ **ငြင်းပယ်ပြီးပါပြီ (Declined)**", chat_id=call.message.chat.id, message_id=call.message.message_id)

@bot.message_handler(commands=['profile'])
def show_profile(message):
    user_id = message.from_user.id
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, email, coins, mining_level, machine_status FROM users WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            username, email, coins, mining_level, status = row
            text = (
                f"👤 **User Profile**\n\n"
                f"▪️ Username: @{username}\n"
                f"▪️ Email: {email}\n"
                f"▪️ Coins: {coins}\n"
                f"▪️ Mining Level: {mining_level}\n"
                f"▪️ Status: {status}"
            )
            bot.send_message(user_id, text, parse_mode="Markdown")
        else:
            bot.send_message(user_id, "အကောင့်မရှိသေးပါ။ /start ဖြင့် အစမှစတင်ပါ။")
    except Exception as e:
        bot.send_message(user_id, f"Error: {e}")

@app.route('/')
def home():
    return "Mining Bot is running!"

if __name__ == "__main__":
    init_db()
    import threading
    def run_bot():
        bot.infinity_polling()
    
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

