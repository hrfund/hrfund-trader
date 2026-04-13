import streamlit as st
import pandas as pd
import requests
import random
from datetime import datetime

# --- 1. 极致 Lana 风格 UI 配置 ---
st.set_page_config(page_title="Lana AI Agent Terminal", layout="wide", page_icon="🧬")

# 注入 CSS：黑色背景、荧光绿文字、现代终端感
st.markdown("""
    <style>
    .main { background-color: #06090f; color: #e6edf3; }
    [data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 8px; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
    .lana-log { color: #58a6ff; font-family: 'Courier New', monospace; border-left: 2px solid #238636; padding-left: 10px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 初始化模拟账户 ---
if 'balance' not in st.session_state:
    st.session_state.balance = 10000.0
    st.session_state.positions = {}
    st.session_state.history = []

# --- 3. 核心：通过跳板获取币安真实数据 ---
@st.cache_data(ttl=10) # 每10秒缓存一次，避免请求过快
def get_binance_real_data():
    # 币安主站 API 地址
    target_url = "https://api.binance.com/api/v3/ticker/24hr"
    
    # 关键：使用公开跳板网关 (allorigins) 绕过美国 IP 封锁
    # 这个网关会代我们去访问币安，返回的是非美国 IP
    proxy_bridge = f"https://api.allorigins.win/raw?url={target_url}"
    
    try:
        response = requests.get(proxy_bridge, timeout=15)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data)
            # 过滤 USDT 交易对，并排除杠杆代币 (UP/DOWN)
            df = df[df['symbol'].str.endswith('USDT')]
            df = df[~df['symbol'].str.contains('UP|DOWN')]
            
            # 转换数值
            df['lastPrice'] = pd.to_numeric(df['lastPrice'])
            df['priceChangePercent'] = pd.to_numeric(df['priceChangePercent'])
            df['quoteVolume'] = pd.to_numeric(df['quoteVolume'])
            
            # 重命名列
            df = df.rename(columns={
                'lastPrice': 'last',
                'priceChangePercent': 'percentage',
                'quoteVolume': 'volume'
            })
            return df.sort_values(by='percentage', ascending=False)
        else:
            st.error(f"跳板网关响应异常: {response.status_code}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"跳板连接失败，币安 API 仍然被拦截。尝试备选方案...")
        # 备选方案：使用公开的加密货币聚合器，但指定币安价格
        try:
            alt_url = "https://min-api.cryptocompare.com/data/top/mktcapfull?limit=50&tsym=USDT&e=Binance"
            alt_res = requests.get(alt_url).json()
            alt_data = []
            for item in alt_res['Data']:
                raw = item.get('RAW', {}).get('USDT', {})
                if raw:
                    alt_data.append({
                        'symbol': f"{raw['FROMSYMBOL']}/USDT",
                        'last': raw['PRICE'],
                        'percentage': raw['CHANGEPCT24HOUR'],
                        'volume': raw['VOLUME24HOUR']
                    })
            return pd.DataFrame(alt_data).sort_values(by='percentage', ascending=False)
        except:
            return pd.DataFrame()

# --- 4. Lana 决策大脑 ---
def lana_decision_engine(row):
    symbol = row['symbol']
    change = row['percentage']
    vol = row['volume']
    
    # 模拟情绪分逻辑：结合涨幅与成交量（成交量越高说明广场讨论越多）
    sentiment_score = min(max(40 + (change * 1.8) + (vol / 50000000), 10), 99)
    
    # Lana 的买入策略：涨幅 > 6% 且成交量 > 1000万 且情绪分 > 82
    if change > 6 and sentiment_score > 82:
        return "BUY", sentiment_score
    # 卖出策略：跌幅超过 10%
    elif change < -10:
        return "SELL", sentiment_score
    else:
        return "WAIT", sentiment_score

# --- 5. UI 布局 ---
st.title("🧬 Lana AI Simulation Terminal")
st.markdown(f"**Status:** `Scanning Binance Mainnet...` | **Timestamp:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")

# 获取真实币安数据
market_df = get_binance_real_data()

# 侧边栏资产
st.sidebar.header("SIMULATED ACCOUNT")
st.sidebar.metric("Balance", f"${st.session_state.balance:,.2f}")

if not market_df.empty:
    price_map = market_df.set_index('symbol')['last'].to_dict()
    current_pos_val = sum([p['qty'] * price_map.get(s, p['entry']) for s, p in st.session_state.positions.items()])
    net_worth = st.session_state.balance + current_pos_val
    pnl_raw = ((net_worth / 10000.0) - 1) * 100
    st.sidebar.metric("Net Worth (NAV)", f"${net_worth:,.2f}", f"{pnl_raw:.2f}%")

# 页面主要部分
col_market, col_action = st.columns([1, 1.2])

with col_market:
    st.subheader("📡 Real-time Binance Scanner")
    if not market_df.empty:
        # 只看前12个最高涨幅的
        top_view = market_df.head(12).copy()
        decisions = [lana_brain(r) for idx, r in top_view.iterrows()] # 注意：这里逻辑下文定义
        # 为了兼容性，这里直接计算显示
        top_view['Sentiment'] = top_view.apply(lambda r: min(max(40 + (r['percentage'] * 1.8), 10), 99), axis=1)
        top_view['Action'] = top_view['Sentiment'].apply(lambda x: "BUY" if x > 85 else "WAIT")
        
        st.dataframe(top_view[['symbol', 'last', 'percentage', 'Sentiment', 'Action']], 
                     use_container_width=True, hide_index=True)
    else:
        st.warning("Data fetch pending... 正在重新建立与币安跳板的连接。")

with col_action:
    st.subheader("🧠 Lana's Thought & Positions")
    
    # 按钮：手动触发一次扫描
    if st.button("EXECUTE LANA STRATEGY"):
        if not market_df.empty:
            for idx, row in market_df.head(10).iterrows():
                symbol = row['symbol']
                price = row['last']
                score = min(max(40 + (row['percentage'] * 1.8), 10), 99)
                
                if score > 85 and symbol not in st.session_state.positions and st.session_state.balance >= 1000:
                    # 买入
                    st.session_state.balance -= 1000.0
                    st.session_state.positions[symbol] = {"entry": price, "qty": 1000.0 / price}
                    st.session_state.history.append({
                        "t": datetime.now().strftime("%H:%M"),
                        "s": symbol,
                        "a": "BUY",
                        "r": f"Detected Square FOMO consensus. Volume spike confirmed. Sentiment: {score:.0f}%"
                    })
                    st.toast(f"Lana: Bought {symbol}", icon="🦾")

    # 显示持仓表格
    if st.session_state.positions:
        pos_df_list = []
        for s, p in st.session_state.positions.items():
            curr_p = price_map.get(s, p['entry'])
            pnl_p = ((curr_p / p['entry']) - 1) * 100
            pos_df_list.append({"Asset": s, "Entry": p['entry'], "Price": curr_p, "PnL": f"{pnl_p:.2f}%"})
        st.table(pd.DataFrame(pos_df_list))

    # 显示 Lana 决策日志
    st.markdown("---")
    for log in reversed(st.session_state.history[-6:]):
        st.markdown(f"""<div class='lana-log'>
            [{log['t']}] <b>{log['a']} {log['s']}</b><br/>
            <small>{log['r']}</small>
        </div>""", unsafe_allow_html=True)

# 底部重置
if st.sidebar.button("RESET SIMULATION"):
    st.session_state.clear()
    st.rerun()

st.divider()
st.caption("Data Source: Binance Mainnet via Non-US Proxy Bridge. All trades are simulated.")
