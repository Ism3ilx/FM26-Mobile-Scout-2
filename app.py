"""
app.py – واجهة المستخدم لتطبيق كشاف FM26 Mobile
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from decoder import extract_players_from_save
from io import BytesIO
import tempfile

st.set_page_config(
    page_title="FM26 Mobile Scout",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── تحميل البيانات ───
@st.cache_data(show_spinner=False)
def load_data(uploaded_file, use_demo: bool = False):
    if use_demo or not uploaded_file:
        # توليد بيانات تجريبية للعرض
        from decoder import _generate_demo_data
        return _generate_demo_data()
    else:
        file_bytes = uploaded_file.read()
        return extract_players_from_save(file_bytes)

# ─── تصفية البيانات ───
def filter_dataframe(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    filtered = df.copy()
    if filters["search"]:
        mask = filtered["الاسم"].str.contains(filters["search"], case=False, na=False)
        filtered = filtered[mask]
    if filters["age_range"]:
        mi, ma = filters["age_range"]
        filtered = filtered[(filtered["العمر"] >= mi) & (filtered["العمر"] <= ma)]
    if filters["ca_range"]:
        mi, ma = filters["ca_range"]
        filtered = filtered[(filtered["CA"] >= mi) & (filtered["CA"] <= ma)]
    if filters["pa_range"]:
        mi, ma = filters["pa_range"]
        filtered = filtered[(filtered["PA"] >= mi) & (filtered["PA"] <= ma)]
    if filters["nationalities"]:
        filtered = filtered[filtered["الجنسية"].isin(filters["nationalities"])]
    if filters["clubs"]:
        filtered = filtered[filtered["النادي"].isin(filters["clubs"])]
    if filters["positions"]:
        filtered = filtered[filtered["المركز"].isin(filters["positions"])]
    return filtered

# ─── تحويل القيمة النقدية إلى رقم ───
def parse_market_value(val):
    if isinstance(val, str):
        return float(val.replace("M","").replace(",",""))
    return val

# ─── الواجهة الرئيسية ───
def main():
    st.title("⚽ كشاف FM26 Mobile التفاعلي")
    st.markdown("ارفع ملف الحفظ (`.dat`, `.sav`) لاستعراض وتحليل اللاعبين.")

    # رفع الملف
    uploaded_file = st.file_uploader("اختر ملف الحفظ", type=["dat","sav","bin","fms"], help="ملف save.dat الخاص بلعبة FM26 Mobile")
    use_demo = st.checkbox("🔮 استخدام بيانات تجريبية للعرض", value=not uploaded_file)

    if uploaded_file or use_demo:
        with st.spinner("جاري فك التشفير واستخراج البيانات..."):
            df = load_data(uploaded_file, use_demo)
            st.session_state["df"] = df
        st.success(f"تم تحميل {len(df)} لاعباً.")
    else:
        st.info("من فضلك ارفع ملف الحفظ أو فعّل البيانات التجريبية.")
        st.stop()

    df = st.session_state["df"]

    # ─── القوائم الجانبية للفلاتر ───
    with st.sidebar:
        st.header("🔎 خيارات التصفية")
        search = st.text_input("بحث بالاسم")
        # مدى العمر
        age_min = int(df["العمر"].min())
        age_max = int(df["العمر"].max())
        age_range = st.slider("العمر", age_min, age_max, (age_min, age_max))
        # CA
        ca_min = int(df["CA"].min())
        ca_max = int(df["CA"].max())
        ca_range = st.slider("القدرة الحالية (CA)", ca_min, ca_max, (ca_min, ca_max))
        # PA
        pa_min = int(df["PA"].min())
        pa_max = int(df["PA"].max())
        pa_range = st.slider("القدرة الكامنة (PA)", pa_min, pa_max, (pa_min, pa_max))
        # الجنسيات
        all_nats = sorted(df["الجنسية"].unique())
        selected_nats = st.multiselect("الجنسية", all_nats, default=[])
        # الأندية
        all_clubs = sorted(df["النادي"].unique())
        selected_clubs = st.multiselect("النادي", all_clubs, default=[])
        # المراكز
        all_pos = sorted(df["المركز"].unique())
        selected_pos = st.multiselect("المركز", all_pos, default=[])

    filters = {
        "search": search,
        "age_range": age_range,
        "ca_range": ca_range,
        "pa_range": pa_range,
        "nationalities": selected_nats,
        "clubs": selected_clubs,
        "positions": selected_pos
    }
    filtered_df = filter_dataframe(df, filters)

    # ─── تبويبات الصفحات ───
    tab1, tab2, tab3, tab4 = st.tabs(["📋 قائمة اللاعبين", "🪪 بطاقة لاعب", "🆚 مقارنة لاعبين", "📊 تقارير"])

    with tab1:
        st.subheader("قائمة اللاعبين المُصفّاة")
        col_count = st.columns(2)
        with col_count[0]:
            st.metric("عدد اللاعبين", len(filtered_df))
        with col_count[1]:
            # تصدير
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                filtered_df.to_excel(writer, index=False)
            st.download_button(
                label="📥 تصدير Excel",
                data=output.getvalue(),
                file_name="fm26_players.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        # عرض الجدول مع إمكانية الفرز
        st.dataframe(
            filtered_df,
            column_config={
                "الاسم": st.column_config.TextColumn("الاسم", width="medium"),
                "CA": st.column_config.ProgressColumn("CA", min_value=0, max_value=200, format="%d"),
                "PA": st.column_config.ProgressColumn("PA", min_value=0, max_value=200, format="%d"),
            },
            hide_index=True,
            use_container_width=True,
            height=600
        )

    with tab2:
        st.subheader("بطاقة اللاعب التفصيلية")
        player_name = st.selectbox("اختر لاعباً", filtered_df["الاسم"].unique())
        if player_name:
            player = filtered_df[filtered_df["الاسم"] == player_name].iloc[0]
            cols = st.columns(3)
            with cols[0]:
                st.metric("الاسم", player["الاسم"])
                st.metric("العمر", player["العمر"])
                st.metric("الجنسية", player["الجنسية"])
            with cols[1]:
                st.metric("النادي", player["النادي"])
                st.metric("المركز", player["المركز"])
                st.metric("القيمة السوقية", player["القيمة السوقية (€)"])
            with cols[2]:
                st.metric("CA", player["CA"])
                st.metric("PA", player["PA"])
                st.metric("الراتب (أسبوعي)", player["الراتب (€/أسبوع)"])
            st.divider()
            subcols = st.columns(4)
            with subcols[0]:
                st.metric("الأهداف", player["الأهداف"])
            with subcols[1]:
                st.metric("التمريرات الحاسمة", player["التمريرات الحاسمة"])
            with subcols[2]:
                st.metric("التقييم", player["التقييم"])
            with subcols[3]:
                st.metric("مدة العقد", f"{player['مدة العقد (سنوات)']} سنة")
        else:
            st.warning("لا يوجد لاعب مطابق")

    with tab3:
        st.subheader("مقارنة لاعبين")
        col_left, col_right = st.columns(2)
        with col_left:
            player1 = st.selectbox("اللاعب الأول", filtered_df["الاسم"].unique(), key="p1")
        with col_right:
            player2 = st.selectbox("اللاعب الثاني", filtered_df["الاسم"].unique(), key="p2")
        if player1 and player2:
            p1 = filtered_df[filtered_df["الاسم"] == player1].iloc[0]
            p2 = filtered_df[filtered_df["الاسم"] == player2].iloc[0]
            # جدول مقارنة
            comp_df = pd.DataFrame({
                "السمة": ["CA","PA","العمر","القيمة السوقية","الأهداف","التقييم"],
                player1: [p1["CA"], p1["PA"], p1["العمر"], p1["القيمة السوقية (€)"], p1["الأهداف"], p1["التقييم"]],
                player2: [p2["CA"], p2["PA"], p2["العمر"], p2["القيمة السوقية (€)"], p2["الأهداف"], p2["التقييم"]]
            })
            # إضافة الفرق
            comp_df["الفرق"] = comp_df[player1].astype(str) + " vs " + comp_df[player2].astype(str)
            st.dataframe(comp_df, hide_index=True, use_container_width=True)

    with tab4:
        st.subheader("تقارير وإحصائيات")
        if not filtered_df.empty:
            col1, col2 = st.columns(2)
            with col1:
                # أفضل 10 بـ CA
                top_ca = filtered_df.nlargest(10, "CA")[["الاسم","CA","النادي"]]
                fig1 = px.bar(top_ca, x="CA", y="الاسم", orientation='h', title="أفضل 10 لاعبين حسب CA", color="CA")
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                # توزيع المراكز
                pos_count = filtered_df["المركز"].value_counts().reset_index()
                pos_count.columns = ["المركز", "العدد"]
                fig2 = px.pie(pos_count, names="المركز", values="العدد", title="توزيع المراكز")
                st.plotly_chart(fig2, use_container_width=True)
            # توزيع الأعمار
            fig3 = px.histogram(filtered_df, x="العمر", nbins=20, title="التوزيع العمري للاعبين")
            st.plotly_chart(fig3, use_container_width=True)

if __name__ == "__main__":
    main()
