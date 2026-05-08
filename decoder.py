"""
decoder.py – محاولة فك تشفير ملف حفظ FM26 Mobile واستخراج اللاعبين
يدعم وضع العرض التجريبي التلقائي عند فشل المعالجة
"""
import struct
import zlib
import lz4.block  # قد يكون مطلوباً حسب الصيغة
import pandas as pd
import re
import random
from io import BytesIO

def extract_players_from_save(file_bytes: bytes) -> pd.DataFrame:
    """
    تحاول قراءة الملف الثنائي وإرجاع DataFrame باللاعبين.
    إذا فشلت، تُنشئ بيانات وهمية للعرض التجريبي.
    """
    try:
        # 1. فحص الترويسة بحثاً عن ضغط zlib (Magic: 0x78 0x9C)
        if file_bytes[:2] == b'\x78\x9c':
            decompressed = zlib.decompress(file_bytes)
        else:
            # ربما LZ4 أو غير مضغوط – نجرب LZ4
            try:
                decompressed = lz4.block.decompress(file_bytes, uncompressed_size=len(file_bytes)*10)
            except:
                decompressed = file_bytes  # نحاول كملف خام

        # 2. البحث عن أسماء اللاعبين (نصوص مقروءة)
        # نمط: سلسلة أحرف إنجليزية بمسافات، طول بين 3 و 30
        names = re.findall(rb'[\x20-\x7E]{4,30}', decompressed)
        # قد نحتاج لتصفية سلاسل غير منطقية
        possible_names = []
        for n in names:
            try:
                name = n.decode('ascii').strip()
                if 2 < len(name) < 25 and not name.startswith(('/', '\\', '.')):
                    possible_names.append(name)
            except:
                pass
        if not possible_names:
            raise ValueError("لم يتم العثور على أسماء")

        # 3. محاولة بناء سجلات حول الأسماء (افتراض بنية ثابتة)
        # سنكتفي بإرجاع DataFrame أولي من الأسماء التي وجدناها
        # مع حقول وهمية لتوضيح الفكرة (يمكن تعديل الإزاحات لاحقاً)
        players = []
        gen = random.Random(42)
        for i, name in enumerate(possible_names[:200]):  # حد أقصى 200 لاعب
            players.append({
                "الاسم": name,
                "العمر": gen.randint(16, 38),
                "الجنسية": gen.choice(["مصر","إنجلترا","البرازيل","فرنسا","إسبانيا"]),
                "النادي": gen.choice(["الأهلي","برشلونة","مانشستر سيتي","بايرن ميونخ","يوفنتوس"]),
                "المركز": gen.choice(["GK","DC","DL","DR","MC","AMC","AML","ST"]),
                "CA": gen.randint(40, 195),
                "PA": gen.randint(50, 200),
                "القيمة السوقية (€)": f"{gen.randint(0,120)}M",
                "الراتب (€/أسبوع)": f"{gen.randint(1,350):,}",
                "مدة العقد (سنوات)": gen.randint(1,5),
                "الأهداف": gen.randint(0,30),
                "التمريرات الحاسمة": gen.randint(0,20),
                "التقييم": round(gen.uniform(6.0,8.9),1)
            })
        df = pd.DataFrame(players)
        df["CA"] = df["CA"].astype(int)
        df["PA"] = df["PA"].astype(int)
        return df
    except Exception as e:
        # العودة لوضع التجريبي
        print(f"فشل فك التشفير: {e}")
        return _generate_demo_data()

def _generate_demo_data(num=150) -> pd.DataFrame:
    """ينشئ بيانات وهمية لاستعراض التطبيق"""
    random.seed(99)
    data = []
    first_names = ["محمد","أحمد","عمر","علي","كريم","حسن","يوسف","إبراهيم","طارق","محمود"]
    last_names = ["صلاح","النني","تريزيجيه","حجازي","فتحي","عاشور","زيزو","عبد المنعم"]
    clubs = ["الأهلي","بيراميدز","الزمالك","ليفربول","ريال مدريد","برشلونة","بايرن ميونخ","مانشستر سيتي"]
    nats = ["مصر","إنجلترا","إسبانيا","ألمانيا","فرنسا","البرازيل","الأرجنتين"]
    pos_list = ["GK","DC","DL","DR","DMC","MC","AMC","AML","AMR","ST"]
    for i in range(num):
        ca = random.randint(40,195)
        pa = max(ca, random.randint(ca,200))
        market = random.uniform(0.1, 150)
        salary = random.randint(3000, 400000)
        contract = random.randint(1,5)
        data.append({
            "الاسم": f"{random.choice(first_names)} {random.choice(last_names)}",
            "العمر": random.randint(16,38),
            "الجنسية": random.choice(nats),
            "النادي": random.choice(clubs),
            "المركز": random.choice(pos_list),
            "CA": ca,
            "PA": pa,
            "القيمة السوقية (€)": f"{market:.1f}M",
            "الراتب (€/أسبوع)": f"{salary:,}",
            "مدة العقد (سنوات)": contract,
            "الأهداف": random.randint(0,30),
            "التمريرات الحاسمة": random.randint(0,20),
            "التقييم": round(random.uniform(6.0,8.9),1)
        })
    return pd.DataFrame(data)
