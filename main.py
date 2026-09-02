import os
import requests
import telebot
from telebot import types

TOKEN = "8926250265:AAGnD4oGlgcOJBtHZ60n5A9UxlrnVtCHvbM"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(TOKEN)
user_data = {}

# دالة إرسال الأزرار الرئيسية العالمية
def main_menu_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('🔥 تحدي اليوم الناري'),
        types.KeyboardButton('🥩 حساب السعرات والماكروز'),
        types.KeyboardButton('🦾 جدول التمارين الذكي'),
        types.KeyboardButton('🥗 وجبات أبطال الحديد'),
        types.KeyboardButton('💬 استشر الكابتن مباشرة')
    )
    return markup

def ask_ai(prompt_text, user_profile):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    system_prompt = (
        "أنت مدرب كمال أجسام وتخسيس محترف جداً، أسلوبك حماسي ناري مشجع يدفع للبطولات! "
        f"معلومات المستخدم الحالي: الجنس: {user_profile.get('gender', 'غير محدد')}، "
        f"الهدف الحالي أو الوضع: {user_profile.get('current_focus', 'غير محدد')}."
        " جاوب دائماً باللغة العربية وبنبرة حماسية قوية مع مراعاة تفاصيل جسم وفيسيولوجيا جنس المستخدم."
    )
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_text}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        res_json = response.json()
        if "choices" in res_json and len(res_json["choices"]) > 0:
            return res_json["choices"][0]["message"]["content"]
        else:
            return f"يا بطل، صار عدنا رد غير متوقع من الخادم: {res_json}"
    except Exception as e:
        return f"يا بطل صار عدنا خلل بالاتصال مع تشات جي بي تي: {e}"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"step": "waiting_gender"}
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('ذكر 🦾', 'أنثى 👑')
    
    bot.send_message(
        chat_id,
        "🔥 أهلاً بك يا وحش في حلبة الأبطال! معك مدربك الشخصي.\n"
        "حتى أفصل لك الجدول والتمارين والسعرات بدقة على جسمك.. **هل أنت ذكر أم أنثى؟**",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text

    if chat_id not in user_data:
        send_welcome(message)
        return

    user_info = user_data[chat_id]

    # مرحلة اختيار الجنس
    if user_info.get("step") == "waiting_gender":
        if "ذكر" in text:
            user_info["gender"] = "ذكر"
        elif "أنثى" in text:
            user_info["gender"] = "أنثى"
        else:
            user_info["gender"] = text
            
        user_info["step"] = "ready"
        
        bot.send_message(
            chat_id,
            f"💪 ممتاز! تم تسجيلك يا بطل ({user_info['gender']}). هسة صرت جاهز للمعركة!\n"
            "استخدم الأزرار بالأسفل لتختار الخطوة التالية أو اسألني مباشرة:",
            reply_markup=main_menu_markup()
        )
        return

    # معالجة الأزرار العالمية الاحترافية
    if text == '🔥 تحدي اليوم الناري':
        user_info["current_focus"] = "تحدي اليوم"
        prompt = "اعطني تحدي رياضي ناري قصير ومحفز لليوم يجب على البطل تنفيذه لتحطيم الكسل!"
        bot.send_chat_action(chat_id, 'typing')
        response = ask_ai(prompt, user_info)
        bot.send_message(chat_id, response, reply_markup=main_menu_markup())
        return

    elif text == '🥩 حساب السعرات والماكروز':
        user_info["current_focus"] = "حساب السعرات والماكروز"
        bot.send_message(
            chat_id,
            "📝 اكتب لي الآن: (وزنك، طولك، عمرك، وهدفك: تضخيم أو تنشيف)، والكابتن راح يحسبلك السعرات والبروتين بدقة نارية!",
            reply_markup=main_menu_markup()
        )
        return

    elif text == '🦾 جدول التمارين الذكي':
        user_info["current_focus"] = "جدول التمارين"
        prompt = "اقترح لي نظام تمارين أسبوعي احترافي (مثل Push/Pull/Legs) مع نصائح حماسية."
        bot.send_chat_action(chat_id, 'typing')
        response = ask_ai(prompt, user_info)
        bot.send_message(chat_id, response, reply_markup=main_menu_markup())
        return

    elif text == '🥗 وجبات أبطال الحديد':
        user_info["current_focus"] = "تغذية ووجبات"
        prompt = "اقترح عليّ 3 وجبات سريعة وعالية البروتين تناسب أبطال كمال الأجسام وسهلة التحضير."
        bot.send_chat_action(chat_id, 'typing')
        response = ask_ai(prompt, user_info)
        bot.send_message(chat_id, response, reply_markup=main_menu_markup())
        return

    elif text == '💬 استشر الكابتن مباشرة':
        user_info["current_focus"] = "استشارة حرة"
        bot.send_message(
            chat_id,
            "🎤 تفضل يا وحش، المايك يمك! اسأل عن أي شي تريده (تمارين، مكملات، إصابات، أوزان)... وأنا بالخدمة.",
            reply_markup=main_menu_markup()
        )
        return

    # المحادثة العادية المفتوحة مع الذكاء الاصطناعي مع بقاء الأزرار ظاهرة
    bot.send_chat_action(chat_id, 'typing')
    ai_response = ask_ai(text, user_info)
    bot.reply_to(message, ai_response, reply_markup=main_menu_markup())

bot.remove_webhook()
print("تم تشغيل البوت بنجاح مع الأزرار العالمية...")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
