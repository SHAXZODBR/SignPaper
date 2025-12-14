"""
AI Summary Service
Generates summaries and quizzes using Groq API (FREE) with Llama models.
"""
import os
import re
from groq import Groq
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Configure Groq (FREE tier available)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Initialize client
_client = None


def get_client():
    """Get or initialize Groq client."""
    global _client
    
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY not set in .env file.\n"
            "Get FREE API key from: https://console.groq.com/keys"
        )
    
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    
    return _client


def generate_summary(
    content: str,
    theme_name: str,
    language: str = "uz"
) -> Optional[str]:
    """
    Generate a summary of chapter content using AI.
    
    Args:
        content: The chapter text content
        theme_name: Name of the theme/chapter
        language: 'uz' for Uzbek, 'ru' for Russian
    
    Returns:
        Summary text or None if failed
    """
    if not content or len(content) < 100:
        return None
    
    try:
        client = get_client()
        
        # Truncate content if too long
        max_chars = 10000
        if len(content) > max_chars:
            content = content[:max_chars] + "..."
        
        # Create prompt based on language
        if language == "ru":
            prompt = f"""Вы - образовательный помощник. Создайте краткое резюме следующей главы учебника.

Глава: {theme_name}

Содержание:
{content}

Требования к резюме:
1. Напишите на русском языке
2. Выделите 3-5 ключевых понятий
3. Объясните главную идею
4. Длина: 150-250 слов
5. Используйте простой язык для учеников

Резюме:"""
        else:
            prompt = f"""Siz ta'lim yordamchisiz. Quyidagi darslik bobining qisqa xulosasini yarating.

Bob: {theme_name}

Mazmuni:
{content}

Xulosa talablari:
1. O'zbek tilida yozing
2. 3-5 ta asosiy tushunchalarni ajratib ko'rsating
3. Asosiy g'oyani tushuntiring
4. Uzunligi: 150-250 so'z
5. O'quvchilar uchun oddiy til ishlating

Xulosa:"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a helpful educational assistant that writes in Uzbek or Russian as requested."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content.strip()
        
        return None
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        return None


def generate_quiz(
    content: str,
    theme_name: str,
    num_questions: int = 10,
    language: str = "uz"
) -> Optional[str]:
    """
    Generate quiz questions from chapter content with spoilered answers.
    
    Args:
        content: The chapter text content
        theme_name: Name of the theme/chapter
        num_questions: Number of questions to generate (default 10)
        language: 'uz' for Uzbek, 'ru' for Russian
    
    Returns:
        Quiz text with spoilered answers or None if failed
    """
    if not content or len(content) < 100:
        return None
    
    try:
        client = get_client()
        
        max_chars = 8000
        if len(content) > max_chars:
            content = content[:max_chars] + "..."
        
        if language == "ru":
            prompt = f"""Создайте ровно {num_questions} тестовых вопросов по следующей главе учебника.

Глава: {theme_name}

Содержание:
{content}

ВАЖНЫЕ ТРЕБОВАНИЯ:
1. Создайте ровно {num_questions} вопросов
2. Каждый вопрос должен иметь 4 варианта ответа (A, B, C, D)
3. Только один ответ правильный
4. Вопросы должны проверять понимание материала

СТРОГИЙ ФОРМАТ:

1️⃣ [Текст вопроса]
A) [вариант]
B) [вариант]
C) [вариант]
D) [вариант]
💡 Ответ: [БУКВА]

(продолжайте до {num_questions})"""
        else:
            prompt = f"""Quyidagi darslik bobi bo'yicha aniq {num_questions} ta test savoli tuzing.

Bob: {theme_name}

Mazmun:
{content}

MUHIM TALABLAR:
1. Aniq {num_questions} ta savol tuzing
2. Har bir savolda 4 ta javob varianti bo'lsin (A, B, C, D)
3. Faqat bitta to'g'ri javob bo'lsin
4. Savollar materialni tushunishni tekshirsin

QATIY FORMAT:

1️⃣ [Savol matni]
A) [variant]
B) [variant]
C) [variant]
D) [variant]
💡 Javob: [HARF]

({num_questions} tagacha davom eting)"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a helpful educational assistant that creates quizzes in Uzbek or Russian as requested."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,
            temperature=0.7
        )
        
        if response.choices and response.choices[0].message.content:
            quiz_text = response.choices[0].message.content.strip()
            return format_quiz_with_spoilers(quiz_text, language)
        
        return None
        
    except Exception as e:
        print(f"Error generating quiz: {e}")
        return None


def format_quiz_with_spoilers(quiz_text: str, language: str = "uz") -> str:
    """
    Format quiz text to hide answers using Telegram HTML spoiler format.
    Uses <tg-spoiler> tag for proper spoiler rendering.
    """
    lines = quiz_text.split('\n')
    formatted_lines = []
    
    for line in lines:
        # Match answer lines in both Uzbek and Russian
        answer_pattern = r'(💡\s*(?:Javob|Ответ|Answer)|✅\s*(?:To\'g\'ri javob|Правильный ответ)):\s*([A-Da-d])'
        match = re.search(answer_pattern, line, re.IGNORECASE)
        
        if match:
            answer_letter = match.group(2).upper()
            if language == "ru":
                formatted_lines.append(f"💡 Ответ: <tg-spoiler>{answer_letter}</tg-spoiler>")
            else:
                formatted_lines.append(f"💡 Javob: <tg-spoiler>{answer_letter}</tg-spoiler>")
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)


# Test the service
if __name__ == "__main__":
    test_content = """
    Natural sonlar - bu 1, 2, 3, 4, 5, ... kabi sonlardir.
    Ular sanash uchun ishlatiladi. Natural sonlar cheksiz ko'p.
    Eng kichik natural son 1 ga teng. 0 natural son emas.
    Natural sonlarni qo'shish, ayirish, ko'paytirish mumkin.
    """
    
    print("Testing Groq AI Service...")
    summary = generate_summary(test_content, "Natural sonlar", "uz")
    if summary:
        print(f"Summary generated:\n{summary}")
    else:
        print("Failed to generate summary. Check GROQ_API_KEY in .env")
