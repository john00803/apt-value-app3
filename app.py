import streamlit as st
import pandas as pd
import openai
import os
from io import BytesIO
from datetime import datetime
from reportlab.pdfgen import canvas

from usage_tracker import load_user_plan, increment_usage, is_usage_exceeded
from ocr_utils import extract_text_from_image
from gpt_module import gpt_fix_ocr_text
from parser import parse_text_v2

st.set_page_config(page_title="아파트 값지 평가", layout="centered")
st.info("🚀 처음 접속 시 앱이 깨어나는 데 약 10초 정도 걸리는 것을 걸린다. 조금만 기다리세요 😊")
st.title("🏠 아파트 값지 평가 프로그램")
st.write("이미지를 업로드하면 자동으로 시세 정보를 추출합니다.")

user_email = st.sidebar.text_input("이메일을 입력하세요")
user_plan = load_user_plan(user_email) if user_email else None
is_premium_user = user_plan in ["standard", "pro"]

gpt_answer = None

uploaded_image = st.file_uploader("�햼️ 아파트 정보 이미지 업로드", type=["png", "jpg", "jpeg"])
if uploaded_image:
    image_bytes = uploaded_image.read()
    extracted_text = extract_text_from_image(BytesIO(image_bytes))
    st.write("**�퓝 OCR 추출 결과:**")
    st.code(extracted_text)

    openai.api_key = os.getenv("OPENAI_API_KEY")
    fixed_text = gpt_fix_ocr_text(extracted_text)
    st.write("**🔧 GPT 보정 결과:**")
    st.code(fixed_text)

    parsed_data = parse_text_v2(fixed_text)
    st.success(f"자동 인식 결과: {parsed_data}")

    apt_name = st.text_input("🏢 아파트 이름", value=parsed_data['apt_name'] or "")
    size = st.text_input("💨 전용면적 (㎡)", value=parsed_data['size'] or "")
    floor = st.text_input("🏙️ 치수", value=parsed_data['floor'] or "")
    direction = st.text_input("🧭 방향", value=parsed_data['direction'] or "")
    price = st.number_input("💰 현재 시세 (억)", min_value=0.0, value=float(parsed_data['price'] or 0), step=0.1)

    if apt_name and price > 0:
        st.subheader("📊 요약 평가 (v1~v2 기반)")
        st.write(f"`{apt_name}`의 시세는 **{price:.1f}억**입니다.")
        st.bar_chart({"항목": [price, price * 1.05, price * 0.95]})

        st.markdown("---")
        st.subheader("💬 GPT 질의응답")
        sample_questions = [
            f"{apt_name} 아파트는 투자 가치가 있나요?",
            f"{apt_name}의 시세는 아래로 어떻게 될까요?",
            f"{apt_name}의 실거주 맛적도는 어떻게나요?"
        ]
        question = st.selectbox("자동 질문 예시 또는 직접 입력:", sample_questions + ["직접 입력"])
        user_question = st.text_input("질문을 입력하세요") if question == "직접 입력" else question

        if st.button("질문하기") and user_question:
            if openai.api_key:
                plan = user_plan or "free"
                exceeded, used, limit = is_usage_exceeded(user_email, plan)
                if exceeded:
                    st.warning(f"'{plan}' 플래는 하루 {limit}회까지만 질문할 수 있어요. (현재 {used}회 사용)")
                else:
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "너는 부동산 분석 및 투자 조언 전문가야."},
                            {"role": "user", "content": user_question}
                        ]
                    )
                    gpt_answer = response.choices[0].message.content.strip()
                    st.success(gpt_answer)
                    increment_usage(user_email)
            else:
                st.error("OpenAI API 키가 누락되었습니다.")

        if gpt_answer:
            if st.button("📄 PDF로 저장"):
                buffer = BytesIO()
                c = canvas.Canvas(buffer)
                c.setFont("Helvetica", 12)
                c.drawString(50, 800, f"아파트 값지 평가 리포트 - {apt_name}")
                c.drawString(50, 780, f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                text_object = c.beginText(50, 750)
                for line in gpt_answer.split('\n'):
                    text_object.textLine(line)
                c.drawText(text_object)
                c.showPage()
                c.save()
                st.download_button(
                    label="PDF 다운로드",
                    data=buffer.getvalue(),
                    file_name=f"{apt_name}_GPT분석.pdf",
                    mime="application/pdf"
                )
