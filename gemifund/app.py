import streamlit as st
import pandas as pd
import ccxt
import time
import random
from datetime import datetime

# --- 配置 ---
st.set_page_config(page_title="Lana AI Sim-Trader", layout="wide", page_icon="🪄")

# 初始化模拟盘状态 (使用 Session State 模拟数据库)
if 'balance' not in st.session_state:
    st.session_state.balance = 10000.0
    st.session_state.positions = {} # { symbol: {entry_price, amount, time} }
    st.session_state.history = []   # 交易日志

# --- 数据获取函数 ---
def get_market_data():
    try:
        binance = ccxt.binance()
        tickers = binance.fetch_tickers()
        df = pd.DataFrame.from_dict(tickers, orient='index')
        # 计算 24h 涨幅
        df['symbol'] = df.index
        df = df[df['symbol'].str.contains('/USDT')]
        df = df[['symbol', 'last', 'percentage', 'quoteVolume']]
        # 筛选涨幅前 50 名作为 Lana 的初选池
        top_gainers = df.sort_values(by='percentage', reverse=True).head(50)
        return top_gainers
    except Exception as e:
        st.error(f"连接币安 API 失败: {e}")
        return pd.DataFrame()

def simulate_lana_logic(symbol, percentage, volume):
    """
    模拟 Lana 的筛选逻辑：
    结合涨幅 + 交易量异动 (作为广场情绪的代用指标)
    """
    # 模拟情绪分 (真实情况应接入爬虫分析词频)
    sentiment_score = random.randint(60, 98) if percentage > 5 else random.randint(20, 65)
    
    # 逻辑：涨幅 > 8% 且 情绪分 > 85，执行买入
    action = "WAIT"
    reason = "盘整中，广场讨论热度不足。"
    
    if percentage > 8 and sentiment_score > 85:
        action = "BUY"
        reasons = [
            "币安广场提及率突增，散户情绪开始 Fomo。",
            "检测到主力资金在大单净流入，动能极强。",
            "突破关键阻力位，社交媒体看多预期达成共识。"
        ]
        reason = random.choice(reasons)
    elif percentage < -5:
        action = "SELL"
        reason = "动能衰减，跌破支撑，广场情绪转冷。"
        
    return action, sentiment_score, reason

# --- UI 界面 ---
st.title("🧙‍♂️ Lana AI 模拟盘策略中心")
st.caption("基于币安广场情绪监控与涨幅量化的智能 Agent 模拟界面")

# 侧边栏：模拟盘资产
st.sidebar.title("💰 模拟账户")
st.sidebar.metric("账户余额", f"${st.session_state.balance:,.2f}")
if st.session_state.positions:
    total_value = st.session_state.balance + sum([p['amount'] * get_market_data().loc[s]['last'] for s, p in st.session_state.positions.items() if s in get_market_data().index])
else:
    total_value = st.session_state.balance
st.sidebar.metric("总资产净值 (PNL)", f"${total_value:,.2f}", f"{((total_value/10000)-1)*100:.2f}%")

# 第一部分：Lana 正在扫描的标的
st.subheader("🔍 Lana 实时热度扫描")
market_df = get_market_data()
if not market_df.empty:
    display_df = market_df.head(10).copy()
    display_df['Lana 决策'], display_df['情绪分'], _ = zip(*[simulate_lana_logic(row.symbol, row.percentage, row.quoteVolume) for idx, row in display_df.iterrows()])
    st.dataframe(display_df, use_container_width=True)

# 第二部分：持仓与决策日志
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📊 当前持仓")
    if st.session_state.positions:
        pos_df = pd.DataFrame.from_dict(st.session_state.positions, orient='index')
        st.table(pos_df)
    else:
        st.info("目前处于空仓状态，等待 Lana 发现机会。")

with col2:
    st.subheader("📝 决策流日志 (Lana's Logic)")
    # 模拟自动交易循环
    if st.button("立即扫描并执行"):
        for idx, row in market_df.head(10).iterrows():
            action, score, reason = simulate_lana_logic(row.symbol, row.percentage, row.quoteVolume)
            
            # 模拟买入逻辑
            if action == "BUY" and row.symbol not in st.session_state.positions and st.session_state.balance > 1000:
                buy_cost = 1000.0 # 固定每仓 1000 刀
                amount = buy_cost / row.last
                st.session_state.balance -= buy_cost
                st.session_state.positions[row.symbol] = {
                    "买入价": row.last,
                    "数量": amount,
                    "时间": datetime.now().strftime("%H:%M:%S")
                }
                st.session_state.history.append({"time": datetime.now(), "symbol": row.symbol, "action": "BUY", "reason": reason})
                st.success(f"Lana 执行买入: {row.symbol} | 理由: {reason}")
    
    for log in reversed(st.session_state.history[-5:]):
        st.write(f"**[{log['time'].strftime('%H:%M')}] {log['action']} {log['symbol']}**")
        st.caption(f"理由: {log['reason']}")

st.divider()
st.markdown("⚠️ **提示**: 本网页为 Lana AI 模拟环境，所有操作均为虚拟资金。你可以根据 Lana 的决策日志手动在真实交易所跟单。")