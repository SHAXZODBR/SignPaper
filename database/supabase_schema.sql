-- ═══════════════════════════════════════════════════════════════════════════
-- SignPaper - Uzbek School Books Bot
-- Supabase Database Schema
-- ═══════════════════════════════════════════════════════════════════════════
-- Run this SQL in your Supabase SQL Editor:
-- https://supabase.com/dashboard/project/YOUR_PROJECT/sql/new
-- ═══════════════════════════════════════════════════════════════════════════

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ═══════════════════════════════════════════════════════════════════════════
-- BOOKS TABLE
-- Stores all school textbooks with bilingual support
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    title_uz VARCHAR(500),          -- Uzbek title
    title_ru VARCHAR(500),          -- Russian title
    subject VARCHAR(100) NOT NULL,  -- Subject code: matematika, fizika, kimyo, etc.
    grade INTEGER NOT NULL CHECK (grade >= 1 AND grade <= 11),
    pdf_path_uz VARCHAR(500),       -- Path/URL to Uzbek PDF
    pdf_path_ru VARCHAR(500),       -- Path/URL to Russian PDF
    pdf_url_uz TEXT,                -- Supabase Storage URL for Uzbek PDF
    pdf_url_ru TEXT,                -- Supabase Storage URL for Russian PDF
    cover_image_url TEXT,           -- Book cover image URL
    description_uz TEXT,            -- Description in Uzbek
    description_ru TEXT,            -- Description in Russian
    author VARCHAR(255),            -- Author name
    publisher VARCHAR(255),         -- Publisher name
    year_published INTEGER,         -- Publication year
    page_count INTEGER,             -- Total pages
    is_active BOOLEAN DEFAULT true, -- Whether book is visible
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_books_grade ON books(grade);
CREATE INDEX IF NOT EXISTS idx_books_subject ON books(subject);
CREATE INDEX IF NOT EXISTS idx_books_active ON books(is_active);
CREATE INDEX IF NOT EXISTS idx_books_grade_subject ON books(grade, subject);

-- ═══════════════════════════════════════════════════════════════════════════
-- THEMES TABLE
-- Stores chapters/topics within books with full text content
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS themes (
    id SERIAL PRIMARY KEY,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    name_uz VARCHAR(500),           -- Theme name in Uzbek
    name_ru VARCHAR(500),           -- Theme name in Russian
    content_uz TEXT,                -- Full text content in Uzbek
    content_ru TEXT,                -- Full text content in Russian
    start_page INTEGER,             -- Starting page number
    end_page INTEGER,               -- Ending page number
    chapter_number VARCHAR(50),     -- Chapter/section number (e.g., "1.2", "Chapter 3")
    order_index INTEGER,            -- For sorting themes within a book
    keywords_uz TEXT[],             -- Search keywords in Uzbek
    keywords_ru TEXT[],             -- Search keywords in Russian
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for themes
CREATE INDEX IF NOT EXISTS idx_themes_book_id ON themes(book_id);
CREATE INDEX IF NOT EXISTS idx_themes_order ON themes(book_id, order_index);
CREATE INDEX IF NOT EXISTS idx_themes_active ON themes(is_active);

-- Full-text search indexes for theme names and content
CREATE INDEX IF NOT EXISTS idx_themes_name_uz_search ON themes USING GIN (to_tsvector('simple', COALESCE(name_uz, '')));
CREATE INDEX IF NOT EXISTS idx_themes_name_ru_search ON themes USING GIN (to_tsvector('russian', COALESCE(name_ru, '')));
CREATE INDEX IF NOT EXISTS idx_themes_content_uz_search ON themes USING GIN (to_tsvector('simple', COALESCE(content_uz, '')));
CREATE INDEX IF NOT EXISTS idx_themes_content_ru_search ON themes USING GIN (to_tsvector('russian', COALESCE(content_ru, '')));

-- ═══════════════════════════════════════════════════════════════════════════
-- RESOURCES TABLE
-- Educational resources linked to themes (videos, courses, articles)
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS resources (
    id SERIAL PRIMARY KEY,
    theme_id INTEGER NOT NULL REFERENCES themes(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    url VARCHAR(1000) NOT NULL,
    resource_type VARCHAR(50) NOT NULL, -- video, course, article, research
    language VARCHAR(10) NOT NULL,      -- uz, ru, en
    source VARCHAR(100),                -- youtube, khan_academy, bilim.uz, etc.
    description TEXT,
    thumbnail_url TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for resources
CREATE INDEX IF NOT EXISTS idx_resources_theme_id ON resources(theme_id);
CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(resource_type);
CREATE INDEX IF NOT EXISTS idx_resources_language ON resources(language);

-- ═══════════════════════════════════════════════════════════════════════════
-- USER ANALYTICS TABLE
-- Track user activity for insights
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS user_analytics (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,
    telegram_username VARCHAR(255),
    first_name VARCHAR(255),
    action_type VARCHAR(50) NOT NULL,  -- start, search, view_book, download, quiz, summary
    action_data JSONB,                  -- Additional action metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for user analytics
CREATE INDEX IF NOT EXISTS idx_user_analytics_user_id ON user_analytics(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_user_analytics_action ON user_analytics(action_type);
CREATE INDEX IF NOT EXISTS idx_user_analytics_created_at ON user_analytics(created_at);

-- ═══════════════════════════════════════════════════════════════════════════
-- SEARCH ANALYTICS TABLE
-- Track search queries for understanding user needs
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS search_analytics (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT,
    query TEXT NOT NULL,
    language_detected VARCHAR(10),       -- uz or ru
    results_count INTEGER DEFAULT 0,
    clicked_theme_id INTEGER REFERENCES themes(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for search analytics
CREATE INDEX IF NOT EXISTS idx_search_analytics_query ON search_analytics(query);
CREATE INDEX IF NOT EXISTS idx_search_analytics_created_at ON search_analytics(created_at);

-- ═══════════════════════════════════════════════════════════════════════════
-- DOWNLOAD TRACKING TABLE
-- Track book and theme downloads
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS downloads (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT,
    book_id INTEGER REFERENCES books(id),
    theme_id INTEGER REFERENCES themes(id),
    download_type VARCHAR(20) NOT NULL,  -- book_pdf, theme_pdf
    language VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for downloads
CREATE INDEX IF NOT EXISTS idx_downloads_book_id ON downloads(book_id);
CREATE INDEX IF NOT EXISTS idx_downloads_user ON downloads(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_downloads_created_at ON downloads(created_at);

-- ═══════════════════════════════════════════════════════════════════════════
-- FEEDBACK TABLE
-- Store user ratings and feedback
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,
    telegram_username VARCHAR(255),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for feedback
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback(rating);
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at);

-- ═══════════════════════════════════════════════════════════════════════════
-- SUPPORT MESSAGES TABLE
-- Store support conversations
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS support_messages (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,
    telegram_username VARCHAR(255),
    first_name VARCHAR(255),
    message TEXT NOT NULL,
    is_from_user BOOLEAN DEFAULT true,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for support messages
CREATE INDEX IF NOT EXISTS idx_support_user ON support_messages(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_support_unread ON support_messages(is_read) WHERE is_read = false;

-- ═══════════════════════════════════════════════════════════════════════════
-- HELPER FUNCTIONS
-- ═══════════════════════════════════════════════════════════════════════════

-- Function to update 'updated_at' timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for auto-updating timestamps
DROP TRIGGER IF EXISTS update_books_updated_at ON books;
CREATE TRIGGER update_books_updated_at
    BEFORE UPDATE ON books
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_themes_updated_at ON themes;
CREATE TRIGGER update_themes_updated_at
    BEFORE UPDATE ON themes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ═══════════════════════════════════════════════════════════════════════════
-- SEARCH FUNCTION WITH RANKING
-- Combined search in Uzbek and Russian with relevance scoring
-- ═══════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION search_themes(
    search_query TEXT,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE (
    theme_id INTEGER,
    book_id INTEGER,
    name_uz VARCHAR(500),
    name_ru VARCHAR(500),
    subject VARCHAR(100),
    grade INTEGER,
    book_title_uz VARCHAR(500),
    book_title_ru VARCHAR(500),
    start_page INTEGER,
    end_page INTEGER,
    relevance_score REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id AS theme_id,
        t.book_id,
        t.name_uz,
        t.name_ru,
        b.subject,
        b.grade,
        b.title_uz AS book_title_uz,
        b.title_ru AS book_title_ru,
        t.start_page,
        t.end_page,
        (
            -- Score for exact name match (highest priority)
            CASE 
                WHEN LOWER(t.name_uz) = LOWER(search_query) THEN 10000
                WHEN LOWER(t.name_ru) = LOWER(search_query) THEN 10000
                ELSE 0
            END +
            -- Score for name contains query
            CASE 
                WHEN LOWER(t.name_uz) LIKE '%' || LOWER(search_query) || '%' THEN 1000
                WHEN LOWER(t.name_ru) LIKE '%' || LOWER(search_query) || '%' THEN 1000
                ELSE 0
            END +
            -- Score for content contains query
            CASE 
                WHEN LOWER(COALESCE(t.content_uz, '')) LIKE '%' || LOWER(search_query) || '%' THEN 100
                WHEN LOWER(COALESCE(t.content_ru, '')) LIKE '%' || LOWER(search_query) || '%' THEN 100
                ELSE 0
            END
        )::REAL AS relevance_score
    FROM themes t
    JOIN books b ON t.book_id = b.id
    WHERE 
        t.is_active = true 
        AND b.is_active = true
        AND (
            LOWER(t.name_uz) LIKE '%' || LOWER(search_query) || '%'
            OR LOWER(t.name_ru) LIKE '%' || LOWER(search_query) || '%'
            OR LOWER(COALESCE(t.content_uz, '')) LIKE '%' || LOWER(search_query) || '%'
            OR LOWER(COALESCE(t.content_ru, '')) LIKE '%' || LOWER(search_query) || '%'
        )
    ORDER BY relevance_score DESC, t.id
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- ═══════════════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY (RLS)
-- Enable secure access for anon users (read-only for public data)
-- ═══════════════════════════════════════════════════════════════════════════

-- Enable RLS on all tables
ALTER TABLE books ENABLE ROW LEVEL SECURITY;
ALTER TABLE themes ENABLE ROW LEVEL SECURITY;
ALTER TABLE resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE downloads ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_messages ENABLE ROW LEVEL SECURITY;

-- Public read access for books (only active ones)
CREATE POLICY "Public can read active books" ON books
    FOR SELECT USING (is_active = true);

-- Public read access for themes (only active ones)
CREATE POLICY "Public can read active themes" ON themes
    FOR SELECT USING (is_active = true);

-- Public read access for resources (only active ones)
CREATE POLICY "Public can read active resources" ON resources
    FOR SELECT USING (is_active = true);

-- Allow inserts for analytics (service role only for full access)
CREATE POLICY "Allow insert user_analytics" ON user_analytics
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow insert search_analytics" ON search_analytics
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow insert downloads" ON downloads
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow insert feedback" ON feedback
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow insert support_messages" ON support_messages
    FOR INSERT WITH CHECK (true);

-- ═══════════════════════════════════════════════════════════════════════════
-- VIEWS FOR STATISTICS
-- ═══════════════════════════════════════════════════════════════════════════

-- View: Database statistics
CREATE OR REPLACE VIEW stats_overview AS
SELECT 
    (SELECT COUNT(*) FROM books WHERE is_active = true) AS total_books,
    (SELECT COUNT(*) FROM themes WHERE is_active = true) AS total_themes,
    (SELECT COUNT(*) FROM resources WHERE is_active = true) AS total_resources,
    (SELECT COUNT(DISTINCT telegram_user_id) FROM user_analytics) AS total_users,
    (SELECT COUNT(*) FROM downloads) AS total_downloads,
    (SELECT COUNT(*) FROM search_analytics) AS total_searches;

-- View: Popular search queries
CREATE OR REPLACE VIEW popular_searches AS
SELECT 
    query,
    COUNT(*) as search_count,
    AVG(results_count) as avg_results
FROM search_analytics
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY query
ORDER BY search_count DESC
LIMIT 50;

-- View: Books by grade
CREATE OR REPLACE VIEW books_by_grade AS
SELECT 
    grade,
    COUNT(*) as book_count,
    array_agg(DISTINCT subject) as subjects
FROM books
WHERE is_active = true
GROUP BY grade
ORDER BY grade;

-- ═══════════════════════════════════════════════════════════════════════════
-- SAMPLE DATA (RUN SEPARATELY IF NEEDED)
-- Uncomment and run this section to add sample data for testing
-- ═══════════════════════════════════════════════════════════════════════════

/*
-- Sample Books
INSERT INTO books (title_uz, title_ru, subject, grade) VALUES
('Matematika 5-sinf', 'Математика 5 класс', 'matematika', 5),
('Matematika 6-sinf', 'Математика 6 класс', 'matematika', 6),
('Matematika 7-sinf', 'Математика 7 класс', 'matematika', 7),
('Matematika 8-sinf', 'Математика 8 класс', 'matematika', 8),
('Fizika 7-sinf', 'Физика 7 класс', 'fizika', 7),
('Fizika 8-sinf', 'Физика 8 класс', 'fizika', 8),
('Kimyo 8-sinf', 'Химия 8 класс', 'kimyo', 8),
('Kimyo 9-sinf', 'Химия 9 класс', 'kimyo', 9),
('Biologiya 9-sinf', 'Биология 9 класс', 'biologiya', 9),
('Tarix 5-sinf', 'История 5 класс', 'tarix', 5);

-- Sample Themes for Matematika 5-sinf (book_id = 1)
INSERT INTO themes (book_id, name_uz, name_ru, content_uz, content_ru, start_page, end_page, order_index) VALUES
(1, 'Natural sonlar', 'Натуральные числа', 
 'Natural sonlar - bu 1, 2, 3, 4, 5, ... kabi sonlardir. Ular sanash uchun ishlatiladi. Natural sonlar cheksiz ko''p. Eng kichik natural son 1 ga teng. 0 natural son emas.',
 'Натуральные числа - это числа 1, 2, 3, 4, 5, ... Они используются для счёта. Натуральных чисел бесконечно много. Наименьшее натуральное число равно 1. 0 не является натуральным числом.',
 1, 20, 1),
(1, 'Kasrlar', 'Дроби',
 'Kasrlar - bu butun sonning bir qismini ifodalovchi sonlardir. Kasr surat va maxrajdan iborat. Surat - bu olingan qismlar soni, maxraj - butun necha qismga bo''lingani.',
 'Дроби - это числа, выражающие часть целого. Дробь состоит из числителя и знаменателя. Числитель - количество взятых частей, знаменатель - на сколько частей разделено целое.',
 21, 45, 2),
(1, 'Geometrik shakllar', 'Геометрические фигуры',
 'Geometrik shakllar - nuqta, to''g''ri chiziq, kesma, nur, burchak, uchburchak, to''rtburchak va boshqa shakllar. Har bir shaklning o''z xossalari bor.',
 'Геометрические фигуры - точка, прямая линия, отрезок, луч, угол, треугольник, четырёхугольник и другие фигуры. У каждой фигуры есть свои свойства.',
 46, 70, 3);

-- Sample Themes for Matematika 8-sinf (book_id = 4)
INSERT INTO themes (book_id, name_uz, name_ru, content_uz, content_ru, start_page, end_page, order_index) VALUES
(4, 'Pifagor teoremasi', 'Теорема Пифагора',
 'Pifagor teoremasi: To''g''ri burchakli uchburchakda gipotenuzaning kvadrati katetlar kvadratlari yig''indisiga teng. c² = a² + b². Bu teorema qadimgi yunon matematigi Pifagor tomonidan isbotlangan.',
 'Теорема Пифагора: В прямоугольном треугольнике квадрат гипотенузы равен сумме квадратов катетов. c² = a² + b². Эта теорема была доказана древнегреческим математиком Пифагором.',
 1, 15, 1),
(4, 'Kvadrat tenglamalar', 'Квадратные уравнения',
 'Kvadrat tenglama - ax² + bx + c = 0 ko''rinishidagi tenglama (a ≠ 0). Diskriminant D = b² - 4ac. Agar D > 0 bo''lsa, ikkita ildiz; D = 0 bo''lsa, bitta ildiz; D < 0 bo''lsa, haqiqiy ildiz yo''q.',
 'Квадратное уравнение - это уравнение вида ax² + bx + c = 0 (a ≠ 0). Дискриминант D = b² - 4ac. Если D > 0, два корня; D = 0, один корень; D < 0, действительных корней нет.',
 16, 35, 2),
(4, 'Trigonometriya asoslari', 'Основы тригонометрии',
 'Trigonometrik funksiyalar: sin, cos, tan (tg), cot (ctg). Asosiy tenglama: sin²α + cos²α = 1. To''g''ri burchakli uchburchakda: sin = qarshi katet / gipotenuz, cos = yonidagi katet / gipotenuz.',
 'Тригонометрические функции: sin, cos, tan (tg), cot (ctg). Основное тождество: sin²α + cos²α = 1. В прямоугольном треугольнике: sin = противолежащий катет / гипотенуза, cos = прилежащий катет / гипотенуза.',
 36, 55, 3);

-- Sample Themes for Fizika 7-sinf (book_id = 5)
INSERT INTO themes (book_id, name_uz, name_ru, content_uz, content_ru, start_page, end_page, order_index) VALUES
(5, 'Mexanika', 'Механика',
 'Mexanika - jismlarning harakati va muvozanatini o''rganadigan fizika bo''limi. Kinematika harakat parametrlarini, dinamika esa harakat sabablarini o''rganadi.',
 'Механика - раздел физики, изучающий движение и равновесие тел. Кинематика изучает параметры движения, а динамика - причины движения.',
 1, 25, 1),
(5, 'Nyuton qonunlari', 'Законы Ньютона',
 'Birinchi qonun: Jism tashqi kuch ta''sir qilmaganda o''z holatini saqlaydi. Ikkinchi qonun: F = ma. Uchinchi qonun: Har bir ta''sirga teng va qarama-qarshi ta''sir mavjud.',
 'Первый закон: Тело сохраняет своё состояние покоя или равномерного движения, если на него не действует внешняя сила. Второй закон: F = ma. Третий закон: Каждому действию есть равное и противоположное противодействие.',
 26, 50, 2),
(5, 'Energiya', 'Энергия',
 'Energiya - jismning ish bajarish qobiliyati. Kinetik energiya - harakat energiyasi: E = mv²/2. Potentsial energiya - holatga bog''liq energiya. Energiya saqlanish qonuni.',
 'Энергия - способность тела совершать работу. Кинетическая энергия - энергия движения: E = mv²/2. Потенциальная энергия - энергия, связанная с положением. Закон сохранения энергии.',
 51, 70, 3);

-- Sample Themes for Kimyo 8-sinf (book_id = 7)
INSERT INTO themes (book_id, name_uz, name_ru, content_uz, content_ru, start_page, end_page, order_index) VALUES
(7, 'Atom tuzilishi', 'Строение атома',
 'Atom yadro va elektronlardan iborat. Yadro protonlar va neytronlardan tashkil topgan. Elektronlar yadro atrofida aylanadi. Protonlar soni = atom raqami.',
 'Атом состоит из ядра и электронов. Ядро состоит из протонов и нейтронов. Электроны вращаются вокруг ядра. Число протонов = атомный номер.',
 1, 20, 1),
(7, 'Kimyoviy bog''lanish', 'Химическая связь',
 'Kimyoviy bog''lanish - atomlarni molekulada birlashtiruvchi kuch. Kovalent bog''lanish - elektronlarni ulashish. Ionli bog''lanish - elektronni berish va olish.',
 'Химическая связь - сила, объединяющая атомы в молекуле. Ковалентная связь - обобществление электронов. Ионная связь - отдача и принятие электрона.',
 21, 40, 2),
(7, 'Davriy jadval', 'Периодическая таблица',
 'Mendeleyev davriy jadvali - kimyoviy elementlarni atom raqami bo''yicha tartiblaydigan jadval. Davr - gorizontal qator. Guruh - vertikal ustun.',
 'Периодическая таблица Менделеева - таблица, систематизирующая химические элементы по атомному номеру. Период - горизонтальный ряд. Группа - вертикальный столбец.',
 41, 60, 3);

-- Sample Themes for Biologiya 9-sinf (book_id = 9)
INSERT INTO themes (book_id, name_uz, name_ru, content_uz, content_ru, start_page, end_page, order_index) VALUES
(9, 'Hujayra', 'Клетка',
 'Hujayra - tirik organizmning eng kichik tuzilish birligi. Hujayra membrana, sitoplazma va yadrodan iborat. Mitoxondriya - energiya ishlab chiqaradi. Ribosoma - oqsil sintezi.',
 'Клетка - наименьшая структурная единица живого организма. Клетка состоит из мембраны, цитоплазмы и ядра. Митохондрия - производит энергию. Рибосома - синтез белка.',
 1, 30, 1),
(9, 'Genetika', 'Генетика',
 'Genetika - irsiyat va o''zgaruvchanlikni o''rganadigan fan. DNK - genetik ma''lumot tashuvchisi. Gen - DNK ning belgilangan qismi. Mendel qonunlari.',
 'Генетика - наука о наследственности и изменчивости. ДНК - носитель генетической информации. Ген - определённый участок ДНК. Законы Менделя.',
 31, 60, 2),
(9, 'Evolyutsiya', 'Эволюция',
 'Evolyutsiya - tirik organizmlarning tarixiy rivojlanishi. Darvin tabiiy tanlanish nazariyasi. Moslashish - organizmning atrof-muhitga moslashuvi.',
 'Эволюция - историческое развитие живых организмов. Теория естественного отбора Дарвина. Адаптация - приспособление организма к окружающей среде.',
 61, 90, 3);
*/

-- ═══════════════════════════════════════════════════════════════════════════
-- SETUP COMPLETE!
-- ═══════════════════════════════════════════════════════════════════════════
-- Now:
-- 1. Go to Settings > API in your Supabase dashboard
-- 2. Copy the URL and anon key
-- 3. Add them to your .env file:
--    SUPABASE_URL=your-project-url
--    SUPABASE_KEY=your-anon-key
-- ═══════════════════════════════════════════════════════════════════════════
