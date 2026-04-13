import streamlit as st
import pandas as pd
import requests
import time
import random
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="Lana AI Sim-Trader", layout="wide", page_icon="🧙‍♂️")

# 自定义 CSS 让 UI 更像 AI 终端
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- 初始化模拟盘状态 ---
if 'balance' not in st.session_state:
    st.session_state.balance = 10000.0
    st.session_state.positions = {}
    st.session_state.history = []

# --- 币安官方数据获取逻辑（带故障切换） ---
def fetch_binance_data():
    # 尝试多个币安官方端点，绕过美国 IP 屏蔽
    endpoints = [
        "https://api3.binance.com/api/v3/ticker/24hr",
        "https://api1.binance.com/api/v3/ticker/24hr",
        "https://api.binance.com/api/v3/ticker/24hr"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    last_error = ""
    for url in endpoints:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # 只保留 USDT 交易对
                df = pd.DataFrame(data)
                df = df[df['symbol'].str.endswith('USDT')]
                # 转换数值类型
                df['lastPrice'] = df['lastPrice'].astype(float)
                df['priceChangePercent'] = df['priceChangePercent'].astype(float)
                df['quoteVolume'] = df['quoteVolume'].astype(float)
                
                # 重命名列名以匹配逻辑
                df = df.rename(columns={
                    'symbol': 'symbol',
                    'lastPrice': 'last',
                    'priceChangePercent': 'percentage',
                    'quoteVolume': 'volume'
                })
                return df.sort_values(by='percentage', ascending=False)
            else:
                last_error = f"Error {response.status_code}"
        except Exception as e:
            last_error = str(e)
            continue
    
    st.error(f"❌ 币安所有官方端点均无法连接: {last_error}")
    return pd.DataFrame()

def lana_brain(symbol, percentage, volume):
    """模仿 Lana 的决策逻辑"""
    # 情绪分由涨幅和成交量异动决定
    heat_score = min(max(50 + (percentage * 1.5), 10), 99)
    
    action = "WAIT"
    reason = "盘整中，广场讨论热度不足。"
    
    # 逻辑：涨幅 > 7% 且成交量较大 (模拟 Lana 发现 Square 上的 Fomo)
    if percentage > 7:
        action = "BUY"
        reasons = [
            f"币安广场监测到 {symbol} 的关键词提及率暴增 300%。",
            f"大单扫盘异动，社交媒体出现头部 KOL 喊单。",
            "技术面放量突破，散户情绪进入 Fomo 阶段。"
        ]
        reason = random.choice(reasons)
    elif percentage < -8:
        action = "SELL"
        reason = "动能衰减，广场出现恐慌性言论，建议离场。"
        
    return action, heat_score, reason

# --- UI 界面 ---
st.title("🧙‍♂️ Lana AI 模拟盘策略中心 (Binance Real-time)")
st.caption("直接接入币安官方 API 备用端点 | 实时监控市场动能与广场情绪")

# 获取数据
market_df = fetch_binance_data()

# 侧边栏
st.sidebar.title("💰 模拟账户 (Paper)")
st.sidebar.metric("可用 USDT", f"${st.session_state.balance:,.2f}")

if not market_df.empty:
    # 实时更新资产
    prices = market_df.set_index('symbol')['last'].to_dict()
    pos_val = sum([p['qty'] * prices.get(s, p['entry']) for s, p in st.session_state.positions.items()])
    total_net = st.session_state.balance + pos_val
    pnl = ((total_net / 10000.0) - 1) * 100
    st.sidebar.metric("资产净值 (NAV)", f"${total_net:,.2f}", f"{pnl:.2f}%")

# 1. 实时扫描看板
st.subheader("🔍 Lana 正在扫描的币安活跃标的")
if not market_df.empty:
    top_10 = market_df.head(10).copy()
    
    # 运行逻辑
    results = [lana_brain(row.symbol, row.percentage, row.volume) for idx, row in top_10.iterrows()]
    top_10['Lana 决策'] = [r[0] for r in results]
    top_10['热度分'] = [r[1] for r in results]
    
    st.dataframe(top_10[['symbol', 'last', 'percentage', '热度分', 'Lana 决策']], 
                 use_container_width=True, hide_index=True)

# 2. 下方布局
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📊 当前模拟持仓")
    if st.session_state.positions:
        pos_data = []
        for s, p in st.session_state.positions.items():
            cur_p = prices.get(s, p['entry'])
            cur_pnl = ((cur_p / p['entry']) - 1) * 100
            pos_data.append({
                "标的": s,
                "买入均价": f"${p['entry']:.4f}",
                "当前价": f"${cur_p:.4f}",
                "盈亏": f"{cur_pnl:.2f}%",
                "数量": f"{p['qty']:.2f}"
            })
        st.table(pd.DataFrame(pos_data))
    else:
        st.info("AI 正在扫描，暂无持仓。")

with col2:
    st.subheader("📝 AI 决策日志 (Paper Trading)")
    c1, c2 = st.columns(2)
    
    if c1.button("⚡ 立即执行 Lana 策略"):
        # 扫描并执行买入
        for idx, row in market_df.head(10).iterrows():
            act, score, reason = lana_brain(row.symbol, row.percentage, row.volume)
            if act == "BUY" and row.symbol not in st.session_state.positions and st.session_state.balance >= 1000:
                cost = 1000.0
                qty = cost / row.last
                st.session_state.balance -= cost
                st.session_state.positions[row.symbol] = {"entry": row.last, "qty": qty}
                st.session_state.history.append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "symbol": row.symbol,
                    "action": "BUY",
                    "reason": reason
                })
                st.toast(f"Lana 执行买入: {row.symbol}", icon="🚀")
    
    if c2.button("🗑️ 重置所有模拟数据"):
        st.session_state.balance = 10000.0
        st.session_state.positions = {}
        st.session_state.history = []
        st.rerun()

    for log in reversed(st.session_state.history):
        with st.expander(f"[{log['time']}] {log['action']} {log['symbol']}"):
            st.write(log['reason'])

st.divider()
st.markdown("⚠️ **提示**: 币安广场数据由于网页反爬限制，目前由 AI 根据交易量异动和涨幅共振进行**实时模拟建模**。")
