"""
decoder.py – فك تشفير ملف حفظ FM26 Mobile
يستخدم طريقة مسح الملف بايت بايت للبحث عن نصوص بطول مسبوق (Length-Prefixed)
ثم استخراج أسماء اللاعبين والإحصائيات القريبة.
"""
import struct
import pandas as pd

def extract_players_from_save(file_bytes: bytes) -> pd.DataFrame:
    """
    يمسح الملف بالكامل، يبحث عن نصوص بطول مسبوق،
    يحلل الأسماء المحتملة للاعبين ويستخرج العمر، CA، PA.
    """
    offset = 0
    players_raw = []
    excl = {s.lower() for s in [
        'stadium', 'league', 'cup', 'madrid', 'arena', 'park', 'centre',
        'club', 'city', 'united', 'town', 'county', 'division', 'group',
        'round', 'final', 'cup', 'trophy', 'international', 'super', 'first',
        'second', 'third', 'premier', 'championship', 'qualifying', 'team',
        'national', 'world', 'european', 'african', 'asian', 'cup', 'game',
        'match', 'season', 'transfer', 'window', 'manager', 'coach', 'format',
        'rules', 'system', 'data', 'version', 'staging', 'rel', 'fmm', 'fm',
    ]}

    while offset < len(file_bytes) - 4:
        try:
            # قراءة الطول
            str_len = struct.unpack_from('<I', file_bytes, offset)[0]
            if str_len < 3 or str_len > 100:  # طول غير منطقي لاسم
                offset += 1
                continue
            offset += 4
            if offset + str_len > len(file_bytes):
                break

            # قراءة النص
            raw = file_bytes[offset:offset+str_len]
            try:
                string_val = raw.decode('utf-8')
            except:
                offset += str_len
                continue
            offset += str_len

            # هل يشبه اسم لاعب؟
            words = string_val.strip().split()
            if not (1 <= len(words) <= 6):
                continue
            if not any(c.isalpha() for c in string_val):
                continue
            if any(w.lower() in excl for w in words):
                continue
            # يجب أن يحتوي على حروف كبيرة وصغيرة
            if not string_val[0].isupper():
                continue

            # ربما لاعب - اقرأ 50 بايت التالية للبحث عن أرقام
            stat_start = offset
            stat_end = min(offset + 50, len(file_bytes))
            stat_bytes = file_bytes[stat_start:stat_end]

            # استخراج كل القيم الصحيحة بين 1-200 (مرشحة لتكون CA/PA)
            candidates = []
            for i in range(0, len(stat_bytes)):
                val = stat_bytes[i]
                if 1 <= val <= 200:
                    # تحقق من أن البايت التالي أو السابق يساعد في كونه قيمة مفردة
                    if i+1 < len(stat_bytes) and stat_bytes[i+1] == 0:
                        candidates.append(val)
                    elif i-1 >= 0 and stat_bytes[i-1] == 0:
                        candidates.append(val)
                    else:
                        candidates.append(val)  # نقبله بصعوبة

            if len(candidates) < 2:
                continue

            ca = candidates[0] if 100 <= candidates[0] <= 200 else None
            pa = candidates[1] if 100 <= candidates[1] <= 200 else None

            # محاولة استخراج العمر من البايتات حول الـ CA/PA
            age = None
            for j in range(0, len(stat_bytes)):
                val = stat_bytes[j]
                if 15 <= val <= 45:
                    # تحقق من أن البايت التالي صفر غالباً (علامة على عمر منفرد)
                    if j+1 < len(stat_bytes) and stat_bytes[j+1] == 0:
                        age = val
                        break

            if ca is not None and pa is not None and age is not None:
                players_raw.append({
                    "الاسم": string_val.strip(),
                    "العمر": age,
                    "CA": ca,
                    "PA": pa,
                })
        except:
            offset += 1

    # إزالة التكرارات
    seen = set()
    unique = []
    for p in players_raw:
        key = (p["الاسم"], p["العمر"])
        if key not in seen:
            seen.add(key)
            unique.append(p)

    if not unique:
        return pd.DataFrame({"خطأ": ["لم يتم العثور على لاعبين بهذه الطريقة."]})

    df = pd.DataFrame(unique)
    # إضافة الأعمدة المفقودة لتجنب رسالة التحذير
    for col in ["الجنسية", "النادي", "المركز", "القيمة السوقية (€)",
                "الراتب (€/أسبوع)", "مدة العقد (سنوات)", "الأهداف", "التمريرات الحاسمة", "التقييم"]:
        if col not in df.columns:
            df[col] = ""
    return df
