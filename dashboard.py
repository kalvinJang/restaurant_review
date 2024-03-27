import pickle
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 페이지 레이아웃 설정
st.set_page_config(layout="wide")
# 폰트 설정
st.set_option('deprecation.showfileUploaderEncoding', False)
st.set_option('deprecation.showPyplotGlobalUse', False)
st.set_option('deprecation.showfileUploaderEncoding', False)

# 페이지 제목 설정
st.title("서울 맛집 빅데이터 검색 / 빅데이터로 맛집 찾기")

# 사이드바 너비 조절을 위한 HTML 스타일 적용
st.markdown(
    """
    <style>
    .sidebar .sidebar-content {
        width: 100px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 사이드바에 내용 추가
st.sidebar.header('사이드바 내용')
st.sidebar.write('이것은 사이드바에 표시되는 내용입니다.')
tabs = st.sidebar.radio("메뉴 선택:", ("카테고리별 보기", "지역별 보기", "맛집 정보 검색"))


# 각 탭에 대한 내용 표시
if tabs == "카테고리별 보기":
    st.sidebar.header("카테고리별")
    st.sidebar.write("최고 인기 식당 : 카테고리별로 훑어보기")
    st.write('2022.08 ~ 2023.08  서울 식당 데이터를 이용해 분석한 맛집 대시보드입니다')

    # 4개의 블럭 (1 행, 4 열)
    col1, col2, col3, col4 = st.columns(4)

    # 섹션 1
    with col1:
        st.markdown("<h1 style='font-size: 24px;'>서울 전체 분석 식당 수</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='font-size: 18px;'>139,010 개</h2>", unsafe_allow_html=True)

    # 섹션 2
    with col2:
        st.markdown("<h1 style='font-size: 24px;'>참고한 리뷰 작성 유저</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='font-size: 18px;'>2,042,758 개</h2>", unsafe_allow_html=True)

    # 섹션 3
    with col3:
        st.markdown("<h1 style='font-size: 24px;'>분석한 리뷰 수</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='font-size: 18px;'>19,274,978 개</h2>", unsafe_allow_html=True)

    # 섹션 4
    with col4:
        st.markdown("<h1 style='font-size: 24px;'>최근 2개월(7,8월) 서울 최다 리뷰 식당 top3 </h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='font-size: 18px;'> 1. 카츠공방 남부터미널점 / 리뷰 1842개 </h2>", unsafe_allow_html=True)
        st.markdown("<h2 style='font-size: 18px;'> 2. 은행골 강남역점 / 리뷰 1621개 </h2>", unsafe_allow_html=True)
        st.markdown("<h2 style='font-size: 18px;'> 3. 백소정 교대점 / 리뷰 1511개  </h2>", unsafe_allow_html=True)

    st.header("카테고리별 서울 맛집 통계")

    with open('dashboard_each_review.pkl', 'rb') as f:
        df = pickle.load(f)


    with open('dashboard_category.pkl', 'rb') as f:
        category = pickle.load(f)


    # '이름' 또는 '카테고리' 중 어떤 필드를 선택할지 유저에게 묻기 (selectbox 사용)
    selected_field = st.selectbox("어떤 필드를 기준으로 검색하시겠습니까?", ('이름', '카테고리'))

    # 선택한 필드에 따라 검색할 값을 입력받기 (text_input 대신 selectbox 사용)
    if selected_field == '이름':
        search_value = st.selectbox(f"{selected_field}을(를) 선택하세요.", df['이름'].unique())
    elif selected_field == '카테고리':
        search_value = st.selectbox(f"{selected_field}을(를) 선택하세요.", df['카테고리'].unique())

    # 선택한 필드와 검색어에 따라 데이터 필터링
    filtered_data = df[df[selected_field] == search_value]

    if not filtered_data.empty:
        # 검색 결과 표시
        st.write("검색 결과:")
        st.write(filtered_data)
    else:
        st.write("검색 결과가 없습니다.")


    # 라인 그래프와 히스토그램
    st.markdown("<h1 style='font-size: 24px;'>이것은 큰 제목입니다.</h1>", unsafe_allow_html=True)
    st.header("Line 그래프와 Histogram")


elif tabs == "지역별 보기":
    st.sidebar.header("지역별")
    st.sidebar.write("최고 인기 식당 : 지역별로 훑어보기")
    st.header("섹션 2")
    st.write("이것은 섹션 2의 내용입니다.")

    # 4개의 블럭 (1 행, 4 열)
    col1, col2, col3, col4 = st.columns(4)

    # 섹션 1
    with col1:
        st.markdown("<h1 style='font-size: 24px;'>서울 전체 식당 수</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='font-size: 18px;'>139,010 개</h2>", unsafe_allow_html=True)

    # 섹션 2
    with col2:
        st.markdown("<h1 style='font-size: 24px;'>참고한 리뷰 작성 유저</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='font-size: 18px;'>2,042,758 개</h2>", unsafe_allow_html=True)

    # 섹션 3
    with col3:
        st.markdown("<h1 style='font-size: 24px;'>분석한 리뷰 수</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='font-size: 18px;'>19,273,316 개</h2>", unsafe_allow_html=True)

    # 섹션 4
    with col4:
        st.markdown("<h1 style='font-size: 24px;'>최근 2개월 최다 리뷰 식당</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='font-size: 18px;'> 하하호호 (서울 금천구) / 리뷰 500개 </h2>", unsafe_allow_html=True)
    
    st.header("카테고리별 서울 맛집 통계")  

    # Line 그래프 데이터 생성
    data = pd.DataFrame({
        '날짜': pd.date_range('2023-01-01', periods=100),
        '값': np.random.randn(100).cumsum()
    })

    # 기간을 조절하는 슬라이더
    start_date = st.date_input("시작 날짜", data['날짜'].min())
    end_date = st.date_input("종료 날짜", data['날짜'].max())

    # 날짜 데이터 타입 변환 (datetime.date에서 datetime64[ns]로)
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)


    filtered_data = data[(data['날짜'] >= start_date) & (data['날짜'] <= end_date)]

    # Line 그래프 그리기
    st.line_chart(filtered_data.set_index('날짜'))

    # Histogram 그리기
    st.bar_chart(filtered_data['값'].value_counts())

    # 통계 자료 (가상 데이터)
    st.markdown("<h3 style='font-size: 16px;'>이것은 작은 제목입니다.</h3>", unsafe_allow_html=True)
    st.header("통계 자료")

    # 가상의 데이터프레임 생성
    data_stats = pd.DataFrame({
        '항목': ['평균', '표준편차', '최소값', '최대값'],
        '값': [filtered_data['값'].mean(), filtered_data['값'].std(), filtered_data['값'].min(), filtered_data['값'].max()]
    })

    st.table(data_stats)


elif tabs == "맛집 정보 검색":
    st.sidebar.header("맛집 정보 검색")
    st.sidebar.write("해당 맛집 빅데이터 분석 확인하기")
    st.header("섹션 3")
    st.write("이것은 섹션 3의 내용입니다.")

    data = pd.DataFrame({
    '이름': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
    '나이': [25, 30, 35, 40, 45]
    })

    st.header("서울 개별 맛집의 모든 분석")  
    options = data['이름'].tolist()
    selected_items = st.selectbox("식당을 검색학고 골라보세요", options, index=0)

    if selected_items:
        st.write(selected_items)


    # 텍스트 출력
    st.header('텍스트 출력')
    st.write('이것은 텍스트입니다.')

    # 숫자 출력
    st.header('숫자 출력')
    number = st.number_input('숫자를 입력하세요', min_value=0, max_value=100, value=50)
    st.write(f'입력한 숫자: {number}')

    # 그래프 출력
    st.header('그래프 출력')
    fig, ax = plt.subplots(figsize=(20, 5))  # 크기를 조절하려면 figsize를 조정하세요

    x = np.linspace(0, 10, 100)
    y = np.sin(x)
    ax.plot(x, y)
    st.pyplot(fig)

    window = st.slider('forcast window (days)')

    # 데이터프레임 출력
    st.header('데이터프레임 출력')

    data = {'이름': ['Alice', 'Bob', 'Charlie'],
            '나이': [25, 30, 35]}
    df = pd.DataFrame(data)
    st.write(df)

    # 사용자 입력
    st.header('사용자 입력')
    user_input = st.text_input('사용자 입력: ')
    st.write(f'입력한 내용: {user_input}')

    # 버튼 클릭
    st.header('버튼 클릭')
    if st.button('버튼을 클릭하세요'):
        st.write('버튼이 클릭되었습니다.')


