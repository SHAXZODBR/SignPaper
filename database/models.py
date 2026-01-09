"""
Database Models
Supports both Supabase (cloud) and SQLite (local fallback).
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, create_engine
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import sys
sys.path.append('..')
from config import DATABASE_PATH

# Try to import Supabase client
try:
    from database.supabase_client import (
        is_supabase_configured,
        get_book_by_id as sb_get_book,
        get_books_by_grade as sb_get_books_by_grade,
        get_theme_by_id as sb_get_theme,
        get_themes_by_book as sb_get_themes_by_book,
        get_theme_with_book as sb_get_theme_with_book,
        count_themes_by_book as sb_count_themes,
        search_themes as sb_search_themes,
        get_resources_by_theme as sb_get_resources,
        get_stats as sb_get_stats,
        track_user_action,
        track_search,
        track_download,
        save_feedback,
        save_support_message,
    )
    SUPABASE_AVAILABLE = is_supabase_configured()
except ImportError:
    SUPABASE_AVAILABLE = False

Base = declarative_base()


class Book(Base):
    """Represents a school book."""
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title_uz = Column(String(500), nullable=True)
    title_ru = Column(String(500), nullable=True)
    subject = Column(String(100), nullable=False)  # math, physics, etc.
    grade = Column(Integer, nullable=False)  # 5-11
    pdf_path_uz = Column(String(500), nullable=True)
    pdf_path_ru = Column(String(500), nullable=True)
    
    # Relationships
    themes = relationship("Theme", back_populates="book", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Book(id={self.id}, title='{self.title_uz}', grade={self.grade})>"


class Theme(Base):
    """Represents a theme/chapter within a book."""
    __tablename__ = "themes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    name_uz = Column(String(500), nullable=True)
    name_ru = Column(String(500), nullable=True)
    content_uz = Column(Text, nullable=True)  # Full text content
    content_ru = Column(Text, nullable=True)
    start_page = Column(Integer, nullable=True)
    end_page = Column(Integer, nullable=True)
    chapter_number = Column(String(50), nullable=True)  # e.g., "1.2", "Chapter 3"
    
    # Relationships
    book = relationship("Book", back_populates="themes")
    resources = relationship("Resource", back_populates="theme", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Theme(id={self.id}, name='{self.name_uz}', pages={self.start_page}-{self.end_page})>"


class Resource(Base):
    """Represents an educational resource for a theme."""
    __tablename__ = "resources"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    theme_id = Column(Integer, ForeignKey("themes.id"), nullable=False)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False)
    resource_type = Column(String(50), nullable=False)  # video, course, article, research
    language = Column(String(10), nullable=False)  # uz, ru, en
    source = Column(String(100), nullable=True)  # youtube, khan_academy, etc.
    
    # Relationships
    theme = relationship("Theme", back_populates="resources")
    
    def __repr__(self):
        return f"<Resource(id={self.id}, title='{self.title}', type='{self.resource_type}')>"


# Synchronous engine for setup
def get_sync_engine():
    return create_engine(f"sqlite:///{DATABASE_PATH}", echo=False)


# Async engine for bot operations
def get_async_engine():
    return create_async_engine(f"sqlite+aiosqlite:///{DATABASE_PATH}", echo=False)


def init_db():
    """Initialize the database and create all tables."""
    engine = get_sync_engine()
    Base.metadata.create_all(engine)
    print(f"Database initialized at {DATABASE_PATH}")
    return engine


def get_session():
    """Get a synchronous database session."""
    engine = get_sync_engine()
    Session = sessionmaker(bind=engine)
    return Session()


async def get_async_session():
    """Get an async database session."""
    engine = get_async_engine()
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session()


# ═══════════════════════════════════════════════════════════════════════════
# UNIFIED DATA ACCESS FUNCTIONS
# These functions use Supabase when configured, SQLite otherwise
# ═══════════════════════════════════════════════════════════════════════════

def use_supabase() -> bool:
    """Check if we should use Supabase."""
    return SUPABASE_AVAILABLE


def get_book(book_id: int):
    """Get book by ID - uses Supabase if configured, SQLite otherwise."""
    if SUPABASE_AVAILABLE:
        data = sb_get_book(book_id)
        if data:
            # Convert dict to object-like access
            return DictWrapper(data)
        return None
    else:
        session = get_session()
        return session.query(Book).filter(Book.id == book_id).first()


def get_theme(theme_id: int):
    """Get theme by ID - uses Supabase if configured, SQLite otherwise."""
    if SUPABASE_AVAILABLE:
        data = sb_get_theme(theme_id)
        if data:
            return DictWrapper(data)
        return None
    else:
        session = get_session()
        return session.query(Theme).filter(Theme.id == theme_id).first()


def get_theme_and_book(theme_id: int):
    """Get theme with its book - uses Supabase if configured."""
    if SUPABASE_AVAILABLE:
        data = sb_get_theme_with_book(theme_id)
        if data:
            theme = DictWrapper(data)
            if data.get("books"):
                theme._book = DictWrapper(data["books"])
            return theme
        return None
    else:
        session = get_session()
        theme = session.query(Theme).filter(Theme.id == theme_id).first()
        if theme:
            theme._book = session.query(Book).filter(Book.id == theme.book_id).first()
        return theme


def fetch_books_by_grade(grade: int, language: str = None):
    """Get books for a grade - uses Supabase if configured."""
    if SUPABASE_AVAILABLE:
        data = sb_get_books_by_grade(grade, language=language)
        return [DictWrapper(b) for b in data]
    else:
        session = get_session()
        # Local SQLite fallback doesn't support language filtering easily without schema change
        # but for now we just return all
        return session.query(Book).filter(Book.grade == grade).all()


def fetch_themes_by_book(book_id: int):
    """Get themes for a book - uses Supabase if configured."""
    if SUPABASE_AVAILABLE:
        data = sb_get_themes_by_book(book_id)
        return [DictWrapper(t) for t in data]
    else:
        session = get_session()
        return session.query(Theme).filter(Theme.book_id == book_id).all()


def count_book_themes(book_id: int) -> int:
    """Count themes for a book."""
    if SUPABASE_AVAILABLE:
        return sb_count_themes(book_id)
    else:
        session = get_session()
        return session.query(Theme).filter(Theme.book_id == book_id).count()


def fetch_theme_resources(theme_id: int):
    """Get resources for a theme."""
    if SUPABASE_AVAILABLE:
        data = sb_get_resources(theme_id)
        return [DictWrapper(r) for r in data]
    else:
        session = get_session()
        return session.query(Resource).filter(Resource.theme_id == theme_id).all()


def get_database_stats():
    """Get database statistics."""
    if SUPABASE_AVAILABLE:
        return sb_get_stats()
    else:
        session = get_session()
        return {
            "books": session.query(Book).count(),
            "themes": session.query(Theme).count(),
            "resources": session.query(Resource).count()
        }


class DictWrapper:
    """Wrapper to access dict keys as attributes."""
    def __init__(self, data):
        self._data = data
        self._book = None
    
    def __getattr__(self, name):
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        return self._data.get(name)
    
    def __getitem__(self, key):
        return self._data.get(key)
    
    def get(self, key, default=None):
        return self._data.get(key, default)


if __name__ == "__main__":
    init_db()
    if SUPABASE_AVAILABLE:
        print("✅ Using Supabase as primary database")
    else:
        print("ℹ️ Using SQLite (Supabase not configured)")
