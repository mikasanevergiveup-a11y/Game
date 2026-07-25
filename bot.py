import os
import telebot
import psycopg2
from flask import Flask

# Bot Token ကို ဤနေရာတွင် ထည့်ပါ
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DATABASE_URL = "postgresql://postgres.oziuwtfvqalrndxrlhfu:5MsTXrMV6foC4FGS@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres"

# ⚠️ သင့်၏ ADMIN ID ကို အတိအကျ ထည့်ပါ
ADMIN_ID = 123456789 

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
        # Database Schema အသစ် (Machine Count နှင့် Live Mining အတွက်)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                email TEXT,
                password TEXT,
                coins DOUBLE PRECISION DEFAULT 0.0,
                mining_level INT DEFAULT 0,
                machine_count INT DEFAULT 0,
                machine_status TEXT DEFAULT 'None',
                mining_rate DOUBLE PRECISION DEFAULT 0.0,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        telebot.types.InlineKeyboardButton("📝 Sign up", callback_data="auth_signup"),
        telebot.types.InlineKeyboardButton("🔑 Log in", callback_data="auth_login")
    )
    bot.send_message(user_id, "ကျေးဇူးပြု၍ အောက်ပါတို့မှ တစ်ခုကို ရွေးချယ်ပါ:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["auth_signup", "auth_login"])
def handle_auth_mode(call):
    user_id = call.from_user.id
    mode = "signup" if call.data == "auth_signup" else "login"
    user_states[user_id] = {'mode': mode, 'step': 'waiting_email'}
    
    action_text = "အကောင့်သစ်ဖွင့်ရန်" if mode == "signup" else "အကောင့်ဝင်ရန်"
    bot.send_message(user_id, f"{action_text} သင့်ရဲ့ Email ကို ရိုက်ထည့်ပေးပါ:")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    state_data = user_states.get(user_id)
    
    if state_data and state_data.get('step') == 'waiting_payment_proof':
        level = state_data.get('level')
        photo_id = message.photo[-1].file_id 
        username = message.from_user.username or "User"
        
        bot.send_message(user_id, "✅ ငွေလွှဲပြေစာ (Screenshot) ပေးပို့မှု အောင်မြင်ပါသည်။ Admin အတည်ပြုချက်ကို စောင့်ဆိုင်းပေးပါ။")
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(
            telebot.types.InlineKeyboardButton("✅ Confirm", callback_data=f"adm_conf_{user_id}_{level}"),
            telebot.types.InlineKeyboardButton("❌ Decline", callback_data=f"adm_decl_{user_id}")
        )
        caption = f"🧾 **New Machine Request**\n\n👤 User: @{username} (ID: `{user_id}`)\n🎮 Requested Level: {level}"
        
        try:
            bot.send_photo(ADMIN_ID, photo_id, caption=caption, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            bot.send_message(user_id, "⚠️ Admin ထံသို့ ပေးပို့ရာတွင် အမှားအယွင်းရှိနေပါသည်။ (Admin ID စစ်ဆေးပါ)")
            
        user_states.pop(user_id, None)

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
                    bot.send_message(user_id, "✅ Log in ဝင်ရောက်ခြင်း အောင်မြင်ပါသည်။\n/profile ဟုရိုက်၍ စစ်ဆေးနိုင်ပါသည်။")
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
                INSERT INTO users (user_id, username, email, password, coins, mining_level, machine_count, machine_status, mining_rate) 
                VALUES (%s, %s, %s, %s, 0.0, 0, 0, 'None', 0.0)
                ON CONFLICT (user_id) 
                DO UPDATE SET email = EXCLUDED.email, password = EXCLUDED.password, username = EXCLUDED.username
            """, (user_id, username, email, password))
            conn.commit()
            cursor.close()
            conn.close()
            bot.send_message(user_id, "✅ အကောင့်ဖွင့်ခြင်း အောင်မြင်ပါသည်။\n/buy ဟု ရိုက်၍ Mining Machine ဝယ်ယူပါ။")
        except Exception as e:
            bot.send_message(user_id, f"❌ DB Error: {e}")
        finally:
            user_states.pop(user_id, None)
    else:
        user_states.pop(user_id, None)
        bot.send_message(user_id, "❌ ပယ်ဖျက်လိုက်ပါသည်။")

@bot.message_handler(commands=['buy'])
def buy_machine(message):
    user_id = message.from_user.id
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("Level 1 (10000 coin)", callback_data="buy_lvl1"))
    markup.add(telebot.types.InlineKeyboardButton("Level 2 (15000 coin)", callback_data="buy_lvl2"))
    markup.add(telebot.types.InlineKeyboardButton("Level 3 (30000 coin)", callback_data="buy_lvl3"))
    markup.add(telebot.types.InlineKeyboardButton("Level 4 (40000 coin)", callback_data="buy_lvl4"))
    markup.add(telebot.types.InlineKeyboardButton("Level 5 (50000 coin)", callback_data="buy_lvl5"))
    
    bot.send_message(user_id, "ဝယ်ယူမည့် Mining Machine ရွေးချယ်ပါ:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_lvl"))
def process_buy_level(call):
    user_id = call.from_user.id
    level = call.data.replace("buy_lvl", "")
    
    costs = {"1": 10000, "2": 15000, "3": 30000, "4": 40000, "5": 50000}
    cost = costs.get(level, 0)
    
    text = f"Email: adm@adm.com သို့ coin {cost} လွှဲပေးပါ။\n\nငွေလွှဲပြီးပါက ပုံပို့ရန် Yes ကိုနှိပ်ပါ။"
    
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
        bot.send_message(user_id, "ငွေလွှဲထားသော ပုံ (Screenshot) ကို ပို့ပေးပါ။")
    else:
        user_states.pop(user_id, None)
        bot.send_message(user_id, "ပယ်ဖျက်လိုက်ပါသည်။")

# Admin Confirm လုပ်ခြင်း (Mining Rate နှင့် Machine Count တိုးပေးမည်)
@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_conf_") or call.data.startswith("adm_decl_"))
def admin_verification_handler(call):
    data = call.data.split('_')
    action = data[1]
    target_user_id = int(data[2])
    
    if action == "conf":
        level = int(data[3])
        # Level အလိုက် 1 စက္ကန့်လျှင် တိုးမည့် Coin ပမာဏ (0.00001 ကစပြီး)
        mining_rates = {1: 0.00001, 2: 0.00002, 3: 0.00005, 4: 0.0001, 5: 0.0002}
        rate_to_add = mining_rates.get(level, 0.00001)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # Machine အရေအတွက် 1 ခု တိုးပေးပြီး၊ Mining Rate ကိုလည်း ပေါင်းထည့်ပေးပါမည်
            cursor.execute("""
                UPDATE users 
                SET mining_level = %s, 
                    machine_status = 'Active', 
                    machine_count = machine_count + 1,
                    mining_rate = mining_rate + %s,
                    last_update = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (level, rate_to_add, target_user_id))
            conn.commit()
            cursor.close()
            conn.close()
            
            bot.send_message(target_user_id, f"🎉 Admin မှ အတည်ပြုလိုက်ပါသည်။ Level {level} Machine စတင်အလုပ်လုပ်နေပါပြီ။ /profile တွင်စစ်ဆေးပါ။")
            bot.edit_message_caption("✅ **အတည်ပြုပြီးပါပြီ**", chat_id=call.message.chat.id, message_id=call.message.message_id)
        except Exception as e:
            bot.send_message(call.message.chat.id, f"DB Error: {e}")
            
    elif action == "decl":
        bot.send_message(target_user_id, "❌ သင့်ငွေလွှဲမှုကို Admin မှ ငြင်းပယ်လိုက်ပါသည်။")
        bot.edit_message_caption("❌ **ငြင်းပယ်ပြီးပါပြီ**", chat_id=call.message.chat.id, message_id=call.message.message_id)

@bot.message_handler(commands=['profile'])
def show_profile(message):
    user_id = message.from_user.id
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. အချိန်နဲ့အမျှ ရရှိလာတဲ့ Coin များကို အရင်ဆုံး တွက်ချက်ပေါင်းထည့်မည် (Live Mining Calculation)
        cursor.execute("""
            UPDATE users 
            SET coins = coins + (EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_update)) * mining_rate),
                last_update = CURRENT_TIMESTAMP
            WHERE user_id = %s AND machine_status = 'Active'
        """, (user_id,))
        conn.commit()
        
        # 2. Update ဖြစ်သွားသော အချက်အလက်များကို ပြန်ယူမည်
        cursor.execute("SELECT username, email, coins, mining_level, machine_count, machine_status FROM users WHERE user_id = %s", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            username, email, coins, mining_level, machine_count, status = row
            text = (
                f"👤 **User Profile**\n\n"
                f"▪️ Username: @{username}\n"
                f"▪️ Email: {email}\n"
                f"▪️ 💰 Live Coins: {coins:.5f}\n"  # 0.00001 အထိ ပြသရန် .5f အသုံးပြုထားသည်
                f"▪️ 🛠 Mining Machines: {machine_count} (Level {mining_level})\n"
                f"▪️ ⚡ Status: {status}"
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
