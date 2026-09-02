import os
import base64
import json
import sqlite3
import time
import requests
import telebot
from telebot import types

TOKEN = "8926250265:AAF_DY8uxukj-DLSBsJB9w5Ml6-_Ma7XpqM"
ADMIN_CHAT_ID = "582282128"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = telebot.TeleBot(TOKEN)
user_data = {}


def init_db():
  conn = sqlite3.connect("bot_database.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            is_banned INTEGER DEFAULT 0,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
  try:
    cursor.execute("SELECT is_banned FROM users LIMIT 1")
  except sqlite3.OperationalError:
    cursor.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            goal TEXT,
            weight REAL,
            height REAL,
            age INTEGER,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
  conn.commit()
  conn.close()


init_db()


def add_user_to_db(user_id, first_name, username):
  try:
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, first_name, username, is_banned)"
        " VALUES (?, ?, ?, 0)",
        (user_id, first_name, username or "لا يوجد"),
    )
    conn.commit()
    conn.close()
  except Exception as e:
    print(f"DB Error: {e}")


def is_user_banned(user_id):
  try:
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] == 1 if res else False
  except Exception:
    return False


def save_user_stat(user_id, goal, weight, height, age):
  try:
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO stats (user_id, goal, weight, height, age) VALUES (?, ?,"
        " ?, ?, ?)",
        (user_id, goal, weight, height, age),
    )
    conn.commit()
    conn.close()
  except Exception as e:
    print(f"DB Error: {e}")


def get_bot_stats():
  try:
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM stats")
    total_assessments = cursor.fetchone()[0]

    cursor.execute(
        "SELECT user_id, first_name, username, join_date FROM users ORDER BY"
        " join_date DESC LIMIT 5"
    )
    last_users = cursor.fetchall()
    conn.close()
    return total_users, total_assessments, last_users
  except Exception:
    return 0, 0, []


class UserProfile:

  def __init__(self):
    self.gender = ""
    self.age = 0
    self.weight, self.height = 0, 0
    self.goal = ""
    self.food_item = None
    self.step = None


FOOD_DATABASE = {
    "صدر دجاج (مشوي/مسلوق)": {
        "calories": 165,
        "protein": 31.0,
        "carbs": 0.0,
        "fat": 3.6,
        "unit": "100 غرام",
    },
    "تمن أبيض/أحمر مطبوخ": {
        "calories": 130,
        "protein": 2.7,
        "carbs": 28.0,
        "fat": 0.3,
        "unit": "100 غرام",
    },
    "لحم عجل أحمر مفروم": {
        "calories": 215,
        "protein": 24.0,
        "carbs": 0.0,
        "fat": 13.0,
        "unit": "100 غرام",
    },
    "بيض مسلوق": {
        "calories": 68,
        "protein": 6.3,
        "carbs": 0.6,
        "fat": 4.8,
        "unit": "بيضة واحدة",
    },
    "بيض مقلي (زيت خفيف)": {
        "calories": 90,
        "protein": 6.3,
        "carbs": 0.6,
        "fat": 7.0,
        "unit": "بيضة واحدة",
    },
    "شوفان": {
        "calories": 389,
        "protein": 16.9,
        "carbs": 66.3,
        "fat": 6.9,
        "unit": "100 غرام",
    },
    "تونا بالماء (مصفاة)": {
        "calories": 116,
        "protein": 26.0,
        "carbs": 0.0,
        "fat": 1.0,
        "unit": "100 غرام",
    },
    "بطاطا مسلوقة": {
        "calories": 87,
        "protein": 1.9,
        "carbs": 20.0,
        "fat": 0.1,
        "unit": "100 غرام",
    },
    "بطاطا حلوة": {
        "calories": 86,
        "protein": 1.6,
        "carbs": 20.1,
        "fat": 0.1,
        "unit": "100 غرام",
    },
    "خبز أسمر / شعير": {
        "calories": 250,
        "protein": 9.0,
        "carbs": 48.0,
        "fat": 2.0,
        "unit": "100 غرام",
    },
    "زبدة الفول السوداني": {
        "calories": 588,
        "protein": 25.0,
        "carbs": 20.0,
        "fat": 50.0,
        "unit": "100 غرام",
    },
    "سكوب واي بروتين": {
        "calories": 120,
        "protein": 24.0,
        "carbs": 3.0,
        "fat": 1.5,
        "unit": "سكوب واحد (30 غ)",
    },
    "تمر": {
        "calories": 20,
        "protein": 0.2,
        "carbs": 5.3,
        "fat": 0.0,
        "unit": "تمرة واحدة",
    },
    "موز": {
        "calories": 105,
        "protein": 1.3,
        "carbs": 27.0,
        "fat": 0.3,
        "unit": "حبة متوسطة",
    },
    "تفاح": {
        "calories": 52,
        "protein": 0.3,
        "carbs": 14.0,
        "fat": 0.2,
        "unit": "حبة متوسطة",
    },
    "جبن قريش / عرب خفيف": {
        "calories": 98,
        "protein": 11.0,
        "carbs": 3.4,
        "fat": 4.3,
        "unit": "100 غرام",
    },
    "حليب كامل الدسم": {
        "calories": 61,
        "protein": 3.2,
        "carbs": 4.8,
        "fat": 3.3,
        "unit": "100 مل",
    },
}


def ask_ai(prompt_text):
  try:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    response = requests.post(
        url, headers=headers, data=json.dumps(payload), timeout=30
    )
    res_json = response.json()

    if "candidates" in res_json and len(res_json["candidates"]) > 0:
      return res_json["candidates"][0]["content"]["parts"][0]["text"]
    elif "error" in res_json:
      return f"خطأ من جوجل API: {res_json['error'].get('message', 'خطأ غير معروف')}"
    else:
      return f"استجابة غير متوقعة من السيرفر: {res_json}"
  except Exception as e:
    return f"حدث خطأ تقني في الاتصال: {e}"


def ask_ai_with_image(prompt_text, image_bytes_base64):
  try:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt_text},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_bytes_base64,
                    }
                },
            ]
        }]
    }
    response = requests.post(
        url, headers=headers, data=json.dumps(payload), timeout=40
    )
    res_json = response.json()

    if "candidates" in res_json and len(res_json["candidates"]) > 0:
      return res_json["candidates"][0]["content"]["parts"][0]["text"]
    elif "error" in res_json:
      return f"خطأ من جوجل API: {res_json['error'].get('message', 'خطأ غير معروف')}"
    else:
      return f"استجابة غير متوقعة من السيرفر: {res_json}"
  except Exception as e:
    return f"حدث خطأ تقني في تحليل الصورة: {e}"


@bot.message_handler(commands=["start"])
def send_welcome(message):
  try:
    user_id = message.from_user.id
    if is_user_banned(user_id):
      return

    user_name = message.from_user.first_name
    username = message.from_user.username

    add_user_to_db(user_id, user_name, username)
    user_data[user_id] = UserProfile()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        types.KeyboardButton("🔥 ابدأ التقييم البدني الذكي"),
        types.KeyboardButton("🍽️ حاسبة سعرات الأكل الموسعة"),
    )
    markup.row(
        types.KeyboardButton("🎯 تمارين عزل لعضلة محددة"),
        types.KeyboardButton("💧 جدول وتذكير الماء"),
    )
    markup.row(
        types.KeyboardButton("💡 الدليل الشامل للتغذية والبناء العضلي"),
        types.KeyboardButton("⚖️ حاسبة الـ BMI"),
    )
    markup.row(
        types.KeyboardButton("🤝 للتعاون والإعلانات"),
        types.KeyboardButton("ℹ️ معلومات البوت"),
    )

    if str(user_id) == ADMIN_CHAT_ID:
      markup.row(types.KeyboardButton("📊 لوحة التحكم والأحصائيات"))

    welcome_text = (
        f"أهلاً بك يا {user_name} في بوت التدريب الاحترافي. 💪🔥\n\n"
        "• يمكنك اختيار أي خيار من القائمة أدناه.\n"
        "• أو **أرسل صورة وجبتك وسيقوم الكابتن بحساب سعراتها وماكروزها فوراً!** 📸🍽️"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
  except Exception as e:
    print(f"Error in start: {e}")


@bot.message_handler(
    func=lambda message: True,
    content_types=[
        "text",
        "photo",
        "document",
        "video",
        "audio",
        "voice",
        "sticker",
    ],
)
def forward_and_handle(message):
  try:
    user_id = message.from_user.id

    if is_user_banned(user_id):
      return

    if str(user_id) == ADMIN_CHAT_ID:
      text = message.text
      if user_data.get(user_id) and getattr(
          user_data[user_id], "admin_step", None
      ) == "waiting_broadcast":
        user_data[user_id].admin_step = None
        broadcast_message_to_all(message)
        return
      elif user_data.get(user_id) and getattr(
          user_data[user_id], "admin_step", None
      ) == "waiting_ban_id":
        user_data[user_id].admin_step = None
        ban_user_action(message, 1)
        return
      elif user_data.get(user_id) and getattr(
          user_data[user_id], "admin_step", None
      ) == "waiting_unban_id":
        user_data[user_id].admin_step = None
        ban_user_action(message, 0)
        return

    if str(user_id) != ADMIN_CHAT_ID:
      user_name = message.from_user.first_name
      username = message.from_user.username or "لا يوجد معرف"

      info_header = (
          f"📩 رسالة جديدة من:\n👤 الاسم: {user_name}\n🔗 المعرف:"
          f" @{username}\n🆔 الأيدي: {user_id}"
      )
      bot.send_message(ADMIN_CHAT_ID, info_header)
      bot.forward_message(ADMIN_CHAT_ID, message.chat.id, message.message_id)

  except Exception as e:
    print(f"Error in forwarding: {e}")

  process_bot_logic(message)


def process_bot_logic(message):
  try:
    user_id = message.from_user.id
    text = message.text

    if user_id not in user_data:
      user_data[user_id] = UserProfile()

    if message.content_type == "photo":
      bot.send_chat_action(message.chat.id, "typing")
      bot.reply_to(
          message,
          "🔄 جاري تحليل الوجبة وسحب السعرات والماكروز من الصورة، ثواني...",
      )

      photo = message.photo[-1]
      file_info = bot.get_file(photo.file_id)
      downloaded_file = bot.download_file(file_info.file_path)
      encoded_image = base64.b64encode(downloaded_file).decode("utf-8")

      prompt = (
          "أنت خبير تغذية رياضية محترف. قم بتحليل الوجبة الموجودة في الصورة بدقة،"
          " واذكر:\n"
          "1. مكونات الوجبة الظاهرة.\n"
          "2. السعرات الحرارية التقريبية للوجبة.\n"
          "3. توزيع الماكروز (بروتين، كاربوهيدرات، دهون) بشكل تقريبي.\n"
          "أجب بأسلوب عراقي احترافي، محفز، ومنسق بشكل جميل."
      )

      ai_response = ask_ai_with_image(prompt, encoded_image)
      bot.reply_to(message, ai_response)
      return

    if not text:
      return

    if text == "📊 لوحة التحكم والأحصائيات" and str(user_id) == ADMIN_CHAT_ID:
      markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
      markup.row(
          types.KeyboardButton("📢 إرسال إعلان (إذاعة)"),
          types.KeyboardButton("👥 عرض قائمة المشتركين"),
      )
      markup.row(
          types.KeyboardButton("🚫 حظر مستخدم"),
          types.KeyboardButton("✅ إلغاء حظر مستخدم"),
      )
      markup.row(types.KeyboardButton("🔙 القائمة الرئيسية للبوت"))

      total_users, total_assessments, _ = get_bot_stats()
      panel_text = (
          "🛠️ **لوحة التحكم المركزية للأدمن:**\n\n"
          f"👥 إجمالي المشتركين: {total_users}\n"
          f"📋 إجمالي التقييمات: {total_assessments}\n\n"
          "اختر الإجراء المطلوبة من الأزرار أدناه:"
      )
      bot.send_message(message.chat.id, panel_text, reply_markup=markup)
      return

    if str(user_id) == ADMIN_CHAT_ID:
      if text == "📢 إرسال إعلان (إذاعة)":
        user_data[user_id].admin_step = "waiting_broadcast"
        bot.send_message(
            message.chat.id,
            "ارسل النص أو الوسائط (صورة/رسالة) التي تريد إذاعتها لكل"
            " المشتركين الآن:",
        )
        return
      elif text == "👥 عرض قائمة المشتركين":
        total_users, total_assessments, last_users = get_bot_stats()
        users_list_str = ""
        for u in last_users:
          users_list_str += (
              f"- الأيدي: `{u[0]}` | الاسم: {u[1]} | المعرف: @{u[2]} | التاريخ:"
              f" {u[3][:16]}\n"
          )
        report = (
            f"📊 **تقرير المشتركين:**\nإجمالي العدد: {total_users}\n\nآخر 5"
            f" مشتركين:\n{users_list_str if users_list_str else 'لا يوجد'}"
        )
        bot.send_message(message.chat.id, report, parse_mode="Markdown")
        return
      elif text == "🚫 حظر مستخدم":
        user_data[user_id].admin_step = "waiting_ban_id"
        bot.send_message(
            message.chat.id, "أرسل (أيدي) المستخدم المراد حظره أرقاماً:"
        )
        return
      elif text == "✅ إلغاء حظر مستخدم":
        user_data[user_id].admin_step = "waiting_unban_id"
        bot.send_message(
            message.chat.id, "أرسل (أيدي) المستخدم لرفع الحظر عنه أرقاماً:"
        )
        return
      elif text == "🔙 القائمة الرئيسية للبوت":
        send_welcome(message)
        return

    if user_data[user_id].step == "waiting_for_muscle_choice":
      muscle_name = text
      gender = user_data[user_id].gender
      user_data[user_id].step = None

      bot.send_chat_action(message.chat.id, "typing")
      prompt = (
          f"أنت كابتن ومدرب رياضي محترف. شخص متدرب بجنس ({gender})"
          f" يريد جدول تمارين مكثف وعزل خاص لعضلة ({muscle_name})."
          " اعطِ له أفضل 4-5 تمارين دقيقة لهذه العضلة مع عدد الجولات (Sets) والتكرارات (Reps)"
          " ونصيحة احترافية لأفضل تركيز عضلي (Mind-Muscle Connection)"
          " بأسلوب عراقي محفز ومرتب."
      )
      ai_response = ask_ai(prompt)
      bot.reply_to(message, ai_response)
      return

    if text == "ℹ️ معلومات البوت":
      bot.reply_to(
          message,
          "🤖 بوت رياضي ذكي مزود بنظام ذكاء اصطناعي متكامل للرد على كافة"
          " الاستفسارات البدنية والغذائية وتحليل صور الوجبات.",
      )

    elif text == "🤝 للتعاون والإعلانات":
      bot.reply_to(
          message,
          "🤝 للتعاون التجاري، الإعلانات، أو التواصل المباشر:\nيمكنك المراسلة"
          " عبر الحساب الرسمي: @om_fmm",
      )

    elif text == "💡 الدليل الشامل للتغذية والبناء العضلي":
      pro_tips = (
          "💡 **الدليل الشامل للتغذية والبناء العضلي الاحترافي:**\n\n"
          "1️⃣ **أهمية توزيع البروتين:** الجسم يحتاج البروتين لبناء الألياف"
          " العضلية المتضررة. الهدف المثالي هو تناول 1.6 إلى 2.2 غرام بروتين لكل"
          " كيلوجرام من وزنك مقسمة على 4-5 وجبات.\n\n"
          "2️⃣ **منظومة الكاربوهيدرات:** الكارب المعقد (الشوفان، الأرز، البطاطا)"
          " يزودك بالطاقة المخزنة (الجلايكوجين) لرفع أوزان أثقل، بينما الكارب"
          " السريع (الموز، التمر) ممتاز فوراً بعد التمرين.\n\n"
          "3️⃣ **الدهون الصحية وتوازن الهرمونات:** تجنب قطع الدهون نهائياً."
          " الدهون الصحية (زيت الزيتون، المكسرات، صفار البيض) أساسية لإنتاج"
          " هرمون التستوستيرون والهرمونات البنائية.\n\n"
          "4️⃣ **الاستشفاء والنوم العميق:** البناء العضلي الفعلي يحدث أثناء"
          " النوم. الحصول على 7 إلى 8 ساعات من النوم المنتظم ليلاً يحفز إفراز"
          " هرمون النمو (GH).\n\n"
          "5️⃣ **مبدأ الاستمرارية:** النتائج المستدامة تتطلب التزاماً طويلاً"
          " بنظام متوازن بدلاً من الأنظمة القاسية القصيرة."
      )
      bot.send_message(message.chat.id, pro_tips)

    elif text == "💧 جدول وتذكير الماء":
      water_guide = (
          "💧 **جدول تنظيم وشرب الماء للرياضيين:**\n\n"
          "• **عند الاستيقاظ:** اشرب 2 كوب ماء لتنشيط الدورة الدموية والأعضاء.\n"
          "• **قبل التمرين بساعة:** اشرب نصف لتر لترطيب العضلات وضمان الأداء"
          " القوي.\n• **أثناء التمرين:** رشفات منتظمة كل 15 دقيقة لمنع الشد"
          " العضلي والجفاف.\n• **بقية اليوم:** شرب الماء بانتظام لتسهيل امتصاص"
          " البروتين والماكروز.\n\n"
          "💡 *معادلة الاحتياج:* الوزن × 0.033 = كمية الماء اليومية باللتر."
      )
      bot.send_message(message.chat.id, water_guide)

    elif text == "⚖️ حاسبة الـ BMI":
      bot.send_message(
          message.chat.id,
          "أدخل وزنك بالكيلوجرام والطول بالسنتيمتر هكذا (مثال: 75 175):\n(اكتب"
          " الوزن ثم مسافة ثم الطول)",
      )
      bot.register_next_step_handler(message, process_bmi)

    elif text == "🍽️ حاسبة سعرات الأكل الموسعة":
      markup = types.ReplyKeyboardMarkup(
          resize_keyboard=True, one_time_keyboard=True
      )
      for food in FOOD_DATABASE.keys():
        markup.add(types.KeyboardButton(food))
      markup.add(types.KeyboardButton("🔙 القائمة الرئيسية"))

      bot.send_message(
          message.chat.id,
          "🍽️ اختر المادة الغذائية لحساب السعرات والماكروز التفصيلي:\n(أو أرسل"
          " صورة وجبتك مباشرة في المحادثة لتحليلها بالذكاء الاصطناعي 📸)",
          reply_markup=markup,
      )
      bot.register_next_step_handler(message, process_food_selection)

    elif text == "🎯 تمارين عزل لعضلة محددة":
      markup = types.ReplyKeyboardMarkup(
          resize_keyboard=True, one_time_keyboard=True
      )
      markup.add(types.KeyboardButton("ذكر 👨"), types.KeyboardButton("أنثى 👩"))
      bot.send_message(
          message.chat.id,
          "🎯 لاختيار تمارين العضلة بدقة، يرجى تحديد الجنس أولاً:",
          reply_markup=markup,
      )
      bot.register_next_step_handler(message, process_target_muscle_gender)

    elif text == "🔥 ابدأ التقييم البدني الذكي" or text == "إعادة المحاولة":
      markup = types.ReplyKeyboardMarkup(
          resize_keyboard=True, one_time_keyboard=True
      )
      markup.add(types.KeyboardButton("ذكر 👨"), types.KeyboardButton("أنثى 👩"))
      bot.send_message(
          message.chat.id,
          "خطوة 1/4: اختر الجنس البيولوجي لحساب الأيض بدقة:",
          reply_markup=markup,
      )
      bot.register_next_step_handler(message, process_gender)

    else:
      bot.send_chat_action(message.chat.id, "typing")
      prompt = (
          "أنت كابتن ومدرب رياضي محترف في قاعة حديد وبناء عضلات. أجب على سياق"
          " المتدرب التالي بأسلوب عراقي احترافي، محفز، ومفيد علمياً:\n\n"
          f"{text}"
      )
      ai_response = ask_ai(prompt)
      bot.reply_to(message, ai_response)
  except Exception as e:
    print(f"Error in process_bot_logic: {e}")


def broadcast_message_to_all(message):
  try:
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
    users = cursor.fetchall()
    conn.close()

    success_count = 0
    fail_count = 0

    bot.send_message(
        ADMIN_CHAT_ID,
        f"⏳ جاري بدء إذاعة الرسالة لعدد {len(users)} مشترك...",
    )

    for u in users:
      target_id = u[0]
      try:
        bot.copy_message(target_id, message.chat.id, message.message_id)
        success_count += 1
        time.sleep(0.05)
      except Exception:
        fail_count += 1

    bot.send_message(
        ADMIN_CHAT_ID,
        "📢 **تمت الإذاعة بنجاح!**\n\n• وصل إلى: "
        f"{success_count}\n• فشل الوصول (بلوك/محذوف): {fail_count}",
    )
  except Exception as e:
    bot.send_message(ADMIN_CHAT_ID, f"حدث خطأ أثناء الإذاعة: {e}")


def ban_user_action(message, ban_status):
  try:
    target_id = int(message.text.strip())
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET is_banned = ? WHERE user_id = ?", (ban_status, target_id)
    )
    conn.commit()
    conn.close()

    action_name = "حظر" if ban_status == 1 else "إلغاء حظر"
    bot.send_message(
        ADMIN_CHAT_ID,
        f"✅ تم {action_name} المستخدم ذو الأيدي (`{target_id}`) بنجاح.",
        parse_mode="Markdown",
    )
  except ValueError:
    bot.send_message(ADMIN_CHAT_ID, "❌ الأيدي المدخل غير صحيح، يجلب أن يكون رقماً.")
  except Exception as e:
    bot.send_message(ADMIN_CHAT_ID, f"❌ حدث خطأ: {e}")


def process_target_muscle_gender(message):
  try:
    user_id = message.from_user.id
    text = message.text
    user_data[user_id] = user_data.get(user_id, UserProfile())

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True
    )
    if "ذكر" in text:
      user_data[user_id].gender = "ذكر"
      user_data[user_id].step = "waiting_for_muscle_choice"
      markup.add(
          types.KeyboardButton("صدر"),
          types.KeyboardButton("ظهر"),
          types.KeyboardButton("أكتاف"),
      )
      markup.add(
          types.KeyboardButton("بايسبس"),
          types.KeyboardButton("ترايسبس"),
          types.KeyboardButton("أرجل وبايسبس خلفي"),
      )
      bot.send_message(
          message.chat.id,
          "اختر العضلة المستهدفة للتمارين:",
          reply_markup=markup,
      )
    else:
      user_data[user_id].gender = "أنثى"
      user_data[user_id].step = "waiting_for_muscle_choice"
      markup.add(
          types.KeyboardButton("الكلوتس (المؤخرة)"),
          types.KeyboardButton("الأرجل الأمامية والخلفية"),
      )
      markup.add(
          types.KeyboardButton("شد البطن والخصر"),
          types.KeyboardButton("الأكتاف والظهر العلوي"),
      )
      bot.send_message(
          message.chat.id,
          "اختر العضلة أو المنطقة المستهدفة للتمارين:",
          reply_markup=markup,
      )
  except Exception as e:
    print(f"Error in target muscle gender: {e}")


def process_food_selection(message):
  try:
    user_id = message.from_user.id
    food_name = message.text

    if food_name == "🔙 القائمة الرئيسية":
      send_welcome(message)
      return

    if food_name not in FOOD_DATABASE:
      bot.reply_to(
          message,
          "العنصر غير موجود. يرجى الضغط على الزر مجدداً أو اختيار مادة صحيحة.",
      )
      return

    user_data[user_id] = user_data.get(user_id, UserProfile())
    user_data[user_id].food_item = food_name

    info = FOOD_DATABASE[food_name]
    bot.send_message(
        message.chat.id,
        f"لقد اخترت: **{food_name}**\nالقياس الأساسي: ({info['unit']})\n\nأدخل"
        " الكمية المطلوبة (مثال: اكتب 150 للغرامات، أو 3 لعدد البيض/التمر):",
    )
    bot.register_next_step_handler(message, process_food_amount)
  except Exception as e:
    print(f"Error in food selection: {e}")


def process_food_amount(message):
  try:
    user_id = message.from_user.id
    amount = float(message.text)
    food_name = user_data[user_id].food_item

    info = FOOD_DATABASE[food_name]

    if "100 غرام" in info["unit"] or "100 مل" in info["unit"]:
      multiplier = amount / 100.0
    else:
      multiplier = amount

    cal = round(info["calories"] * multiplier, 1)
    pro = round(info["protein"] * multiplier, 1)
    carb = round(info["carbs"] * multiplier, 1)
    fat = round(info["fat"] * multiplier, 1)

    result = (
        f"📊 **تفاصيل السعرات والماكروز للوجبة:**\n\n"
        f"• المادة: {food_name}\n"
        f"• الكمية المدخلة: {amount}\n\n"
        f"🔥 السعرات الحرارية: {cal} سعرة\n"
        f"🥩 البروتين: {pro} غرام\n"
        f"🍞 الكاربوهيدرات: {carb} غرام\n"
        f"🥑 الدهون الصحية: {fat} غرام"
    )

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True
    )
    markup.add(
        types.KeyboardButton("🍽️ حاسبة سعرات الأكل الموسعة"),
        types.KeyboardButton("🔥 ابدأ التقييم البدني الذكي"),
    )

    bot.send_message(message.chat.id, result, reply_markup=markup)
  except ValueError:
    bot.reply_to(message, "الرجاء إدخال رقم صحيح للكمية. أعد المحاولة:")
    bot.register_next_step_handler(message, process_food_amount)


def process_bmi(message):
  try:
    parts = message.text.strip().split()
    weight = float(parts[0])
    height = float(parts[1]) / 100
    bmi = round(weight / (height**2), 1)

    if bmi < 18.5:
      status = "نحافة (تحتاج تضخيم وزيادة سعرات)"
    elif 18.5 <= bmi < 25:
      status = "وزن مثالي ورشيق 🟢"
    elif 25 <= bmi < 30:
      status = "زيادة وزن (تحتاج تنشيف خفيف)"
    else:
      status = "سمنة (تحتاج برنامج تنشيف ونظام غذائي)"

    result = f"⚖️ نتيجة مؤشر كتلة الجسم (BMI):\n\n• النسبة: {bmi}\n• الحالة: {status}"
    bot.send_message(message.chat.id, result)
  except Exception:
    bot.reply_to(
        message,
        "خطأ بالإدخال! يرجى كتابة الوزن مسافة الطول بشكل صحيح (مثال: 75 175).",
    )


def process_gender(message):
  try:
    user_id = message.from_user.id
    text = message.text
    if "ذكر" in text:
      user_data[user_id].gender = "male"
    else:
      user_data[user_id].gender = "female"
    bot.send_message(message.chat.id, "خطوة 2/4: كم عمرك بالسنوات؟ (مثال: 23):")
    bot.register_next_step_handler(message, process_age)
  except Exception as e:
    print(f"Error in gender: {e}")


def process_age(message):
  try:
    user_id = message.from_user.id
    age = int(message.text)
    user_data[user_id].age = age
    bot.send_message(
        message.chat.id, "خطوة 3/4: أدخل وزنك الحالي بالكيلوجرام (مثال: 75):"
    )
    bot.register_next_step_handler(message, process_weight)
  except ValueError:
    bot.send_message(
        message.chat.id, "الرجاء إدخال رقم صحيح للعمر. أعد المحاولة:"
    )
    bot.register_next_step_handler(message, process_age)


def process_weight(message):
  try:
    user_id = message.from_user.id
    weight = float(message.text)
    user_data[user_id].weight = weight
    bot.send_message(
        message.chat.id, "خطوة 4/4: أدخل طولك بالسنتيمتر (مثال: 175):"
    )
    bot.register_next_step_handler(message, process_height)
  except ValueError:
    bot.send_message(
        message.chat.id, "الرجاء إدخال رقم صحيح للوزن. أعد المحاولة:"
    )
    bot.register_next_step_handler(message, process_weight)


def process_height(message):
  try:
    user_id = message.from_user.id
    height = float(message.text)
    user_data[user_id].height = height

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True
    )
    markup.add(
        types.KeyboardButton("تنشيف (حرق دهون ونحت العضل)"),
        types.KeyboardButton("تضخيم (زيادة الكتلة وضخامة)"),
    )
    bot.send_message(
        message.chat.id,
        "ما هو هدفك التدريبي الحالي؟",
        reply_markup=markup,
    )
    bot.register_next_step_handler(message, process_goal)
  except ValueError:
    bot.send_message(
        message.chat.id, "الرجاء إدخال رقم صحيح للطول. أعد المحاولة:"
    )
    bot.register_next_step_handler(message, process_height)


def process_goal(message):
  try:
    user_id = message.from_user.id
    goal = message.text
    if user_id not in user_data:
      user_data[user_id] = UserProfile()
    user_data[user_id].goal = goal
    data = user_data[user_id]

    save_user_stat(user_id, goal, data.weight, data.height, data.age)

    if data.gender == "male":
      bmr = (10 * data.weight) + (6.25 * data.height) - (5 * data.age) + 5
    else:
      bmr = (10 * data.weight) + (6.25 * data.height) - (5 * data.age) - 161

    tdee = bmr * 1.375

    if "تنشيف" in goal:
      final_calories = int(tdee - 450)
      goal_title = "تنشيف (حرق دهون ونحت العضل)"
      cardio = (
          "• الكارديو: 3 إلى 4 أيام أسبوعياً بعد الحديد (مشي مائل 25 دقيقة)."
      )
      push_routine = "1. بنش بريس مائل\n2. تفتيح كابل\n3. رفرفة جانبي"
      pull_routine = "1. سحب عالي\n2. سحب أرضي\n3. فيس بول"
      leg_routine = "1. لج بريس\n2. مرجحة أمامي وخلفي\n3. سمانة"
    else:
      final_calories = int(tdee + 350)
      goal_title = "تضخيم (زيادة الكتلة وضخامة عضلية)"
      cardio = (
          "• الكارديو: جلسة واحدة خفيفة جداً أسبوعياً للحفاظ على صحة القلب فقط."
      )
      push_routine = "1. بنش بريس بالبار\n2. ضغط عسكري للكتف\n3. ترايليبس"
      pull_routine = "1. سحب بار حر\n2. سحب عالي مسكة ضيقة\n3. بايليبس بار"
      leg_routine = "1. سكوات حر\n2. ديدليفت روماني\n3. سمانة"

    water_intake = round(data.weight * 0.033, 1)

    result_text = (
        "📋 تقرير التقييم الرياضي الشامل:\n\n"
        f"- الجنس: {'ذكر 👨' if data.gender == 'male' else 'أنثى 👩'}\n"
        f"- العمر: {data.age} سنة | الوزن: {data.weight} كغ | الطول:"
        f" {data.height} سم\n"
        f"- الهدف: {goal_title}\n"
        f"- السعرات اليومية المستهدفة: {final_calories} سعرة حرارية\n"
        f"- احتياج الماء الموصى به: {water_intake} لتر يومياً.\n\n"
        "🏋️‍♂️ جدول الـ PPL:\n\n"
        f"1️⃣ الدفع:\n{push_routine}\n\n"
        f"2️⃣ السحب:\n{pull_routine}\n\n"
        f"3️⃣ الأرجل:\n{leg_routine}\n\n"
        f"{cardio}"
    )

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True
    )
    markup.add(types.KeyboardButton("إعادة المحاولة"))

    bot.send_message(message.chat.id, result_text, reply_markup=markup)

    try:
      user_info = (
          "🚨 مستخدم جديد أكمل التقييم!\n\n"
          f"👤 الاسم: {message.from_user.first_name}\n"
          f"🔗 المعرف: @{message.from_user.username}\n"
          f"🆔 الأيدي: {user_id}\n"
          f"📊 الوزن: {data.weight}kg | الطول: {data.height}cm | العمر:"
          f" {data.age}\n"
          f"🎯 الهدف: {goal_title}"
      )
      bot.send_message(ADMIN_CHAT_ID, user_info)
    except Exception as e:
      print(f"Failed to send admin notification: {e}")

  except Exception as e:
    print(f"Error in goal processing: {e}")


print("البوت يعمل الآن بدون أخطاء قاعدة البيانات...")

while True:
  try:
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
  except Exception as e:
    print(f"Polling connection dropped: {e}. Reconnecting in 5 seconds...")
    time.sleep(5)
