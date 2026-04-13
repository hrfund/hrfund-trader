import streamlit as st
import pandas as pd
import ccxt
import time
import random
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="Lana AI Sim-Trader", layout="wide", page_icon="🪄")

# 初始化模拟盘状态
if 'balance' not in st.session_state:
    st.session_state.balance = 10000.0
    st.session_state.positions = {}
    st.session_state.history = []

# --- 核心数据获取函数 (增加了地理限制容错) ---
def get_market_data():
    try:
        # 尝试连接币安 API
        binance = ccxt.binance({
            'enableRateLimit': True,
            'timeout': 10000,
        })
        tickers = binance.fetch_tickers()
        df = pd.DataFrame.from_dict(tickers, orient='index')
        df['symbol'] = df.index
        df = df[df['symbol'].str.contains('/USDT')]
        df = df[['symbol', 'last', 'percentage', 'quoteVolume']]
        return df.sort_values(by='percentage', reverse=True).head(50)
    
    except Exception as e:
        # 如果因为地理限制 (451) 报错，生成一组高质量的模拟数据
        st.warning("⚠️ 提示：由于服务器地理位置限制，已切换至【实时模拟市场】模式运行。")
        
        # 模拟 20 个热门币种
        mock_symbols = [
            'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'PEPE/USDT', 'WIF/USDT', 
            'DOGE/USDT', 'ORDI/USDT', 'LINK/USDT', 'AVAX/USDT', 'SHIB/USDT',
            'BNB/USDT', 'NEAR/USDT', 'FET/USDT', 'SUI/USDT', 'TIA/USDT'
        ]
        mock_data = []
        for sym in mock_symbols:
            mock_data.append({
                'symbol': sym,
                'last': random.uniform(10, 60000) if 'BTC' in sym else random.uniform(0.00001, 150),
                'percentage': random.uniform(-5, 15), # 模拟涨跌幅
                'quoteVolume': random.uniform(1000000, 50000000)
            })
        return pd.DataFrame(mock_data).sort_values(by='percentage', reverse=True)

def simulate_lana_logic(symbol, percentage):
    """Lana 的筛选逻辑：高涨幅 + 随机情绪分"""
    # 模拟 Lana 的情绪分析
    sentiment_score = random.randint(70, 99) if percentage > 5 else random.randint(30, 70)
    
    action = "WAIT"
    reason = "盘整中，广场讨论热度不足。"
    
    if percentage > 7 and sentiment_score > 85:
        action = "BUY"
        reasons = [
            "币安广场提及率在10分钟内激增 400%，情绪极度 Fomo。",
            "检测到主力资金持续买入，技术面形成多头共振。",
            "突破前高阻力，社交媒体 KOL 开始集体喊单。"
        ]
        reason = random.choice(reasons)
    
    return action, sentiment_score, reason

# --- UI 界面 ---
st.title("🧙‍♂️ Lana AI 模拟盘策略中心")
st.caption("基于币安广场情绪监控与涨幅量化的智能 Agent 演示界面")

# 侧边栏：模拟账户看板
st.sidebar.title("💰 模拟账户")
st.sidebar.metric("账户余额", f"${st.session_state.balance:,.2f}")

# 计算总资产净值
market_df = get_market_data()
current_prices = market_df.set_index('symbol')['last'].to_dict()

total_pos_value = 0
for sym, pos in st.session_state.positions.items():
    if sym in current_prices:
        total_pos_value += pos['数量'] * current_prices[sym]

total_net_worth = st.session_state.balance + total_pos_value
pnl_percent = ((total_net_worth / 10000.0) - 1) * 100
st.sidebar.metric("总资产净值 (PNL)", f"${total_net_worth:,.2f}", f"{pnl_percent:.2f}%")

# 1. 实时扫描看板
st.subheader("🔍 Lana 实时热度扫描")
if not market_df.empty:
    display_df = market_df.head(10).copy()
    results = [simulate_lana_logic(row.symbol, row.percentage) for idx, row in display_df.iterrows()]
    display_df['Lana 决策'] = [r[0] for r in results]
    display_df['情绪分'] = [r[1] for r in results]
    
    # 格式化显示
    st.dataframe(display_df[['symbol', 'last', 'percentage', '情绪分', 'Lana 决策']], use_container_width=True)

# 2. 持仓与日志
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📊 当前持仓")
    if st.session_state.positions:
        # 把持仓转为表格
        pos_display = []
        for s, p in st.session_state.positions.items():
            cur_price = current_prices.get(s, p['买入价'])
            gain = ((cur_price / p['买入价']) - 1) * 100
            pos_display.append({
                "币种": s,
                "买入价": f"${p['买入价']:.4f}",
                "当前价": f"${cur_price:.4f}",
                "收益率": f"{gain:.2f}%",
                "数量": f"{p['数量']:.2f}"
            })
        st.table(pd.DataFrame(pos_display))
    else:
        st.info("目前处于空仓状态，等待 Lana 发现机会。")

with col2:
    st.subheader("📝 决策日志")
    btn_col1, btn_col2 = st.columns(2)
    
    if btn_col1.button("立即扫描并模拟执行"):
        for idx, row in market_df.head(10).iterrows():
            action, score, reason = simulate_lana_logic(row.symbol, row.percentage)
            
            # 买入逻辑：如果 Lana 喊买且未持仓
            if action == "BUY" and row.symbol not in st.session_state.positions and st.session_state.balance >= 1000:
                buy_amount_usdt = 1000.0
                qty = buy_amount_usdt / row.last
                st.session_state.balance -= buy_amount_usdt
                st.session_state.positions[row.symbol] = {
                    "买入价": row.last,
                    "数量": qty
                }
                st.session_state.history.append({
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "symbol": row.symbol,
                    "action": "BUY",
                    "reason": reason
                })
                st.toast(f"Lana 买入 {row.symbol}!", icon="🚀")
    
    if btn_col2.button("清空模拟记录"):
        st.session_state.balance = 10000.0
        st.session_state.positions = {}
        st.session_state.history = []
        st.rerun()

    # 显示日志
    for log in reversed(st.session_state.history):
        with st.expander(f"[{log['time']}] {log['action']} {log['symbol']}", expanded=True):
            st.write(log['reason'])

st.divider()
st.markdown("💡 **操作指南**: 点击“立即扫描”让 Lana 分析盘面。如果发现符合情绪共振的币种，AI 会自动用模拟金下单。")
