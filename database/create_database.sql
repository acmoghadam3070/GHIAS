-- =====================================================================
-- سامانه GHIAS
-- ارزیابی هوشمند حفاظت فیزیکی بیمارستان
-- اسکیمای نسخه ۲ پایگاه داده
-- =====================================================================
-- این فایل، ساختار کامل پایگاه داده را می‌سازد.
-- اجرای این فایل کاملاً بی‌خطر است و اگر جدولی از قبل ساخته شده باشد،
-- دوباره ساخته نمی‌شود.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- =====================================================================
-- جدول انواع سازمان
-- مثال: بیمارستان، کارخانه، اداره. این جدول امکان توسعه سامانه به
-- سازمان‌های غیر از بیمارستان را در آینده فراهم می‌کند.
-- =====================================================================

CREATE TABLE IF NOT EXISTS facility_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_key TEXT UNIQUE NOT NULL,
    type_name TEXT NOT NULL,
    description TEXT,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);


-- =====================================================================
-- جدول واحدهای تحت ارزیابی (بیمارستان، کارخانه، اداره و غیره)
-- =====================================================================

CREATE TABLE IF NOT EXISTS facilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_type_id INTEGER NOT NULL,
    facility_code TEXT UNIQUE,
    facility_name TEXT NOT NULL,
    hospital_type TEXT,
    ownership TEXT,
    province TEXT,
    city TEXT,
    address TEXT,
    postal_code TEXT,
    phone TEXT,
    email TEXT,
    manager_name TEXT,
    security_manager TEXT,
    beds INTEGER,
    area_m2 REAL,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (facility_type_id)
        REFERENCES facility_types(id)
        ON DELETE RESTRICT
);


-- =====================================================================
-- جدول ارزیابان
-- افرادی که ارزیابی میدانی را انجام می‌دهند.
-- =====================================================================

CREATE TABLE IF NOT EXISTS inspectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    organization TEXT,
    position TEXT,
    phone TEXT,
    email TEXT,
    certificate_number TEXT,
    national_code TEXT,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);


-- =====================================================================
-- جدول حوزه‌های ارزیابی
-- مثال: کنترل دسترسی، دوربین مداربسته، نگهبانی و غیره.
-- =====================================================================

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_type_id INTEGER NOT NULL,
    category_key TEXT UNIQUE NOT NULL,
    category_name TEXT NOT NULL,
    description TEXT,
    display_order INTEGER DEFAULT 0,
    default_weight INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,

    FOREIGN KEY (facility_type_id)
        REFERENCES facility_types(id)
        ON DELETE RESTRICT
);


-- =====================================================================
-- جدول بانک سؤالات
-- بانک اصلی و مرکزی تمام سؤالات ارزیابی.
-- =====================================================================

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    question_code TEXT UNIQUE NOT NULL,
    question_text TEXT NOT NULL,
    answer_type TEXT NOT NULL DEFAULT 'yes_no',
    weight INTEGER NOT NULL DEFAULT 1,
    is_critical INTEGER DEFAULT 0,
    standard_reference TEXT,
    recommendation TEXT,
    evaluator_guide TEXT,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (category_id)
        REFERENCES categories(id)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_question_category
ON questions(category_id);


-- =====================================================================
-- جدول بازدیدها (جلسات ارزیابی)
-- هر بار که یک ارزیاب به یک بیمارستان می‌رود، یک رکورد بازدید ساخته می‌شود.
-- =====================================================================

CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id INTEGER NOT NULL,
    inspector_id INTEGER NOT NULL,
    visit_date DATE NOT NULL,
    visit_start_time TIME,
    visit_end_time TIME,
    status TEXT NOT NULL DEFAULT 'IN_PROGRESS',
    overall_score REAL,
    overall_risk_level TEXT,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME,

    FOREIGN KEY (facility_id)
        REFERENCES facilities(id)
        ON DELETE CASCADE,

    FOREIGN KEY (inspector_id)
        REFERENCES inspectors(id)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_visit_facility
ON visits(facility_id);

CREATE INDEX IF NOT EXISTS idx_visit_inspector
ON visits(inspector_id);


-- =====================================================================
-- جدول پاسخ‌ها
-- پاسخ ارزیاب به هر سؤال، در هر بازدید، در این جدول ذخیره می‌شود.
-- این جدول قلب موتور امتیازدهی است.
-- =====================================================================

CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    answer_value TEXT,
    score REAL,
    is_deficiency INTEGER DEFAULT 0,
    comment TEXT,
    answered_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (visit_id)
        REFERENCES visits(id)
        ON DELETE CASCADE,

    FOREIGN KEY (question_id)
        REFERENCES questions(id)
        ON DELETE RESTRICT,

    UNIQUE (visit_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_answer_visit
ON answers(visit_id);

CREATE INDEX IF NOT EXISTS idx_answer_question
ON answers(question_id);


-- =====================================================================
-- جدول تصاویر
-- عکس‌هایی که ارزیاب حین بازدید، به عنوان مستند برای یک پاسخ ثبت می‌کند.
-- =====================================================================

CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    answer_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    caption TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (answer_id)
        REFERENCES answers(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_photo_answer
ON photos(answer_id);


-- =====================================================================
-- جدول اقدامات اصلاحی پیشنهادی
-- برای هر پاسخ ناقص، یک یا چند اقدام اصلاحی با اولویت مشخص ثبت می‌شود.
-- =====================================================================

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    answer_id INTEGER NOT NULL,
    recommendation_text TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'MEDIUM',
    status TEXT NOT NULL DEFAULT 'OPEN',
    due_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (answer_id)
        REFERENCES answers(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_recommendation_answer
ON recommendations(answer_id);


-- =====================================================================
-- جدول گزارش‌های تولید شده
-- هر فایل خروجی (Word یا PDF) که برای یک بازدید ساخته می‌شود.
-- =====================================================================

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_id INTEGER NOT NULL,
    report_format TEXT NOT NULL,
    file_path TEXT NOT NULL,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (visit_id)
        REFERENCES visits(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_report_visit
ON reports(visit_id);


-- =====================================================================
-- داده اولیه: نوع سازمان پیش‌فرض (بیمارستان)
-- =====================================================================

INSERT OR IGNORE INTO facility_types (type_key, type_name) VALUES
    ('hospital', 'بیمارستان');


-- =====================================================================
-- داده اولیه: نُه حوزه ارزیابی بیمارستان طبق ساختار پروژه
-- اگر این رکوردها از قبل وجود داشته باشند، دوباره درج نمی‌شوند.
-- =====================================================================

INSERT OR IGNORE INTO categories (facility_type_id, category_key, category_name, display_order)
SELECT ft.id, c.category_key, c.category_name, c.display_order
FROM facility_types ft
JOIN (
    SELECT 'access_control' AS category_key, 'کنترل دسترسی' AS category_name, 1 AS display_order
    UNION ALL SELECT 'cctv', 'دوربین‌های مداربسته (CCTV)', 2
    UNION ALL SELECT 'guards', 'نگهبانی و گشت‌زنی', 3
    UNION ALL SELECT 'perimeter', 'حصار و محیط پیرامونی', 4
    UNION ALL SELECT 'lighting', 'روشنایی امنیتی', 5
    UNION ALL SELECT 'fire', 'آتش‌نشانی و اطفاء حریق', 6
    UNION ALL SELECT 'crisis', 'مدیریت بحران', 7
    UNION ALL SELECT 'hics', 'سیستم فرماندهی حوادث بیمارستانی', 8
    UNION ALL SELECT 'server_room', 'اتاق سرور و فناوری اطلاعات', 9
) AS c
WHERE ft.type_key = 'hospital';
