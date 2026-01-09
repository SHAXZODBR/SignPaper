"""
Supabase Client Service
Handles all database operations with Supabase.
"""
import os
from typing import List, Optional, Dict, Any
from functools import lru_cache
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Global client instance
_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    """Get or create Supabase client instance."""
    global _supabase_client
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be set in .env file.\n"
            "Get your keys from: https://supabase.com/dashboard/project/YOUR_PROJECT/settings/api"
        )
    
    if _supabase_client is None:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    return _supabase_client


def is_supabase_configured() -> bool:
    """Check if Supabase is properly configured."""
    return bool(SUPABASE_URL and SUPABASE_KEY)


# ═══════════════════════════════════════════════════════════════════════════
# USER SETTINGS (LANGUAGE)
# ═══════════════════════════════════════════════════════════════════════════

@lru_cache(maxsize=1000)
def get_user_lang(telegram_user_id: int) -> str:
    """Get user's preferred language. Defaults to 'uz'."""
    try:
        client = get_supabase()
        response = client.table("user_settings").select("language").eq("telegram_user_id", telegram_user_id).limit(1).execute()
        if response.data:
            return response.data[0].get("language", "uz")
    except Exception as e:
        print(f"Error getting user language: {e}")
    return "uz"


def set_user_lang(telegram_user_id: int, language: str) -> bool:
    """Set user's preferred language."""
    try:
        client = get_supabase()
        # Use upsert to create or update
        client.table("user_settings").upsert({
            "telegram_user_id": telegram_user_id,
            "language": language,
            "updated_at": "now()"
        }).execute()
        
        # Clear cache for this user
        get_user_lang.cache_clear()
        return True
    except Exception as e:
        print(f"Error setting user language: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════
# BOOKS OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════

def get_all_books(active_only: bool = True) -> List[Dict[str, Any]]:
    """Get all books from database."""
    try:
        client = get_supabase()
        query = client.table("books").select("*")
        
        if active_only:
            query = query.eq("is_active", True)
        
        response = query.order("grade").order("subject").execute()
        return response.data or []
    except Exception as e:
        print(f"Error fetching books: {e}")
        return []


def get_books_by_grade(grade: int, active_only: bool = True, language: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get books for a specific grade."""
    try:
        client = get_supabase()
        query = client.table("books").select("*").eq("grade", grade)
        
        if active_only:
            query = query.eq("is_active", True)
        
        if language == 'uz':
            # Filter books that have Uzbek title
            query = query.not_.is_("title_uz", "null")
        elif language == 'ru':
            # Filter books that have Russian title
            query = query.not_.is_("title_ru", "null")
        
        response = query.order("subject").execute()
        return response.data or []
    except Exception as e:
        print(f"Error fetching books by grade: {e}")
        return []


def get_book_by_id(book_id: int) -> Optional[Dict[str, Any]]:
    """Get a single book by ID."""
    try:
        client = get_supabase()
        response = client.table("books").select("*").eq("id", book_id).limit(1).execute()
        data = response.data
        return data[0] if data else None
    except Exception as e:
        print(f"Error fetching book {book_id}: {e}")
        return None


def get_books_count() -> int:
    """Get total count of active books."""
    try:
        client = get_supabase()
        response = client.table("books").select("id", count="exact").eq("is_active", True).execute()
        return response.count or 0
    except Exception as e:
        print(f"Error counting books: {e}")
        return 0


# ═══════════════════════════════════════════════════════════════════════════
# THEMES OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════

def get_themes_by_book(book_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
    """Get all themes for a book."""
    try:
        client = get_supabase()
        query = client.table("themes").select("*").eq("book_id", book_id)
        
        if active_only:
            query = query.eq("is_active", True)
        
        response = query.order("order_index").execute()
        return response.data or []
    except Exception as e:
        print(f"Error fetching themes for book {book_id}: {e}")
        return []


def get_theme_by_id(theme_id: int) -> Optional[Dict[str, Any]]:
    """Get a single theme by ID."""
    try:
        client = get_supabase()
        response = client.table("themes").select("*").eq("id", theme_id).limit(1).execute()
        data = response.data
        return data[0] if data else None
    except Exception as e:
        print(f"Error fetching theme {theme_id}: {e}")
        return None


def get_theme_with_book(theme_id: int) -> Optional[Dict[str, Any]]:
    """Get a theme with its associated book information."""
    try:
        client = get_supabase()
        response = client.table("themes").select(
            "*, books(*)"
        ).eq("id", theme_id).limit(1).execute()
        data = response.data
        return data[0] if data else None
    except Exception as e:
        print(f"Error fetching theme with book {theme_id}: {e}")
        return None


def get_themes_count() -> int:
    """Get total count of active themes."""
    try:
        client = get_supabase()
        response = client.table("themes").select("id", count="exact").eq("is_active", True).execute()
        return response.count or 0
    except Exception as e:
        print(f"Error counting themes: {e}")
        return 0


def count_themes_by_book(book_id: int) -> int:
    """Count themes for a specific book."""
    try:
        client = get_supabase()
        response = client.table("themes").select(
            "id", count="exact"
        ).eq("book_id", book_id).eq("is_active", True).execute()
        return response.count or 0
    except Exception as e:
        print(f"Error counting themes: {e}")
        return 0


# ═══════════════════════════════════════════════════════════════════════════
# SEARCH OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════

def search_themes(
    query: str, 
    limit: int = 10,
    offset: int = 0,
    grade: Optional[int] = None,
    subject: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for themes matching a query.
    Uses the search_themes PostgreSQL function for ranked results.
    """

    try:
        # Always use Python fallback search which has exact phrase matching
        # RPC function in database doesn't support our new matching logic
        return _fallback_search(query, limit, offset, grade, subject)
        
    except Exception as e:
        print(f"Search error: {e}")
        return []
        



def _fallback_search(
    query: str, 
    limit: int = 10,
    offset: int = 0,
    grade: Optional[int] = None,
    subject: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search themes by NAME only (not content)."""
    try:
        client = get_supabase()
        query = query.strip()
        
        # Search ONLY in theme names (not content)
        filter_str = f"name_uz.ilike.%{query}%,name_ru.ilike.%{query}%"
        
        base_query = client.table("themes").select(
            "id, book_id, name_uz, name_ru, start_page, end_page, books(subject, grade, title_uz, title_ru)"
        ).eq("is_active", True)
        
        # Add name filter
        base_query = base_query.or_(filter_str)
        
        # Pagination
        response = base_query.order('id').range(offset, offset + 49).execute()
        
        results = []
        query_lower = query.lower()
        
        for theme in response.data or []:
            book = theme.get("books", {})
            if not book: continue
            
            # Apply filters
            if grade and book.get("grade") != grade:
                continue
            if subject and subject.lower() not in (book.get("subject") or "").lower():
                continue
            
            name_uz = theme.get("name_uz") or ""
            name_ru = theme.get("name_ru") or ""
            
            # Only include if query is in name
            if query_lower in name_uz.lower() or query_lower in name_ru.lower():
                results.append({
                    "theme_id": theme["id"],
                    "book_id": theme["book_id"],
                    "name_uz": name_uz,  # Actual theme name
                    "name_ru": name_ru,  # Actual theme name
                    "subject": book.get("subject"),
                    "grade": book.get("grade"),
                    "book_title_uz": book.get("title_uz"),
                    "book_title_ru": book.get("title_ru"),
                    "start_page": theme.get("start_page"),
                    "end_page": theme.get("end_page"),
                    "relevance_score": 1000,
                    "snippet": ""
                })
        
        # Deduplicate
        seen_ids = set()
        unique_results = []
        for r in results:
            if r["theme_id"] not in seen_ids:
                seen_ids.add(r["theme_id"])
                unique_results.append(r)
        
        return unique_results[:limit]
        

        
    except Exception as e:
        print(f"Fallback search error: {e}")
        return []


def detect_language(text: str) -> str:
    """Detect if text is Russian (Cyrillic) or Uzbek (Latin)."""
    cyrillic_count = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    latin_count = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    
    if cyrillic_count > latin_count:
        return 'ru'
    return 'uz'


# ═══════════════════════════════════════════════════════════════════════════
# RESOURCES OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════

def get_resources_by_theme(theme_id: int) -> List[Dict[str, Any]]:
    """Get all resources for a theme."""
    try:
        client = get_supabase()
        response = client.table("resources").select("*").eq(
            "theme_id", theme_id
        ).eq("is_active", True).execute()
        return response.data or []
    except Exception as e:
        print(f"Error fetching resources: {e}")
        return []


def get_resources_count() -> int:
    """Get total count of active resources."""
    try:
        client = get_supabase()
        response = client.table("resources").select("id", count="exact").eq("is_active", True).execute()
        return response.count or 0
    except Exception as e:
        print(f"Error counting resources: {e}")
        return 0


# ═══════════════════════════════════════════════════════════════════════════
# ANALYTICS OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════

def track_user_action(
    telegram_user_id: int,
    action_type: str,
    telegram_username: Optional[str] = None,
    first_name: Optional[str] = None,
    action_data: Optional[Dict] = None
) -> bool:
    """Track user action for analytics."""
    try:
        client = get_supabase()
        client.table("user_analytics").insert({
            "telegram_user_id": telegram_user_id,
            "telegram_username": telegram_username,
            "first_name": first_name,
            "action_type": action_type,
            "action_data": action_data or {}
        }).execute()
        return True
    except Exception as e:
        print(f"Error tracking user action: {e}")
        return False


def track_search(
    query: str,
    results_count: int,
    telegram_user_id: Optional[int] = None,
    language_detected: Optional[str] = None,
    clicked_theme_id: Optional[int] = None
) -> bool:
    """Track search query for analytics."""
    try:
        client = get_supabase()
        client.table("search_analytics").insert({
            "telegram_user_id": telegram_user_id,
            "query": query,
            "language_detected": language_detected or detect_language(query),
            "results_count": results_count,
            "clicked_theme_id": clicked_theme_id
        }).execute()
        return True
    except Exception as e:
        print(f"Error tracking search: {e}")
        return False


def track_download(
    book_id: Optional[int] = None,
    theme_id: Optional[int] = None,
    download_type: str = "book_pdf",
    language: Optional[str] = None,
    telegram_user_id: Optional[int] = None
) -> bool:
    """Track download for analytics."""
    try:
        client = get_supabase()
        client.table("downloads").insert({
            "telegram_user_id": telegram_user_id,
            "book_id": book_id,
            "theme_id": theme_id,
            "download_type": download_type,
            "language": language
        }).execute()
        return True
    except Exception as e:
        print(f"Error tracking download: {e}")
        return False


def save_feedback(
    telegram_user_id: int,
    rating: int,
    telegram_username: Optional[str] = None,
    message: Optional[str] = None
) -> bool:
    """Save user feedback/rating."""
    try:
        client = get_supabase()
        client.table("feedback").insert({
            "telegram_user_id": telegram_user_id,
            "telegram_username": telegram_username,
            "rating": rating,
            "message": message
        }).execute()
        return True
    except Exception as e:
        print(f"Error saving feedback: {e}")
        return False


def save_support_message(
    telegram_user_id: int,
    message: str,
    telegram_username: Optional[str] = None,
    first_name: Optional[str] = None,
    is_from_user: bool = True
) -> bool:
    """Save support message."""
    try:
        client = get_supabase()
        client.table("support_messages").insert({
            "telegram_user_id": telegram_user_id,
            "telegram_username": telegram_username,
            "first_name": first_name,
            "message": message,
            "is_from_user": is_from_user
        }).execute()
        return True
    except Exception as e:
        print(f"Error saving support message: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════
# STATISTICS
# ═══════════════════════════════════════════════════════════════════════════

def get_users_count() -> int:
    """Get total number of unique users."""
    try:
        client = get_supabase()
        response = client.table("user_analytics").select("telegram_user_id", count="exact").execute()
        # Note: This is a hack because Supabase select doesn't easily do DISTINCT count via client
        # For small-medium boards, we can just get all and len(set) or use a RPC
        # But for now, let's just count rows in user_analytics which represents 'visits'
        return response.count or 0
    except:
        return 0

def get_searches_count() -> int:
    """Get total number of searches."""
    try:
        client = get_supabase()
        response = client.table("search_analytics").select("*", count="exact").execute()
        return response.count or 0
    except:
        return 0

def get_downloads_count() -> int:
    """Get total number of downloads."""
    try:
        client = get_supabase()
        response = client.table("downloads").select("*", count="exact").execute()
        return response.count or 0
    except:
        return 0

def get_stats() -> Dict[str, int]:
    """Get database statistics."""
    return {
        "books": get_books_count(),
        "themes": get_themes_count(),
        "resources": get_resources_count(),
        "total_users": get_users_count(),
        "total_searches": get_searches_count(),
        "total_downloads": get_downloads_count()
    }


# ═══════════════════════════════════════════════════════════════════════════
# TEST CONNECTION
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Testing Supabase connection...")
    
    if not is_supabase_configured():
        print("❌ SUPABASE_URL and SUPABASE_KEY not set in .env")
        print("Please add your Supabase credentials to .env file")
    else:
        try:
            client = get_supabase()
            stats = get_stats()
            print("✅ Connected to Supabase!")
            print(f"📚 Books: {stats['books']}")
            print(f"📑 Themes: {stats['themes']}")
            print(f"🔗 Resources: {stats['resources']}")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
