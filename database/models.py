from sqlalchemy import Column, Integer, String, Text, ForeignKey, create_engine
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import sys
sys.path.append('..')
from config import DATABASE_PATH

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


if __name__ == "__main__":
    init_db()
