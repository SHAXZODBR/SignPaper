"""
Search Engine Service
Full-text search using Whoosh for book themes.
"""
import os
from pathlib import Path
from typing import List, Optional
from whoosh import index
from whoosh.fields import Schema, TEXT, ID, NUMERIC, STORED
from whoosh.qparser import MultifieldParser, OrGroup
from whoosh.analysis import StemmingAnalyzer
from whoosh import scoring
import sys
sys.path.append('..')
from config import SEARCH_INDEX_PATH


# Define the search schema
THEME_SCHEMA = Schema(
    theme_id=ID(stored=True, unique=True),
    book_id=ID(stored=True),
    name_uz=TEXT(stored=True, analyzer=StemmingAnalyzer()),
    name_ru=TEXT(stored=True, analyzer=StemmingAnalyzer()),
    content_uz=TEXT(analyzer=StemmingAnalyzer()),
    content_ru=TEXT(analyzer=StemmingAnalyzer()),
    subject=TEXT(stored=True),
    grade=NUMERIC(stored=True),
    book_title_uz=STORED,
    book_title_ru=STORED,
    start_page=NUMERIC(stored=True),
    end_page=NUMERIC(stored=True),
)


class SearchEngine:
    """Full-text search engine for book themes using Whoosh."""
    
    def __init__(self, index_path: Optional[Path] = None):
        self.index_path = index_path or SEARCH_INDEX_PATH
        self.index_path = Path(self.index_path)
        self.ix = None
    
    def create_index(self) -> bool:
        """Create a new search index."""
        try:
            self.index_path.mkdir(parents=True, exist_ok=True)
            self.ix = index.create_in(str(self.index_path), THEME_SCHEMA)
            return True
        except Exception as e:
            print(f"Error creating index: {e}")
            return False
    
    def open_index(self) -> bool:
        """Open an existing search index."""
        try:
            if index.exists_in(str(self.index_path)):
                self.ix = index.open_dir(str(self.index_path))
                return True
            else:
                return self.create_index()
        except Exception as e:
            print(f"Error opening index: {e}")
            return False
    
    def add_theme(
        self,
        theme_id: int,
        book_id: int,
        name_uz: str,
        name_ru: str,
        content_uz: str,
        content_ru: str,
        subject: str,
        grade: int,
        book_title_uz: str,
        book_title_ru: str,
        start_page: int,
        end_page: int
    ) -> bool:
        """Add a theme to the search index."""
        if not self.ix:
            if not self.open_index():
                return False
        
        try:
            writer = self.ix.writer()
            writer.update_document(
                theme_id=str(theme_id),
                book_id=str(book_id),
                name_uz=name_uz or "",
                name_ru=name_ru or "",
                content_uz=content_uz or "",
                content_ru=content_ru or "",
                subject=subject or "",
                grade=grade,
                book_title_uz=book_title_uz or "",
                book_title_ru=book_title_ru or "",
                start_page=start_page,
                end_page=end_page
            )
            writer.commit()
            return True
        except Exception as e:
            print(f"Error adding theme to index: {e}")
            return False
    
    def bulk_add_themes(self, themes: List[dict]) -> int:
        """Add multiple themes to the index at once."""
        if not self.ix:
            if not self.open_index():
                return 0
        
        added = 0
        try:
            writer = self.ix.writer()
            for theme in themes:
                writer.update_document(
                    theme_id=str(theme['theme_id']),
                    book_id=str(theme['book_id']),
                    name_uz=theme.get('name_uz', ''),
                    name_ru=theme.get('name_ru', ''),
                    content_uz=theme.get('content_uz', ''),
                    content_ru=theme.get('content_ru', ''),
                    subject=theme.get('subject', ''),
                    grade=theme.get('grade', 0),
                    book_title_uz=theme.get('book_title_uz', ''),
                    book_title_ru=theme.get('book_title_ru', ''),
                    start_page=theme.get('start_page', 0),
                    end_page=theme.get('end_page', 0)
                )
                added += 1
            writer.commit()
        except Exception as e:
            print(f"Error bulk adding themes: {e}")
        
        return added
    
    def search(
        self, 
        query: str, 
        limit: int = 10,
        grade: Optional[int] = None,
        subject: Optional[str] = None
    ) -> List[dict]:
        """
        Search for themes matching the query.
        Searches BOTH theme names AND content directly from database.
        Ranking: exact name match > partial name match > content match
        
        Args:
            query: Search query (works in both Uzbek and Russian)
            limit: Maximum number of results
            grade: Optional filter by grade
            subject: Optional filter by subject
        
        Returns:
            List of matching themes with scores
        """
        # Import database models for direct search
        from database.models import get_session, Theme, Book
        
        try:
            results = []
            query_lower = query.lower().strip()
            
            session = get_session()
            themes = session.query(Theme).all()
            
            for theme in themes:
                name_uz = (theme.name_uz or '').lower()
                name_ru = (theme.name_ru or '').lower()
                content_uz = (theme.content_uz or '').lower()
                content_ru = (theme.content_ru or '').lower()
                
                # Check for matches in name or content
                in_name_uz = query_lower in name_uz
                in_name_ru = query_lower in name_ru
                in_content = query_lower in content_uz or query_lower in content_ru
                
                # Skip if no match anywhere
                if not (in_name_uz or in_name_ru or in_content):
                    continue
                
                # Get book info
                book = session.query(Book).filter(Book.id == theme.book_id).first()
                
                # Apply filters
                if grade and book and book.grade != grade:
                    continue
                if subject and book and subject.lower() not in (book.subject or '').lower():
                    continue
                
                # Calculate score based on match type
                score = 0
                if name_uz == query_lower or name_ru == query_lower:
                    score = 10000  # Exact full name match - HIGHEST
                elif name_uz.startswith(query_lower) or name_ru.startswith(query_lower):
                    score = 5000   # Name starts with query
                elif in_name_uz or in_name_ru:
                    score = 1000   # Query found in name
                elif in_content:
                    score = 100    # Query found in content only
                
                results.append({
                    'theme_id': theme.id,
                    'book_id': theme.book_id,
                    'name_uz': theme.name_uz or '',
                    'name_ru': theme.name_ru or '',
                    'subject': book.subject if book else '',
                    'grade': book.grade if book else None,
                    'book_title_uz': book.title_uz if book else '',
                    'book_title_ru': book.title_ru if book else '',
                    'start_page': theme.start_page,
                    'end_page': theme.end_page,
                    'score': score,
                    'match_type': 'name' if (in_name_uz or in_name_ru) else 'content'
                })
            
            # Sort by score (descending) and limit
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:limit]
            
        except Exception as e:
            print(f"Error searching: {e}")
            return []
    
    def get_suggestions(self, prefix: str, limit: int = 5) -> List[str]:
        """Get autocomplete suggestions based on theme names."""
        if not self.ix:
            if not self.open_index():
                return []
        
        suggestions = set()
        try:
            with self.ix.searcher() as searcher:
                # Get suggestions from both language fields
                for field in ['name_uz', 'name_ru']:
                    for term in searcher.lexicon(field):
                        term_str = term.decode('utf-8') if isinstance(term, bytes) else term
                        if term_str.lower().startswith(prefix.lower()):
                            suggestions.add(term_str)
                            if len(suggestions) >= limit:
                                break
        except Exception as e:
            print(f"Error getting suggestions: {e}")
        
        return list(suggestions)[:limit]
    
    def clear_index(self) -> bool:
        """Clear all documents from the index."""
        return self.create_index()


# Singleton instance
_search_engine = None

def get_search_engine() -> SearchEngine:
    """Get the global search engine instance."""
    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine()
        _search_engine.open_index()
    return _search_engine


if __name__ == "__main__":
    # Test the search engine
    engine = SearchEngine()
    engine.create_index()
    
    # Add a test theme
    engine.add_theme(
        theme_id=1,
        book_id=1,
        name_uz="Pifagor teoremasi",
        name_ru="Теорема Пифагора",
        content_uz="Pifagor teoremasi to'g'ri burchakli uchburchakning...",
        content_ru="Теорема Пифагора гласит, что в прямоугольном треугольнике...",
        subject="Matematika",
        grade=8,
        book_title_uz="Matematika 8-sinf",
        book_title_ru="Математика 8 класс",
        start_page=45,
        end_page=52
    )
    
    # Test search
    results = engine.search("Пифагор")
    print(f"Search results: {results}")
