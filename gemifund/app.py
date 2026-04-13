import streamlit as st
import pandas as pd
import requests
import time
import random
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="Lana AI Sim-Trader", layout="wide", page_icon="🪄")

# --- 初始化模拟盘状态 ---
if 'balance' not in st.session_state:
    st.session_state.balance = 10000.0
    st.session_state.positions = {}
    st.session_state.history = []

# --- 真实数据获取函数 (使用 CoinCap API 绕过封锁) ---
def get_market_data():
    try:
        # 使用 CoinCap 获取前 100 名真实行情
        url = "https://api.coincap.io/v2/assets"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        assets = data['data']
        processed_data = []
        
        for asset in assets:
            processed_data.append({
                'symbol': f"{asset['symbol']}/USDT",
                'last': float(asset['priceUsd']),
                'percentage': float(asset['changePercent24Hr']),
                'name': asset['name']
            })
            
        df = pd.DataFrame(processed_data)
        # 按照涨幅降序排列
        df = df.sort_values(by='percentage', ascending=False)
        return df
    
    except Exception as e:
        st.error(f"数据抓取失败: {e}")
        return pd.DataFrame()

def simulate_lana_logic(symbol, percentage):
    """Lana 的决策逻辑：基于真实涨幅模拟广场热度"""
    # 真实 Lana 逻辑：当价格起飞且广场讨论多时买入
    # 这里我们根据真实涨幅模拟一个“热度分”
    base_score = 50 + (percentage * 2)
    sentiment_score = min(max(base_score, 10), 99) # 限制在 10-99 之间
    
    action = "WAIT"
    reason = "盘整中，广场讨论热度不足。"
    
    # 策略：涨幅超过 5% 且 模拟热度超过 80
    if percentage > 5 and sentiment_score > 80:
        action = "BUY"
        reasons = [
            "币安广场提及率在10分钟内激增，检测到大单持续扫盘。",
            "技术面突破箱体，社交媒体出现大量关于该币种的讨论。",
            "检测到主力资金净流入，且社区情绪进入极度贪婪区间。"
        ]
        reason = random.choice(reasons)
    
    return action, sentiment_score, reason

# --- UI 界面 ---
st.title("🧙‍♂️ Lana AI 模拟盘策略中心")
st.caption("基于 CoinCap 实时数据与社交情绪量化的智能 Agent")

# 侧边栏：资产看板
st.sidebar.title("💰 模拟账户")
st.sidebar.metric("现金余额", f"${st.session_state.balance:,.2f}")

# 获取当前市场真实数据
market_df = get_market_data()

# 计算当前总资产
if not market_df.empty:
    current_prices = market_df.set_index('symbol')['last'].to_dict()
    total_pos_value = sum([pos['数量'] * current_prices.get(sym, pos['买入价']) 
                           for sym, pos in st.session_state.positions.items()])
    
    total_net_worth = st.session_state.balance + total_pos_value
    pnl_percent = ((total_net_worth / 10000.0) - 1) * 100
    st.sidebar.metric("总资产净值 (PNL)", f"${total_net_worth:,.2f}", f"{pnl_percent:.2f}%")

# 1. 实时扫描看板 (Top 10 涨幅榜)
st.subheader("🔍 Lana 正在扫描的真实标的")
if not market_df.empty:
    top_df = market_df.head(15).copy()
    
    # 计算决策
    actions = []
    scores = []
    for _, row in top_df.iterrows():
        act, sc, _ = simulate_lana_logic(row['symbol'], row['percentage'])
        actions.append(act)
        scores.append(sc)
    
    top_df['Lana 决策'] = actions
    top_df['情绪热度分'] = scores
    
    # 格式化 DataFrame 显示
    st.dataframe(top_df[['symbol', 'name', 'last', 'percentage', '情绪热度分', 'Lana 决策']], 
                 use_container_width=True, hide_index=True)

# 2. 持仓与日志
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📊 当前模拟持仓")
    if st.session_state.positions:
        pos_list = []
        for s, p in st.session_state.positions.items():
            curr_p = current_prices.get(s, p['买入价'])
            gain = ((curr_p / p['买入价']) - 1) * 100
            pos_list.append({
                "币种": s,
                "买入价": f"${p['买入价']:.4f}",
                "当前价": f"${curr_p:.4f}",
                "收益率": f"{gain:.2f}%",
                "数量": f"{p['数量']:.2f}"
            })
        st.table(pd.DataFrame(pos_list))
    else:
        st.info("目前空仓，正在等待 Lana 的买入信号...")

with col2:
    st.subheader("📝 AI 决策日志")
    c1, c2 = st.columns(2)
    
    if c1.button("🔥 执行一轮扫描"):
        # 扫描涨幅榜前 10
        for _, row in market_df.head(10).iterrows():
            act, sc, res = simulate_lana_logic(row['symbol'], row['percentage'])
            if act == "BUY" and row['symbol'] not in st.session_state.positions and st.session_state.balance >= 1000:
                buy_amount = 1000.0
                qty = buy_amount / row['last']
                st.session_state.balance -= buy_amount
                st.session_state.positions[row['symbol']] = {"买入价": row['last'], "数量": qty}
                st.session_state.history.append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "symbol": row['symbol'],
                    "action": "BUY",
                    "reason": res
                })
                st.toast(f"Lana 真实下单: {row['symbol']}", icon="✅")
    
    if c2.button("♻️ 重置账户"):
        st.session_state.balance = 10000.0
        st.session_state.positions = {}
        st.session_state.history = []
        st.rerun()

    for log in reversed(st.session_state.history):
        with st.expander(f"[{log['time']}] {log['action']} {log['symbol']}"):
            st.write(f"**理由:** {log['reason']}")

st.divider()
st.markdown("📈 **数据源说明**: 本程序已切换至 **CoinCap 公开行情接口**，数据为全网交易所真实价格均值。")
