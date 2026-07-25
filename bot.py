import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import psycopg2
from datetime import datetime, timedelta
from flask import Flask
import threading
import time
import requests

# ==========================================
# BOT CONFIGURATION
# ==========================================
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 6673230697 

# Database URL (Port 5432 သို့ ပြင်ဆင်ထားပါသည်)
DB_URL = "postgresql://postgres.oziuwtfvqalrndxrlhfu:5MsTXrMV6foC4FGS@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN ကို Render Environment Variables ထဲမှာ ထည့်သွင်းပေးရန်လိုအပ်ပါသည်။")

bot = telebot.TeleBot(BOT_TOKEN)

# ==========================================
# FLASK KEEP-ALIVE SERVER
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "🍬 Candy Hub Bot is alive and running smoothly! 🚀"

@app.route('/health')
def health():
    return "OK", 200

def ping_self():
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        url = "https://beta-no7j.onrender.com" 
        print(f"🔄 Using hardcoded URL: {url}")
        
    print(f"🔄 Self-ping စတင်ပါပြီ။ URL: {url}")
    while True:
        time.sleep(300)
        try:
            response = requests.get(f"{url}/health", timeout=10)
            print(f"🟢 Ping အောင်မြင်သည် - Status: {response.status_code}")
        except Exception as e:
            print(f"🔴 Ping ပျက်ကွက်သည်: {e}")

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

# ==========================================
# DATABASE SETUP
# ==========================================
def get_db_connection():
    return psycopg2.connect(DB_URL)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            email TEXT UNIQUE,
            password TEXT,
            coin FLOAT DEFAULT 0,
            machine_level INT DEFAULT 0,
            mining_rate FLOAT DEFAULT 0,
            expire_time TIMESTAMP
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

init_db()

# User States နှင့် Logged-in Sessions များကို မှတ်သားရန်
user_states = {}
logged_in_users = set()  # Login ဝင်ထားပြီးသော user_id များကို သိမ်းရန်

CHANNELS = [
    "@candyhubass",
    "@CandyHub_Ch",
    "@CandyHub_Chat"
]

# ==========================================
# BOT COMMANDS & LOGIC
# ==========================================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Join Channel 1", url="https://t.me/candyhubass"))
    markup.add(InlineKeyboardButton("Join Channel 2", url="https://t.me/CandyHub_Ch"))
    markup.add(InlineKeyboardButton("Join Group", url="https://t.me/CandyHub_Chat"))
    markup.add(InlineKeyboardButton("✅ Check Join", callback_data="check_join"))
    
    text = (f"မင်္ဂလာပါ @{username} 🤍\n"
            "Candy Hub Bot မှ ကြိုဆိုပါတယ်။\n"
            "အောက်ပါ Channel/Group များကို Join ပြီးမှ ဆက်လုပ်ပါ။\n\n"
            "အကောင့်ရှိပြီးသားဆိုပါက /login ဖြင့် ဝင်ရောက်နိုင်ပါသည်။")
    bot.send_message(user_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join(call):
    user_id = call.from_user.id
    try:
        all_joined = True
        for channel in CHANNELS:
            status = bot.get_chat_member(channel, user_id).status
            if status in ['left', 'kicked']:
                all_joined = False
                break
        
        if all_joined:
            bot.answer_callback_query(call.id, "✅ Confirm ဖြစ်ပါတယ်။")
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("📝 Register (အကောင့်သစ်ဖွင့်ရန်)", callback_data="action_register"),
                InlineKeyboardButton("🔑 Login (အကောင့်ဝင်ရန်)", callback_data="action_login")
            )
            bot.send_message(user_id, "ကျေးဇူးပြု၍ အောက်ပါတို့မှ တစ်ခုကို ရွေးချယ်ပါ:", reply_markup=markup)
        else:
            bot.answer_callback_query(call.id, "❌ Group/Channel အားလုံးကို Join ရန်လိုအပ်ပါတယ်။", show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, "Error! Bot ကို Channel များတွင် Admin ပေးထားရန်လိုအပ်ပါသည်။", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data in ["action_register", "action_login"])
def choice_handler(call):
    user_id = call.from_user.id
    if call.data == "action_register":
        bot.send_message(user_id, "အကောင့်ဖွင့်ရန် သင့်ရဲ့ Email ကို ရိုက်ထည့်ပေးပါ:")
        user_states[user_id] = {'step': 'waiting_email'}
    elif call.data == "action_login":
        bot.send_message(user_id, "🔑 Login ဝင်ရန် သင့်အကောင့်၏ Email ကို ရိုက်ထည့်ပေးပါ:")
        user_states[user_id] = {'step': 'waiting_login_email'}
    bot.answer_callback_query(call.id)

# ------------------------------------------
# REGISTER FLOW
# ------------------------------------------
@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('step') == 'waiting_email')
def get_email(message):
    user_id = message.from_user.id
    user_states[user_id]['email'] = message.text
    user_states[user_id]['step'] = 'waiting_password'
    bot.send_message(user_id, "ကျေးဇူးပြု၍ Password (စကားဝှက်) အသစ်ကို ရိုက်ထည့်ပေးပါ:")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('step') == 'waiting_password')
def get_password(message):
    user_id = message.from_user.id
    user_states[user_id]['password'] = message.text
    user_states[user_id]['step'] = 'confirm_account'
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Yes", callback_data="acc_yes"), InlineKeyboardButton("No", callback_data="acc_no"))
    
    text = f"အကောင့်အချက်အလက်များမှန်ကန်ပါသလား?\n\nEmail: {user_states[user_id]['email']}\nPassword: {user_states[user_id]['password']}"
    bot.send_message(user_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["acc_yes", "acc_no"])
def confirm_account(call):
    user_id = call.from_user.id
    if call.data == "acc_yes":
        email = user_states[user_id]['email']
        password = user_states[user_id]['password']
        username = call.from_user.username or "User"
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (user_id, username, email, password) VALUES (%s, %s, %s, %s)", 
                           (user_id, username, email, password))
            conn.commit()
            logged_in_users.add(user_id)
            bot.send_message(user_id, "✅ အကောင့်ဖွင့်ခြင်းနှင့် Login ဝင်ပြီးဖြစ်ပါသည်။\n/buy ဟုရိုက်၍ Mining Machine ဝယ်ယူနိုင်ပါပြီ။")
        except Exception as e:
            bot.send_message(user_id, "❌ အကောင့်ဖွင့်ရာတွင် အမှားအယွင်းဖြစ်ပေါ်ခဲ့ပါသည်။ Email တူနေနိုင်ပါသည် (သို့) အကောင့်ရှိပြီးသားဖြစ်နေပါသည်။")
        finally:
            cursor.close()
            conn.close()
            user_states.pop(user_id, None)
            
    else:
        user_states.pop(user_id, None)
        bot.send_message(user_id, "❌ အကောင့်ဖွင့်ခြင်းကို ပယ်ဖျက်လိုက်ပါသည်။ ပြန်စရန် /start ကိုနှိပ်ပါ။")

# ------------------------------------------
# LOGIN FLOW
# ------------------------------------------
@bot.message_handler(commands=['login'])
def login_command(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "🔑 Login ဝင်ရန် သင့်ရဲ့ **Email** ကို ရိုက်ထည့်ပေးပါ:")
    user_states[user_id] = {'step': 'waiting_login_email'}

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('step') == 'waiting_login_email')
def process_login_email(message):
    user_id = message.from_user.id
    user_states[user_id]['login_email'] = message.text
    user_states[user_id]['step'] = 'waiting_login_password'
    bot.send_message(user_id, "🔑 ကျေးဇူးပြု၍ သင့်အကောင့်၏ **Password** ကို ရိုက်ထည့်ပေးပါ:")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('step') == 'waiting_login_password')
def process_login_password(message):
    user_id = message.from_user.id
    email = user_states[user_id]['login_email']
    password = message.text
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Database ထဲမှ Email နှင့် Password တိုက်စစ်ခြင်း
        cursor.execute("SELECT user_id, password FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[1] == password:
            db_user_id = row[0]
            # အကယ်၍ Telegram ID က Database ထဲမှာ အခြားသူနဲ့ ချိတ်နေရင် update လုပ်တာဖြစ်စေ၊ လက်ရှိ user_id နဲ့ တွဲတာဖြစ်စေ စစ်နိုင်ပါတယ်။ 
            # ဒီနေရာမှာ user_id ကို update လုပ်ပေးပါမယ် (Telegram ဖြင့် ဝင်လာသူအတွက်)
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET user_id = %s WHERE email = %s", (user_id, email))
            conn.commit()
            cursor.close()
            conn.close()
            
            logged_in_users.add(user_id)
            bot.send_message(user_id, "✅ Login အောင်မြင်ပါသည်။ ယခုဂိမ်းကို ဆက်လက်ကစားနိုင်ပါပြီ။ /buy သို့မဟုတ် /profile ကို အသုံးပြုပါ။")
        else:
            bot.send_message(user_id, "❌ Email သို့မဟုတ် Password မှားယွင်းနေပါသည်။ /login ဖြင့် ပြန်လည်ကြိုးစားပါ။")
    except Exception as e:
        bot.send_message(user_id, f"❌ Error ဖြစ်ပေါ်သည်: {e}")
    finally:
        user_states.pop(user_id, None)

@bot.message_handler(commands=['logout'])
def logout_command(message):
    user_id = message.from_user.id
    if user_id in logged_in_users:
        logged_in_users.remove(user_id)
        bot.send_message(user_id, "✅ အကောင့်မှ ထွက်လိုက်ပါပြီ (Logouted)။ ပြန်ဝင်ရန် /login ကိုနှိပ်ပါ။")
    else:
        bot.send_message(user_id, "⚠️ သင်သည် Login ဝင်ထားခြင်း မရှိသေးပါ။")

# ==========================================
# MINING & PROFILE COMMANDS (Login လိုအပ်သည်)
# ==========================================
@bot.message_handler(commands=['buy'])
def buy_command(message):
    user_id = message.from_user.id
    if user_id not in logged_in_users:
        bot.send_message(user_id, "⚠️ ကျေးဇူးပြု၍ ပထမဦးစွာ /login ဖြင့် အကောင့်ဝင်ပေးပါရန်။")
        return

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("Level 1 (1hr) - 10000 chcoin [0.0001/sec]", callback_data="buy_1"),
        InlineKeyboardButton("Level 2 (2hr) - 20000 chcoin [0.0005/sec]", callback_data="buy_2"),
        InlineKeyboardButton("Level 3 (3hr) - 30000 chcoin [0.0009/sec]", callback_data="buy_3")
    )
    bot.send_message(message.chat.id, "🛒 ဝယ်ယူလိုသော Mining Machine Level ကိုရွေးချယ်ပါ:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_buy(call):
    level = int(call.data.split("_")[1])
    user_id = call.from_user.id
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Yes", callback_data=f"payyes_{level}"), InlineKeyboardButton("No", callback_data="payno"))
    
    text = (f"Level {level} ကို ဝယ်ယူရန် ရွေးချယ်ထားပါတယ်။\n\n"
            "Payment 💳\nadm@adm.com သို့ CandyHub ထဲတွင် chcoin လွှဲပေးပါ။\n\n"
            "လွှဲပြီးပါက ငွေလွှဲပြေစာပုံ (Screenshot) ပို့ရန်အဆင်သင့်ဖြစ်ပြီလား?")
    bot.edit_message_text(text, chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("payyes_") or call.data == "payno")
def confirm_payment_intent(call):
    user_id = call.from_user.id
    if call.data == "payno":
        bot.send_message(user_id, "ဝယ်ယူခြင်းကို ပယ်ဖျက်လိုက်ပါတယ်။")
    else:
        level = int(call.data.split("_")[1])
        user_states[user_id] = {'step': 'waiting_payment_proof', 'level': level}
        bot.send_message(user_id, "ကျေးဇူးပြု၍ ငွေလွှဲပြေစာပုံ (Screenshot) ကို ယခု Chat သို့ ပို့ပေးပါ။")

@bot.message_handler(content_types=['photo'], func=lambda m: user_states.get(m.from_user.id, {}).get('step') == 'waiting_payment_proof')
def receive_payment_proof(message):
    user_id = message.from_user.id
    level = user_states[user_id]['level']
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Confirm", callback_data=f"adminok_{user_id}_{level}"),
        InlineKeyboardButton("❌ Decline", callback_data=f"adminno_{user_id}")
    )
    
    bot.send_message(ADMIN_ID, f"User {user_id} (@{message.from_user.username}) မှ Level {level} အတွက် ငွေလွှဲပြေစာပေးပို့ထားပါတယ်။")
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, reply_markup=markup)
    
    bot.send_message(user_id, "ပြေစာကို Admin ထံသို့ ပို့ပြီးပါပြီ။ Admin မှ Confirm လုပ်ပေးသည်အထိ ခဏစောင့်ပေးပါ။")
    user_states.pop(user_id, None)

@bot.callback_query_handler(func=lambda call: call.data.startswith("adminok_") or call.data.startswith("adminno_"))
def admin_payment_action(call):
    if call.from_user.id != ADMIN_ID:
        return
    
    action = call.data.split("_")
    status = action[0]
    target_user = int(action[1])
    
    if status == "adminok":
        level = int(action[2])
        rates = {
            1: (0.0001, 1), 
            2: (0.0005, 2), 
            3: (0.0009, 3)
        }
        
        if level in rates:
            rate, hours = rates[level]
            expire = datetime.now() + timedelta(hours=hours)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET machine_level = %s, mining_rate = %s, expire_time = %s WHERE user_id = %s",
                           (level, rate, expire, target_user))
            conn.commit()
            cursor.close()
            conn.close()
            
            bot.send_message(target_user, f"✅ Admin မှအတည်ပြုပေးလိုက်ပါသည်။\nLevel {level} Mining Machine စတင်အလုပ်လုပ်နေပါပြီ!")
            bot.answer_callback_query(call.id, "Confirmed")
        else:
            bot.answer_callback_query(call.id, "Invalid Level")
        
    elif status == "adminno":
        bot.send_message(target_user, "❌ သင့်၏ငွေလွှဲပြေစာကို Admin မှ ငြင်းပယ်လိုက်ပါသည်။ ပြန်လည်စစ်ဆေးပါ။")
        bot.answer_callback_query(call.id, "Declined")

@bot.message_handler(commands=['profile'])
def profile_command(message):
    user_id = message.from_user.id
    if user_id not in logged_in_users:
        bot.send_message(user_id, "⚠️ ကျေးဇူးပြု၍ ပထမဦးစွာ /login ဖြင့် အကောင့်ဝင်ပေးပါရန်။")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, email, password, coin, machine_level, mining_rate FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        username, email, password, coin, level, rate = row
        text = f"👤 **Profile**\n\n" \
               f"Username: @{username}\n" \
               f"Email: {email}\n" \
               f"Password: {password}\n" \
               f"Coin: {coin:.6f} chcoin\n" \
               f"Machine Level: {level}\n" \
               f"Mining Rate: {rate} per sec"
        bot.send_message(user_id, text)
    else:
        bot.send_message(user_id, "သင့်အကောင့်အချက်အလက် ရှာမတွေ့ပါ။ /start ဖြင့် အကောင့်ပြန်ဆောက်ပါ သို့မဟုတ် /login ဝင်ပါ။")

@bot.message_handler(commands=['update'])
def update_command(message):
    user_id = message.from_user.id
    if user_id not in logged_in_users:
        bot.send_message(user_id, "⚠️ ကျေးဇူးပြု၍ ပထမဦးစွာ /login ဖြင့် အကောင့်ဝင်ပေးပါရန်။")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT machine_level, mining_rate, coin FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    
    if not row or row[0] == 0:
        bot.send_message(user_id, "သင် Machine ဝယ်ယူထားခြင်းမရှိသေးပါ။ /buy ဖြင့် အရင်ဝယ်ယူပါ။")
        conn.close()
        return
        
    level, rate, coin = row
    update_cost = 0.001
    new_rate = rate * 2 
    
    cursor.execute("UPDATE users SET mining_rate = %s, coin = coin - %s WHERE user_id = %s", (new_rate, update_cost, user_id))
    conn.commit()
    conn.close()
    
    bot.send_message(user_id, f"✅ Update လုပ်ခြင်းအောင်မြင်ပါသည်။\nကုန်ကျစရိတ်: {update_cost} chcoin\nယခု Mining Rate: {new_rate:.6f} per sec")

# ==========================================
# ADMIN COMMANDS
# ==========================================
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    if not message.reply_to_message:
        bot.send_message(ADMIN_ID, "Broadcast လုပ်လိုသော message ကို Reply ပြန်ပြီး /broadcast ဟုရိုက်ပါ။")
        return
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    count = 0
    for u in users:
        try:
            bot.copy_message(u[0], message.chat.id, message.reply_to_message.message_id)
            count += 1
        except:
            pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast ပြီးပါပြီ။ User {count} ယောက်ထံ ရောက်ရှိပါသည်။")

@bot.message_handler(commands=['user'])
def admin_user(message):
    if message.from_user.id != ADMIN_ID:
        return
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, email, password, coin FROM users")
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        bot.send_message(ADMIN_ID, "No users found.")
        return
        
    text = "👥 **User List:**\n\n"
    for u in users:
        text += f"User: @{u[0]}\nEmail: {u[1]}\nPass: {u[2]}\nCoin: {u[3]}\n\n"
        if len(text) > 3500:
            bot.send_message(ADMIN_ID, text)
            text = ""
    if text:
        bot.send_message(ADMIN_ID, text)

@bot.message_handler(commands=['setcoin'])
def set_coin(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        args = message.text.split()
        target_email = args[1]
        amount = float(args[2])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET coin = %s WHERE email = %s", (amount, target_email))
        if cursor.rowcount > 0:
            bot.send_message(ADMIN_ID, f"✅ {target_email} ၏ Coin ကို {amount} သို့ ပြောင်းလဲပြီးပါပြီ။")
        else:
            bot.send_message(ADMIN_ID, "❌ User email ကိုရှာမတွေ့ပါ။")
        conn.commit()
        conn.close()
    except Exception as e:
        bot.send_message(ADMIN_ID, "Format မှားယွင်းနေပါသည်။ (ဥပမာ - /setcoin a@gmail.com 100)")

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print("=" * 50)
    print("🍬 Candy Hub Bot စတင်နေပါပြီ...")
    print(f"🤖 Bot Token: {BOT_TOKEN[:10]}...")
    print(f"📢 Admin ID: {ADMIN_ID}")
    print("=" * 50)

    # Flask server ကို background thread မှာ run
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    print("✅ Flask server started")

    # Self-ping ကို background thread မှာ run
    ping_thread = threading.Thread(target=ping_self)
    ping_thread.daemon = True
    ping_thread.start()
    print("✅ Self-ping system started")

    print("=" * 50)
    print("🤖 Bot is now running...")
    print("=" * 50)

    # Remove webhook and use polling
    try:
        bot.remove_webhook()
        print("✅ Webhook removed successfully")
    except Exception as e:
        print(f"⚠️ Webhook removal error: {e}")

    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f"⚠️ Polling error: {e}")
            print("🔄 5 seconds နောက် ပြန်စတင်မည်...")
            time.sleep(5)
