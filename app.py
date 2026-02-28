import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import tempfile
import os

# --- 1. الإعدادات العامة ---
SETTINGS = {
    "MAIN_COLOR": "#2E7D32",
    "BG_COLOR": "#F0F2F6",
    "TITLE": "🗺️ Web-based GIS Application for Spatial and Attribute Join"
}

st.set_page_config(page_title=SETTINGS["TITLE"], layout="wide")

# --- 2. دوال معالجة البيانات ---
@st.cache_data
def load_data(uploaded_file):
    """تحميل البيانات والتعامل مع الملفات المرفوعة"""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # التعامل مع ZIP (Shapefile) أو GeoJSON
            if uploaded_file.name.endswith('.zip'):
                gdf = gpd.read_file(f"zip://{file_path}")
            else:
                gdf = gpd.read_file(file_path)
            
            # التأكد من نظام الإحداثيات للعرض على الخريطة
            if gdf.crs is None:
                gdf.set_crs(epsg=4326, inplace=True)
            return gdf.to_crs(epsg=4326)
    except Exception as e:
        st.error(f"خطأ في تحميل الملف {uploaded_file.name}: {e}")
        return None

def display_file_info(gdf, title):
    """عرض الخريطة والجدول لكل ملف (على نمط app6.py)"""
    st.subheader(title)
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.write("📄 أول 5 صفوف:")
        st.dataframe(gdf.head(), use_container_width=True)
    
    with col2:
        st.write("📍 معاينة سريعة:")
        m = folium.Map(location=[gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()], zoom_start=10)
        folium.GeoJson(gdf).add_to(m)
        st_folium(m, height=250, use_container_width=True, key=f"map_{title}")

# --- 3. واجهة المستخدم الرئيسية ---
st.title(SETTINGS["TITLE"])
st.markdown("قم برفع ملفاتك الجغرافية لإجراء عمليات الربط المكاني والوصفي بسهولة.")

# --- شريط التحكم (Sidebar) ---
st.sidebar.header("📁 الخطوة 1: رفع الملفات")
left_file = st.sidebar.file_uploader("رفع الملف الأساسي (Left) - ZIP", type=['zip'], key="left")
right_file = st.sidebar.file_uploader("رفع الملف الثانوي (Right) - JSON/GeoJSON", type=["json", 'geojson'], key="right")

# --- العرض الرئيسي للملفات ---
if left_file:
    gdf_left = load_data(left_file)
    if gdf_left is not None:
        display_file_info(gdf_left, "الملف الأساسي (Left)")

if right_file:
    gdf_right = load_data(right_file)
    if gdf_right is not None:
        display_file_info(gdf_right, "الملف الثانوي (Right)")

st.divider()

# --- عمليات الربط ---
if left_file and right_file:
    st.header("⚙️ الخطوة 2: إعدادات الربط")
    
    tab1, tab2 = st.tabs(["🔗 ربط مكاني (Spatial Join)", "📝 ربط وصفي (Attribute Join)"])
    
    with tab1:
        st.info("يتم الربط بناءً على التداخل الجغرافي بين الطبقتين.")
        predicate = st.selectbox("نوع العلاقة المكانية:", ["intersects", "contains", "within", "touches", "crosses"])
        if st.button("تنفيذ الربط المكاني"):
            with st.spinner("جاري المعالجة..."):
                result = gpd.sjoin(gdf_left, gdf_right, predicate=predicate, how="left")
                st.session_state['result_gdf'] = result
                st.success(f"تم الربط! عدد الأسطر الناتجة: {len(result)}")

    with tab2:
        st.info("يتم الربط بناءً على قيم الأعمدة المشتركة.")
        col_left = st.selectbox("حقل الربط من الملف الأساسي:", gdf_left.columns)
        col_right = st.selectbox("حقل الربط من الملف الثانوي:", gdf_right.columns)
        join_type = st.selectbox("نوع الربط:", ["left", "right", "inner", "outer"])
        
        if st.button("تنفيذ الربط الوصفي"):
            with st.spinner("جاري المعالجة..."):
                # نستخدم merge للربط الوصفي مع الحفاظ على الخصائص الجغرافية
                result = gdf_left.merge(gdf_right.drop(columns='geometry'), left_on=col_left, right_on=col_right, how=join_type)
                st.session_state['result_gdf'] = result
                st.success(f"تم الربط! عدد الأسطر الناتجة: {len(result)}")

# --- 4. عرض النتائج وتحميلها ---
if 'result_gdf' in st.session_state:
    res = st.session_state['result_gdf']
    st.divider()
    st.header("📊 النتيجة النهائية")
    
    if len(res) > 0:
        st.dataframe(res.head())
        
        # تحويل النتيجة لـ GeoJSON للتحميل
        geojson_data = res.to_json()
        st.download_button(
            label="📥 تحميل النتائج بصيغة GeoJSON",
            data=geojson_data,
            file_name="spatial_join_result.geojson",
            mime="application/json"
        )
    else:
        st.warning("⚠️ لا توجد نتائج مطابقة لعملية الربط المختارة.")

else:

    st.info("يرجى رفع الملفين من القائمة الجانبية للبدء.")
