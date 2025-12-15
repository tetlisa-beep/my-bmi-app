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

# --- 設定檔案路徑 ---
DATA_FILE = 'trip_ledger.csv'      # 存帳務資料
CONFIG_FILE = 'members.json'       # 存成員名單
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
        new_name = st.text_input("輸入名字", placeholder="例如: 傑克", label_visibility="collapsed")
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
                if not os.path.exists("history"): os.makedirs("history")
                timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
                backup_file = f"history/ledger_{timestamp}.csv"
                df_current = pd.read_csv(DATA_FILE)
                df_current.to_csv(backup_file, index=False)
                # 清空
                empty_df = pd.DataFrame(columns=['Date', 'Item', 'Payer', 'Amount', 'Currency', 'Beneficiaries'])
                empty_df.to_csv(DATA_FILE, index=False)
                st.success(f"已封存！")
                time.sleep(1)
                st.rerun()
        
        # C. 歷史下載
        if os.path.exists("history"):
            st.markdown("<br>", unsafe_allow_html=True)
            files = [f for f in os.listdir("history") if f.endswith(".csv")]
            files.sort(reverse=True)
            if files:
                selected_hist = st.selectbox("下載歷史紀錄", files)
                file_path = os.path.join("history", selected_hist)
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
            amount = col2.number_input("金額", min_value=0.0, step=10.0, key="exp_amt")
            
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
            amount_s = col_s3.number_input("還款金額", min_value=0.0, step=100.0, key="stl_amount")
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

# 1. 標題區 (Hero Section) - 取代原本最上面的 st.title
# 使用 HTML 自訂標題，增加設計感與間距
st.markdown("""
<div style="margin-bottom: 20px; padding-top: 10px;">
    <h1 style="font-family:'Inter', sans-serif; font-weight: 800; font-size: 2.5rem; color: #1F2937; margin-bottom: 0;">
        ✈️ 旅程分帳系統
    </h1>
    <p style="color: #6B7280; font-size: 1rem; margin-top: 5px;">
        簡單、直覺的動態成員分帳工具
    </p>
</div>
""", unsafe_allow_html=True)

# 2. 懸浮控制島 (Floating Command Bar)
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

# 3. 強制留白 (Spacer) - 解決太擠的問題
# 在控制島與下方明細之間，強制推開 40px 的距離
st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)

# 2. 消費明細 (互動美學版：懸停特效 + 浮動陰影 + 背景分層)
st.subheader("📝 帳務明細")

# --- CSS 樣式注入 (美化的核心) ---
st.markdown("""
<style>
    /* 1. 全站背景色：改成極淡灰，讓白色卡片突顯出來 */
    .stApp {
        background-color: #F7F8FA;
    }

    /* 2. 卡片容器樣式 (Target Streamlit's container with border) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF;
        border: 1px solid #E6E8EB;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        padding: 16px;
        margin-bottom: 12px;
        /* 動畫設定：150ms */
        transition: all 0.15s ease-in-out;
    }

    /* 3. 卡片懸停 (Hover) 特效 */
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        background-color: #FCFCFC;      /* 背景微灰 */
        border-color: #D1D5DB;          /* 邊框加深 */
        box-shadow: 0 6px 12px rgba(0,0,0,0.08); /* 陰影加深浮起 */
        transform: translateY(-2px);    /* 微微上浮 */
        cursor: pointer;                /* 鼠標變手勢 */
    }

    /* 4. Icon 動畫特效 */
    .transaction-icon {
        transition: transform 0.15s ease, filter 0.15s ease;
    }
    /* 當卡片被懸停時，裡面的 Icon 做動作 */
    [data-testid="stVerticalBlockBorderWrapper"]:hover .transaction-icon {
        transform: scale(1.15);  /* 放大 1.15 倍 */
        filter: brightness(0.9); /* 顏色微深 */
    }
    
    /* 修正 Popover 按鈕位置 */
    [data-testid="stPopover"] {
        margin-top: 2px;
    }
</style>
""", unsafe_allow_html=True)

if not df.empty:
    # --- 0. 篩選控制區 ---
    all_members_opt = "👀 全員 (不篩選)"
    view_options = [all_members_opt] + st.session_state['members']
    
    col_filter_1, col_filter_2 = st.columns([1, 2])
    
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

    # --- 2. 畫出卡片 (美化版) ---
    for i, (index, row) in enumerate(filtered_df.iterrows()):
        
        is_settlement = "還款" in str(row['Item'])
        currency = row['Currency']
        amount = float(row['Amount'])
        date_str = str(row['Date'])[5:] 
        item_name = row['Item']
        payer = row['Payer']
        
        bens = [b.strip() for b in str(row['Beneficiaries']).split(",") if b.strip()]
        
        # 這裡不特別改背景色，因為我們用 CSS 統一控制了白色卡片
        if is_settlement:
            icon = "🤝"
            amount_color = "#28a745"
            amount_display = f"+ {currency} {amount:,.0f}"
        else:
            icon = "💸"
            amount_color = "#dc3545"
            amount_display = f"- {currency} {amount:,.2f}"

        # HTML Tags (維持舒適樣式)
        payer_html = f"<span style='background-color: #4A5568; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem; font-weight: bold; margin-right: 6px; display: inline-block; margin-bottom: 4px;'>🧍 {payer}</span>"
        
        bens_html_parts = []
        for b in bens:
            tag = f"<span style='border: 1px solid #E2E8F0; background-color: #F7FAFC; color: #4A5568; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem; margin-right: 4px; margin-bottom: 4px; display: inline-block;'>{b}</span>"
            bens_html_parts.append(tag)
        bens_html = "".join(bens_html_parts)
        people_html = f"{payer_html}<span style='color:#ccc; margin:0 4px; font-size:0.9rem;'>➜</span>{bens_html}"

        # --- 卡片容器 (Streamlit Container) ---
        # 這裡的 border=True 會被上面的 CSS 選取到，變身成漂亮卡片
        with st.container(border=True):
            
            c1, c2, c3, c4 = st.columns([0.7, 3.3, 1.2, 0.5])
            
            with c1:
                # 加上 transaction-icon class 讓 CSS 可以控制動畫
                st.markdown(f"<div class='transaction-icon' style='font-size:1.8rem; text-align:center; padding-top: 4px;'>{icon}</div>", unsafe_allow_html=True)
            
            with c2:
                st.markdown(f"""
                <div style="margin-bottom: 6px;">
                    <span style="font-weight:bold; font-size:1.05rem; color:#2D3748;">{item_name}</span>
                    <span style="color:#A0AEC0; font-size:0.85rem; margin-left:8px;">{date_str}</span>
                </div>
                <div style="line-height: 1.6;">{people_html}</div>
                """, unsafe_allow_html=True)

            with c3:
                st.markdown(f"<div style='text-align: right; color: {amount_color}; font-weight:bold; font-size:1.1rem; padding-top: 4px;'>{amount_display}</div>", unsafe_allow_html=True)

            with c4:
                # 側邊選單 (Popover)
                with st.popover("⋮", use_container_width=True, help="查看詳情與修改"):
                    st.markdown("##### 🔍 交易詳情")
                    if not is_settlement and len(bens) > 0:
                        avg = amount / len(bens)
                        st.markdown(f"**🧮 分帳計算：**")
                        st.info(f"總額 {amount:,.0f} ÷ {len(bens)} 人 = **{avg:,.1f} /人**")
                    elif is_settlement:
                        st.success(f"這是 {payer} 還給 {bens[0]} 的款項")
                    
                    st.divider()
                    
                    # 修改按鈕
                    if st.button("✏️ 修改/刪除", key=f"btn_edit_{index}", type="primary", use_container_width=True):
                        edit_entry_dialog(index, row)

else:
    st.info("📭 目前還沒有任何紀錄")

# 3. 結算儀表板 (最終修正版：解決 HTML 縮排導致顯示原始碼的問題)
st.divider()
st.subheader("💰 結算儀表板")

# --- CSS 樣式 ---
st.markdown("""
<style>
    .tabular-nums { font-family: 'Inter', monospace; font-variant-numeric: tabular-nums; }
    .premium-card {
        background-color: white; border-radius: 12px; padding: 20px; margin-bottom: 16px;
        border: 1px solid #f0f0f0; box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    .transfer-ticket {
        display: flex; align-items: center; justify-content: space-between;
        background: white; border: 1px dashed #d9d9d9; border-radius: 8px;
        padding: 12px 16px; margin-bottom: 8px;
    }
    .styled-table { width: 100%; border-collapse: collapse; font-family: sans-serif; }
    .styled-table th { border-bottom: 2px solid #f0f0f0; padding: 10px; color: #888; font-size: 0.85rem; text-align: left; }
    .styled-table td { border-bottom: 1px solid #f7f7f7; padding: 12px; font-size: 0.95rem; }
    .styled-table tr:hover { background-color: #f9fbfc; }
    
    .status-green { border-left: 4px solid #52c41a; }
    .status-red { border-left: 4px solid #ff4d4f; }
    .status-gray { border-left: 4px solid #e6e6e6; }
    
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
    
    for i, (currency, group) in enumerate(grouped):
        with tabs[i]:
            # --- A. 計算 ---
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
            # 這裡也改成單行以防萬一
            st.markdown(f"""<div style="display: flex; gap: 20px; margin-bottom: 20px;"><div><small style="color:#888;">TOTAL</small><br><b style="font-size:1.5rem;">{currency} {total_spend:,.0f}</b></div><div style="border-left:1px solid #eee; padding-left:20px;"><small style="color:#888;">AVG/PERSON</small><br><b style="font-size:1.5rem; color:#666;">{currency} {avg_spend:,.0f}</b></div></div>""", unsafe_allow_html=True)

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
                if amt > 0.5:
                    transfer_list.append({'from': temp_d[id_d][0], 'to': temp_c[id_c][0], 'amount': amt})
                temp_d[id_d][1] += amt
                temp_c[id_c][1] -= amt
                if abs(temp_d[id_d][1]) < 0.01: id_d += 1
                if temp_c[id_c][1] < 0.01: id_c += 1

            # --- D. 個人任務 ---
            if dashboard_view != "👀 全員 (不篩選)":
                my_bal = balances.get(dashboard_view, 0)
                st.markdown(f"##### 🎯 {dashboard_view} 的任務")
                if my_bal > 0.5:
                    st.markdown(f"""<div class="mission-box premium-card"><div>應收</div><div style="font-size:1.8rem; font-weight:bold;">+{currency} {my_bal:,.1f}</div></div>""", unsafe_allow_html=True)
                    for t in [x for x in transfer_list if x['to']==dashboard_view]:
                        st.markdown(f"""<div class="transfer-ticket"><span>From <b>{t['from']}</b></span><span style="color:#28a745; font-weight:bold;">+{t['amount']:,.0f}</span></div>""", unsafe_allow_html=True)
                elif my_bal < -0.5:
                    st.markdown(f"""<div class="mission-box-debt premium-card"><div>應付</div><div style="font-size:1.8rem; font-weight:bold;">-{currency} {abs(my_bal):,.1f}</div></div>""", unsafe_allow_html=True)
                    for t in [x for x in transfer_list if x['from']==dashboard_view]:
                        st.markdown(f"""<div class="transfer-ticket"><span>To <b>{t['to']}</b></span><span style="color:#cf1322; font-weight:bold;">➜ {t['amount']:,.0f}</span></div>""", unsafe_allow_html=True)
                else:
                    st.success("🎉 帳目已平！")
                st.divider()

            # --- E. 全員表格 (🔥 這裡做了重點修正：全部壓成單行字串) ---
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown("##### 📊 帳務狀態表")
                
                # HTML 組合：全部用單行字串，避免 Python 縮排干擾 Markdown
                html_parts = []
                html_parts.append('<table class="styled-table"><thead><tr><th>成員</th><th>淨額</th><th>狀態</th></tr></thead><tbody>')
                
                for member, net in sorted_bal:
                    net_val = float(net)
                    if net_val > 0.5:
                        row_cls = "status-green"
                        badge = "<span style='background:#f6ffed; color:#2FB8AC; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>給我錢錢</span>"
                        color = "#2FB8AC"
                        txt = f"+{net_val:,.2f}"
                    elif net_val < -0.5:
                        row_cls = "status-red"
                        badge = "<span style='background:#fff1f0; color:#E5533D; padding:2px 8px; border-radius:10px; font-size:0.8rem; font-weight:bold;'>交出錢錢</span>"
                        color = "#E5533D"
                        txt = f"{net_val:,.2f}"
                    else:
                        row_cls = "status-gray"
                        badge = "<span style='color:#888; font-size:0.8rem;'>平帳</span>"
                        color = "#ccc"
                        txt = "0.00"
                    
                    # 🔥 關鍵：這裡不要換行，也不要縮排，直接串成一行 HTML
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
                    # 這裡也都改成單行 HTML
                    st.markdown('<div class="premium-card">', unsafe_allow_html=True)
                    for t in transfer_list:
                        st.markdown(f"""<div class="transfer-ticket"><div style="text-align:center;"><small style="color:#888;">付款</small><br><b>{t['from']}</b></div><div style="color:#ccc;">➜ <b style="color:#333; font-size:0.9rem;">${t['amount']:,.0f}</b></div><div style="text-align:center;"><small style="color:#888;">收款</small><br><b>{t['to']}</b></div></div>""", unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
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
    if os.path.exists("history"):
        files = sorted([f for f in os.listdir("history") if f.endswith(".csv")], reverse=True)
        for f in files:
            with open(os.path.join("history", f), "rb") as hf:
                st.download_button(f"📥 {f}", hf, file_name=f, key=f)