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
# 2. 사이드바 - 종목/지수 선택
# -----------------------------------------------------------------------------
st.sidebar.header("🎯 종목 및 시장 선택")

TICKER_DICT = {
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
    "💻 마이크로소프트 (MSFT)": "MSFT",
    "✏️ 직접 티커 입력": "CUSTOM"
}

selected_name = st.sidebar.selectbox("분석할 종목 또는 지수", list(TICKER_DICT.keys()), index=5)

if selected_name == "✏️ 직접 티커 입력":
    ticker_symbol = st.sidebar.text_input("티커 심볼 입력 (예: 000270.KS, TSLA, QQQ)", value="005930.KS").strip().upper()
    display_title = f"직접 입력 ({ticker_symbol})"
else:
    ticker_symbol = TICKER_DICT[selected_name]
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
# 4. 사이드바 - 매매 신호 및 지표 설정
# -----------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ 지표 & 매매 신호 설정")

show_signals = st.sidebar.checkbox("🚀 골든/데드크로스 매매 신호 표시", value=True, help="20이평선과 60이평선의 골든크로스(초록 ▲), 데드크로스(빨강 ▼)를 캔들 위에 표시합니다.")

with st.sidebar.expander("📌 캔들 차트 오버레이 지표", expanded=True):
    show_ma_lines = st.checkbox("20선(MA20) & 60선(MA60)", value=True, help="선택한 주기 기준의 20이평선과 60이평선을 겹쳐서 표시합니다.")
    show_bb = st.checkbox("볼린저 밴드 (20, 2σ)", value=False)
    show_ema = st.checkbox("지수이동평균선 (EMA 5, 20, 60, 120)", value=False)
    show_ichimoku = st.checkbox("일목균형표 (9, 26, 52)", value=False)

with st.sidebar.expander("📊 하단 분할 보조지표", expanded=True):
    show_rsi = st.checkbox("1. RSI (14) [과매수 70 / 과매도 30]", value=True)
    show_vol = st.checkbox("2. 거래량 (Volume + 20MA)", value=True)
    show_macd = st.checkbox("3. MACD (12, 26, 9)", value=False)
    show_stoch = st.checkbox("4. 스토캐스틱 슬로우 (14, 3, 3)", value=False)
    show_disparity = st.checkbox("5. 이격도 (20선 기준)", value=False)

# -----------------------------------------------------------------------------
# 5. 분봉/시간봉/일/주/월봉 데이터 로드 및 리샘플링 함수
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)  # 분봉 데이터를 위해 5분 캐시
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

# 결측치 정제
df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
if len(df) < 5:
    st.warning("데이터 포인트가 너무 적습니다. 더 긴 조회 기간을 선택해 주세요.")
    st.stop()

# -----------------------------------------------------------------------------
# 6. 기술적 보조지표 및 매매 신호 계산
# -----------------------------------------------------------------------------
# 20선(MA20) & 60선(MA60)
df['MA20'] = df['Close'].rolling(window=20).mean()
df['MA60'] = df['Close'].rolling(window=60).mean()

# 골든크로스 & 데드크로스 감지
df['Prev_MA20'] = df['MA20'].shift(1)
df['Prev_MA60'] = df['MA60'].shift(1)
df['Golden_Cross'] = (df['MA20'] > df['MA60']) & (df['Prev_MA20'] <= df['Prev_MA60'])
df['Dead_Cross'] = (df['MA20'] < df['MA60']) & (df['Prev_MA20'] >= df['Prev_MA60'])

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
# 7. 매매 신호 및 백테스팅 내역 계산
# -----------------------------------------------------------------------------
signals_list = []
trades = []
in_position = False
entry_date, entry_price = None, None

time_str_format = '%Y-%m-%d %H:%M' if is_intraday else '%Y-%m-%d'

for date, row in df.iterrows():
    if row['Golden_Cross']:
        signals_list.append({
            'date': date,
            'type': '골든크로스 (매수)',
            'price': row['Close'],
            'signal': 'BUY'
        })
        if not in_position:
            in_position = True
            entry_date = date
            entry_price = row['Close']
            
    elif row['Dead_Cross']:
        signals_list.append({
            'date': date,
            'type': '데드크로스 (매도)',
            'price': row['Close'],
            'signal': 'SELL'
        })
        if in_position:
            exit_date = date
            exit_price = row['Close']
            trade_ret = (exit_price - entry_price) / entry_price * 100
            trades.append({
                '매수시점': entry_date.strftime(time_str_format),
                '매수가': entry_price,
                '매도시점': exit_date.strftime(time_str_format),
                '매도가': exit_price,
                '수익률(%)': trade_ret,
                '결과': '승리 🟢' if trade_ret > 0 else '패배 🔴'
            })
            in_position = False

if in_position:
    current_p = df['Close'].iloc[-1]
    trade_ret = (current_p - entry_price) / entry_price * 100
    trades.append({
        '매수시점': entry_date.strftime(time_str_format),
        '매수가': entry_price,
        '매도시점': '현재 보유 중 ⏳',
        '매도가': current_p,
        '수익률(%)': trade_ret,
        '결과': '진행 중'
    })

trades_df = pd.DataFrame(trades)

# -----------------------------------------------------------------------------
# 8. 상단 시세 전광판 및 핵심 요약 카드
# -----------------------------------------------------------------------------
latest = df.iloc[-1]
prev = df.iloc[-2] if len(df) > 1 else latest
change_val = latest['Close'] - prev['Close']
change_pct = (change_val / prev['Close']) * 100 if prev['Close'] != 0 else 0

is_up = change_val >= 0
price_class = "current-price-up" if is_up else "current-price-down"
badge_class = "badge-up" if is_up else "badge-down"
sign_symbol = "▲" if is_up else "▼"

latest_time_str = df.index[-1].strftime(time_str_format)

st.markdown(f"## {display_title} <span style='font-size:1.05rem; color:#2563EB; font-weight:bold;'>[{timeframe_desc}]</span>", unsafe_allow_html=True)

st.markdown(f"""
<div class="trading-header">
    <span class="{price_class}">{latest['Close']:,.2f}</span>
    <span class="{badge_class}">{sign_symbol} {abs(change_val):,.2f} ({change_pct:+.2f}%)</span>
    <span style="color:#64748B; font-size:0.9rem; margin-left:auto;">기준 시점: <b>{latest_time_str}</b></span>
</div>
""", unsafe_allow_html=True)

# 최근 신호 정보
if signals_list:
    last_sig = signals_list[-1]
    sig_date_str = last_sig['date'].strftime(time_str_format)
    sig_type_str = last_sig['type']
    sig_price = last_sig['price']
    sig_elapsed_ret = (latest['Close'] - sig_price) / sig_price * 100
else:
    sig_date_str = "신호 없음"
    sig_type_str = "신호 대기 중"
    sig_price = 0
    sig_elapsed_ret = 0

alignment_status = "정배열 (상승 우세 🟢)" if (pd.notna(latest['MA20']) and pd.notna(latest['MA60']) and latest['MA20'] > latest['MA60']) else "역배열 (조정 우세 🔴)"

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
    st.metric(label="📈 신호 이후 성과", value=f"{sig_elapsed_ret:+.2f}%" if sig_price > 0 else "-", delta="진입 대비 성과")
with top_c3:
    st.metric(label="📐 20선 / 60선 배열", value=alignment_status)
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

# 20선 & 60선
if show_ma_lines:
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], mode='lines', name='20선', line=dict(color='#F59E0B', width=2.0), hovertemplate='20선: %{y:,.2f}<extra></extra>'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], mode='lines', name='60선', line=dict(color='#10B981', width=2.0), hovertemplate='60선: %{y:,.2f}<extra></extra>'), row=1, col=1)

# 골든/데드크로스 마커
if show_signals:
    golden_df = df[df['Golden_Cross']]
    if not golden_df.empty:
        fig.add_trace(go.Scatter(
            x=golden_df.index,
            y=golden_df['Low'] * 0.985,
            mode='markers+text',
            marker=dict(symbol='triangle-up', size=13, color='#10B981', line=dict(width=1.5, color='#047857')),
            text='매수▲',
            textposition='bottom center',
            textfont=dict(color='#10B981', size=11),
            name='골든크로스(매수 ▲)',
            hovertemplate=f'<b>🟢 매수 신호</b><br>시점: {candle_date_fmt}<br>체결가: %{{y:,.2f}}<extra></extra>'
        ), row=1, col=1)

    dead_df = df[df['Dead_Cross']]
    if not dead_df.empty:
        fig.add_trace(go.Scatter(
            x=dead_df.index,
            y=dead_df['High'] * 1.015,
            mode='markers+text',
            marker=dict(symbol='triangle-down', size=13, color='#EF4444', line=dict(width=1.5, color='#B91C1C')),
            text='매도▼',
            textposition='top center',
            textfont=dict(color='#EF4444', size=11),
            name='데드크로스(매도 ▼)',
            hovertemplate=f'<b>🔴 매도 신호</b><br>시점: {candle_date_fmt}<br>체결가: %{{y:,.2f}}<extra></extra>'
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
st.subheader(f"🧪 [{sub_interval}] 20선 & 60선 크로스 전략 검증")

if not trades_df.empty:
    completed_trades = trades_df[trades_df['매도시점'] != '현재 보유 중 ⏳']
    total_trades_cnt = len(completed_trades)
    
    if total_trades_cnt > 0:
        win_trades_cnt = (completed_trades['수익률(%)'] > 0).sum()
        win_rate = (win_trades_cnt / total_trades_cnt) * 100
        cum_strategy_return = ((1 + completed_trades['수익률(%)'] / 100).prod() - 1) * 100
        avg_ret = completed_trades['수익률(%)'].mean()
    else:
        win_rate = 0
        cum_strategy_return = 0
        avg_ret = 0

    buy_and_hold_return = ((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100

    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    b_col1.metric("전략 승률", f"{win_rate:.1f}%", f"{win_trades_cnt}승 {total_trades_cnt - win_trades_cnt}패" if total_trades_cnt > 0 else "완료 거래 없음")
    b_col2.metric("전략 누적 수익률", f"{cum_strategy_return:+.2f}%", f"단순보유比 {cum_strategy_return - buy_and_hold_return:+.2f}%p")
    b_col3.metric("단순 보유 수익률", f"{buy_and_hold_return:+.2f}%")
    b_col4.metric("평균 거래 수익률", f"{avg_ret:+.2f}%")

    with st.expander(f"📜 [{sub_interval}] 상세 매매 일지 (Trade Log)", expanded=True):
        st.dataframe(
            trades_df.style.format({
                '매수가': '{:,.2f}',
                '매도가': '{:,.2f}',
                '수익률(%)': '{:+.2f}%'
            }),
            use_container_width=True
        )
else:
    st.info(f"💡 선택하신 [{timeframe_desc}] 기간 내에 발생한 골든/데드크로스 신호가 없습니다. 사이드바에서 조회 기간을 더 길게 변경해 보세요.")
