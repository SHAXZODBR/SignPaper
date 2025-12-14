"""
Add sample data for testing without actual PDFs.
"""
import sys
sys.path.append('..')
from database.models import init_db, get_session, Book, Theme, Resource
from services.search_engine import get_search_engine
from services.resource_finder import ResourceFinder


def add_sample_data():
    """Add sample books and themes for testing."""
    
    # Initialize database
    init_db()
    session = get_session()
    search_engine = get_search_engine()
    
    # Sample books data
    sample_books = [
        {
            'title_uz': "Matematika 5-sinf",
            'title_ru': "Математика 5 класс",
            'subject': "matematika",
            'grade': 5,
            'themes': [
                {'name_uz': "Natural sonlar", 'name_ru': "Натуральные числа", 'start': 1, 'end': 20},
                {'name_uz': "Kasrlar", 'name_ru': "Дроби", 'start': 21, 'end': 45},
                {'name_uz': "Geometrik shakllar", 'name_ru': "Геометрические фигуры", 'start': 46, 'end': 70},
            ]
        },
        {
            'title_uz': "Matematika 8-sinf",
            'title_ru': "Математика 8 класс",
            'subject': "matematika",
            'grade': 8,
            'themes': [
                {'name_uz': "Pifagor teoremasi", 'name_ru': "Теорема Пифагора", 'start': 1, 'end': 15},
                {'name_uz': "Kvadrat tenglamalar", 'name_ru': "Квадратные уравнения", 'start': 16, 'end': 35},
                {'name_uz': "Trigonometriya asoslari", 'name_ru': "Основы тригонометрии", 'start': 36, 'end': 55},
            ]
        },
        {
            'title_uz': "Fizika 7-sinf",
            'title_ru': "Физика 7 класс",
            'subject': "fizika",
            'grade': 7,
            'themes': [
                {'name_uz': "Mexanika", 'name_ru': "Механика", 'start': 1, 'end': 25},
                {'name_uz': "Nyuton qonunlari", 'name_ru': "Законы Ньютона", 'start': 26, 'end': 50},
                {'name_uz': "Energiya", 'name_ru': "Энергия", 'start': 51, 'end': 70},
            ]
        },
        {
            'title_uz': "Kimyo 8-sinf",
            'title_ru': "Химия 8 класс",
            'subject': "kimyo",
            'grade': 8,
            'themes': [
                {'name_uz': "Atom tuzilishi", 'name_ru': "Строение атома", 'start': 1, 'end': 20},
                {'name_uz': "Kimyoviy bog'lanish", 'name_ru': "Химическая связь", 'start': 21, 'end': 40},
                {'name_uz': "Davriy jadval", 'name_ru': "Периодическая таблица", 'start': 41, 'end': 60},
            ]
        },
        {
            'title_uz': "Biologiya 9-sinf",
            'title_ru': "Биология 9 класс",
            'subject': "biologiya",
            'grade': 9,
            'themes': [
                {'name_uz': "Hujayra", 'name_ru': "Клетка", 'start': 1, 'end': 30},
                {'name_uz': "Genetika", 'name_ru': "Генетика", 'start': 31, 'end': 60},
                {'name_uz': "Evolyutsiya", 'name_ru': "Эволюция", 'start': 61, 'end': 90},
            ]
        },
    ]
    
    print("Adding sample data...")
    
    for book_data in sample_books:
        # Check if book exists
        existing = session.query(Book).filter(
            Book.subject == book_data['subject'],
            Book.grade == book_data['grade']
        ).first()
        
        if existing:
            print(f"  Skipping existing: {book_data['title_uz']}")
            continue
        
        # Create book
        book = Book(
            title_uz=book_data['title_uz'],
            title_ru=book_data['title_ru'],
            subject=book_data['subject'],
            grade=book_data['grade']
        )
        session.add(book)
        session.commit()
        
        print(f"  Added book: {book_data['title_uz']}")
        
        # Add themes
        for theme_data in book_data['themes']:
            theme = Theme(
                book_id=book.id,
                name_uz=theme_data['name_uz'],
                name_ru=theme_data['name_ru'],
                content_uz=f"Sample content for {theme_data['name_uz']}",
                content_ru=f"Пример содержания для {theme_data['name_ru']}",
                start_page=theme_data['start'],
                end_page=theme_data['end']
            )
            session.add(theme)
            session.commit()
            
            # Add to search index
            search_engine.add_theme(
                theme_id=theme.id,
                book_id=book.id,
                name_uz=theme.name_uz,
                name_ru=theme.name_ru,
                content_uz=theme.content_uz or "",
                content_ru=theme.content_ru or "",
                subject=book.subject,
                grade=book.grade,
                book_title_uz=book.title_uz,
                book_title_ru=book.title_ru,
                start_page=theme.start_page,
                end_page=theme.end_page
            )
            
            # Add resources
            resources = ResourceFinder.find_resources_for_theme(
                theme_name=theme.name_uz,
                subject=book.subject,
                grade=book.grade
            )
            
            for res in resources[:3]:
                resource = Resource(
                    theme_id=theme.id,
                    title=res.title,
                    url=res.url,
                    resource_type=res.resource_type,
                    language=res.language,
                    source=res.source
                )
                session.add(resource)
            
            session.commit()
            print(f"    Added theme: {theme_data['name_uz']}")
    
    # Print stats
    books_count = session.query(Book).count()
    themes_count = session.query(Theme).count()
    resources_count = session.query(Resource).count()
    
    print(f"\n✅ Sample data added!")
    print(f"   Books: {books_count}")
    print(f"   Themes: {themes_count}")
    print(f"   Resources: {resources_count}")


if __name__ == "__main__":
    add_sample_data()
