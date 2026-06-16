import streamlit as st
from paddleocr import PaddleOCR
import re
import numpy as np
import pandas as pd
from PIL import Image
import io

# 1. 웹사이트 기본 설정
st.set_page_config(page_title="토너먼트 전적 리더기", page_icon="🏆")
st.title("🏆 토너먼트 전적 리더기")
st.write("게임 전적 화면을 업로드하면 순위와 상금을 자동으로 분석합니다.")

# 2. AI 모델 로딩 (서버 과부하를 막기 위해 캐싱 적용)
@st.cache_resource
def load_ocr():
    # 웹 서버 환경이므로 로그 출력을 끄고 한국어 모델 로드
    return PaddleOCR(use_angle_cls=True, lang='korean', show_log=False)

ocr = load_ocr()

# 3. 이미지 업로드 기능
uploaded_file = st.file_uploader("전적 이미지 선택 (PNG, JPG)", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # 화면에 업로드한 이미지 보여주기
    image = Image.open(uploaded_file)
    st.image(image, caption="업로드된 이미지", use_container_width=True)
    
    with st.spinner("AI가 이미지를 분석 중입니다... 잠시만 기다려주세요!"):
        try:
            # 이미지를 바이트로 변환하여 OCR 엔진에 전달
            img_bytes = uploaded_file.getvalue()
            result = ocr.ocr(img_bytes, cls=True)
            
            # Y좌표 기준으로 글자들의 위치 정렬 준비
            boxes_texts = []
            for line in result[0]:
                box = line[0]
                text = line[1][0]
                y_center = np.mean([box[0][1], box[2][1]])
                boxes_texts.append({'text': text, 'y': y_center})
                
            # 날짜 찾기 (YYYY-MM-DD)
            date_str = "날짜 인식 불가"
            date_pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
            for item in boxes_texts:
                if date_pattern.search(item['text']):
                    date_str = date_pattern.search(item['text']).group()
                    break
                    
            # 오차범위 15픽셀 내의 글자들을 같은 줄(행)로 묶기
            boxes_texts.sort(key=lambda x: x['y'])
            rows = []
            current_row = []
            current_y = boxes_texts[0]['y'] if boxes_texts else 0
            
            for item in boxes_texts:
                if abs(item['y'] - current_y) < 15:
                    current_row.append(item['text'])
                else:
                    rows.append(current_row)
                    current_row = [item['text']]
                    current_y = item['y']
            if current_row:
                rows.append(current_row)
                
            # "토너먼트" 글자가 포함된 줄만 뽑아서 표 데이터로 만들기
            table_data = []
            for row in rows:
                text_line = " ".join(row)
                if "토너먼트" in text_line:
                    rank = next((t for t in row if "등" in t), "-")
                    game_name = next((t for t in row if "GTD" in t), "이름 인식 불가")
                    prize = row[-1] if len(row) > 0 else "-"
                    table_data.append({"순위": rank, "게임 명": game_name, "수익/상금": prize})
                    
            # 4. 분석 결과 화면에 출력하기
            st.success(f"📅 인식된 날짜: {date_str}")
            
            if table_data:
                # 데이터를 깔끔한 표(DataFrame) 형태로 변환하여 출력
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("이미지에서 '토너먼트' 기록을 찾지 못했습니다. 이미지를 다시 확인해주세요.")
                
        except Exception as e:
            st.error(f"분석 중 오류가 발생했습니다: {e}")
