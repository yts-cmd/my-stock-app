import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 및 모바일 반응형 CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="PRO 주식 매매 차트 (초단타~중장기 분석)",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 모바일 화면 대응 반응형 및 PWA 전체화면 커스텀 CSS/메타태그
st.markdown("""
<!-- PWA & 모바일 웹앱 전체화면 메타태그 -->
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="주식분석PRO">
<meta name="theme-color" content="#2563EB">

<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    .trading-header {
        display: flex;
        align-items: baseline;
        gap: 12px;
        margin-bottom: 6px;
        flex-wrap: wrap;
    }
    .current-price-up {
        font-size: 2.2rem;
        font-weight: 800;
        color: #EF4444;
    }
    .current-price-down {
        font-size: 2.2rem;
        font-weight: 800;
        color: #3B82F6;
    }
    .badge-up {
        background-color: #FEE2E2;
        color: #DC2626;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.95rem;
    }
    .badge-down {
        background-color: #DBEAFE;
        color: #2563EB;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.95rem;
    }
    @media (max-width: 768px) {
        .current-price-up, .current-price-down {
            font-size: 1.6rem !important;
        }
        .badge-up, .badge-down {
            font-size: 0.85rem !important;
            padding: 2px 6px !important;
        }
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            padding-top: 1rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 사이드바 - 종목/지수 선택 & 티커 검색 기록 자동 저장 시스템
# -----------------------------------------------------------------------------
st.sidebar.header("🎯 종목 및 시장 선택")

import json
import os

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "search_history.json")

def get_search_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def add_search_history(ticker: str):
    ticker = ticker.strip().upper()
    if not ticker or ticker == "CUSTOM":
        return
    history = get_search_history()
    if ticker in history:
        history.remove(ticker)
    history.insert(0, ticker)  # 최신 검색어가 맨 위로
    history = history[:15]     # 최대 15개 유지
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def clear_search_history():
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    except Exception:
        pass

# 기본 프리셋 종목 맵
BASE_TICKER_DICT = {
    "🇰🇷 코스피 (KOSPI)": "^KS11",
    "🇰🇷 코스닥 (KOSDAQ)": "^KQ11",
    "🇺🇸 S&P 500": "^GSPC",
    "🇺🇸 나스닥 (NASDAQ)": "^IXIC",
    "🇺🇸 다우 존스 (Dow Jones)": "^DJI",
    "🏢 삼성전자 (005930.KS)": "005930.KS",
    "🏢 SK하이닉스 (000660.KS)": "000660.KS",
    "🏢 현대차 (005380.KS)": "005380.KS",
    "🏢 NAVER (035420.KS)": "035420.KS",
    "🍎 애플 (AAPL)": "AAPL",
    "🚗 테슬라 (TSLA)": "TSLA",
    "⚡ 엔비디아 (NVDA)": "NVDA",
    "💻 마이크로소프트 (MSFT)": "MSFT"
}

# 저장된 최근 조회 기록 로드
saved_history = get_search_history()

# 드롭다운 메뉴 구성 (기본 프리셋 + 저장된 최근 조회 티커 + 직접 입력)
dropdown_options = list(BASE_TICKER_DICT.keys())

# 저장된 티커가 있으면 드롭다운에 추가
history_map = {}
if saved_history:
    for h in saved_history:
        label = f"⭐ [최근조회] {h}"
        dropdown_options.append(label)
        history_map[label] = h

dropdown_options.append("✏️ 직접 티커 새로 입력")

selected_name = st.sidebar.selectbox("분석할 종목 또는 지수 선택", dropdown_options, index=5)

# 선택에 따른 티커 심볼 결정
if selected_name == "✏️ 직접 티커 새로 입력":
    # 텍스트 입력창
    user_input = st.sidebar.text_input(
        "티커 심볼 입력 (예: 005490.KS, SOXL, QQQ, TSLA)",
        value=saved_history[0] if saved_history else "005490.KS"
    ).strip().upper()
    
    ticker_symbol = user_input
    display_title = f"직접 입력 ({ticker_symbol})"
    
    # 입력된 티커 자동 저장
    if ticker_symbol:
        add_search_history(ticker_symbol)
        
    # 최근 검색어 빠른 선택 태그 및 삭제
    if saved_history:
        st.sidebar.caption("📌 최근 조회 기록 (클릭 시 자동 입력):")
        tag_cols = st.sidebar.columns(3)
        for idx, h_tick in enumerate(saved_history[:6]):
            col_idx = idx % 3
            if tag_cols[col_idx].button(h_tick, key=f"quick_hist_{h_tick}"):
                ticker_symbol = h_tick
                display_title = f"직접 입력 ({ticker_symbol})"
                add_search_history(h_tick)
                st.rerun()

        if st.sidebar.button("🗑️ 최근 검색 기록 전체 삭제", use_container_width=True):
            clear_search_history()
            st.rerun()

elif selected_name in history_map:
    ticker_symbol = history_map[selected_name]
    display_title = f"{ticker_symbol} (최근 조회)"
    add_search_history(ticker_symbol)  # 다시 조회했으므로 최상단 갱신
else:
    ticker_symbol = BASE_TICKER_DICT[selected_name]
    display_title = selected_name

# -----------------------------------------------------------------------------
# 3. 요청사항: 분 / 시간 / 일 / 주 / 월 단위 캔들 봉 선택 시스템
# -----------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("⏱️ 캔들 주기(Timeframe) 설정")

# 1단계: 단위 대분류 선택 (분 / 시간 / 일·주·월)
unit_type = st.sidebar.radio(
    "1️⃣ 기준 단위 선택",
    ["분 단위 (Minute)", "시간 단위 (Hour)", "일/주/월 단위 (Day/Week/Month)"],
    index=2
)

# 2단계: 세부 주기 선택 및 데이터 수집 파라미터 매핑
if unit_type == "분 단위 (Minute)":
    sub_interval = st.sidebar.selectbox(
        "2️⃣ 세부 분봉 선택",
        ["1분봉", "3분봉", "5분봉", "10분봉", "15분봉", "30분봉"],
        index=2
    )
    # yfinance 제약조건(1분봉은 최대 7일, 그 외 분봉은 최대 60일 지원)에 맞춘 기간 선택
    if sub_interval in ["1분봉", "3분봉"]:
        period_options = {"최근 1일": "1d", "최근 3일": "3d", "최근 5일": "5d", "최근 7일": "7d"}
        selected_period_label = st.sidebar.selectbox("3️⃣ 조회 기간 (최대 7일)", list(period_options.keys()), index=2)
    else:
        period_options = {"최근 5일": "5d", "최근 15일": "15d", "최근 1개월": "1mo", "최근 2개월(60일)": "60d"}
        selected_period_label = st.sidebar.selectbox("3️⃣ 조회 기간 (최대 60일)", list(period_options.keys()), index=2)
    selected_period = period_options[selected_period_label]
    timeframe_desc = f"{sub_interval} ({selected_period_label})"
    is_intraday = True

elif unit_type == "시간 단위 (Hour)":
    sub_interval = st.sidebar.selectbox(
        "2️⃣ 세부 시간봉 선택",
        ["1시간봉", "2시간봉", "4시간봉", "6시간봉", "8시간봉"],
        index=0
    )
    # 시간봉은 최대 730일 지원
    period_options = {"최근 1개월": "1mo", "최근 3개월": "3mo", "최근 6개월": "6mo", "최근 1년": "1y", "최근 2년": "2y"}
    selected_period_label = st.sidebar.selectbox("3️⃣ 조회 기간", list(period_options.keys()), index=1)
    selected_period = period_options[selected_period_label]
    timeframe_desc = f"{sub_interval} ({selected_period_label})"
    is_intraday = True

else: # 일/주/월 단위
    sub_interval = st.sidebar.selectbox(
        "2️⃣ 세부 단위 선택",
        ["일봉 (Day)", "주봉 (Week)", "월봉 (Month)"],
        index=0
    )
    period_options = {"1개월": "1mo", "3개월": "3mo", "6개월": "6mo", "1년 (기본)": "1y", "3년": "3y", "5년": "5y"}
    selected_period_label = st.sidebar.selectbox("3️⃣ 조회 기간", list(period_options.keys()), index=3)
    selected_period = period_options[selected_period_label]
    timeframe_desc = f"{sub_interval} ({selected_period_label})"
    is_intraday = False

# -----------------------------------------------------------------------------
# 4. 사이드바 - 실시간 1초 단위 자동 갱신 & 지표 설정
# -----------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("⚡ 실시간 시세 & 자동 갱신")

auto_refresh = st.sidebar.checkbox("🟢 실시간 자동 갱신 (Live 모드)", value=True, help="네이버증권/실시간 거래소와 0초 딜레이로 연동되어 매 초마다 시세를 갱신합니다.")
refresh_sec = st.sidebar.select_slider(
    "자동 갱신 주기 (초)",
    options=[1, 2, 3, 5, 10],
    value=1,
    help="1초로 설정 시 1초마다 실시간 시세를 감지하여 차트를 새로고침합니다."
)

if auto_refresh:
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=refresh_sec * 1000, key="live_ticker_autorefresh")
    except Exception:
        pass

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 5선/20선 매매 전략 & 수수료 설정")

strategy_type = st.sidebar.selectbox(
    "매매 타점 전략 선택",
    [
        "⚡ 5선/20선 골든크로스 + 0.2%이상 목표익절 (추천)",
        "⚡ 5선/20선 순수 골든/데드크로스 타점",
        "🐢 20선/60선 중기 추세 크로스 타점"
    ],
    index=0,
    help="5일선과 20일선의 교차 타점 및 수수료를 극복하는 목표 익절 전략을 선택합니다."
)

fee_rate = st.sidebar.number_input(
    "💸 매매 수수료율 (% 단위, 제세금 포함)",
    min_value=0.0,
    max_value=1.0,
    value=0.2,
    step=0.05,
    help="매수/매도시 발생하는 총 수수료와 세금입니다. (매수 즉시 -0.2%부터 시작)"
)

if "목표익절" in strategy_type:
    target_net_profit = st.sidebar.number_input(
        "🎯 목표 순익절률 (% 단위, 수수료 0.2% 공제 후)",
        min_value=0.1,
        max_value=10.0,
        value=0.2,
        step=0.05,
        help="매수 즉시 수수료 0.2% 마이너스(-0.2%)로 시작하므로, 수수료를 모두 메꾸고 계좌에 실제로 남는 순수익 목표치(기본 +0.2% 이상)입니다."
    )
else:
    target_net_profit = 0.2

show_signals = st.sidebar.checkbox("🚀 차트 위 매수(▲)/매도(▼) 마커 표시", value=True)

with st.sidebar.expander("📌 캔들 차트 이동평균선 & 오버레이", expanded=True):
    show_ma_lines = st.checkbox("5선 · 20선 · 60선 이평선 표시", value=True, help="5선(보라), 20선(황금), 60선(초록)을 캔들 위에 표시합니다.")
    show_bb = st.checkbox("볼린저 밴드 (20, 2σ)", value=False)
    show_ema = st.checkbox("지수이동평균선 (EMA 5, 20, 60, 120)", value=False)
    show_ichimoku = st.checkbox("일목균형표 (9, 26, 52)", value=False)

with st.sidebar.expander("📊 하단 분할 보조지표", expanded=True):
    show_rsi = st.checkbox("1. RSI (14) [과매수 70 / 과매도 30]", value=True)
    show_vol = st.checkbox("2. 거래량 (Volume + 20MA)", value=True)
    show_macd = st.checkbox("3. MACD (12, 26, 9)", value=False)
    show_stoch = st.checkbox("4. 스토캐스틱 슬로우 (14, 3, 3)", value=False)
    show_disparity = st.checkbox("5. 이격도 (20선 기준)", value=False)

import requests
import re

def get_live_quote(ticker: str):
    """
    네이버증권 실시간 API(한국 주식/지수 0초 딜레이) 및 yfinance fast_info(미국) 연동
    """
    # 1. 한국 지수 (KOSPI, KOSDAQ)
    if ticker in ['^KS11', 'KOSPI']:
        try:
            r = requests.get('https://m.stock.naver.com/api/index/KOSPI/basic', headers={'User-Agent':'Mozilla/5.0'}, timeout=2).json()
            p = float(str(r.get('closePrice', '0')).replace(',', ''))
            c = float(str(r.get('compareToPreviousClosePrice', '0')).replace(',', ''))
            ratio = float(str(r.get('fluctuationsRatio', '0')).replace(',', ''))
            return p, c, ratio, r.get('localTradedAt', '')
        except Exception:
            pass
    elif ticker in ['^KQ11', 'KOSDAQ']:
        try:
            r = requests.get('https://m.stock.naver.com/api/index/KOSDAQ/basic', headers={'User-Agent':'Mozilla/5.0'}, timeout=2).json()
            p = float(str(r.get('closePrice', '0')).replace(',', ''))
            c = float(str(r.get('compareToPreviousClosePrice', '0')).replace(',', ''))
            ratio = float(str(r.get('fluctuationsRatio', '0')).replace(',', ''))
            return p, c, ratio, r.get('localTradedAt', '')
        except Exception:
            pass

    # 2. 한국 개별 주식 (6자리 종목코드 추출)
    kr_match = re.search(r'\d{6}', ticker)
    if kr_match:
        code = kr_match.group(0)
        try:
            r = requests.get(f'https://m.stock.naver.com/api/stock/{code}/basic', headers={'User-Agent':'Mozilla/5.0'}, timeout=2).json()
            p = float(str(r.get('closePrice', '0')).replace(',', ''))
            c = float(str(r.get('compareToPreviousClosePrice', '0')).replace(',', ''))
            ratio = float(str(r.get('fluctuationsRatio', '0')).replace(',', ''))
            return p, c, ratio, r.get('localTradedAt', '')
        except Exception:
            pass

    # 3. 미국/글로벌 종목 및 지수 (yfinance 빠른 시세 fast_info)
    try:
        stk = yf.Ticker(ticker)
        fi = stk.fast_info
        p = fi['last_price']
        prev = fi['previous_close']
        c = p - prev
        ratio = (c / prev) * 100 if prev else 0
        return float(p), float(c), float(ratio), '실시간(US)'
    except Exception:
        return None, None, None, None

# -----------------------------------------------------------------------------
# 5. 분봉/시간봉/일/주/월봉 데이터 로드 및 리샘플링 함수
# -----------------------------------------------------------------------------
@st.cache_data(ttl=15)  # 실시간 대응을 위해 캐시를 15초로 단축
def fetch_candle_data(ticker: str, u_type: str, s_interval: str, period: str):
    stock = yf.Ticker(ticker)
    
    if u_type == "분 단위 (Minute)":
        if s_interval in ["1분봉", "3분봉"]:
            raw = stock.history(period=period, interval="1m")
            if s_interval == "3분봉" and not raw.empty:
                return raw.resample('3min').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
            return raw
        else: # 5분, 10분, 15분, 30분
            base_int = "5m" if s_interval in ["5분봉", "10분봉"] else s_interval.replace("분봉", "m")
            raw = stock.history(period=period, interval=base_int)
            if s_interval == "10분봉" and not raw.empty:
                return raw.resample('10min').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
            return raw
            
    elif u_type == "시간 단위 (Hour)":
        raw = stock.history(period=period, interval="1h")
        if raw.empty:
            return raw
        rule = s_interval.replace("시간봉", "h")
        if rule == "1h":
            return raw
        return raw.resample(rule).agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
        
    else: # 일/주/월
        raw = stock.history(period=period, interval="1d")
        if raw.empty:
            return raw
        if "일봉" in s_interval:
            return raw
        elif "주봉" in s_interval:
            return raw.resample('W').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
        elif "월봉" in s_interval:
            return raw.resample('ME').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
    return raw

with st.spinner(f"'{display_title}' {timeframe_desc} 데이터를 수집하고 있습니다..."):
    df = fetch_candle_data(ticker_symbol, unit_type, sub_interval, selected_period)

if df is None or df.empty:
    st.error(f"'{ticker_symbol}'의 {timeframe_desc} 데이터를 불러올 수 없습니다. 다른 기간이나 종목을 선택해 주세요.")
    st.stop()

# 정상 로드된 경우 검색 기록에 안전하게 자동 저장
if ticker_symbol not in BASE_TICKER_DICT.values():
    add_search_history(ticker_symbol)

# 결측치 정제
df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
if len(df) < 5:
    st.warning("데이터 포인트가 너무 적습니다. 더 긴 조회 기간을 선택해 주세요.")
    st.stop()

# ⚡ [핵심] 네이버증권/실시간 거래소 0초 딜레이 호가 즉시 반영
live_price, live_change, live_ratio, live_time = get_live_quote(ticker_symbol)
has_live_quote = False
if live_price is not None and live_price > 0:
    has_live_quote = True
    # 캔들의 마지막 종가 및 고/저가를 실시간 현재가로 보정
    df.loc[df.index[-1], 'Close'] = live_price
    if live_price > df.loc[df.index[-1], 'High']:
        df.loc[df.index[-1], 'High'] = live_price
    if live_price < df.loc[df.index[-1], 'Low']:
        df.loc[df.index[-1], 'Low'] = live_price

# 실시간 시세 및 현재 표시 가격 결정
if has_live_quote and live_price is not None:
    current_display_price = live_price
    change_val = live_change
    change_pct = live_ratio
    if live_time and 'T' in live_time:
        latest_time_str = live_time.replace('T', ' ')[:19]
    elif live_time:
        latest_time_str = live_time
    else:
        latest_time_str = df.index[-1].strftime(time_str_format)
    live_badge_html = f"<span style='background:#DCFCE7; color:#15803D; padding:3px 8px; border-radius:4px; font-weight:bold; font-size:0.85rem;'>● 실시간 호가 연동 ({refresh_sec}초 갱신)</span>"
else:
    current_display_price = df['Close'].iloc[-1]
    prev_close = df['Close'].iloc[-2] if len(df) > 1 else current_display_price
    change_val = current_display_price - prev_close
    change_pct = (change_val / prev_close) * 100 if prev_close != 0 else 0
    latest_time_str = df.index[-1].strftime(time_str_format)
    live_badge_html = ""

# -----------------------------------------------------------------------------
# 6. 기술적 보조지표 및 5선/20선/60선 이동평균 계산
# -----------------------------------------------------------------------------
# 5선(단기선), 20선(생명선), 60선(수급선)
df['MA5'] = df['Close'].rolling(window=5).mean()
df['MA20'] = df['Close'].rolling(window=20).mean()
df['MA60'] = df['Close'].rolling(window=60).mean()

df['Prev_MA5'] = df['MA5'].shift(1)
df['Prev_MA20'] = df['MA20'].shift(1)
df['Prev_MA60'] = df['MA60'].shift(1)

# 5선/20선 크로스
df['Golden_5_20'] = (df['MA5'] > df['MA20']) & (df['Prev_MA5'] <= df['Prev_MA20'])
df['Dead_5_20'] = (df['MA5'] < df['MA20']) & (df['Prev_MA5'] >= df['Prev_MA20'])

# 20선/60선 크로스
df['Golden_20_60'] = (df['MA20'] > df['MA60']) & (df['Prev_MA20'] <= df['Prev_MA60'])
df['Dead_20_60'] = (df['MA20'] < df['MA60']) & (df['Prev_MA20'] >= df['Prev_MA60'])

# RSI (14)
delta = df['Close'].diff()
gain = delta.where(delta > 0, 0.0)
loss = -delta.where(delta < 0, 0.0)
avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
rs = avg_gain / avg_loss
df['RSI'] = 100 - (100 / (1 + rs))

# 거래량 20MA
df['Vol_MA20'] = df['Volume'].rolling(20).mean()

# 볼린저 밴드
df['BB_Mid'] = df['MA20']
df['BB_Std'] = df['Close'].rolling(window=20).std()
df['BB_Upper'] = df['BB_Mid'] + (2 * df['BB_Std'])
df['BB_Lower'] = df['BB_Mid'] - (2 * df['BB_Std'])

# MACD
ema12 = df['Close'].ewm(span=12, adjust=False).mean()
ema26 = df['Close'].ewm(span=26, adjust=False).mean()
df['MACD'] = ema12 - ema26
df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

# 스토캐스틱
low14 = df['Low'].rolling(14).min()
high14 = df['High'].rolling(14).max()
fast_k = ((df['Close'] - low14) / (high14 - low14)) * 100
df['Stoch_K'] = fast_k.rolling(3).mean()
df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()

# 이격도
df['Disparity20'] = (df['Close'] / df['MA20']) * 100

# 일목균형표
tenkan = (df['High'].rolling(9).max() + df['Low'].rolling(9).min()) / 2
kijun = (df['High'].rolling(26).max() + df['Low'].rolling(26).min()) / 2
df['Ichimoku_Tenkan'] = tenkan
df['Ichimoku_Kijun'] = kijun
df['Ichimoku_SpanA'] = ((tenkan + kijun) / 2).shift(26)
df['Ichimoku_SpanB'] = ((df['High'].rolling(52).max() + df['Low'].rolling(52).min()) / 2).shift(26)
df['Ichimoku_Chikou'] = df['Close'].shift(-26)

# -----------------------------------------------------------------------------
# 7. 매매 전략 타점 및 수수료(-0.2% 시작) 반영 백테스팅 시뮬레이션
# -----------------------------------------------------------------------------
signals_list = []
trades = []
in_position = False
entry_date, entry_price = None, None

for date, row in df.iterrows():
    if "5선/20선" in strategy_type:
        buy_cond = row['Golden_5_20']
        dead_cond = row['Dead_5_20']
        strat_title = "5/20 골든크로스"
        dead_title = "5/20 데드크로스"
    else:
        buy_cond = row['Golden_20_60']
        dead_cond = row['Dead_20_60']
        strat_title = "20/60 골든크로스"
        dead_title = "20/60 데드크로스"

    # 1. 매수 진입 판정
    if buy_cond and not in_position:
        in_position = True
        entry_date = date
        entry_price = row['Close']
        signals_list.append({
            'date': date,
            'type': f'{strat_title} (매수)',
            'price': entry_price,
            'signal': 'BUY'
        })

    # 2. 매도 청산 판정 (보유 중일 때)
    elif in_position and date > entry_date:
        gross_ret = (row['Close'] - entry_price) / entry_price * 100
        net_ret = gross_ret - fee_rate  # 수수료 차감 (매수 즉시 -0.2%부터 시작)
        
        exit_triggered = False
        exit_reason = ""
        
        if "목표익절" in strategy_type:
            # 수수료(0.2%)를 제하고도 사용자가 설정한 순익절률(예: +0.5%) 도달 시 익절!
            if net_ret >= target_net_profit:
                exit_triggered = True
                exit_reason = f"🎯 목표익절 (순수익 {net_ret:+.2f}%)"
            elif dead_cond:
                exit_triggered = True
                exit_reason = f"📉 {dead_title} 청산"
            elif net_ret <= -2.0:
                exit_triggered = True
                exit_reason = "🛡️ 손절 방어 (-2.0%)"
        else:
            if dead_cond:
                exit_triggered = True
                exit_reason = f"📉 {dead_title} 청산"
                
        if exit_triggered:
            trades.append({
                '매수시점': entry_date.strftime(time_str_format),
                '매수가': entry_price,
                '매도시점': date.strftime(time_str_format),
                '매도가': row['Close'],
                '매매타점/사유': f"{strat_title} ➜ {exit_reason}",
                '단순수익률(%)': gross_ret,
                '실질순수익률(%)': net_ret,  # 수수료 0.2% 공제
                '결과': '승리 🟢' if net_ret > 0 else '패배 🔴'
            })
            signals_list.append({
                'date': date,
                'type': exit_reason,
                'price': row['Close'],
                'signal': 'SELL'
            })
            in_position = False

# 현재 보유 중인 경우
if in_position:
    cur_p = current_display_price
    gross_ret = (cur_p - entry_price) / entry_price * 100
    net_ret = gross_ret - fee_rate  # 매수 즉시 -0.2% 시작
    trades.append({
        '매수시점': entry_date.strftime(time_str_format),
        '매수가': entry_price,
        '매도시점': '현재 보유 중 ⏳',
        '매도가': cur_p,
        '매매타점/사유': f"{strat_title} (보유 중 | 초기 -{fee_rate:.2f}%)",
        '단순수익률(%)': gross_ret,
        '실질순수익률(%)': net_ret,
        '결과': '진행 중'
    })

trades_df = pd.DataFrame(trades)

# -----------------------------------------------------------------------------
# 매매 데이터 및 캔들 시세 파일 자동 저장 (데이터 업데이트 시 실시간 자동 저장)
# -----------------------------------------------------------------------------
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if not trades_df.empty:
        trades_df.to_csv(os.path.join(current_dir, "trade_log.csv"), index=False, encoding="utf-8-sig")
        trades_df.to_json(os.path.join(current_dir, "trade_log.json"), orient="records", force_ascii=False, indent=2)
    if not df.empty:
        df.to_csv(os.path.join(current_dir, "latest_candles.csv"), encoding="utf-8-sig")
except Exception:
    pass

# -----------------------------------------------------------------------------
# 8. 상단 시세 전광판 및 핵심 요약 카드
# -----------------------------------------------------------------------------
is_up = change_val >= 0
price_class = "current-price-up" if is_up else "current-price-down"
badge_class = "badge-up" if is_up else "badge-down"
sign_symbol = "▲" if is_up else "▼"

st.markdown(f"## {display_title} <span style='font-size:1.05rem; color:#2563EB; font-weight:bold;'>[{timeframe_desc}]</span>", unsafe_allow_html=True)

st.markdown(f"""
<div class="trading-header">
    <span class="{price_class}">{current_display_price:,.2f}</span>
    <span class="{badge_class}">{sign_symbol} {abs(change_val):,.2f} ({change_pct:+.2f}%)</span>
    {live_badge_html}
    <span style="color:#64748B; font-size:0.9rem; margin-left:auto;">기준 시점: <b>{latest_time_str}</b></span>
</div>
""", unsafe_allow_html=True)

# 최근 신호 정보
if signals_list:
    last_sig = signals_list[-1]
    sig_date_str = last_sig['date'].strftime(time_str_format)
    sig_type_str = last_sig['type']
    sig_price = last_sig['price']
    sig_gross_ret = (current_display_price - sig_price) / sig_price * 100
    sig_net_ret = sig_gross_ret - fee_rate if last_sig['signal'] == 'BUY' else sig_gross_ret
    sig_elapsed_ret = sig_net_ret
else:
    sig_date_str = "신호 없음"
    sig_type_str = "신호 대기 중"
    sig_price = 0
    sig_gross_ret = 0
    sig_net_ret = 0
    sig_elapsed_ret = 0

if "5선" in strategy_type:
    alignment_status = "5선>20선 (단기 정배열 🟢)" if (pd.notna(latest['MA5']) and pd.notna(latest['MA20']) and latest['MA5'] > latest['MA20']) else "5선<20선 (단기 역배열 🔴)"
else:
    alignment_status = "20선>60선 (중기 정배열 🟢)" if (pd.notna(latest['MA20']) and pd.notna(latest['MA60']) and latest['MA20'] > latest['MA60']) else "20선<60선 (중기 역배열 🔴)"

rsi_now = latest['RSI'] if pd.notna(latest['RSI']) else 50
if rsi_now >= 70:
    rsi_desc = f"과매수 ⚠️ ({rsi_now:.1f})"
elif rsi_now <= 30:
    rsi_desc = f"과매도 🟢 ({rsi_now:.1f})"
else:
    rsi_desc = f"중립 ({rsi_now:.1f})"

top_c1, top_c2, top_c3, top_c4 = st.columns(4)
with top_c1:
    st.metric(label="🔔 최근 발생 신호", value=f"{sig_type_str}", delta=f"{sig_date_str}" if sig_price > 0 else "신호 없음")
with top_c2:
    if sig_price > 0 and signals_list and signals_list[-1]['signal'] == 'BUY':
        st.metric(
            label="📈 진입 대비 순수익률",
            value=f"{sig_net_ret:+.2f}%",
            delta=f"수수료 -{fee_rate:.2f}% 선공제 반영"
        )
    elif sig_price > 0:
        st.metric(
            label="📈 직전 청산가",
            value=f"{sig_price:,.2f}",
            delta="청산 완료"
        )
    else:
        st.metric(label="📈 진입 대비 순수익률", value="-")
with top_c3:
    st.metric(label="📐 이평선 정배열 상태", value=alignment_status)
with top_c4:
    st.metric(label="📊 RSI (14)", value=rsi_desc)

st.markdown("---")

# -----------------------------------------------------------------------------
# 9. Plotly 캔들스틱 + 신호 마커 + RSI 반응형 차트
# -----------------------------------------------------------------------------
active_subplots = []
if show_rsi:
    active_subplots.append("RSI (14)")
if show_vol:
    active_subplots.append("거래량")
if show_macd:
    active_subplots.append("MACD")
if show_stoch:
    active_subplots.append("스토캐스틱")
if show_disparity:
    active_subplots.append("이격도")

total_rows = 1 + len(active_subplots)

if total_rows == 1:
    row_heights = [1.0]
else:
    main_height = 0.52
    sub_height = (1.0 - main_height) / len(active_subplots)
    row_heights = [main_height] + [sub_height] * len(active_subplots)

subplot_titles = [f"{display_title} [{sub_interval}] 캔들스틱 매매 차트"] + active_subplots

fig = make_subplots(
    rows=total_rows,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.02,
    row_heights=row_heights,
    subplot_titles=subplot_titles
)

custom_data = np.stack((df['Volume'],), axis=-1)

# 호버 툴팁 포맷 (분봉/시간봉일 때는 시간까지, 일/주/월일 때는 날짜만)
candle_date_fmt = "%{x|%Y-%m-%d %H:%M}" if is_intraday else "%{x|%Y-%m-%d}"

candlestick_hovertemplate = (
    f"<b>📅 {candle_date_fmt}</b><br>"
    "━━━━━━━━━━━━━━━━━━<br>"
    "• <b>시가</b>:  %{open:,.2f}<br>"
    "• <b>고가</b>:  <span style='color:#EF4444;'>%{high:,.2f}</span><br>"
    "• <b>저가</b>:  <span style='color:#3B82F6;'>%{low:,.2f}</span><br>"
    "• <b>종가</b>:  <b>%{close:,.2f}</b><br>"
    "• <b>거래량</b>: %{customdata[0]:,d}<br>"
    "<extra></extra>"
)

# === [ROW 1: 메인 캔들스틱] ===
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    name='캔들(OHLC)',
    increasing_line_color='#EF4444', increasing_fillcolor='#EF4444',
    decreasing_line_color='#3B82F6', decreasing_fillcolor='#3B82F6',
    customdata=custom_data,
    hovertemplate=candlestick_hovertemplate,
    hoverlabel=dict(bgcolor="#1E293B", font_color="#FFFFFF", font_size=12)
), row=1, col=1)

# 이동평균선 (5선, 20선, 60선)
if show_ma_lines:
    fig.add_trace(go.Scatter(
        x=df.index, y=df['MA5'], mode='lines', name='5선 (단기선)',
        line=dict(color='#8B5CF6', width=1.6),
        hovertemplate='5선: %{y:,.2f}<extra></extra>'
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['MA20'], mode='lines', name='20선 (생명선)',
        line=dict(color='#F59E0B', width=2.0),
        hovertemplate='20선: %{y:,.2f}<extra></extra>'
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['MA60'], mode='lines', name='60선 (수급선)',
        line=dict(color='#10B981', width=1.8),
        hovertemplate='60선: %{y:,.2f}<extra></extra>'
    ), row=1, col=1)

# 전략 매수 / 매도 타점 마커 (5선/20선 타점 및 목표익절 반영)
if show_signals and signals_list:
    buy_sigs = [s for s in signals_list if s['signal'] == 'BUY']
    sell_sigs = [s for s in signals_list if s['signal'] == 'SELL']

    if buy_sigs:
        buy_x = [s['date'] for s in buy_sigs]
        buy_y = [s['price'] * 0.992 for s in buy_sigs]
        buy_reasons = [s['type'] for s in buy_sigs]
        fig.add_trace(go.Scatter(
            x=buy_x,
            y=buy_y,
            mode='markers+text',
            marker=dict(symbol='triangle-up', size=13, color='#10B981', line=dict(width=1.5, color='#047857')),
            text=['매수▲'] * len(buy_x),
            textposition='bottom center',
            textfont=dict(color='#10B981', size=11, family='Malgun Gothic, Apple SD Gothic Neo, sans-serif'),
            name='매수 진입점 ▲',
            customdata=buy_reasons,
            hovertemplate=f'<b>🟢 매수 진입</b><br>타점: %{{customdata}}<br>시점: {candle_date_fmt}<br>체결가: %{{y:,.2f}}<extra></extra>'
        ), row=1, col=1)

    if sell_sigs:
        sell_x = [s['date'] for s in sell_sigs]
        sell_y = [s['price'] * 1.008 for s in sell_sigs]
        sell_reasons = [s['type'] for s in sell_sigs]
        fig.add_trace(go.Scatter(
            x=sell_x,
            y=sell_y,
            mode='markers+text',
            marker=dict(symbol='triangle-down', size=13, color='#EF4444', line=dict(width=1.5, color='#B91C1C')),
            text=['매도▼'] * len(sell_x),
            textposition='top center',
            textfont=dict(color='#EF4444', size=11, family='Malgun Gothic, Apple SD Gothic Neo, sans-serif'),
            name='매도 청산점 ▼',
            customdata=sell_reasons,
            hovertemplate=f'<b>🔴 매도 청산</b><br>사유: %{{customdata}}<br>시점: {candle_date_fmt}<br>체결가: %{{y:,.2f}}<extra></extra>'
        ), row=1, col=1)

if show_bb:
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], mode='lines', name='BB 상한', line=dict(color='#DC2626', width=1, dash='dot')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], mode='lines', name='BB 하한', line=dict(color='#2563EB', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(59, 130, 246, 0.05)'), row=1, col=1)

if show_ichimoku:
    fig.add_trace(go.Scatter(x=df.index, y=df['Ichimoku_Tenkan'], mode='lines', name='전환선', line=dict(color='#EF4444', width=1.2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Ichimoku_Kijun'], mode='lines', name='기준선', line=dict(color='#2563EB', width=1.5)), row=1, col=1)

if show_ema:
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA5'], mode='lines', name='EMA 5', line=dict(color='#A855F7', width=1.2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], mode='lines', name='EMA 20', line=dict(color='#EC4899', width=1.3)), row=1, col=1)

fig.update_yaxes(title_text="가격", automargin=True, showgrid=True, gridcolor="#F1F5F9", tickformat=",.0f", row=1, col=1)

# === [하단 분할 보조지표 서브플롯] ===
current_row = 2

if show_rsi:
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI(14)', line=dict(color='#8B5CF6', width=1.8), hovertemplate='RSI: %{y:.1f}<extra></extra>'), row=current_row, col=1)
    fig.add_hline(y=70, line_width=1.2, line_dash="dash", line_color="#EF4444", annotation_text="과매수(70)", annotation_position="top right", row=current_row, col=1)
    fig.add_hline(y=30, line_width=1.2, line_dash="dash", line_color="#3B82F6", annotation_text="과매도(30)", annotation_position="bottom right", row=current_row, col=1)
    fig.add_hline(y=50, line_width=0.8, line_dash="dot", line_color="#94A3B8", row=current_row, col=1)
    fig.update_yaxes(range=[0, 100], title_text="RSI", automargin=True, showgrid=True, gridcolor="#F1F5F9", row=current_row, col=1)
    current_row += 1

if show_vol:
    vol_colors = ['#EF4444' if row['Close'] >= row['Open'] else '#3B82F6' for _, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_colors, name='거래량', hovertemplate='거래량: %{y:,d}<extra></extra>'), row=current_row, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Vol_MA20'], mode='lines', name='거래량 20MA', line=dict(color='#F59E0B', width=1.2)), row=current_row, col=1)
    fig.update_yaxes(title_text="거래량", automargin=True, showgrid=True, gridcolor="#F1F5F9", tickformat=",.0s", row=current_row, col=1)
    current_row += 1

if show_macd:
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', name='MACD', line=dict(color='#2563EB', width=1.5)), row=current_row, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], mode='lines', name='Signal', line=dict(color='#F97316', width=1.5)), row=current_row, col=1)
    hist_colors = ['#EF4444' if v >= 0 else '#3B82F6' for v in df['MACD_Hist']]
    fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], marker_color=hist_colors, name='Hist'), row=current_row, col=1)
    fig.add_hline(y=0, line_width=1, line_dash="solid", line_color="#94A3B8", row=current_row, col=1)
    fig.update_yaxes(title_text="MACD", automargin=True, showgrid=True, gridcolor="#F1F5F9", row=current_row, col=1)
    current_row += 1

if show_stoch:
    fig.add_trace(go.Scatter(x=df.index, y=df['Stoch_K'], mode='lines', name='Slow %K', line=dict(color='#3B82F6', width=1.5)), row=current_row, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Stoch_D'], mode='lines', name='Slow %D', line=dict(color='#F59E0B', width=1.5)), row=current_row, col=1)
    fig.add_hline(y=80, line_width=1, line_dash="dash", line_color="#EF4444", row=current_row, col=1)
    fig.add_hline(y=20, line_width=1, line_dash="dash", line_color="#3B82F6", row=current_row, col=1)
    fig.update_yaxes(range=[0, 100], title_text="스토캐스틱", automargin=True, showgrid=True, gridcolor="#F1F5F9", row=current_row, col=1)
    current_row += 1

if show_disparity:
    fig.add_trace(go.Scatter(x=df.index, y=df['Disparity20'], mode='lines', name='이격도(20)', line=dict(color='#10B981', width=1.5)), row=current_row, col=1)
    fig.add_hline(y=100, line_width=1.2, line_dash="solid", line_color="#64748B", row=current_row, col=1)
    fig.update_yaxes(title_text="이격도", automargin=True, showgrid=True, gridcolor="#F1F5F9", row=current_row, col=1)
    current_row += 1

# 차트 편의 기능 바 (화면 복귀 안내 및 와이드 확대 모드)
c_info, c_wide = st.columns([7, 3])
with c_info:
    st.caption("💡 **화면 조작 팁**: 차트가 안 보일 땐 **[마우스 왼쪽 더블클릭]** 또는 차트 우측 상단의 **[집 모양(Reset) 아이콘]**을 누르면 원래대로 복귀합니다. 차트 우측 상단의 **[⛶ 전체화면 아이콘]**을 누르면 모니터 전체 화면으로 확대됩니다.")
with c_wide:
    is_wide_chart = st.checkbox("🖥️ 차트 세로 확대 (와이드 뷰)", value=False, help="차트 높이를 대폭 확대하여 보조지표와 캔들을 크고 시원하게 봅니다.")

base_height = 780 if is_wide_chart else 500
chart_total_height = base_height + (len(active_subplots) * 140)

fig.update_layout(
    xaxis_rangeslider_visible=False,
    template="plotly_white",
    hovermode="x",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.01,
        xanchor="right",
        x=1,
        font=dict(size=10)
    ),
    margin=dict(l=5, r=5, t=35, b=10),
    height=chart_total_height
)

# Plotly 차트 인터랙티브 및 복귀/전체화면 설정
plotly_chart_config = {
    'responsive': True,
    'scrollZoom': False,
    'doubleClick': 'reset+autosize',   # 요청사항 1: 마우스 왼쪽 더블클릭 시 원래 화면으로 즉시 복귀!
    'doubleClickDelay': 300,           # 더블클릭 감지 딜레이(ms)
    'displayModeBar': True,            # 요청사항 2: 우측 상단 툴바(리셋, 줌, 카메라 등) 활성화
    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
    'displaylogo': False,
    'toImageButtonOptions': {
        'format': 'png',
        'filename': f'{ticker_symbol}_{sub_interval}_chart',
        'scale': 2
    }
}

st.plotly_chart(fig, use_container_width=True, config=plotly_chart_config)

# -----------------------------------------------------------------------------
# 10. 매매 전략 성과 검증 대시보드
# -----------------------------------------------------------------------------
strat_clean_title = strategy_type.split(' (')[0]
st.subheader(f"🧪 [{sub_interval}] {strat_clean_title} 실전 성과 검증")

st.info(
    f"💡 **실전 매매 전략 & 수수료 원칙 안내**<br>"
    f"• **초기 진입 -{fee_rate:.2f}% 페널티**: 매수 체결 즉시 유관기관 수수료, 증권사 수수료 및 거래세({fee_rate:.2f}%)가 선공제되어 **-{fee_rate:.2f}%**부터 시작합니다.<br>"
    f"• **+{target_net_profit:.2f}% 이상 순익절 원칙**: 단순 시세차익뿐 아니라 수수료 {fee_rate:.2f}%를 완전히 만회하고도 실질 순수익이 **+{target_net_profit:.2f}% 이상** 달성되었을 때만 목표 익절을 단행합니다.<br>"
    f"• **5선/20선 골든·데드 타점**: 5일선이 20일선을 상향 돌파(골든크로스) 시 매수하고, 목표익절 도달 또는 데드크로스 이탈 시 안전하게 청산합니다.",
    icon="ℹ️"
)

if not trades_df.empty:
    completed_trades = trades_df[trades_df['매도시점'] != '현재 보유 중 ⏳']
    total_trades_cnt = len(completed_trades)
    
    if total_trades_cnt > 0:
        win_trades_cnt = int((completed_trades['실질순수익률(%)'] > 0).sum())
        win_rate = (win_trades_cnt / total_trades_cnt) * 100
        cum_net_return = ((1 + completed_trades['실질순수익률(%)'] / 100).prod() - 1) * 100
        cum_gross_return = ((1 + completed_trades['단순수익률(%)'] / 100).prod() - 1) * 100
        avg_net_ret = completed_trades['실질순수익률(%)'].mean()
        total_fees = total_trades_cnt * fee_rate
    else:
        win_trades_cnt = 0
        win_rate = 0
        cum_net_return = 0
        cum_gross_return = 0
        avg_net_ret = 0
        total_fees = 0

    buy_and_hold_return = ((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100

    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    b_col1.metric("실전 순승률 (수수료 공제 후)", f"{win_rate:.1f}%", f"{win_trades_cnt}승 {total_trades_cnt - win_trades_cnt}패" if total_trades_cnt > 0 else "완료 거래 없음")
    b_col2.metric("전략 누적 순수익률", f"{cum_net_return:+.2f}%", f"단순보유比 {cum_net_return - buy_and_hold_return:+.2f}%p")
    b_col3.metric("단순 보유(Buy&Hold) 수익률", f"{buy_and_hold_return:+.2f}%", delta="시장 기본 성과")
    b_col4.metric("건당 평균 순수익률", f"{avg_net_ret:+.2f}%", delta=f"총 거래수수료 -{total_fees:.2f}%", delta_color="inverse")

    with st.expander(f"📜 [{sub_interval}] 매매 상세 일지 (5선/20선 타점 & 실질 순익)", expanded=True):
        st.caption(f"💾 **파일 자동 저장 완료**: 시세 및 매매 타점이 업데이트될 때마다 `trade_log.csv`와 `trade_log.json` 파일로 자동 저장됩니다. (최종 저장: {latest_time_str})")
        st.dataframe(
            trades_df.style.format({
                '매수가': '{:,.2f}',
                '매도가': '{:,.2f}',
                '단순수익률(%)': '{:+.2f}%',
                '실질순수익률(%)': '{:+.2f}%'
            }),
            use_container_width=True
        )
        csv_bytes = trades_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="📥 매매 상세 일지 CSV 다운로드 (엑셀 호환)",
            data=csv_bytes,
            file_name=f"trade_log_{ticker_symbol}_{sub_interval}.csv",
            mime="text/csv"
        )
else:
    st.info(f"💡 선택하신 [{timeframe_desc}] 기간 내에 발생한 매매 신호가 없습니다. 사이드바에서 조회 기간을 더 길게 변경해 보세요.")
