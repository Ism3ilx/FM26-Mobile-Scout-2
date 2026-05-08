"""
تطبيق كشاف FM26 Mobile التفاعلي - واجهة المستخدم
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

# -------------------------- إعداد الصفحة --------------------------
st.set_page_config(
    page_title="FM26 Mobile Scout",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------- دوال مساعدة --------------------------
def load_data(uploaded_file, use_demo):
    """
    تحميل البيانات من الملف المرفوع أو استخدام البيانات التجريبية.
    إذا كان الملف من نوع CSV أو Excel يتم قراءته مباشرة،
    وإذا كان ملف حفظ (.dat/.fms/.sav) يحاول فك تشفيره.
    إذا فشل الاستخراج أو كانت الأعمدة الأساسية مفقودة،
    يتم استخدام البيانات التجريبية تلقائياً مع إشعار.
    """
    # البيانات التجريبية المباشرة
    if use_demo:
        from decoder import _generate_demo_data
        return _generate_demo_data()

    if uploaded_file is not None:
        name = uploaded_file.name.lower()

        # CSV أو Excel مباشر
        if name.endswith(".csv"):
            return pd.read_csv(uploaded_file)
        elif name.endswith(".xlsx"):
            return pd.read_excel(uploaded_file)

        # ملف حفظ FM Mobile
        elif name.endswith((".dat", ".fms", ".sav")):
            from decoder import extract_players_from_save

            df = extract_players_from_save(uploaded_file.read())

            # الأعمدة الأساسية التي يحتاجها التطبيق
            essential_cols = [
                "الاسم", "العمر", "الجنسية", "النادي", "المركز",
                "CA", "PA", "القيمة السوقية (€)", "الراتب (€/أسبوع)",
                "مدة العقد (سنوات)", "الأهداف", "التمريرات الحاسمة", "التقييم",
            ]

            missing = [col for col in essential_cols if col not in df.columns]
            if missing:
                st.warning(
                    f"⚠️ تحليل الملف لم يُنتج الأعمدة المطلوبة: {', '.join(missing)}.\n"
                    f"يتم الآن استخدام بيانات تجريبية للعرض."
                )
                from decoder import _generate_demo_data
                return _generate_demo_data()

            return df

    # لا ملف مرفوع ولم يُطلب الوضع التجريبي
    return None


def filter_dataframe(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """تطبيق الفلاتر على DataFrame"""
    filtered = df.copy()

    # بحث نصي بالاسم
    if filters.get("search"):
        mask = filtered["الاسم"].str.contains(filters["search"], case=False, na=False)
        filtered = filtered[mask]

    # نطاق العمر
    if filters.get("age_range"):
        lo, hi = filters["age_range"]
        filtered = filtered[(filtered["العمر"] >= lo) & (filtered["العمر"] <= hi)]

    # نطاق CA
    if filters.get("ca_range"):
        lo, hi = filters["ca_range"]
        filtered = filtered[(filtered["CA"] >= lo) & (filtered["CA"] <= hi)]

    # نطاق PA
    if filters.get("pa_range"):
        lo, hi = filters["pa_range"]
        filtered = filtered[(filtered["PA"] >= lo) & (filtered["PA"] <= hi)]

    # جنسيات محددة
    if filters.get("nationalities"):
        filtered = filtered[filtered["الجنسية"].isin(filters["nationalities"])]

    # أندية محددة
    if filters.get("clubs"):
        filtered = filtered[filtered["النادي"].isin(filters["clubs"])]

    # مراكز محددة
    if filters.get("positions"):
        filtered = filtered[filtered["المركز"].isin(filters["positions"])]

    return filtered


# -------------------------- التطبيق الرئيسي --------------------------
def main():
    st.title("⚽ كشاف FM26 Mobile التفاعلي")
    st.markdown(
        "ارفع ملف الحفظ (`.dat`, `.fms`, `.sav`) أو ملف CSV/XLSX "
        "مُصدَّر من اللعبة، أو استخدم الوضع التجريبي."
    )

    # رفع الملف
    uploaded_file = st.file_uploader(
        "📂 اختر الملف",
        type=["csv", "xlsx", "dat", "fms", "sav"],
        help="ملف حفظ FM26 Mobile أو ملف CSV/Excel مُصدَّر",
    )
    use_demo = st.checkbox(
        "🔮 استخدام بيانات تجريبية للعرض",
        value=not uploaded_file,
        help="عند عدم وجود ملف، يتم عرض بيانات وهمية لتجربة الميزات.",
    )

    # تحميل البيانات
    df = load_data(uploaded_file, use_demo)

    if df is None or df.empty:
        st.info("ℹ️ من فضلك ارفع ملفًا أو فعّل خيار البيانات التجريبية.")
        st.stop()

    st.success(f"✅ تم تحميل {len(df)} لاعباً.")

    # -------------------------- الفلاتر الجانبية --------------------------
    with st.sidebar:
        st.header("🔎 خيارات التصفية")
        search = st.text_input("بحث بالاسم", "")

        # نطاق العمر
        age_min_val = int(df["العمر"].min())
        age_max_val = int(df["العمر"].max())
        age_range = st.slider(
            "العمر", age_min_val, age_max_val, (age_min_val, age_max_val)
        )

        # نطاق CA
        ca_min_val = int(df["CA"].min())
        ca_max_val = int(df["CA"].max())
        ca_range = st.slider("القدرة الحالية (CA)", ca_min_val, ca_max_val, (ca_min_val, ca_max_val))

        # نطاق PA
        pa_min_val = int(df["PA"].min())
        pa_max_val = int(df["PA"].max())
        pa_range = st.slider("القدرة الكامنة (PA)", pa_min_val, pa_max_val, (pa_min_val, pa_max_val))

        # الجنسيات
        all_nationalities = sorted(df["الجنسية"].dropna().unique())
        selected_nats = st.multiselect("الجنسية", all_nationalities, default=[])

        # الأندية
        all_clubs = sorted(df["النادي"].dropna().unique())
        selected_clubs = st.multiselect("النادي", all_clubs, default=[])

        # المراكز
        all_positions = sorted(df["المركز"].dropna().unique())
        selected_positions = st.multiselect("المركز", all_positions, default=[])

    filters = {
        "search": search,
        "age_range": age_range,
        "ca_range": ca_range,
        "pa_range": pa_range,
        "nationalities": selected_nats,
        "clubs": selected_clubs,
        "positions": selected_positions,
    }

    filtered_df = filter_dataframe(df, filters)

    # -------------------------- التبويبات --------------------------
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📋 قائمة اللاعبين", "🪪 بطاقة لاعب", "🆚 مقارنة لاعبين", "📊 تقارير"]
    )

    # ---- التبويب 1: قائمة اللاعبين ----
    with tab1:
        st.subheader("قائمة اللاعبين المُصفّاة")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("عدد اللاعبين", len(filtered_df))
        with col2:
            # تصدير إلى Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                filtered_df.to_excel(writer, index=False)
            st.download_button(
                label="📥 تصدير إلى Excel",
                data=output.getvalue(),
                file_name="fm26_players.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.dataframe(
            filtered_df,
            column_config={
                "CA": st.column_config.ProgressColumn(
                    "CA", min_value=0, max_value=200, format="%d"
                ),
                "PA": st.column_config.ProgressColumn(
                    "PA", min_value=0, max_value=200, format="%d"
                ),
            },
            hide_index=True,
            use_container_width=True,
            height=600,
        )

    # ---- التبويب 2: بطاقة لاعب ----
    with tab2:
        st.subheader("بطاقة اللاعب التفصيلية")
        player_names = filtered_df["الاسم"].unique()
        if len(player_names) == 0:
            st.warning("لا يوجد لاعبون مطابقون للفلاتر الحالية.")
        else:
            selected_player = st.selectbox("اختر لاعباً", player_names)
            if selected_player:
                player = filtered_df[filtered_df["الاسم"] == selected_player].iloc[0]
                cols = st.columns(3)
                with cols[0]:
                    st.metric("الاسم", player["الاسم"])
                    st.metric("العمر", player["العمر"])
                    st.metric("الجنسية", player["الجنسية"])
                with cols[1]:
                    st.metric("النادي", player["النادي"])
                    st.metric("المركز", player["المركز"])
                    st.metric("القيمة السوقية", player.get("القيمة السوقية (€)", ""))
                with cols[2]:
                    st.metric("CA", player["CA"])
                    st.metric("PA", player["PA"])
                    st.metric("الراتب (أسبوعي)", player.get("الراتب (€/أسبوع)", ""))

                st.divider()
                subcols = st.columns(4)
                subcols[0].metric("الأهداف", player.get("الأهداف", 0))
                subcols[1].metric("التمريرات الحاسمة", player.get("التمريرات الحاسمة", 0))
                subcols[2].metric("التقييم", player.get("التقييم", ""))
                subcols[3].metric("مدة العقد (سنوات)", player.get("مدة العقد (سنوات)", ""))

    # ---- التبويب 3: مقارنة لاعبين ----
    with tab3:
        st.subheader("مقارنة لاعبين")
        if len(filtered_df) < 2:
            st.warning("تحتاج إلى لاعبين على الأقل للمقارنة.")
        else:
            col_left, col_right = st.columns(2)
            with col_left:
                player1 = st.selectbox("اللاعب الأول", filtered_df["الاسم"].unique(), key="p1")
            with col_right:
                player2 = st.selectbox("اللاعب الثاني", filtered_df["الاسم"].unique(), key="p2")

            if player1 and player2:
                p1 = filtered_df[filtered_df["الاسم"] == player1].iloc[0]
                p2 = filtered_df[filtered_df["الاسم"] == player2].iloc[0]

                comp_data = {
                    "السمة": ["CA", "PA", "العمر", "الأهداف", "التمريرات الحاسمة", "التقييم"],
                    player1: [
                        p1["CA"], p1["PA"], p1["العمر"],
                        p1.get("الأهداف", 0), p1.get("التمريرات الحاسمة", 0), p1.get("التقييم", ""),
                    ],
                    player2: [
                        p2["CA"], p2["PA"], p2["العمر"],
                        p2.get("الأهداف", 0), p2.get("التمريرات الحاسمة", 0), p2.get("التقييم", ""),
                    ],
                }
                comp_df = pd.DataFrame(comp_data)
                st.dataframe(comp_df, hide_index=True, use_container_width=True)

    # ---- التبويب 4: تقارير ورسوم بيانية ----
    with tab4:
        st.subheader("تقارير وإحصائيات")
        if filtered_df.empty:
            st.info("لا توجد بيانات كافية لعرض التقارير.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                # أفضل 10 لاعبين CA
                top_ca = filtered_df.nlargest(10, "CA")[["الاسم", "CA", "النادي"]]
                fig1 = px.bar(
                    top_ca, x="CA", y="الاسم", orientation='h',
                    title="أفضل 10 لاعبين حسب CA", color="CA",
                )
                st.plotly_chart(fig1, use_container_width=True)

            with col2:
                # توزيع المراكز
                pos_counts = filtered_df["المركز"].value_counts().reset_index()
                pos_counts.columns = ["المركز", "العدد"]
                fig2 = px.pie(
                    pos_counts, names="المركز", values="العدد",
                    title="توزيع المراكز",
                )
                st.plotly_chart(fig2, use_container_width=True)

            # توزيع الأعمار
            fig3 = px.histogram(
                filtered_df, x="العمر", nbins=20,
                title="التوزيع العمري للاعبين",
            )
            st.plotly_chart(fig3, use_container_width=True)


if __name__ == "__main__":
    main()
