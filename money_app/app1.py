import streamlit as st
import pandas as pd
import os
import json

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

# --- 側邊欄：成員管理 ---
with st.sidebar:
    st.header("👥 成員管理")
    
    # 新增成員
    new_name = st.text_input("輸入新成員名字")
    if st.button("新增成員"):
        if new_name and new_name not in st.session_state['members']:
            st.session_state['members'].append(new_name)
            save_members(st.session_state['members'])
            st.success(f"已新增 {new_name}")
            st.rerun()
        elif new_name in st.session_state['members']:
            st.warning("這個名字已經在名單裡了")
        else:
            st.warning("請輸入名字")

    # 顯示目前成員並允許重置
    st.divider()
    st.write("目前成員：")
    for m in st.session_state['members']:
        st.write(f"- {m}")
    
    if st.button("⚠️ 清空所有成員"):
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
else:
    df = pd.DataFrame(columns=['Date', 'Item', 'Payer', 'Amount', 'Currency', 'Beneficiaries'])

# 2. 新增帳目區域
with st.container(border=True):
    st.subheader("➕ 新增一筆消費")
    with st.form("entry_form"):
        col1, col2 = st.columns(2)
        item = col1.text_input("消費項目 (如: 晚餐、車票)")
        amount = col2.number_input("金額", min_value=0.0, step=10.0)
        
        col3, col4 = st.columns(2)
        # 這裡的選單會根據 session_state['members'] 動態改變
        payer = col3.selectbox("誰先付錢?", st.session_state['members'])
        currency = col4.selectbox("幣別", CURRENCIES)
        
        # 多選：分給誰？預設全選
        beneficiaries = st.multiselect(
            "分給誰? (預設全員)", 
            st.session_state['members'], 
            default=st.session_state['members']
        )
        
        submitted = st.form_submit_button("儲存這筆帳")
        
        if submitted:
            if amount > 0 and len(beneficiaries) > 0:
                new_entry = {
                    'Date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
                    'Item': item,
                    'Payer': payer,
                    'Amount': amount,
                    'Currency': currency,
                    'Beneficiaries': ",".join(beneficiaries)
                }
                df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                st.success("已儲存！")
                st.rerun()
            else:
                st.error("請輸入金額並至少選擇一位分帳成員")

# 3. 顯示與管理流水帳
st.divider()
st.subheader("📝 消費明細")
if not df.empty:
    st.dataframe(df, use_container_width=True)
    
    with st.expander("🗑️ 刪除舊資料"):
        idx_to_delete = st.number_input("輸入要刪除的行號 (Index)", min_value=0, max_value=max(0, len(df)-1), step=1)
        if st.button("刪除該行"):
            df = df.drop(df.index[idx_to_delete])
            df.to_csv(DATA_FILE, index=False)
            st.success("已刪除")
            st.rerun()

# 4. 自動結算邏輯
st.divider()
st.subheader("💰 結算儀表板")

# 小工具：把數字變好看 (如果是整數就不要顯示 .00)
def format_money(val):
    if val == int(val):
        return f"{int(val)}"
    else:
        return f"{val:.2f}"

if not df.empty:
    grouped = df.groupby('Currency')
    
    # 建立分頁，每個幣別一個分頁
    tabs = st.tabs([f"{curr}" for curr in grouped.groups.keys()])
    
    for i, (currency, group) in enumerate(grouped):
        with tabs[i]:
            st.write(f"### {currency} 帳務總覽")
            
            # --- 步驟 1: 計算每個人的淨額 (Net Balance) ---
            balances = {m: 0.0 for m in st.session_state['members']}
            
            for index, row in group.iterrows():
                amt = float(row['Amount'])
                who_paid = row['Payer']
                
                # 初始化：防止舊成員資料報錯
                if who_paid not in balances: balances[who_paid] = 0.0

                who_benefits = str(row['Beneficiaries']).split(",")
                valid_beneficiaries = [b for b in who_benefits if b] # 過濾空字串
                
                if valid_beneficiaries:
                    # 先墊錢的人 (加回去)
                    balances[who_paid] += amt
                    
                    # 分錢的人 (扣掉)
                    split_amt = amt / len(valid_beneficiaries)
                    for b in valid_beneficiaries:
                        if b not in balances: balances[b] = 0.0
                        balances[b] -= split_amt

            # --- 步驟 2: 修整數字 (解決 0.0000001 的問題) ---
            # 強制四捨五入到小數點後 2 位
            for k, v in balances.items():
                balances[k] = round(v, 2)

            # --- 步驟 3: 顯示餘額表 ---
            # 製作顯示用的表格
            res_df = pd.DataFrame(list(balances.items()), columns=['成員', '淨額'])
            
            # 增加狀態描述
            def get_status(x):
                if x > 0: return f"應收 {format_money(x)}"
                elif x < 0: return f"應付 {format_money(abs(x))}"
                else: return "✅ 平帳"
            
            res_df['狀態'] = res_df['淨額'].apply(get_status)
            
            # 顏色設定
            def color_surplus(val):
                if val > 0: return 'background-color: #d4edda; color: #155724' # 綠色
                elif val < 0: return 'background-color: #f8d7da; color: #721c24' # 紅色
                return 'color: gray' # 平帳

            st.caption("👇 每個人目前的欠款/收款總額：")
            st.dataframe(res_df[['成員', '狀態']].style.applymap(color_surplus, subset=['狀態']), use_container_width=True)

            # --- 步驟 4: 計算「誰該付錢給誰」 (核心演算法) ---
            st.markdown("#### 💸 建議轉帳路徑 (誰付給誰)")
            
            # 分成兩組：欠錢的人 (Debtors) 和 收錢的人 (Creditors)
            debtors = []
            creditors = []
            
            for person, amount in balances.items():
                # 忽略金額太小的誤差 (例如 0.01)
                if amount < -0.01:
                    debtors.append({'person': person, 'amount': amount})
                elif amount > 0.01:
                    creditors.append({'person': person, 'amount': amount})
            
            # 排序：金額大的排前面，減少轉帳次數 (Greedy Algorithm)
            debtors.sort(key=lambda x: x['amount'])       # 負越多的排前面
            creditors.sort(key=lambda x: x['amount'], reverse=True) # 正越多的排前面
            
            transfer_list = []
            
            # 開始配對
            i = 0 # 指向欠錢的人
            j = 0 # 指向收錢的人
            
            while i < len(debtors) and j < len(creditors):
                debtor = debtors[i]
                creditor = creditors[j]
                
                # 要轉帳的金額 = min(欠錢的人欠的錢, 收錢的人該收的錢)
                amount = min(abs(debtor['amount']), creditor['amount'])
                
                # 紀錄這一筆
                transfer_list.append(f"🔴 **{debtor['person']}** 應轉給 🟢 **{creditor['person']}** : {format_money(amount)}")
                
                # 更新餘額
                debtor['amount'] += amount
                creditor['amount'] -= amount
                
                # 如果這個人還完了/收完了，就換下一個人
                if abs(debtor['amount']) < 0.01:
                    i += 1
                if creditor['amount'] < 0.01:
                    j += 1
            
            # 顯示結果
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
    current_df = pd.read_csv("trip_ledger.csv")
    csv_data = current_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 下載目前的記帳紀錄 (請務必在關閉前下載！)",
        data=csv_data,
        file_name="trip_ledger_backup.csv",
        mime="text/csv",
    )
except:
    st.warning("目前還沒有記帳資料可以下載喔！")

# 2. 製作「上傳按鈕」
uploaded_file = st.file_uploader("📤 上傳上次備份的 CSV 檔 (還原紀錄)", type=["csv"])

if uploaded_file is not None:
    with open("trip_ledger.csv", "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success("🎉 紀錄還原成功！請點擊下方按鈕重新整理。")
    if st.button("點我重新整理載入資料"):
        st.rerun()
        