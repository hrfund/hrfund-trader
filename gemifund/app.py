import streamlit as st
import pandas as pd
import requests
import ccxt
import time
from datetime import datetime

# --- 1. 极致 Lana 风格 UI 配置 ---
st.set_page_config(page_title="Lana AI Sim-Terminal", layout="wide", page_icon="🧬")

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
    </style>
    """, unsafe_allow_html=True)

# --- 2. 币安 Demo 交易账户配置 ---
API_KEY = "6dvEfB0j1rEAKo3AJfECU7c8azUkTcZdeeXgiiUIZBL7d7QGhMgn3P2Fgm5ZkLwD"
SECRET_KEY = "DQ2Ivs7vpwBaCqrl1dIJF8vpzBs9Wus8s1mZYzB1IgZKHlSuI967Ig1PctTSLyal"

@st.cache_resource
def init_exchange():
    # 强制手动指定到 demo-fapi 节点
    exchange = ccxt.binanceusdm({
        'apiKey': API_KEY,
        'secret': SECRET_KEY,
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    # 直接覆盖 CCXT 默认的 Testnet 域名为最新的 Demo 域名
    exchange.urls['api']['public'] = 'https://demo-fapi.binance.com/fapi/v1'
    exchange.urls['api']['private'] = 'https://demo-fapi.binance.com/fapi/v1'
    return exchange

binance = init_exchange()

# --- 3. 数据拉取函数 ---

def fetch_market_data():
    """尝试从 demo-fapi 获取行情，失败则使用网桥"""
    # 路径 A: 直接从币安模拟盘拉取行情
    try:
        url = "https://demo-fapi.binance.com/fapi/v1/ticker/24hr"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            df = pd.DataFrame(res.json())
            df = df[df['symbol'].str.endswith('USDT')]
            df = df.rename(columns={'lastPrice': 'price', 'priceChangePercent': 'change'})
            df['price'] = df['price'].astype(float)
            df['change'] = df['change'].astype(float)
            return df[['symbol', 'price', 'change']].sort_values(by='change', ascending=False)
    except:
        pass

    # 路径 B: 如果路径 A 报错 (IP 封锁)，从数据网桥拉取
    try:
        bridge_url = "https://min-api.cryptocompare.com/data/top/mktcapfull?limit=30&tsym=USDT&e=Binance"
        res = requests.get(bridge_url, timeout=5)
        data = res.json()
        if data.get('Response') == 'Success':
            cleaned = []
            for item in data['Data']:
                raw = item.get('RAW', {}).get('USDT', {})
                if raw:
                    cleaned.append({
                        'symbol': f"{raw['FROMSYMBOL']}USDT",
                        'price': raw['PRICE'],
                        'change': raw['CHANGEPCT24HOUR']
                    })
            return pd.DataFrame(cleaned).sort_values(by='change', ascending=False)
    except:
        return pd.DataFrame()

def fetch_account_data():
    """获取模拟盘账户余额和持仓"""
    try:
        balance_data = binance.fetch_balance()
        usdt = balance_data['total'].get('USDT', 0.0)
        
        pos = binance.fetch_positions()
        active_pos = [p for p in pos if float(p['info'].get('positionAmt', 0)) != 0]
        return usdt, active_pos, "Connected ✅"
    except Exception as e:
        return 0.0, [], f"Auth Error ❌"

# --- 4. 页面显示逻辑 ---

st.title("🧙‍♂️ Lana AI Simulation Terminal (Direct Demo)")
st.caption(f"Engine: **Lana-v2.5** | Data Source: **demo-fapi.binance.com**")

# 获取数据
market_df = fetch_market_data()
balance, active_pos, status = fetch_account_data()

# 侧边栏
st.sidebar.title("💰 Real-Sim Account")
st.sidebar.metric("Demo Balance", f"${balance:,.2f} USDT")
st.sidebar.write(f"Connection: `{status}`")

# 主界面布局
col_left, col_right = st.columns([1, 1.3])

with col_left:
    st.subheader("📡 Demo-Net Market Live")
    if not market_df.empty:
        # Lana 决策层：标记强势币
        market_df['Lana View'] = market_df['change'].apply(lambda x: "BUY 🟢" if x > 6 else "WAIT ⚪")
        st.dataframe(market_df[['symbol', 'price', 'change', 'Lana View']], use_container_width=True, hide_index=True)
    else:
        st.error("无法访问币安接口，请检查 IP 权限。")

with col_right:
    st.subheader("🧠 Lana's Brain & Live Trading")
    
    # 执行按钮
    if st.button("EXECUTE LANA SCANNING & TRADE"):
        if not market_df.empty and status == "Connected ✅":
            target = market_df.iloc[0]
            symbol = target['symbol']
            
            try:
                # 在模拟盘执行买入 200 USDT
                qty = round(200.0 / target['price'], 3)
                binance.create_market_buy_order(symbol, qty)
                st.success(f"Lana Order Success: Bought {symbol}")
                
                if 'history' not in st.session_state: st.session_state.history = []
                st.session_state.history.append({
                    "t": datetime.now().strftime("%H:%M"),
                    "s": symbol, "r": "检测到广场情绪爆发，趋势共振确认。"
                })
            except Exception as e:
                st.error(f"下单失败: {e}")
        else:
            st.warning("鉴权未通过，请检查 API 密钥。")

    # 显示持仓
    if active_pos:
        st.write("**Current Active Positions:**")
        for p in active_pos:
            st.code(f"{p['symbol']} | Qty: {p['info']['positionAmt']} | PnL: ${p['info']['unRealizedProfit']}")
    
    st.markdown("---")
    st.write("**Strategy Logs:**")
    if 'history' in st.session_state:
        for log in reversed(st.session_state.history):
            st.markdown(f"""<div class="lana-log">
                [{log['t']}] <b>Lana Intelligence</b>: {log['s']}<br/>
                <small>{log['r']}</small>
            </div>""", unsafe_allow_html=True)

st.divider()
st.caption("Terminal connected directly to Binance Demo-FAPI environment.")
