import streamlit as st
import pandas as pd
import os
import json
import time

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
st.title("✈️ 旅程分帳系統 (動態成員版)")

# 讀取現有成員
if 'members' not in st.session_state:
    st.session_state['members'] = load_members()

# --- 側邊欄：成員管理 (升級版) ---
with st.sidebar:
    st.header("👥 成員管理")
    
    # A. 新增成員區
    new_name = st.text_input("輸入新成員名字")
    if st.button("➕ 新增成員"):
        if new_name and new_name not in st.session_state['members']:
            st.session_state['members'].append(new_name)
            save_members(st.session_state['members'])
            st.success(f"已新增 {new_name}")
            st.rerun()
        elif new_name in st.session_state['members']:
            st.warning("這個名字已經在名單裡了")
    
    st.divider()
    
    # B. 進階管理區 (修改與刪除)
    st.write("🔧 **進階操作**")
    
    # 如果有名單才顯示操作區
    if st.session_state['members']:
        # 讓使用者選擇要對誰開刀
        target_member = st.selectbox("選擇成員", st.session_state['members'])
        
        # 選擇動作
        action = st.radio("動作", ["修改名字", "移除這位成員"], horizontal=True)
        
        if action == "修改名字":
            rename_input = st.text_input(f"把 {target_member} 改名為：")
            if st.button("確認改名"):
                if rename_input and rename_input != target_member:
                    # 1. 修改名單列表 (JSON)
                    st.session_state['members'] = [rename_input if x == target_member else x for x in st.session_state['members']]
                    save_members(st.session_state['members'])
                    
                    # 2. 修改記帳資料 (CSV) - 這一步最重要！
                    if os.path.exists(DATA_FILE):
                        df_update = pd.read_csv(DATA_FILE)
                        # 更新「付款人」
                        df_update['Payer'] = df_update['Payer'].replace(target_member, rename_input)
                        
                        # 更新「分帳人」 (因為是逗號字串，要拆開來處理)
                        def update_beneficiaries(b_str):
                            if pd.isna(b_str): return b_str
                            names = str(b_str).split(',')
                            # 如果遇到舊名字就換新名字
                            new_names = [rename_input if n.strip() == target_member else n.strip() for n in names]
                            return ",".join(new_names)
                            
                        df_update['Beneficiaries'] = df_update['Beneficiaries'].apply(update_beneficiaries)
                        
                        # 存檔
                        df_update.to_csv(DATA_FILE, index=False)
                    
                    st.success(f"已將 {target_member} 改名為 {rename_input} (相關帳務已同步更新)")
                    time.sleep(1)
                    st.rerun()
                    
        elif action == "移除這位成員":
            st.warning(f"注意：移除 {target_member} 只會從選單移除，不會刪除他過去的記帳紀錄。")
            if st.button(f"確定移除 {target_member}"):
                st.session_state['members'].remove(target_member)
                save_members(st.session_state['members'])
                st.rerun()

    # 顯示目前名單的小清單
    with st.expander("查看目前完整名單"):
        for m in st.session_state['members']:
            st.write(f"- {m}")

    st.divider()
    # 危險區域
    if st.button("⚠️ 清空所有成員 (重置)"):
        st.session_state['members'] = []
        save_members([])
        st.rerun()

# --- 主畫面：記帳邏輯 ---
# 檢查是否有成員，如果沒有，停止渲染後面的內容
if not st.session_state['members']:
    st.info("👈 請先在左側側邊欄「新增成員」才能開始記帳喔！")
    st.stop()

# 1. 讀取/初始化帳務資料
# 1. 讀取/初始化帳務資料
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    
    # --- 🔥 新增這行：自動清洗髒資料 ---
    # 如果發現有 'Unnamed: 0' 這種奇怪的欄位 (Excel 或舊存檔造成的)，直接刪除
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    
else:
    df = pd.DataFrame(columns=['Date', 'Item', 'Payer', 'Amount', 'Currency', 'Beneficiaries'])

# --- 定義彈出視窗函數 (放在主邏輯之前) ---

# A. 新增用的彈出視窗 (修正版：解決按鈕失效問題)
@st.dialog("➕ 新增一筆消費")
def add_entry_dialog():
    with st.form("add_form"):
        st.write("請輸入消費細節：")
        col1, col2 = st.columns(2)
        item = col1.text_input("消費項目 (如: 晚餐、車票)")
        amount = col2.number_input("金額", min_value=0.0, step=10.0)
        
        col3, col4 = st.columns(2)
        payer = col3.selectbox("誰先付錢?", st.session_state['members'])
        currency = col4.selectbox("幣別", CURRENCIES)
        
        beneficiaries = st.multiselect(
            "分給誰? (預設全員)", 
            st.session_state['members'], 
            default=st.session_state['members']
        )
        
        st.markdown("---")
        st.caption("確認以上資訊無誤後，請按下儲存：")
        
        # 改成單一按鈕，直接觸發儲存，避免 Streamlit 巢狀按鈕失效的問題
        submitted = st.form_submit_button("✅ 確認無誤，立即儲存")

        if submitted:
            if amount > 0 and len(beneficiaries) > 0 and item:
                # 重新讀取最新的 df (避免覆蓋)
                if os.path.exists(DATA_FILE):
                    current_df = pd.read_csv(DATA_FILE)
                else:
                    current_df = pd.DataFrame(columns=['Date', 'Item', 'Payer', 'Amount', 'Currency', 'Beneficiaries'])
                
                new_entry = {
                    'Date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
                    'Item': item,
                    'Payer': payer,
                    'Amount': amount,
                    'Currency': currency,
                    'Beneficiaries': ",".join(beneficiaries)
                }
                
                # 存檔邏輯
                current_df = pd.concat([current_df, pd.DataFrame([new_entry])], ignore_index=True)
                current_df.to_csv(DATA_FILE, index=False)
                st.success("已儲存！")
                st.rerun()
            else:
                st.error("❌ 儲存失敗：請檢查「項目名稱」、「金額」與「分帳人」是否都有填寫？")
                
# B. 修改用的彈出視窗
@st.dialog("✏️ 修改消費內容")
def edit_entry_dialog(index, row_data):
    # 先解析原本的分帳人字串變回 list
    original_beneficiaries = str(row_data['Beneficiaries']).split(",")
    # 過濾掉可能不存在的舊成員
    valid_defaults = [m for m in original_beneficiaries if m in st.session_state['members']]

    with st.form("edit_form"):
        col1, col2 = st.columns(2)
        item = col1.text_input("消費項目", value=row_data['Item'])
        amount = col2.number_input("金額", min_value=0.0, step=10.0, value=float(row_data['Amount']))
        
        col3, col4 = st.columns(2)
        # 處理付款人：如果原本的人被刪掉了，就預設選第一個
        default_payer_index = 0
        if row_data['Payer'] in st.session_state['members']:
            default_payer_index = st.session_state['members'].index(row_data['Payer'])
        
        payer = col3.selectbox("誰先付錢?", st.session_state['members'], index=default_payer_index)
        
        # 處理幣別
        default_curr_index = 0
        if row_data['Currency'] in CURRENCIES:
            default_curr_index = CURRENCIES.index(row_data['Currency'])
        currency = col4.selectbox("幣別", CURRENCIES, index=default_curr_index)
        
        beneficiaries = st.multiselect(
            "分給誰?", 
            st.session_state['members'], 
            default=valid_defaults
        )
        
        submitted = st.form_submit_button("💾 儲存修改")
        
        if submitted:
            # 讀取檔案
            if os.path.exists(DATA_FILE):
                current_df = pd.read_csv(DATA_FILE)
                
                # 更新該筆資料 (使用 index 定位)
                current_df.at[index, 'Item'] = item
                current_df.at[index, 'Amount'] = amount
                current_df.at[index, 'Payer'] = payer
                current_df.at[index, 'Currency'] = currency
                current_df.at[index, 'Beneficiaries'] = ",".join(beneficiaries)
                
                current_df.to_csv(DATA_FILE, index=False)
                st.success("修改完成！")
                st.rerun()

# 2. 新增帳目區域 (改為按鈕觸發彈窗)
with st.container(border=True):
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.subheader("📝 帳目管理")
    with col_b:
        if st.button("➕ 新增一筆", use_container_width=True, type="primary"):
            add_entry_dialog()

# 3. 顯示與管理流水帳 (包含修改與刪除)
if not df.empty:
    # 顯示表格
    st.dataframe(df, use_container_width=True)
    
    st.caption("👇 若要修改或刪除，請輸入對應的行號 (最左邊的數字 0, 1, 2...)")
    
    col_manage1, col_manage2, col_manage3 = st.columns([1, 1, 1])
    
    with col_manage1:
        target_index = st.number_input("選擇行號 (Index)", min_value=0, max_value=max(0, len(df)-1), step=1, label_visibility="collapsed")
    
    with col_manage2:
        if st.button("✏️ 修改此筆", use_container_width=True):
            # 抓取該行資料並開啟彈窗
            target_row = df.iloc[target_index]
            edit_entry_dialog(target_index, target_row)
            
    with col_manage3:
        if st.button("🗑️ 刪除此筆", use_container_width=True):
            df = df.drop(df.index[target_index])
            df.to_csv(DATA_FILE, index=False)
            st.success(f"已刪除第 {target_index} 筆")
            st.rerun()
else:
    st.info("目前沒有資料，請點擊右上方「新增一筆」按鈕。")

# 4. 自動結算邏輯
st.divider()
st.subheader("💰 結算儀表板")

# 小工具：把數字變好看
def format_money(val):
    if val == int(val):
        return f"{int(val)}"
    else:
        return f"{val:.2f}"

if not df.empty:
    grouped = df.groupby('Currency')
    
    tabs = st.tabs([f"{curr}" for curr in grouped.groups.keys()])
    
    for i, (currency, group) in enumerate(grouped):
        with tabs[i]:
            st.write(f"### {currency} 帳務總覽")
            
            # --- 步驟 1: 計算每個人的淨額 ---
            balances = {m: 0.0 for m in st.session_state['members']}
            
            for index, row in group.iterrows():
                amt = float(row['Amount'])
                who_paid = row['Payer']
                if who_paid not in balances: balances[who_paid] = 0.0

                who_benefits = str(row['Beneficiaries']).split(",")
                valid_beneficiaries = [b for b in who_benefits if b]
                
                if valid_beneficiaries:
                    balances[who_paid] += amt
                    split_amt = amt / len(valid_beneficiaries)
                    for b in valid_beneficiaries:
                        if b not in balances: balances[b] = 0.0
                        balances[b] -= split_amt

            # --- 步驟 2: 修整數字 ---
            for k, v in balances.items():
                balances[k] = round(v, 2)

            # --- 步驟 3: 顯示餘額表 (這裡修好了！) ---
            res_df = pd.DataFrame(list(balances.items()), columns=['成員', '淨額'])
            
            def get_status(x):
                if x > 0: return f"應收 {format_money(x)}"
                elif x < 0: return f"應付 {format_money(abs(x))}"
                else: return "✅ 平帳"
            
            res_df['狀態'] = res_df['淨額'].apply(get_status)
            
            # 修正點：我們要檢查的是「文字」有沒有包含「應收」或「應付」
            def color_surplus(val):
                val_str = str(val) # 強制轉成文字
                if "應收" in val_str:
                    return 'background-color: #d4edda; color: #155724' # 綠色
                elif "應付" in val_str:
                    return 'background-color: #f8d7da; color: #721c24' # 紅色
                return 'color: gray' # 平帳

            st.caption("👇 每個人目前的欠款/收款總額：")
            st.dataframe(res_df[['成員', '狀態']].style.applymap(color_surplus, subset=['狀態']), use_container_width=True)

            # --- 步驟 4: 計算轉帳路徑 ---
            st.markdown("#### 💸 建議轉帳路徑 (誰付給誰)")
            
            debtors = []
            creditors = []
            
            for person, amount in balances.items():
                if amount < -0.01: debtors.append({'person': person, 'amount': amount})
                elif amount > 0.01: creditors.append({'person': person, 'amount': amount})
            
            debtors.sort(key=lambda x: x['amount'])
            creditors.sort(key=lambda x: x['amount'], reverse=True)
            
            transfer_list = []
            i = 0 
            j = 0
            
            while i < len(debtors) and j < len(creditors):
                debtor = debtors[i]
                creditor = creditors[j]
                amount = min(abs(debtor['amount']), creditor['amount'])
                
                transfer_list.append(f"🔴 **{debtor['person']}** 應轉給 🟢 **{creditor['person']}** : {format_money(amount)}")
                
                debtor['amount'] += amount
                creditor['amount'] -= amount
                
                if abs(debtor['amount']) < 0.01: i += 1
                if creditor['amount'] < 0.01: j += 1
            
            if not transfer_list:
                st.success("🎉 目前沒有人需要轉帳！")
            else:
                for transfer in transfer_list:
                    st.write(transfer)

else:
    st.info("目前還沒有記帳資料。")

# --- 這裡是用來「存檔」跟「讀檔」的功能區 ---
st.markdown("---") 
st.header("💾 資料備份與還原")

# 1. 製作「下載按鈕」
try:
    if os.path.exists(DATA_FILE):
        current_df = pd.read_csv(DATA_FILE)
        csv_data = current_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 下載目前的記帳紀錄 (請務必在關閉前下載！)",
            data=csv_data,
            file_name="trip_ledger_backup.csv",
            mime="text/csv",
        )
    else:
        st.warning("目前還沒有檔案可以下載。")
except Exception as e:
    st.error(f"下載功能發生錯誤: {e}")

# 2. 製作「上傳按鈕」 (強力修正版：同步更新資料與成員)
uploaded_file = st.file_uploader("📤 上傳上次備份的 CSV 檔 (還原紀錄)", type=["csv"])

if uploaded_file is not None:
    # A. 覆蓋舊的記帳檔案
    with open(DATA_FILE, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # B. 同步成員名單 (最重要的一步！從檔案裡把人找回來)
    try:
        # 讀取剛剛寫入的新檔案
        df_restore = pd.read_csv(DATA_FILE)
        
        # 準備一個集合來收集名字 (避免重複)
        restored_members = set(st.session_state.get('members', []))
        
        # 1. 抓付款人 (Payer)
        if 'Payer' in df_restore.columns:
            payers = df_restore['Payer'].dropna().astype(str).unique()
            restored_members.update(payers)
            
        # 2. 抓分帳人 (Beneficiaries)
        if 'Beneficiaries' in df_restore.columns:
            for ben_str in df_restore['Beneficiaries'].dropna():
                # 拆解逗號 "Alice,Bob" -> ["Alice", "Bob"]
                names = str(ben_str).split(',')
                restored_members.update([n.strip() for n in names if n.strip()])
        
        # C. 存回系統設定
        # 更新記憶體中的名單
        st.session_state['members'] = sorted(list(restored_members)) 
        # 更新硬碟中的名單檔案 (json)
        save_members(st.session_state['members'])
        
        # D. 顯示成功並自動重整
        st.success(f"🎉 還原成功！已同步帳目與 {len(restored_members)} 位成員資料。")
        st.progress(100) # 給個進度條視覺回饋
        time.sleep(1.0)  # 停頓 1 秒讓使用者看到成功訊息
        st.rerun()       # <--- 關鍵！強迫網頁立刻從頭重跑，讓上方的表格更新
        
    except Exception as e:
        st.error(f"還原過程中發生錯誤，請檢查 CSV 格式: {e}")