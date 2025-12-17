"""
AI Summary Service
Generates summaries and quizzes using Groq API (FREE) with Llama models.
"""
import os
import re
import time
from groq import Groq
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Configure Groq (FREE tier available)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Rate limiting - track last request time
_last_request_time = 0
_min_request_interval = 3  # Minimum 3 seconds between requests

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


def check_rate_limit():
    """Check if we should wait before making a request. Returns wait time or 0."""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    
    if elapsed < _min_request_interval:
        return _min_request_interval - elapsed
    return 0


def update_rate_limit():
    """Update the last request time."""
    global _last_request_time
    _last_request_time = time.time()


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
    num_questions: int = 5,  # Reduced from 10 for faster generation
    language: str = "uz"
) -> Optional[str]:
    """
    Generate quiz questions from chapter content with spoilered answers.
    OPTIMIZED for speed - uses 5 questions by default.
    
    Args:
        content: The chapter text content
        theme_name: Name of the theme/chapter
        num_questions: Number of questions to generate (default 5 for speed)
        language: 'uz' for Uzbek, 'ru' for Russian
    
    Returns:
        Quiz text with spoilered answers or None if failed
    """
    if not content or len(content) < 100:
        return None
    
    # Check rate limit
    wait_time = check_rate_limit()
    if wait_time > 0:
        time.sleep(wait_time)
    
    try:
        client = get_client()
        
        # Reduce content size for faster processing
        max_chars = 4000  # Reduced from 8000
        if len(content) > max_chars:
            content = content[:max_chars] + "..."
        
        if language == "ru":
            prompt = f"""Создайте {num_questions} тестовых вопросов по главе "{theme_name}".

Содержание:
{content}

ФОРМАТ (строго соблюдайте):

1️⃣ [Вопрос]
A) [вариант]
B) [вариант]
C) [вариант]
D) [вариант]
💡 Ответ: [A/B/C/D]

(повторите для всех {num_questions} вопросов)"""
        else:
            prompt = f""""{theme_name}" mavzusi bo'yicha {num_questions} ta test savoli tuzing.

Mazmun:
{content}

FORMAT (qat'iy rioya qiling):

1️⃣ [Savol]
A) [variant]
B) [variant]
C) [variant]
D) [variant]
💡 Javob: [A/B/C/D]

(barcha {num_questions} ta savol uchun takrorlang)"""

        # Update rate limit tracker
        update_rate_limit()
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Fast model
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,  # Reduced from 4000
            temperature=0.5,  # Lower for more consistent output
            timeout=15.0  # 15 second timeout to avoid long waits
        )
        
        if response.choices and response.choices[0].message.content:
            quiz_text = response.choices[0].message.content.strip()
            return format_quiz_with_spoilers(quiz_text, language)
        
        return None
        
    except Exception as e:
        error_msg = str(e).lower()
        if "rate" in error_msg or "429" in error_msg:
            return "RATE_LIMITED"
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
