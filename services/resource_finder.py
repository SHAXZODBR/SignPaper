"""
Resource Finder Service
Finds educational resources (videos, courses, articles) for themes.
"""
import aiohttp
import asyncio
from typing import List, Optional
from dataclasses import dataclass
from urllib.parse import quote_plus
import re


@dataclass
class EducationalResource:
    """Represents an educational resource."""
    title: str
    url: str
    resource_type: str  # video, course, article, research
    language: str  # uz, ru, en
    source: str  # youtube, khan_academy, etc.
    description: Optional[str] = None


class ResourceFinder:
    """Finds educational resources for themes from various sources."""
    
    # Curated resource mappings for common subjects
    SUBJECT_RESOURCES = {
        'matematika': {
            'uz': [
                {'title': 'Matematika darslari', 'url': 'https://bilim.uz/matematika', 'source': 'bilim.uz'},
            ],
            'ru': [
                {'title': 'Математика - GetAClass', 'url': 'https://www.getaclass.ru/courses/math', 'source': 'getaclass'},
                {'title': 'Математика - InternetUrok', 'url': 'https://interneturok.ru/subject/matematika', 'source': 'interneturok'},
            ],
            'en': [
                {'title': 'Math - Khan Academy', 'url': 'https://www.khanacademy.org/math', 'source': 'khan_academy'},
            ]
        },
        'fizika': {
            'uz': [
                {'title': 'Fizika darslari', 'url': 'https://bilim.uz/fizika', 'source': 'bilim.uz'},
            ],
            'ru': [
                {'title': 'Физика - GetAClass', 'url': 'https://www.getaclass.ru/courses/physics', 'source': 'getaclass'},
                {'title': 'Физика - InternetUrok', 'url': 'https://interneturok.ru/subject/fizika', 'source': 'interneturok'},
            ],
            'en': [
                {'title': 'Physics - Khan Academy', 'url': 'https://www.khanacademy.org/science/physics', 'source': 'khan_academy'},
            ]
        },
        'kimyo': {
            'uz': [
                {'title': 'Kimyo darslari', 'url': 'https://bilim.uz/kimyo', 'source': 'bilim.uz'},
            ],
            'ru': [
                {'title': 'Химия - GetAClass', 'url': 'https://www.getaclass.ru/courses/chemistry', 'source': 'getaclass'},
                {'title': 'Химия - InternetUrok', 'url': 'https://interneturok.ru/subject/himiya', 'source': 'interneturok'},
            ],
            'en': [
                {'title': 'Chemistry - Khan Academy', 'url': 'https://www.khanacademy.org/science/chemistry', 'source': 'khan_academy'},
            ]
        },
        'biologiya': {
            'uz': [
                {'title': 'Biologiya darslari', 'url': 'https://bilim.uz/biologiya', 'source': 'bilim.uz'},
            ],
            'ru': [
                {'title': 'Биология - InternetUrok', 'url': 'https://interneturok.ru/subject/biologiya', 'source': 'interneturok'},
            ],
            'en': [
                {'title': 'Biology - Khan Academy', 'url': 'https://www.khanacademy.org/science/biology', 'source': 'khan_academy'},
            ]
        },
        'tarix': {
            'uz': [
                {'title': 'Tarix darslari', 'url': 'https://bilim.uz/tarix', 'source': 'bilim.uz'},
            ],
            'ru': [
                {'title': 'История - InternetUrok', 'url': 'https://interneturok.ru/subject/istoriya', 'source': 'interneturok'},
            ],
            'en': [
                {'title': 'History - Khan Academy', 'url': 'https://www.khanacademy.org/humanities/world-history', 'source': 'khan_academy'},
            ]
        },
        'geografiya': {
            'uz': [
                {'title': 'Geografiya darslari', 'url': 'https://bilim.uz/geografiya', 'source': 'bilim.uz'},
            ],
            'ru': [
                {'title': 'География - InternetUrok', 'url': 'https://interneturok.ru/subject/geografiya', 'source': 'interneturok'},
            ],
            'en': [
                {'title': 'Geography - Khan Academy', 'url': 'https://www.khanacademy.org/humanities/world-history', 'source': 'khan_academy'},
            ]
        },
        'informatika': {
            'uz': [
                {'title': 'Informatika darslari', 'url': 'https://bilim.uz/informatika', 'source': 'bilim.uz'},
            ],
            'ru': [
                {'title': 'Информатика - InternetUrok', 'url': 'https://interneturok.ru/subject/informatika', 'source': 'interneturok'},
                {'title': 'Программирование - Stepik', 'url': 'https://stepik.org/', 'source': 'stepik'},
            ],
            'en': [
                {'title': 'Computing - Khan Academy', 'url': 'https://www.khanacademy.org/computing', 'source': 'khan_academy'},
            ]
        },
    }
    
    @classmethod
    def get_youtube_search_url(cls, query: str, language: str = 'uz') -> str:
        """Generate YouTube search URL for a query."""
        encoded_query = quote_plus(query)
        lang_filter = {'uz': 'UZ', 'ru': 'RU', 'en': 'US'}.get(language, '')
        return f"https://www.youtube.com/results?search_query={encoded_query}&sp=EgIQAQ%253D%253D"
    
    @classmethod
    def get_google_scholar_url(cls, query: str) -> str:
        """Generate Google Scholar search URL."""
        encoded_query = quote_plus(query)
        return f"https://scholar.google.com/scholar?q={encoded_query}"
    
    @classmethod
    def find_resources_for_theme(
        cls, 
        theme_name: str, 
        subject: str,
        grade: int,
        languages: List[str] = ['uz', 'ru', 'en']
    ) -> List[EducationalResource]:
        """
        Find educational resources for a theme.
        
        Args:
            theme_name: Name of the theme
            subject: Subject (matematika, fizika, etc.)
            grade: Grade level (5-11)
            languages: Languages to include
        
        Returns:
            List of educational resources
        """
        resources = []
        subject_lower = subject.lower()
        
        # Add curated subject resources
        if subject_lower in cls.SUBJECT_RESOURCES:
            for lang in languages:
                if lang in cls.SUBJECT_RESOURCES[subject_lower]:
                    for res in cls.SUBJECT_RESOURCES[subject_lower][lang]:
                        resources.append(EducationalResource(
                            title=res['title'],
                            url=res['url'],
                            resource_type='course',
                            language=lang,
                            source=res['source']
                        ))
        
        # Add YouTube search links for each language
        for lang in languages:
            search_query = f"{theme_name} {grade} sinf dars" if lang == 'uz' else \
                          f"{theme_name} {grade} класс урок" if lang == 'ru' else \
                          f"{theme_name} grade {grade} lesson"
            
            resources.append(EducationalResource(
                title=f"🎥 YouTube: {theme_name} ({lang.upper()})",
                url=cls.get_youtube_search_url(search_query, lang),
                resource_type='video',
                language=lang,
                source='youtube',
                description=f"Search results for {theme_name}"
            ))
        
        # Add Google Scholar for research
        resources.append(EducationalResource(
            title=f"📚 Research: {theme_name}",
            url=cls.get_google_scholar_url(theme_name),
            resource_type='research',
            language='en',
            source='google_scholar',
            description="Academic papers and research"
        ))
        
        return resources
    
    @classmethod
    def format_resources_message(cls, resources: List[EducationalResource]) -> str:
        """Format resources into a readable message for Telegram."""
        if not resources:
            return "No resources found."
        
        lines = ["📚 **Educational Resources:**\n"]
        
        # Group by language
        by_lang = {'uz': [], 'ru': [], 'en': []}
        for res in resources:
            if res.language in by_lang:
                by_lang[res.language].append(res)
        
        lang_names = {'uz': '🇺🇿 O\'zbekcha', 'ru': '🇷🇺 Русский', 'en': '🇬🇧 English'}
        type_icons = {'video': '🎥', 'course': '📖', 'article': '📄', 'research': '🔬'}
        
        for lang, lang_resources in by_lang.items():
            if lang_resources:
                lines.append(f"\n**{lang_names.get(lang, lang)}:**")
                for res in lang_resources:
                    icon = type_icons.get(res.resource_type, '📌')
                    lines.append(f"  {icon} [{res.title}]({res.url})")
        
        return "\n".join(lines)


if __name__ == "__main__":
    # Test resource finding
    resources = ResourceFinder.find_resources_for_theme(
        theme_name="Pifagor teoremasi",
        subject="matematika",
        grade=8
    )
    
    print(ResourceFinder.format_resources_message(resources))
