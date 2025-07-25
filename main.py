import streamlit as st
import random

st.set_page_config(page_title="가위바위보 ✊✌️🖐", layout="centered")
st.title("✊✌️🖐 가위바위보 게임")

choices = ["가위", "바위", "보"]
emojis = {
    "가위": "✌️",
    "바위": "✊",
    "보": "🖐"
}

# 사용자 선택
st.subheader("무엇을 낼래요?")
col1, col2, col3 = st.columns(3)
user_choice = None

with col1:
    if st.button("✌️ 가위"):
        user_choice = "가위"
with col2:
    if st.button("✊ 바위"):
        user_choice = "바위"
with col3:
    if st.button("🖐 보"):
        user_choice = "보"

# 결과 처리
if user_choice:
    computer_choice = random.choice(choices)

    st.write(f"👦 당신: {emojis[user_choice]} ({user_choice})")
    st.write(f"🤖 컴퓨터: {emojis[computer_choice]} ({computer_choice})")

    if user_choice == computer_choice:
        st.success("😲 비겼어요!")
    elif (
        (user_choice == "가위" and computer_choice == "보") or
        (user_choice == "바위" and computer_choice == "가위") or
        (user_choice == "보" and computer_choice == "바위")
    ):
        st.success("🎉 이겼어요!")
    else:
        st.error("😭 졌어요!")
