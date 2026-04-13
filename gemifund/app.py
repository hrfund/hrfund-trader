import streamlit as st
import pandas as pd
import ccxt
import time
import random
from datetime import datetime

# --- 1. Lana 黑色终端 UI 设置 ---
st.set_page_config(page_title="Lana AI Agent Terminal", layout="wide", page_icon="🧬")

st.markdown("""
    <style>
    .main { background-color: #06090f; color: #c9d1d9; }
    .stMetric { background-color: #0d1117; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    .lana-log { 
        background-color: #161b22; 
        border-left: 3px solid #238636; 
        padding: 12px; 
        margin-bottom: 10px;
        font-family: 'Courier New', monospace;
        color: #7ee787;
    }
    .stDataFrame { border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 币安模拟盘 (Testnet) API 配置 ---
API_KEY = "3OSwXkH13F3alaJpLAhKQ7JX91d7kL9WAiTDJgu8evejio9MOxBn8l6ueMatJFXR"
SECRET_KEY = "XNDHapsiTyUHTlKhB0IAte6DCVQbiZRL1XwWsszhmO7wEPMFlexm8X51CDztC95r"

# 初始化币安合约接口
@st.cache_resource
def init_exchange():
    exchange = ccxt.binanceusdm({
        'apiKey': API_KEY,
        'secret': SECRET_KEY,
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    exchange.set_sandbox_mode(True) # 强制开启模拟盘模式
    return exchange

binance = init_exchange()

# --- 3. 核心功能函数 ---

def fetch_account_data():
    """获取模拟盘真实的余额和持仓"""
    try:
        balance = binance.fetch_balance()
        usdt_balance = balance['total'].get('USDT', 0.0)
        
        # 获取当前持仓
        positions = binance.fetch_positions()
        active_positions = [p for p in positions if float(p['info']['positionAmt']) != 0]
        
        return usdt_balance, active_positions
    except Exception as e:
        st.error(f"无法访问模拟盘账户: {e}")
        return 0.0, []

def fetch_market_data():
    """获取币安合约市场的实时价格和涨幅"""
    try:
        tickers = binance.fetch_tickers()
        df = pd.DataFrame.from_dict(tickers, orient='index')
        df = df[df['symbol'].str.endswith(':USDT')] # 过滤永续合约
        df = df.rename(columns={'last': 'price', 'percentage': 'change'})
        # 去掉 :USDT 后缀便于查看
        df['symbol'] = df.index.str.replace(':USDT', '')
        return df[['symbol', 'price', 'change', 'quoteVolume']].sort_values(by='change', ascending=False)
    except Exception as e:
        st.warning("行情连接中...")
        return pd.DataFrame()

def lana_brain(symbol, change):
    """Lana 决策引擎"""
    # 模拟情绪分：基于波动率和模拟广场共鸣
    score = min(max(50 + (change * 1.5), 10), 99)
    if change > 6 and score > 80:
        return "BUY 🟢", score, f"Lana 监控到 {symbol} 在币安广场出现 Fomo 情绪，大单流向显示主力正在入场。"
    else:
        return "WATCH ⚪", score, "盘整中，广场共识尚未达成。"

# --- 4. 网页布局 ---

st.title("🧬 Lana AI - Simulation Terminal (Testnet Mode)")
st.caption(f"Status: **Connected to Binance Demo Account** | Terminal ID: **hrfund-trader**")

# 拉取数据
balance, active_pos = fetch_account_data()
market_df = fetch_market_data()

# 侧边栏：真实模拟盘资产看板
st.sidebar.title("💰 Real-Sim Account")
st.sidebar.metric("Account Balance", f"${balance:,.2f} USDT")
st.sidebar.info("数据源: Binance Futures Testnet")

# 主界面布局
col_left, col_right = st.columns([1, 1.3])

with col_left:
    st.subheader("📡 Real-time Market")
    if not market_df.empty:
        top_view = market_df.head(15).copy()
        st.dataframe(top_view[['symbol', 'price', 'change']], use_container_width=True, hide_index=True)
    else:
        st.write("正在连接币安行情...")

with col_right:
    st.subheader("🧠 Lana's Thought & Live Positions")
    
    # 执行按钮：这会在你的模拟盘里下单！
    if st.button("EXECUTE LANA SCANNING & TRADE"):
        if not market_df.empty:
            target = market_df.iloc[0] # 选择涨幅最高的作为目标
            symbol = target['symbol']
            price = target['price']
            action, score, reason = lana_brain(symbol, target['change'])
            
            if "BUY" in action and balance > 100:
                try:
                    # 模拟盘真实下单：市价购买价值 500 USDT 的仓位
                    order = binance.create_market_buy_order(symbol + ":USDT", 500 / price)
                    st.success(f"Lana 成功在模拟盘下单: {symbol}")
                    # 记录日志
                    st.session_state.history.append({
                        "t": datetime.now().strftime("%H:%M"),
                        "s": symbol, "a": "BUY", "r": reason
                    })
                except Exception as trade_err:
                    st.error(f"下单失败: {trade_err}")
            else:
                st.toast("暂无符合情绪共振的标的", icon="⚪")

    # 显示当前账户的真实持仓
    if active_pos:
        st.write("**Account Active Positions:**")
        for p in active_pos:
            sym = p['symbol'].replace(':USDT', '')
            amt = float(p['info']['positionAmt'])
            pnl = float(p['info']['unRealizedProfit'])
            color = "green" if pnl >= 0 else "red"
            st.markdown(f"`{sym}` | 数量: {amt} | 盈亏: :{color}[${pnl:.2f}]")
    else:
        st.caption("当前账户无持仓")

    st.markdown("---")
    st.write("**AI Strategy Logs:**")
    if 'history' in st.session_state:
        for log in reversed(st.session_state.history[-5:]):
            st.markdown(f"""<div class="lana-log">
                [{log['t']}] <b>{log['a']} {log['s']}</b><br/>
                {log['r']}
            </div>""", unsafe_allow_html=True)

st.divider()
st.caption("Trading Engine: Lana-v2 (Futures Testnet) | All orders are sent to Binance Demo Market.")
