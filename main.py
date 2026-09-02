import os
import telebot
from telebot import types
import openai

# المتغيرات الأساسية
TOKEN = "8926250265:AAGnD4oGlgcOJBtHZ60n5A9UxlrnVtCHvbM"
ADMIN_CHAT_ID = "582282128"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY
bot = telebot.TeleBot(TOKEN)

# قاموس لحفظ معلومات المستخدمين مؤقتاً بالذاكرة
user_data = {}

# دالة الاتصال بالذكاء الاصطناعي بنبرة حماسية واحترافية
def ask_ai(prompt_text, user_profile):
    try:
        system_prompt = (
            "أنت مدرب كمال أجسام وتخسيس محترف جداً، أسلوبك حماسي ناري مشجع يدفع للبطولات! "
            f"معلومات المستخدم الحالي: الجنس: {user_profile.get('gender', 'غير محدد')}، "
            f"الهدف: {user_profile.get('goal', 'عام')}."
            " جاوب دائماً باللغة العربية مع مراعاة تفاصيل جسم وفيسيولوجيا جنس المستخدم (ذكر أو أنثى) في التمارين والسعرات."
        )
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_text}
            ],
            timeout=30
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"يا بطل صار عدنا خلل بسيط بالاتصال، بس الأبطال ما توقفهم الظروف! عود حاول مرة لُخ: {e}"

# بداية البوت وتسجيل المستخدم
@bot.message_handler(commands=['start'])
def send_welcome(chat_id):
    user_data[chat_id] = {"step": "waiting_gender"}
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('ذكر 🦾', 'أنثى 👑')
    
    bot.send_message(
        chat_id,
        "🔥 أهلاً بك يا وحش في حلبة الأبطال! معك مدربك الشخصي.\n"
        "حتى أفصل لك الجدول والتمارين والسعرات بدقة على جسمك.. هل أنت ذكر أم أنثى؟",
        reply_markup=markup
    )

# استقبال الرسائل ومعالجة الخطوات والذاكرة
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text

    # إذا المستخدم جديد ديختار جنسه
    if chat_id not in user_data:
        send_welcome(chat_id)
        return

    user_info = user_data[chat_id]

    if user_info.get("step") == "waiting_gender":
        if "ذكر" in text:
            user_info["gender"] = "ذكر"
        elif "أنثى" in text:
            user_info["gender"] = "أنثى"
        else:
            user_info["gender"] = text
            
        user_info["step"] = "chatting"
        
        # إزالة الكيبورد المؤقت والترحيب الحماسي
        markup = types.ReplyKeyboardRemove()
        bot.send_message(
            chat_id,
            f"💪 ممتاز! تم تسجيلك يا بطل ({user_info['gender']}). هسة صرت جاهز للمعركة!\n"
            "شنو هدفك اليوم؟ (تخسيس، بناء عضلات، شد جسم، جدول طعام)؟ اسألني وشوف الحماس!",
            reply_markup=markup
        )
        return

    # مرحلة الاستجابة الذكية وحفظ السياق والتفاعل الحماسي
        bot.send_chat_action(chat_id, 'typing')
        ai_response = ask_ai(text, user_info)
        bot.reply_to(message, ai_response)

# أمر لتنظيف الويب هوك وتشغيل البوت بسلام
bot.remove_webhook()
while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"Polling connection dropped: {e}. Reconnecting in 5 seconds...")
        time.sleep(5)
