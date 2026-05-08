"""
decoder.py – فك تشفير ملف حفظ FM26 Mobile (يدعم SQLite)
"""
import sqlite3
import pandas as pd
from io import BytesIO

def extract_players_from_save(file_bytes: bytes) -> pd.DataFrame:
    """
    يحاول فتح ملف الحفظ كقاعدة بيانات SQLite،
    ثم يستخرج بيانات اللاعبين ويعيدها كـ DataFrame.
    إذا فشل، يعيد DataFrame فارغ مع رسالة خطأ.
    """
    try:
        # فتح الملف كقاعدة بيانات في الذاكرة
        db_file = BytesIO(file_bytes)
        conn = sqlite3.connect(db_file)

        # التحقق من وجود جداول
        tables_query = "SELECT name FROM sqlite_master WHERE type='table';"
        tables = pd.read_sql_query(tables_query, conn)
        table_names = tables["name"].tolist()
        print("📋 الجداول الموجودة:", table_names)

        # البحث عن جدول اللاعبين (أسماء شائعة في إصدارات FM)
        player_table = None
        for candidate in ["player", "players", "people", "player_data", "staff"]:
            if candidate in table_names:
                player_table = candidate
                break

        if player_table is None:
            # إذا لم نجد جدولًا معروفًا، نعرض كل الجداول للمستخدم
            conn.close()
            error_msg = (
                f"⚠️ لم يتم العثور على جدول اللاعبين في الملف.\n"
                f"الجداول الموجودة: {table_names}\n\n"
                f"يرجى فتح الملف باستخدام DB Browser for SQLite "
                f"ومعرفة اسم جدول اللاعبين يدويًا، ثم تعديل الكود."
            )
            print(error_msg)
            return pd.DataFrame({"خطأ": [error_msg]})

        # قراءة بيانات اللاعبين
        df = pd.read_sql_query(f"SELECT * FROM {player_table}", conn)
        conn.close()

        if df.empty:
            return pd.DataFrame({"تنبيه": ["جدول اللاعبين موجود لكنه فارغ."]})

        print(f"✅ تم استخراج {len(df)} لاعبًا من جدول '{player_table}'.")
        return _normalize_columns(df)

    except sqlite3.DatabaseError:
        # الملف ليس قاعدة بيانات SQLite
        error_msg = (
            "❌ هذا الملف ليس قاعدة بيانات SQLite.\n"
            "قد يكون مضغوطًا أو مشفرًا أو بتنسيق غير معروف.\n"
            "حاول فتح الملف بأداة Hex Editor لفحص الترويسة."
        )
        print(error_msg)
        return pd.DataFrame({"خطأ": [error_msg]})
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
        return pd.DataFrame({"خطأ": [str(e)]})


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    يعيد تسمية الأعمدة الإنجليزية إلى العربية المطلوبة للتطبيق.
    يقبل فقط الأعمدة الموجودة فعلًا في قاعدة البيانات.
    """
    column_map = {
        # أسماء أعمدة شائعة في إصدارات FM
        "name": "الاسم",
        "first_name": "الاسم",
        "age": "العمر",
        "nationality": "الجنسية",
        "club": "النادي",
        "position": "المركز",
        "current_ability": "CA",
        "potential_ability": "PA",
        "value": "القيمة السوقية (€)",
        "wage": "الراتب (€/أسبوع)",
        "contract_expiry": "مدة العقد (سنوات)",
        "goals": "الأهداف",
        "assists": "التمريرات الحاسمة",
        "average_rating": "التقييم",
    }
    # إعادة تسمية الأعمدة الموجودة فقط
    rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
    df = df.rename(columns=rename_dict)
    return df
