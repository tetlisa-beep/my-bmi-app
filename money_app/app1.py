import streamlit as st
import pandas as pd
import os
import json
import time
from datetime import datetime, timedelta, timezone # <--- 新增這個

# --- 設定 ---
# 定義台灣時區 (UTC+8)
TW_TIMEZONE = timezone(timedelta(hours=8))

# --- 設定 ---
# 定義哪些幣別是「整數幣別」(不需要小數點)
INT_CURRENCIES = ['TWD', 'JPY', 'KRW', 'VND']
# 定義所有支援幣別
CURRENCIES = ['TWD', 'JPY', 'USD', 'EUR']

# --- 設定檔案路徑 (固定在程式所在資料夾，避免受啟動目錄影響) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'trip_ledger.csv')      # 存帳務資料
CONFIG_FILE = os.path.join(BASE_DIR, 'members.json')       # 存成員名單
HISTORY_DIR = os.path.join(BASE_DIR, 'history')
CURRENCIES = ['JPY', 'TWD', 'USD', 'EUR'] # 這裡可以自己擴充

# --- 函數：讀取與儲存成員 ---
def load_members():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_members(members_list):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(members_list, f, ensure_ascii=False)

# --- 初始化 ---
st.set_page_config(page_title="旅程分帳系統", layout="centered")

# 讀取現有成員
if 'members' not in st.session_state:
    st.session_state['members'] = load_members()

# --- 側邊欄：成員管理 (深色質感版) ---
with st.sidebar:
    # 1. CSS 魔法：強制側邊欄深色化、優化分隔線
    st.markdown("""
    <style>
        /* 強制側邊欄背景變深灰藍色 */
        [data-testid="stSidebar"] {
            background-color: #1E293B; /* 質感深藍灰 */
        }
        /* 側邊欄的所有文字變白 */
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3, 
        [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] p {
            color: #E2E8F0 !important;
        }
        /* 成員名單的膠囊樣式 */
        .member-capsule {
            display: inline-block;
            background-color: rgba(255, 255, 255, 0.1);
            color: #F8FAFC;
            padding: 4px 12px;
            border-radius: 20px;
            margin: 4px 2px;
            font-size: 0.9rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        /* 優化分隔線：改成半透明虛線 */
        .custom-divider {
            margin: 20px 0;
            border-top: 1px dashed rgba(255, 255, 255, 0.2);
        }
        /* 讓輸入框標題不明顯的問題修正 */
        .stTextInput label, .stSelectbox label {
            color: #CBD5E1 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.header("👥 成員名單")
    
    # 2. 成員展示區 (常態秀出)
    # 使用 HTML 膠囊標籤顯示，比純文字列表好看
    if st.session_state['members']:
        member_html = ""
        for m in st.session_state['members']:
            member_html += f"<span class='member-capsule'>{m}</span>"
        st.markdown(f"<div style='margin-bottom: 15px;'>{member_html}</div>", unsafe_allow_html=True)
    else:
        st.info("目前還沒有成員，請在下方新增")

    # 3. 新增成員 (簡單快速)
    # 這裡只放最常用的「新增」，保持乾淨
    col_add_1, col_add_2 = st.columns([2, 1])
    with col_add_1:
        new_name = st.text_input("輸入名字", placeholder="你的名字", label_visibility="collapsed")
    with col_add_2:
        if st.button("➕", help="新增成員", use_container_width=True):
            if new_name and new_name not in st.session_state['members']:
                st.session_state['members'].append(new_name)
                save_members(st.session_state['members'])
                st.rerun()
            elif new_name in st.session_state['members']:
                st.toast("這個名字已經有了喔！", icon="⚠️")

    # 漂亮的自訂分隔線
    st.markdown("<div class='custom-divider'></div>", unsafe_allow_html=True)

    # 4. 進階後台 (全部收納在這裡)
    # 使用 expander 讓平常不需要的功能藏起來
    with st.expander("⚙️ 設定與進階操作"):
        
        # A. 修改/移除成員
        st.caption("🔧 成員管理")
        if st.session_state['members']:
            target_member = st.selectbox("選擇對象", st.session_state['members'])
            action = st.radio("動作", ["修改名字", "移除成員"], horizontal=True, label_visibility="collapsed")
            
            if action == "修改名字":
                rename_input = st.text_input(f"把 {target_member} 改為")
                if st.button("確認改名"):
                    if rename_input and rename_input != target_member:
                        # 更新名單
                        st.session_state['members'] = [rename_input if x == target_member else x for x in st.session_state['members']]
                        save_members(st.session_state['members'])
                        # 更新帳本 (這段邏輯保留)
                        if os.path.exists(DATA_FILE):
                            df_update = pd.read_csv(DATA_FILE)
                            # 清洗 Unnamed
                            df_update = df_update.loc[:, ~df_update.columns.str.contains('^Unnamed')]
                            
                            df_update['Payer'] = df_update['Payer'].replace(target_member, rename_input)
                            def update_bens(b_str):
                                if pd.isna(b_str): return b_str
                                names = str(b_str).split(',')
                                new_names = [rename_input if n.strip() == target_member else n.strip() for n in names]
                                return ",".join(new_names)
                            df_update['Beneficiaries'] = df_update['Beneficiaries'].apply(update_bens)
                            df_update.to_csv(DATA_FILE, index=False)
                        
                        st.success("改名成功！")
                        time.sleep(0.5)
                        st.rerun()
            
            elif action == "移除成員":
                st.caption(f"⚠️ 移除不會刪除 {target_member} 的記帳紀錄")
                if st.button(f"確定移除 {target_member}", type="primary"):
                    st.session_state['members'].remove(target_member)
                    save_members(st.session_state['members'])
                    st.rerun()
        
        st.markdown("<div class='custom-divider'></div>", unsafe_allow_html=True)

        # B. 階段性結算 (關帳)
        st.caption("🔒 帳務封存")
        if st.button("封存目前帳本並開新局"):
             if os.path.exists(DATA_FILE):
                if not os.path.exists(HISTORY_DIR): os.makedirs(HISTORY_DIR)
                timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
                backup_file = os.path.join(HISTORY_DIR, f"ledger_{timestamp}.csv")
                df_current = pd.read_csv(DATA_FILE)
                df_current.to_csv(backup_file, index=False)
                # 清空
                empty_df = pd.DataFrame(columns=['Date', 'Item', 'Payer', 'Amount', 'Currency', 'Beneficiaries'])
                empty_df.to_csv(DATA_FILE, index=False)
                st.success(f"已封存！")
                time.sleep(1)
                st.rerun()
        
        # C. 歷史下載
        if os.path.exists(HISTORY_DIR):
            st.markdown("<br>", unsafe_allow_html=True)
            files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".csv")]
            files.sort(reverse=True)
            if files:
                selected_hist = st.selectbox("下載歷史紀錄", files)
                file_path = os.path.join(HISTORY_DIR, selected_hist)
                with open(file_path, "r", encoding="utf-8") as f:
                    st.download_button(f"📥 下載 {selected_hist}", f, file_name=selected_hist, mime="text/csv")

        # D. 危險操作
        st.markdown("<div class='custom-divider'></div>", unsafe_allow_html=True)
        if st.button("⚠️ 重置所有成員 (危險)", type="secondary"):
            st.session_state['members'] = []
            save_members([])
            st.rerun()

# --- 主畫面：記帳邏輯 ---
# 檢查是否有成員，如果沒有，停止渲染後面的內容
if not st.session_state['members']:
    st.info("👈 請先在左側側邊欄「新增成員」才能開始記帳喔！")
    st.stop()

# 1. 讀取/初始化帳務資料
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    
    # --- 🔥 新增這行：自動清洗髒資料 ---
    # 如果發現有 'Unnamed: 0' 這種奇怪的欄位 (Excel 或舊存檔造成的)，直接刪除
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
else:
    df = pd.DataFrame(columns=['Date', 'Item', 'Payer', 'Amount', 'Currency', 'Beneficiaries'])

# --- 定義彈出視窗函數 (放在主邏輯之前) ---

# A. 新增用的彈出視窗 (簡潔版：單一模式，不顯示切換選單)
@st.dialog("➕ 新增紀錄")
def add_entry_dialog(mode):
    # mode: 0 = 一般消費, 1 = 結帳還款

    # --- 情況一：一般消費 ---
    if mode == 0:
        st.subheader("💸 新增消費")
        # st.caption("📝 記錄大家的消費支出") # 想要更簡潔這行也可以拿掉
        
        with st.form("add_expense_form"):
            col1, col2 = st.columns(2)
            item = col1.text_input("消費項目", placeholder="如: 晚餐、車票")
            amount = col2.number_input("金額", min_value=0.0, step=10.0, format="%g", key="exp_amt")
            
            col3, col4 = st.columns(2)
            payer = col3.selectbox("誰先墊錢?", st.session_state['members'], key="exp_payer")
            currency = col4.selectbox("幣別", CURRENCIES, key="exp_curr")
            
            beneficiaries = st.multiselect(
                "分給誰? (預設全員)", 
                st.session_state['members'], 
                default=st.session_state['members'],
                key="exp_ben"
            )
            
            if st.form_submit_button("💾 儲存消費", type="primary"):
                if amount > 0 and len(beneficiaries) > 0 and item:
                    save_entry(item, payer, amount, currency, beneficiaries)
                else:
                    st.error("請輸入完整資訊")

    # --- 情況二：結帳/還款 ---
    elif mode == 1:
        st.subheader("🤝 登記還款")
        st.info("💡 記錄「誰把錢還給了誰」。")
        
        with st.form("settle_form"):
            col_s1, col_s2 = st.columns(2)
            payer_s = col_s1.selectbox("誰還錢? (付款)", st.session_state['members'], key="stl_payer")
            receiver_s = col_s2.selectbox("還給誰? (收錢)", st.session_state['members'], key="stl_receiver")
            
            col_s3, col_s4 = st.columns(2)
            amount_s = col_s3.number_input("還款金額", min_value=0.0, step=100.0, format="%g", key="stl_amount")
            currency_s = col_s4.selectbox("幣別", CURRENCIES, key="stl_curr")
            
            if st.form_submit_button("🤝 確認還款", type="primary"):
                if amount_s > 0 and payer_s != receiver_s:
                    item_name = f"還款: {payer_s} -> {receiver_s}"
                    save_entry(item_name, payer_s, amount_s, currency_s, [receiver_s])
                else:
                    st.error("金額需大於0且不能自己還自己")

# --- 輔助函數：存檔 (修正時區) ---
def save_entry(item, payer, amount, currency, beneficiaries):
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        # 清洗舊資料 (避免 Unnamed 欄位)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    else:
        df = pd.DataFrame(columns=['Date', 'Item', 'Payer', 'Amount', 'Currency', 'Beneficiaries'])
    
    # 使用台灣時間
    tw_now = datetime.now(TW_TIMEZONE).strftime('%Y-%m-%d %H:%M')

    new_entry = {
        'Date': tw_now,
        'Item': item,
        'Payer': payer,
        'Amount': amount,
        'Currency': currency,
        'Beneficiaries': ",".join(beneficiaries)
    }
    
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    
    st.success("已儲存！")
    st.balloons()
    time.sleep(1.0)
    st.rerun()

# --- B. 修改用的彈出視窗 ---
@st.dialog("✏️ 修改紀錄")
def edit_entry_dialog(index, row_data):
    # 解析舊資料
    original_beneficiaries = str(row_data['Beneficiaries']).split(",")
    # 過濾有效成員
    valid_defaults = [m for m in original_beneficiaries if m in st.session_state['members']]
    
    with st.form("edit_form"):
        col1, col2 = st.columns(2)
        item = col1.text_input("項目", value=row_data['Item'])
        amount = col2.number_input("金額", min_value=0.0, step=10.0, value=float(row_data['Amount']))
        
        col3, col4 = st.columns(2)
        
        # 處理付款人 (防呆)
        try:
            p_index = st.session_state['members'].index(row_data['Payer'])
        except:
            p_index = 0
        payer = col3.selectbox("付款人", st.session_state['members'], index=p_index)
        
        # 處理幣別
        try:
            c_index = CURRENCIES.index(row_data['Currency'])
        except:
            c_index = 0
        currency = col4.selectbox("幣別", CURRENCIES, index=c_index)
        
        beneficiaries = st.multiselect(
            "分帳人 / 收款人", 
            st.session_state['members'], 
            default=valid_defaults
        )
        
        col_btn_a, col_btn_b = st.columns([1, 1])
        with col_btn_a:
            if st.form_submit_button("💾 保存修改", type="primary"):
                if os.path.exists(DATA_FILE):
                    df = pd.read_csv(DATA_FILE)
                    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
                    
                    df.at[index, 'Item'] = item
                    df.at[index, 'Amount'] = amount
                    df.at[index, 'Payer'] = payer
                    df.at[index, 'Currency'] = currency
                    df.at[index, 'Beneficiaries'] = ",".join(beneficiaries)
                    
                    df.to_csv(DATA_FILE, index=False)
                    st.success("修改完成！")
                    st.rerun()
                    
    # 刪除功能
    st.markdown("---")
    col_del_1, col_del_2 = st.columns([3, 2])
    with col_del_2:
        if st.button("🗑️ 刪除此筆資料", type="secondary", use_container_width=True):
            if os.path.exists(DATA_FILE):
                df = pd.read_csv(DATA_FILE)
                df = df.drop(index)
                df.to_csv(DATA_FILE, index=False)
                st.success("已刪除！")
                st.rerun()

# --- 主畫面：Hero Header & 控制島 (取代原本的步驟 3 按鈕區) ---
# --- 統計數據準備 ---
num_members = len(st.session_state['members'])
num_records = len(df) if not df.empty else 0

# 1. 標題區 (Hero Section) - 取代原本最上面的 st.title
# 使用 HTML 自訂標題，增加設計感與間距
st.markdown("""
<div style="margin-bottom: 20px; padding-top: 10px;">
    <h1 style="font-family:'Inter', sans-serif; font-weight: 800; font-size: 2.5rem; color: #1F2937; margin-bottom: 0;">
        ✈️ 旅程分帳系統
    </h1>
            
</div>
""", unsafe_allow_html=True)

# 2. 插入狀態列 (在這裡！)
st.markdown(f"""
<div style="color: #64748B; font-size: 0.95rem; margin-top: -15px; margin-bottom: 20px; font-weight: 500;">
    👥 {num_members} 位同行夥伴 &nbsp; <span style="color:#CBD5E1">|</span> &nbsp; 💰 {num_records} 筆消費紀錄
</div>
""", unsafe_allow_html=True)

# 3. 懸浮控制島 (Floating Command Bar)
# 我們把按鈕包在一個 container(border=True) 裡
# 因為 CSS 已經美化了 container，所以它會自動變成漂亮的懸浮卡片
with st.container(border=True):
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        # 新增消費按鈕 (Primary 色)
        if st.button("💸 新增消費", use_container_width=True, type="primary"):
            add_entry_dialog(0) 
            
    with col_btn2:
        # 登記還款按鈕 (Secondary 色)
        if st.button("🤝 登記還款", use_container_width=True):
            add_entry_dialog(1)

# 4. 強制留白 (Spacer) - 解決太擠的問題
# 在控制島與下方明細之間，強制推開 40px 的距離
st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)

# 2. 消費明細 (手機版極致壓縮版：圖示整合、成員全開、高度縮減)
st.subheader("📝 帳務明細")

# --- CSS 優化 (針對手機版緊湊排版) ---
st.markdown("""
<style>
    /* 1. 卡片基礎樣式 */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        margin-bottom: 8px !important; /* 減少卡片間距 */
        padding: 12px !important;      /* 減少內部留白 */
    }
    
    /* 2. 避免文字被深色模式吃掉 */
    [data-testid="stVerticalBlockBorderWrapper"] div,
    [data-testid="stVerticalBlockBorderWrapper"] span,
    [data-testid="stVerticalBlockBorderWrapper"] p {
        color: #334155 !important;
    }

    /* 3. Popover 按鈕樣式 (靠右、不佔空間) */
    [data-testid="stPopover"] {
        display: flex;
        justify-content: center;
        align-items: center;
    }
    [data-testid="stPopover"] > button {
        border: none !important;
        background: transparent !important;
        color: #94A3B8 !important;
        padding: 0 !important;
        width: 30px !important; /* 限制按鈕寬度 */
    }
    
    /* 4. 成員標籤容器 (自動換行) */
    .people-container {
        display: flex;
        flex-wrap: wrap; /* 關鍵：人名太多時自動折行 */
        gap: 4px;        /* 標籤之間的間距 */
        align-items: center;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

if not df.empty:
    # --- 0. 篩選控制區 (保持不變) ---
    all_members_opt = "👀 全員 (不篩選)"
    view_options = [all_members_opt] + st.session_state['members']
    
    col_filter_1, col_filter_2 = st.columns([1.2, 2])
    with col_filter_1:
        current_view = st.selectbox("視角模式", view_options, index=0, label_visibility="collapsed")

    if current_view == all_members_opt:
        filter_options = ["💸 大額 (>5k)", "🌍 外幣"]
    else:
        filter_options = ["👤 我先墊的", "👥 有我的份", "💸 大額 (>5k)", "🌍 外幣"]

    with col_filter_2:
        try:
            selection = st.pills("篩選條件", filter_options, selection_mode="multi", label_visibility="collapsed")
        except AttributeError:
            selection = st.multiselect("篩選條件", filter_options, label_visibility="collapsed")

    # --- 1. 執行篩選邏輯 ---
    filtered_df = df.iloc[::-1]

    if current_view != all_members_opt:
        filtered_df = filtered_df[
            (filtered_df['Payer'] == current_view) | 
            (filtered_df['Beneficiaries'].astype(str).str.contains(current_view))
        ]

    if selection:
        if "👤 我先墊的" in selection and current_view != all_members_opt:
            filtered_df = filtered_df[filtered_df['Payer'] == current_view]
        if "👥 有我的份" in selection and current_view != all_members_opt:
            filtered_df = filtered_df[filtered_df['Beneficiaries'].astype(str).str.contains(current_view)]
        if "💸 大額 (>5k)" in selection:
            filtered_df = filtered_df[filtered_df['Amount'] > 5000]
        if "🌍 外幣" in selection:
            filtered_df = filtered_df[filtered_df['Currency'] != "TWD"]

    st.caption(f"顯示 {len(filtered_df)} 筆紀錄")

    # --- 2. 畫出卡片 (使用 2 欄式佈局) ---
    for i, (index, row) in enumerate(filtered_df.iterrows()):
        
        is_settlement = "還款" in str(row['Item'])
        currency = row['Currency']
        amount = float(row['Amount'])
        date_str = str(row['Date'])[5:] 
        item_name = row['Item']
        payer = row['Payer']
        bens = [b.strip() for b in str(row['Beneficiaries']).split(",") if b.strip()]
        
        # 聰明金額格式
        if amount.is_integer():
            formatted_amount = f"{amount:,.0f}"
        else:
            formatted_amount = f"{amount:,.2f}"

        if is_settlement:
            icon = "🤝"
            amount_color = "#16A34A" # 綠色
            amount_display = f"+ {currency} {formatted_amount}"
        else:
            icon = "💸"
            amount_color = "#DC2626" # 紅色
            amount_display = f"- {currency} {formatted_amount}"

        # --- HTML 組合 ---
        # 1. 標題列：[圖示] [項目名稱] -------- [金額]
        # 使用 Flexbox 讓金額自動靠右
        header_html = f"""
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2px;">
            <div style="font-weight:bold; font-size:1rem; color:#334155; display:flex; align-items:center; gap:6px;">
                <span style="font-size:1.2rem;">{icon}</span>
                <span>{item_name}</span>
            </div>
            <div style="font-weight:bold; color:{amount_color}; font-size:1rem; white-space:nowrap; margin-left:8px;">
                {amount_display}
            </div>
        </div>
        """

        # 2. 成員與日期列
        # 付款人 Tag
        payer_html = f"<span style='background-color: #475569; color: white; padding: 1px 6px; border-radius: 6px; font-size: 0.75rem; font-weight: bold; white-space:nowrap;'>{payer}</span>"
        
        # 分帳人 Tag (全部顯示，沒有 [:3] 限制)
        bens_html_parts = []
        for b in bens:
            tag = f"<span style='border: 1px solid #CBD5E1; color: #475569; padding: 0px 5px; border-radius: 6px; font-size: 0.75rem; white-space:nowrap;'>{b}</span>"
            bens_html_parts.append(tag)
        bens_html = "".join(bens_html_parts)
        
        # 組合人員列
        # 使用我們定義的 .people-container 讓它自動換行
        people_html = f"""
        <div class="people-container">
            {payer_html}
            <span style='color:#ccc; font-size:0.8rem;'>➜</span>
            {bens_html}
            <span style="color:#94A3B8; font-size:0.75rem; margin-left: auto;">{date_str}</span>
        </div>
        """

        # --- 卡片容器 ---
        with st.container(border=True):
            # 🔥 關鍵改變：只切成 2 欄 [內容 85% | 按鈕 15%]
            # 這樣左邊的 HTML 內容會自適應，不會被強制切斷
            c_content, c_action = st.columns([8.5, 1.5], vertical_alignment="center")
            
            with c_content:
                # 這裡把所有資訊一次畫出來
                st.markdown(header_html + people_html, unsafe_allow_html=True)

            with c_action:
                # 右邊只放一個編輯按鈕
                with st.popover("⋮", use_container_width=True):
                    st.markdown("##### 交易詳情")
                    if not is_settlement and len(bens) > 0:
                        avg = amount / len(bens)
                        st.info(f"💰 總額 {amount:,.0f} ÷ {len(bens)} 人 = **{avg:,.1f} /人**")
                    elif is_settlement:
                        st.success(f"這是 {payer} 還給 {bens[0]} 的款項")
                    
                    st.divider()
                    if st.button("✏️ 修改/刪除", key=f"btn_edit_{index}", type="primary", use_container_width=True):
                        edit_entry_dialog(index, row)

else:
    st.info("📭 目前還沒有任何紀錄")

# 3. 結算儀表板 (全域聰明金額版：淨額、車票、任務卡都自動隱藏 .00)
st.divider()
st.subheader("🧾 結算儀表板")

# --- CSS 樣式 ---
st.markdown("""
<style>
    .tabular-nums { font-family: 'Inter', monospace; font-variant-numeric: tabular-nums; }
    
    /* 1. 儀表板卡片 */
    .premium-card {
        background-color: white; border-radius: 12px; padding: 20px; margin-bottom: 16px;
        border: 1px solid #f0f0f0; box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }

    /* 2. 轉帳車票 (三欄對齊) */
    .transfer-ticket {
        display: flex; 
        align-items: center; 
        justify-content: center; 
        background: white; 
        border: 1px dashed #cbd5e1; 
        border-radius: 10px;
        padding: 12px 10px; 
        margin-bottom: 10px;
    }
    
    .ticket-side {
        flex: 1;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    
    .ticket-center {
        flex: 0 0 100px; /* 固定寬度確保置中 */
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    
    .ticket-label { font-size: 0.75rem; color: #94a3b8; margin-bottom: 2px; }
    .ticket-name { font-weight: 700; color: #334155; font-size: 0.95rem; }
    .ticket-arrow { color: #cbd5e1; font-size: 1.2rem; line-height: 1; margin-bottom: 2px;}
    .ticket-amount { font-weight: 700; color: #334155; font-size: 0.95rem; }

    /* 表格樣式 */
    .styled-table { width: 100%; border-collapse: collapse; font-family: sans-serif; }
    .styled-table th { border-bottom: 2px solid #f0f0f0; padding: 10px; color: #888; font-size: 0.85rem; text-align: left; }
    .styled-table td { border-bottom: 1px solid #f7f7f7; padding: 12px; font-size: 0.95rem; }
    .styled-table tr:hover { background-color: #f9fbfc; }
    .status-green { border-left: 4px solid #52c41a; }
    .status-red { border-left: 4px solid #ff4d4f; }
    .status-gray { border-left: 4px solid #e6e6e6; }
    
    /* 任務卡 */
    .mission-box { background: #f6ffed; border: 1px solid #b7eb8f; padding: 16px; border-radius: 8px; color: #389e0d; }
    .mission-box-debt { background: #fff1f0; border: 1px solid #ffa39e; padding: 16px; border-radius: 8px; color: #cf1322; }
</style>
""", unsafe_allow_html=True)

if not df.empty:
    try:
        dashboard_view = current_view
    except NameError:
        dashboard_view = "👀 全員 (不篩選)"

    grouped = df.groupby('Currency')
    tabs = st.tabs([f"💵 {curr}" for curr in grouped.groups.keys()])
    
    # 定義一個小幫手函數：聰明格式化
    def smart_fmt(val):
        if float(val).is_integer():
            return f"{val:,.0f}"
        return f"{val:,.2f}"

    for i, (currency, group) in enumerate(grouped):
        with tabs[i]:
            # --- A. 計算邏輯 ---
            balances = {m: 0.0 for m in st.session_state['members']}
            total_spend = 0.0
            
            for index, row in group.iterrows():
                if "還款" not in str(row['Item']):
                    total_spend += float(row['Amount'])
                
                amt = float(row['Amount'])
                payer = row['Payer']
                bens = [b.strip() for b in str(row['Beneficiaries']).split(",") if b.strip()]
                
                if payer not in balances: balances[payer] = 0.0
                if bens:
                    balances[payer] += amt
                    split = amt / len(bens)
                    for b in bens:
                        if b not in balances: balances[b] = 0.0
                        balances[b] -= split

            # --- B. 總計 ---
            avg_spend = total_spend / len(st.session_state['members']) if st.session_state['members'] else 0
            st.markdown(f"""<div style="display: flex; gap: 20px; margin-bottom: 20px;"><div><small style="color:#888;">TOTAL</small><br><b style="font-size:1.5rem;">{currency} {smart_fmt(total_spend)}</b></div><div style="border-left:1px solid #eee; padding-left:20px;"><small style="color:#888;">AVG/PERSON</small><br><b style="font-size:1.5rem; color:#666;">{currency} {smart_fmt(avg_spend)}</b></div></div>""", unsafe_allow_html=True)

            # --- C. 排序 ---
            sorted_bal = sorted(balances.items(), key=lambda x: x[1], reverse=True)
            debtors = sorted([x for x in sorted_bal if x[1] < -0.01], key=lambda x: x[1])
            creditors = sorted([x for x in sorted_bal if x[1] > 0.01], key=lambda x: x[1], reverse=True)
            transfer_list = []
            temp_d = [list(d) for d in debtors]
            temp_c = [list(c) for c in creditors]
            id_d, id_c = 0, 0
            while id_d < len(temp_d) and id_c < len(temp_c):
                amt = min(abs(temp_d[id_d][1]), temp_c[id_c][1])
                if amt > 0.01: # 這裡稍微放寬一點容許度
                    transfer_list.append({'from': temp_d[id_d][0], 'to': temp_c[id_c][0], 'amount': amt})
                temp_d[id_d][1] += amt
                temp_c[id_c][1] -= amt
                if abs(temp_d[id_d][1]) < 0.01: id_d += 1
                if temp_c[id_c][1] < 0.01: id_c += 1

            # --- D. 個人任務 ---
            if dashboard_view != "👀 全員 (不篩選)":
                my_bal = balances.get(dashboard_view, 0)
                st.markdown(f"##### 🎯 {dashboard_view} 的任務")
                
                # 使用 smart_fmt 處理顯示
                if my_bal > 0.01:
                    st.markdown(f"""<div class="mission-box premium-card"><div>應收</div><div style="font-size:1.8rem; font-weight:bold;">+{currency} {smart_fmt(my_bal)}</div></div>""", unsafe_allow_html=True)
                    for t in [x for x in transfer_list if x['to']==dashboard_view]:
                        st.markdown(f"""
                        <div class="transfer-ticket">
                            <div class="ticket-side">
                                <div class="ticket-label">From</div>
                                <div class="ticket-name">{t['from']}</div>
                            </div>
                            <div class="ticket-center">
                                <div class="ticket-arrow" style="color:#28a745;">➜</div>
                                <div class="ticket-amount" style="color:#28a745;">+{smart_fmt(t['amount'])}</div>
                            </div>
                            <div class="ticket-side">
                                <div class="ticket-label">To</div>
                                <div class="ticket-name">Me</div>
                            </div>
                        </div>""", unsafe_allow_html=True)
                elif my_bal < -0.01:
                    st.markdown(f"""<div class="mission-box-debt premium-card"><div>應付</div><div style="font-size:1.8rem; font-weight:bold;">-{currency} {smart_fmt(abs(my_bal))}</div></div>""", unsafe_allow_html=True)
                    for t in [x for x in transfer_list if x['from']==dashboard_view]:
                        st.markdown(f"""
                        <div class="transfer-ticket">
                            <div class="ticket-side">
                                <div class="ticket-label">From</div>
                                <div class="ticket-name">Me</div>
                            </div>
                            <div class="ticket-center">
                                <div class="ticket-arrow" style="color:#cf1322;">➜</div>
                                <div class="ticket-amount" style="color:#cf1322;">-{smart_fmt(t['amount'])}</div>
                            </div>
                            <div class="ticket-side">
                                <div class="ticket-label">To</div>
                                <div class="ticket-name">{t['to']}</div>
                            </div>
                        </div>""", unsafe_allow_html=True)
                else:
                    st.success("🎉 帳目已平！")
                st.divider()

            # --- E. 全員表格 (左) & 轉帳路徑 (右) ---
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown("##### 📊 帳務狀態表")
                html_parts = []
                html_parts.append('<table class="styled-table"><thead><tr><th>成員</th><th>淨額</th><th>狀態</th></tr></thead><tbody>')
                
                for member, net in sorted_bal:
                    net_val = float(net)
                    # 🔥 關鍵修正：這裡也套用 smart_fmt
                    formatted_net = smart_fmt(abs(net_val))

                    if net_val > 0.01:
                        row_cls = "status-green"
                        badge = "<span style='background:#f6ffed; color:#4DB6AC; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>收錢錢囉✨💰</span>"
                        color = "#4DB6AC"
                        txt = f"+{formatted_net}"
                    elif net_val < -0.01:
                        row_cls = "status-red"
                        badge = "<span style='background:#fff1f0; color:#FF8A65; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>繳錢錢囉💵</span>"
                        color = "#FF8A65"
                        txt = f"-{formatted_net}"
                    else:
                        row_cls = "status-gray"
                        badge = "<span style='color:#888; font-size:0.8rem;'>平帳</span>"
                        color = "#ccc"
                        txt = "0"
                    
                    row_html = f'<tr class="{row_cls}"><td style="font-weight:500;">{member}</td><td class="tabular-nums" style="color:{color}; font-weight:600;">{txt}</td><td>{badge}</td></tr>'
                    html_parts.append(row_html)
                html_parts.append('</tbody></table>')
                final_table_html = "".join(html_parts)
                st.markdown(f'<div class="premium-card" style="padding:0; overflow:hidden;">{final_table_html}</div>', unsafe_allow_html=True)

            with c2:
                st.markdown("##### 🎫 轉帳路徑")
                if not transfer_list:
                    st.info("無須轉帳 ✨")
                else:
                    for t in transfer_list:
                        # 🔥 這裡也套用 smart_fmt，確保車票金額也乾淨
                        st.markdown(f"""
                        <div class="transfer-ticket">
                            <div class="ticket-side">
                                <div class="ticket-label">付款</div>
                                <div class="ticket-name">{t['from']}</div>
                            </div>
                            <div class="ticket-center">
                                <div class="ticket-arrow">➜</div>
                                <div class="ticket-amount">${smart_fmt(t['amount'])}</div>
                            </div>
                            <div class="ticket-side">
                                <div class="ticket-label">收款</div>
                                <div class="ticket-name">{t['to']}</div>
                            </div>
                        </div>""", unsafe_allow_html=True)
else:
    st.info("尚無資料")

# --- 備份區 (維持原本設計) ---
st.markdown("---")
with st.expander("📂 資料庫備份/還原 - 程式人員專用", expanded=False):
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        st.markdown("#### 📥 下載備份")
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "rb") as f:
                st.download_button("下載 .csv 檔", f, file_name="ledger_backup.csv", mime="text/csv")
    with col_b2:
        st.markdown("#### 📤 上傳還原")
        up_file = st.file_uploader("選擇檔案", type=["csv"], label_visibility="collapsed")
        if up_file:
            pd.read_csv(up_file).to_csv(DATA_FILE, index=False)
            st.success("還原成功！")
            time.sleep(1)
            st.rerun()
    
    st.divider()
    st.caption("📜 歷史結算封存檔：")
    if os.path.exists(HISTORY_DIR):
        files = sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith(".csv")], reverse=True)
        for f in files:
            with open(os.path.join(HISTORY_DIR, f), "rb") as hf:
                st.download_button(f"📥 {f}", hf, file_name=f, key=f)
