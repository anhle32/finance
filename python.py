import streamlit as st
import pandas as pd
import numpy as np

# --- Cấu hình trang Streamlit ---
st.set_page_config(
    page_title="Hệ Thống Thẩm Định Năng Lực Tài Chính Doanh Nghiệp",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Dữ liệu chỉ tiêu cần phân tích (Theo sơ đồ bạn cung cấp) ---
# Đây là các dòng dữ liệu mà ứng dụng sẽ tìm và tính toán
FINANCIAL_ITEMS = [
    "TIỀN MẶT",
    "KHOẢN PHẢI THU",
    "HÀNG TỒN KHO",
    "TÀI SẢN NGẮN HẠN",
    "TÀI SẢN CỐ ĐỊNH",
    "TÀI SẢN DÀI HẠN",
    "TỔNG TÀI SẢN",
    "NỢ NGẮN HẠN",
    "NỢ DÀI HẠN",
    "NỢ PHẢI TRẢ",
    "VỐN CHỦ SỞ HỮU",
    "TỔNG NGUỒN VỐN" # Tổng Nguồn Vốn = Tổng Tài Sản
]

# --- Hàm xử lý chính ---

def process_financial_data(df: pd.DataFrame):
    """
    Chuẩn bị và tính toán các chỉ tiêu cần thiết từ DataFrame đầu vào.
    Giả định rằng DataFrame có một cột chứa tên chỉ tiêu (ví dụ: 'Chỉ tiêu')
    và hai cột chứa giá trị tài chính cho hai kỳ (ví dụ: 'Năm Trước', 'Năm Sau').
    """
    # 1. Đặt lại tên cột để chuẩn hóa việc xử lý
    df.columns = [col.upper().strip() for col in df.columns]
    
    # 2. Tìm cột chứa chỉ tiêu, năm trước, năm sau
    item_col = None
    year_cols = []
    
    # Heuristic: Tìm cột chỉ tiêu (cột đầu tiên thường là chỉ tiêu)
    if 'CHỈ TIÊU' in df.columns:
        item_col = 'CHỈ TIÊU'
    elif 'KHOẢN MỤC' in df.columns:
        item_col = 'KHOẢN MỤC'
    else:
        # Nếu không tìm thấy tên rõ ràng, dùng cột đầu tiên
        item_col = df.columns[0]
        
    # Heuristic: Tìm 2 cột giá trị (thường là 2 cột số cuối cùng)
    numeric_cols = df.select_dtypes(include=np.number).columns
    if len(numeric_cols) >= 2:
        year_cols = list(numeric_cols[-2:])
    else:
        st.error("Lỗi: Dữ liệu tải lên không đủ 2 cột chứa giá trị tài chính (Năm Trước, Năm Sau).")
        return None, None
        
    # Đặt tên chuẩn hóa
    df = df.rename(columns={year_cols[0]: 'NĂM TRƯỚC', year_cols[1]: 'NĂM SAU', item_col: 'CHỈ TIÊU'})
    
    # 3. Lọc và chuẩn hóa các chỉ tiêu cần thiết
    # Chuẩn hóa tên chỉ tiêu để khớp với FINANCIAL_ITEMS (không phân biệt hoa thường)
    df['CHỈ TIÊU UPPER'] = df['CHỈ TIÊU'].astype(str).str.upper().str.strip()
    
    # Tạo DataFrame chuẩn hóa chỉ chứa các mục quan trọng
    filtered_df = pd.DataFrame(FINANCIAL_ITEMS, columns=['CHỈ TIÊU'])
    
    # Merge dữ liệu. Dùng apply để tìm chỉ tiêu khớp tốt nhất (đảm bảo tổng tài sản/nguồn vốn có)
    def find_value(item, df_source, year_col):
        match = df_source[df_source['CHỈ TIÊU UPPER'] == item]
        return match[year_col].iloc[0] if not match.empty else np.nan

    # Ánh xạ giá trị từ file Excel vào DataFrame chuẩn hóa
    filtered_df['NĂM TRƯỚC'] = filtered_df['CHỈ TIÊU'].apply(
        lambda x: find_value(x, df, 'NĂM TRƯỚC')
    )
    filtered_df['NĂM SAU'] = filtered_df['CHỈ TIÊU'].apply(
        lambda x: find_value(x, df, 'NĂM SAU')
    )
    
    # Xử lý Total Asset/Total Equity nếu chưa có
    try:
        # Nếu cột "TỔNG TÀI SẢN" không có, thử tính tổng Tài sản ngắn hạn + Tài sản dài hạn
        if filtered_df[filtered_df['CHỈ TIÊU'] == "TỔNG TÀI SẢN"]['NĂM TRƯỚC'].isnull().all():
            tsnh_index = filtered_df[filtered_df['CHỈ TIÊU'] == "TÀI SẢN NGẮN HẠN"].index
            tsdh_index = filtered_df[filtered_df['CHỈ TIÊU'] == "TÀI SẢN DÀI HẠN"].index
            if not tsnh_index.empty and not tsdh_index.empty:
                 filtered_df.loc[filtered_df['CHỈ TIÊU'] == "TỔNG TÀI SẢN", 'NĂM TRƯỚC'] = filtered_df.loc[tsnh_index[0], 'NĂM TRƯỚC'] + filtered_df.loc[tsdh_index[0], 'NĂM TRƯỚC']
                 filtered_df.loc[filtered_df['CHỈ TIÊU'] == "TỔNG TÀI SẢN", 'NĂM SAU'] = filtered_df.loc[tsnh_index[0], 'NĂM SAU'] + filtered_df.loc[tsdh_index[0], 'NĂM SAU']

        # Đảm bảo TỔNG NGUỒN VỐN = TỔNG TÀI SẢN
        filtered_df.loc[filtered_df['CHỈ TIÊU'] == "TỔNG NGUỒN VỐN", 'NĂM TRƯỚC'] = filtered_df.loc[filtered_df['CHỈ TIÊU'] == "TỔNG TÀI SẢN", 'NĂM TRƯỚC'].values[0]
        filtered_df.loc[filtered_df['CHỈ TIÊU'] == "TỔNG NGUỒN VỐN", 'NĂM SAU'] = filtered_df.loc[filtered_df['CHỈ TIÊU'] == "TỔNG TÀI SẢN", 'NĂM SAU'].values[0]
        
    except Exception as e:
        st.warning(f"Không thể tính tự động Tổng Tài Sản/Tổng Nguồn Vốn. Vui lòng kiểm tra file đầu vào. Lỗi: {e}")
    
    # Loại bỏ các hàng bị thiếu (NaN) sau khi lọc
    filtered_df = filtered_df.dropna(subset=['NĂM TRƯỚC', 'NĂM SAU'], how='all').reset_index(drop=True)
    
    return filtered_df

def calculate_growth(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Tính toán Tăng trưởng theo công thức: (Năm Sau - Năm Trước) / Năm Trước
    """
    df = df_input.copy()
    
    # Công thức: (Năm Sau - Năm Trước) / Năm Trước
    df['TĂNG TRƯỞNG'] = (df['NĂM SAU'] - df['NĂM TRƯỚC']) / df['NĂM TRƯỚC']
    
    # Định dạng kết quả
    df_output = df[['CHỈ TIÊU', 'NĂM TRƯỚC', 'NĂM SAU', 'TĂNG TRƯỞNG']].copy()
    
    # Định dạng tiền tệ cho 2 năm
    currency_format = "{:,.0f}"
    df_output['NĂM TRƯỚC'] = df_output['NĂM TRƯỚC'].apply(lambda x: currency_format.format(x) if pd.notnull(x) else '-')
    df_output['NĂM SAU'] = df_output['NĂM SAU'].apply(lambda x: currency_format.format(x) if pd.notnull(x) else '-')
    
    # Định dạng phần trăm cho Tăng trưởng
    df_output['TĂNG TRƯỞNG'] = df_output['TĂNG TRƯỞNG'].apply(lambda x: f"{x:.2%}" if pd.notnull(x) and np.isfinite(x) else 'N/A')
    
    # Đổi tên cột để hiển thị đẹp hơn
    df_output.columns = ['CHỈ TIÊU', 'GIÁ TRỊ NĂM TRƯỚC', 'GIÁ TRỊ NĂM SAU', 'TĂNG TRƯỞNG (%)']
    
    return df_output

def calculate_weight(df_input: pd.DataFrame) -> pd.DataFrame:
    """
    Tính toán Tỷ trọng.
    - Tài sản: Chỉ tiêu / Tổng Tài Sản
    - Nguồn vốn: Chỉ tiêu / Tổng Nguồn Vốn
    """
    df = df_input.copy()
    
    # Lấy giá trị Tổng Tài Sản và Tổng Nguồn Vốn (giả định chúng khớp nhau)
    total_asset_prev = df[df['CHỈ TIÊU'] == "TỔNG TÀI SẢN"]['NĂM TRƯỚC'].iloc[0] if "TỔNG TÀI SẢN" in df['CHỈ TIÊU'].values else np.nan
    total_asset_current = df[df['CHỈ TIÊU'] == "TỔNG TÀI SẢN"]['NĂM SAU'].iloc[0] if "TỔNG TÀI SẢN" in df['CHỈ TIÊU'].values else np.nan
    
    df['TỶ TRỌNG NĂM TRƯỚC'] = np.nan
    df['TỶ TRỌNG NĂM SAU'] = np.nan
    
    # Danh sách các chỉ tiêu thuộc Tài sản (chia cho Tổng Tài Sản)
    asset_items = [
        "TIỀN MẶT", "KHOẢN PHẢI THU", "HÀNG TỒN KHO", "TÀI SẢN NGẮN HẠN",
        "TÀI SẢN CỐ ĐỊNH", "TÀI SẢN DÀI HẠN", "TỔNG TÀI SẢN"
    ]
    
    for index, row in df.iterrows():
        item = row['CHỈ TIÊU']
        
        # Nếu là chỉ tiêu Tài sản
        if item in asset_items and pd.notnull(total_asset_prev) and total_asset_prev != 0:
            df.loc[index, 'TỶ TRỌNG NĂM TRƯỚC'] = row['NĂM TRƯỚC'] / total_asset_prev
        
        if item in asset_items and pd.notnull(total_asset_current) and total_asset_current != 0:
            df.loc[index, 'TỶ TRỌNG NĂM SAU'] = row['NĂM SAU'] / total_asset_current

        # Nếu là chỉ tiêu Nguồn vốn (chia cho Tổng Nguồn Vốn)
        # Vì Tổng Nguồn Vốn = Tổng Tài Sản, ta dùng cùng mẫu số
        equity_items = [
            "NỢ NGẮN HẠN", "NỢ DÀI HẠN", "NỢ PHẢI TRẢ", "VỐN CHỦ SỞ HỮU", "TỔNG NGUỒN VỐN"
        ]
        
        if item in equity_items and pd.notnull(total_asset_prev) and total_asset_prev != 0:
            df.loc[index, 'TỶ TRỌNG NĂM TRƯỚC'] = row['NĂM TRƯỚC'] / total_asset_prev
        
        if item in equity_items and pd.notnull(total_asset_current) and total_asset_current != 0:
            df.loc[index, 'TỶ TRỌNG NĂM SAU'] = row['NĂM SAU'] / total_asset_current


    # Định dạng kết quả
    df_output = df[['CHỈ TIÊU', 'NĂM TRƯỚC', 'NĂM SAU', 'TỶ TRỌNG NĂM TRƯỚC', 'TỶ TRỌNG NĂM SAU']].copy()
    
    # Định dạng tiền tệ cho 2 năm
    currency_format = "{:,.0f}"
    df_output['NĂM TRƯỚC'] = df_output['NĂM TRƯỚC'].apply(lambda x: currency_format.format(x) if pd.notnull(x) else '-')
    df_output['NĂM SAU'] = df_output['NĂM SAU'].apply(lambda x: currency_format.format(x) if pd.notnull(x) else '-')
    
    # Định dạng phần trăm cho Tỷ trọng
    percent_format = lambda x: f"{x:.2%}" if pd.notnull(x) and np.isfinite(x) else 'N/A'
    df_output['TỶ TRỌNG NĂM TRƯỚC'] = df_output['TỶ TRỌNG NĂM TRƯỚC'].apply(percent_format)
    df_output['TỶ TRỌNG NĂM SAU'] = df_output['TỶ TRỌNG NĂM SAU'].apply(percent_format)

    # Đổi tên cột để hiển thị đẹp hơn
    df_output.columns = ['CHỈ TIÊU', 'GIÁ TRỊ NĂM TRƯỚC', 'GIÁ TRỊ NĂM SAU', 'TỶ TRỌNG NĂM TRƯỚC (%)', 'TỶ TRỌNG NĂM SAU (%)']
    
    return df_output

# --- Giao diện Streamlit ---

st.title("Ứng Dụng Thẩm Định Tài Chính Doanh Nghiệp Tự Động")

st.markdown("""
Chào mừng bạn đến với công cụ phân tích tài chính tự động. 
Vui lòng tải lên file **Excel** chứa Bảng Cân Đối Kế Toán của khách hàng.

⚠️ **Lưu ý về định dạng file Excel:**
1.  Báo cáo phải chứa **2 kỳ dữ liệu** (Năm Trước, Năm Sau).
2.  File phải có **ít nhất 3 cột**: **(1)** Tên chỉ tiêu/khoản mục (ví dụ: 'Tiền mặt', 'Nợ ngắn hạn'), **(2)** Giá trị năm trước, **(3)** Giá trị năm sau.
""")

uploaded_file = st.file_uploader(
    "Tải lên file Excel (.xlsx) chứa báo cáo tài chính", 
    type=['xlsx']
)

if uploaded_file is not None:
    try:
        # Đọc dữ liệu từ file Excel
        raw_df = pd.read_excel(uploaded_file, sheet_name=0)
        
        st.subheader("1. Dữ liệu thô đã tải lên")
        st.dataframe(raw_df.head(), use_container_width=True)
        
        # Xử lý và chuẩn hóa dữ liệu
        processed_df = process_financial_data(raw_df.copy())
        
        if processed_df is not None and not processed_df.empty:
            st.success("Dữ liệu đã được chuẩn hóa thành công! Tiến hành phân tích.")

            st.subheader("2. Dữ liệu đã chuẩn hóa (Chỉ các chỉ tiêu quan trọng)")
            st.dataframe(processed_df, use_container_width=True)

            st.markdown("---")
            st.header("3. Kết Quả Phân Tích")
            
            # --- Hiển thị kết quả bằng các nút nhấn theo yêu cầu ---
            col1, col2 = st.columns(2)

            with col1:
                if st.button("📊 Xem Kết Quả PHÂN TÍCH TĂNG TRƯỞNG", use_container_width=True):
                    with st.spinner('Đang tính toán phân tích tăng trưởng...'):
                        growth_df = calculate_growth(processed_df)
                        st.subheader("BẢNG KẾT QUẢ PHÂN TÍCH TĂNG TRƯỞNG")
                        
                        # Sử dụng st.data_editor để hiển thị DataFrame có màu sắc trực quan hơn
                        st.data_editor(
                            growth_df,
                            column_config={
                                "TĂNG TRƯỞNG (%)": st.column_config.ProgressColumn(
                                    "TĂNG TRƯỞNG (%)",
                                    help="Mức tăng trưởng so với năm trước",
                                    format="%.2f",
                                    min_value=-1, # Giả định mức giảm tối đa là -100%
                                    max_value=1,  # Giả định mức tăng tối đa là +100%. Có thể điều chỉnh.
                                )
                            },
                            hide_index=True,
                            use_container_width=True
                        )
                        st.caption("Công thức: (Giá trị Năm Sau - Giá trị Năm Trước) / Giá trị Năm Trước")

            with col2:
                if st.button("📈 Xem Kết Quả PHÂN TÍCH TỶ TRỌNG", use_container_width=True):
                    with st.spinner('Đang tính toán phân tích tỷ trọng...'):
                        weight_df = calculate_weight(processed_df)
                        st.subheader("BẢNG KẾT QUẢ PHÂN TÍCH TỶ TRỌNG")
                        st.dataframe(weight_df, hide_index=True, use_container_width=True)
                        st.caption("Công thức: Chỉ tiêu / (Tổng Tài Sản hoặc Tổng Nguồn Vốn)")
            
        elif processed_df is not None and processed_df.empty:
            st.warning("Dữ liệu đã tải lên không chứa bất kỳ chỉ tiêu tài chính nào trong danh sách cần phân tích.")

    except Exception as e:
        st.error(f"Đã xảy ra lỗi trong quá trình xử lý file: {e}")
        st.warning("Vui lòng kiểm tra lại cấu trúc file Excel và đảm bảo rằng tên các khoản mục tài chính được viết đúng chính tả.")

else:
    st.info("Chờ đợi bạn tải lên file Excel để bắt đầu phân tích...")
