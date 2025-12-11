import streamlit as st
import pandas as pd
import os
import json

# --- 設定檔案路徑 ---
DATA_FILE = 'trip_ledger.csv'      # 存帳務資料
CONFIG_FILE = 'members.json'       # 存成員名單
CURRENCIES = ['TWD', 'JPY', 'USD', 'EUR', 'KRW'] # 這裡可以自己擴充

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

if not df.empty:
    grouped = df.groupby('Currency')
    
    tabs = st.tabs([f"{curr}" for curr in grouped.groups.keys()])
    
    for i, (currency, group) in enumerate(grouped):
        with tabs[i]:
            st.write(f"### {currency} 結算")
            balances = {m: 0.0 for m in st.session_state['members']}
            
            for index, row in group.iterrows():
                amt = row['Amount']
                who_paid = row['Payer']
                
                # 處理可能發生的舊成員已被刪除的情況
                if who_paid not in balances: balances[who_paid] = 0.0

                who_benefits = str(row['Beneficiaries']).split(",")
                
                # 先墊錢的人 +
                balances[who_paid] += amt
                
                # 分錢的人 -
                valid_beneficiaries = [b for b in who_benefits if b] # 過濾空字串
                if valid_beneficiaries:
                    split_amt = amt / len(valid_beneficiaries)
                    for b in valid_beneficiaries:
                        if b not in balances: balances[b] = 0.0
                        balances[b] -= split_amt
            
            # 格式化顯示
            res_df = pd.DataFrame(list(balances.items()), columns=['成員', '結算金額'])
            res_df['狀態'] = res_df['結算金額'].apply(
                lambda x: f"應收 {x:.2f}" if x > 0 else (f"應付 {abs(x):.2f}" if x < 0 else "平")
            )
            
            # 用顏色標記 (收錢顯示綠色，付錢顯示紅色)
            def color_surplus(val):
                color = '#d4edda' if val > 0 else '#f8d7da' if val < 0 else 'transparent'
                return f'background-color: {color}'

            st.dataframe(res_df.style.applymap(color_surplus, subset=['結算金額']))
            
            # 簡單的文字總結
            st.caption("正數代表因為先墊錢所以要「收錢」，負數代表需要「拿錢出來」。")

else:
    st.info("目前還沒有記帳資料。")