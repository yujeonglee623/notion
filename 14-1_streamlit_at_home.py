import streamlit as st
import pandas as pd
import numpy as np
import joblib
import os
import requests
import zipfile
import io
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

# 1. 페이지 설정
st.set_page_config(page_title="AI 기업 신용 신호등 (Ultimate)", page_icon="🚦", layout="wide")

# 2. 스타일 CSS
st.markdown("""
<style>
    .green-light { color: #2ecc71; font-size: 50px; font-weight: bold; }
    .orange-light { color: #f39c12; font-size: 50px; font-weight: bold; }
    .red-light { color: #e74c3c; font-size: 50px; font-weight: bold; }
    .log-text { font-size: 12px; color: #555; }
</style>
""", unsafe_allow_html=True)

# 3. 시스템 로드
@st.cache_resource
def load_system():
    load_dotenv()
    api_key = os.getenv('DART_API_KEY')
    try:
        model = joblib.load('bankruptcy_model_final_ratio.pkl')
        return api_key, model, "Success"
    except Exception as e:
        return api_key, None, str(e)

api_key, model, status = load_system()

# 🔥 [핵심 1] DART 고유번호(8자리) 최신본 다운로드 함수
# 매핑이 틀릴 수 있으니, DART에서 직접 최신 매핑 파일을 받아옵니다.
@st.cache_data
def get_corp_code_map(api_key):
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    params = {'crtfc_key': api_key}
    try:
        r = requests.get(url, params=params)
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            with z.open('CORPCODE.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                data = []
                for child in root:
                    corp_code = child.find('corp_code').text
                    stock_code = child.find('stock_code').text
                    corp_name = child.find('corp_name').text
                    # 주식코드가 있는 상장사만 저장
                    if stock_code and stock_code.strip():
                        data.append({'code': stock_code.strip(), 'dart': corp_code, 'name': corp_name})
        return pd.DataFrame(data)
    except Exception as e:
        return None

# 🔥 [핵심 2] 집요한 데이터 조회 함수 (과정 중계)
def fetch_financial_data(api_key, dart_code):
    log = [] # 로그 기록용
    
    # 1. API 종류: 주요계정(Multi) -> 전체계정(Single)
    apis = [
        ("fnlttMultiAcnt", "주요계정API"),
        ("fnlttSinglAcnt", "전체계정API")
    ]
    
    # 2. 연도: 2025 -> 2024 -> 2023
    years = [2025, 2024, 2023]
    
    # 3. 보고서: 3분기(11014) -> 반기(11012) -> 사업보고서(11011)
    # (최신순으로 배치)
    reports = [
        ('11014', '3분기'), 
        ('11012', '반기'), 
        ('11011', '사업보고서')
    ]
    
    for year in years:
        for r_code, r_name in reports:
            for api_name, api_desc in apis:
                url = f"https://opendart.fss.or.kr/api/{api_name}.json"
                params = {
                    'crtfc_key': api_key,
                    'corp_code': dart_code,
                    'bsns_year': str(year),
                    'reprt_code': r_code
                }
                
                try:
                    res = requests.get(url, params=params, timeout=2)
                    data = res.json()
                    
                    status_code = data.get('status')
                    
                    if status_code == '000':
                        msg = f"✅ {year}년 {r_name} ({api_desc}) 발견! 성공!"
                        log.append(msg)
                        st.toast(msg)
                        return pd.DataFrame(data['list']), year, r_name, log
                    else:
                        # 실패 로그 기록
                        err_msg = data.get('message', '알수없음')
                        log.append(f"❌ {year}년 {r_name} ({api_desc}): {err_msg}")
                        
                except Exception as e:
                    log.append(f"⚠️ 통신오류: {str(e)}")
                    continue
                    
    return None, None, None, log

# 4. 사이드바
st.sidebar.title("🚦 AI Credit Monitor")
st.sidebar.divider()

if status == "Success":
    st.sidebar.subheader("📡 엔진 상태")
    st.sidebar.success("AI 모델 로드 완료")
    st.sidebar.info("DART API 직결 모드 가동 중")
    
    # 분석 이력이나 기준일 표시
    st.sidebar.divider()
    st.sidebar.write("📅 **분석 기준일**")
    st.sidebar.code("2025-12-17")
    
    # 리셋 버튼 배치
    if st.sidebar.button("🔄 시스템 리셋", use_container_width=True):
        st.cache_resource.clear()
        st.cache_data.clear()
        st.rerun()
else:
    st.sidebar.error(f"🚨 시스템 오류: {status}")

# 5. 메인 화면
st.title("🚦 기업 부도 위험 진단 (API 해결판)")
st.info("💡 종목코드 6자리를 입력하세요. DART 서버에서 **직접** 고유번호를 찾아냅니다.")

col1, col2 = st.columns([3, 1])
with col1:
    user_input = st.text_input("종목코드 입력", placeholder="예: 034020 (두산에너빌리티)")
with col2:
    st.write("") 
    st.write("")
    search_btn = st.button("🔍 진단 시작", use_container_width=True)

if search_btn and user_input:
    if not api_key:
        st.error("API 키가 필요합니다.")
        st.stop()

    # 1. DART 고유번호 찾기 (XML 다운로드)
    with st.spinner("📡 DART에서 최신 기업 리스트를 받아오는 중... (최초 1회만 느림)"):
        corp_map_df = get_corp_code_map(api_key)
        
        if corp_map_df is None:
            st.error("🚨 DART 기업 리스트 다운로드 실패. API 키를 확인해주세요.")
            st.stop()
            
        # 입력된 종목코드로 DART 코드 찾기
        found = corp_map_df[corp_map_df['code'] == user_input]
        
        if found.empty:
            st.error(f"❌ 종목코드 '{user_input}'을 찾을 수 없습니다.")
            st.stop()
            
        dart_code = found.iloc[0]['dart']
        corp_name = found.iloc[0]['name']
        
        st.success(f"🔎 기업 식별 성공: **{corp_name}** (DART 코드: {dart_code})")

    # 2. 재무 데이터 스캔
    with st.spinner(f"📡 '{corp_name}'의 재무제표를 샅샅이 뒤지는 중..."):
        df, found_year, report_name, logs = fetch_financial_data(api_key, dart_code)
        
        # 로그 보여주기 (디버깅용 expander)
        with st.expander("🕵️‍♀️ 데이터 추적 로그 보기 (클릭)"):
            for l in logs:
                st.write(l)
        
        if df is None:
            st.error("🚨 모든 연도/보고서 조회 실패.")
            st.write("DART 서버에 해당 기업의 데이터가 표준 양식으로 없거나, API 한도가 초과되었습니다.")
            st.stop()

        # 3. 데이터 추출
        if 'fs_div' in df.columns:
            cfs = df[df['fs_div'] == 'CFS']
            df_t = cfs if not cfs.empty else df[df['fs_div'] == 'OFS']
        else: df_t = df

        def get_val(kws):
            for k in kws:
                # 공백 제거 후 포함 여부 확인
                rows = df_t[df_t['account_nm'].str.replace(' ', '').str.contains(k, na=False)]
                if not rows.empty: 
                    val = str(rows.iloc[0]['thstrm_amount']).replace(',', '').strip()
                    return float(val) if val else 0.0
            return 0.0

        assets = get_val('자산총계')
        liabilities = get_val('부채총계')
        equity = get_val('자본총계')
        sales = get_val('매출액') 
        if sales == 0: sales = get_val('영업수익') # 금융/지주사 대비
        if sales == 0: sales = get_val('수익(매출액)')
        
        op_profit = get_val('영업이익')
        net_profit = get_val('당기순이익')

        # 4. 비율 계산 & 예측
        if equity == 0 or sales == 0 or assets == 0:
            st.warning(f"⚠️ 중요 데이터 누락 (자산:{assets}, 매출:{sales}, 자본:{equity})")
            st.stop()

        debt_ratio = (liabilities / equity) * 100
        op_margin = (op_profit / sales) * 100
        net_margin = (net_profit / sales) * 100
        roa = (net_profit / assets) * 100

        # 모델 예측
        input_df = pd.DataFrame({'부채비율': [debt_ratio], '영업이익률': [op_margin], '순이익률': [net_margin], 'ROA': [roa]})
        risk_prob = model.predict_proba(input_df)[0][1] * 100

        # 5. 결과 출력
        if risk_prob < 10.0: c, l, t = "🟢 Green", "green-light", "안전"
        elif risk_prob < 70.0: c, l, t = "🟠 Orange", "orange-light", "주의"
        else: c, l, t = "🔴 Red", "red-light", "위험"

        st.divider()
        st.subheader(f"📊 {corp_name} ({found_year}년 {report_name})")
        col_a, col_b = st.columns([1, 2])
        with col_a: st.markdown(f'<div style="text-align:center;"><p class="{l}">{c.split()[0]}</p><h3>{c.split()[1]}</h3></div>', unsafe_allow_html=True)
        with col_b:
            st.info(f"**{t}**")
            st.write(f"부도 확률: **{risk_prob:.2f}%**")
        
        st.divider()
        cols = st.columns(4)
        cols[0].metric("부채비율", f"{debt_ratio:.1f}%")
        cols[1].metric("영업이익률", f"{op_margin:.1f}%")
        cols[2].metric("순이익률", f"{net_margin:.1f}%")
        cols[3].metric("ROA", f"{roa:.1f}%")
