"""Streamlit: вход, RAG, задачи, Гант, экспорт."""
import os,time,httpx,streamlit as st
from auth_core import authenticate,allowed
from export_utils import excel,pdf,json_bytes
from gantt_utils import build_gantt
API=os.getenv("API_URL","http://localhost:8000")
st.set_page_config(page_title="Лабораторная 7",layout="wide")
if "user" not in st.session_state:st.session_state.user=None
if "logged_at" not in st.session_state:st.session_state.logged_at=0
if st.session_state.user and time.time()-st.session_state.logged_at>8*3600:st.session_state.user=None
if not st.session_state.user:
    st.title("Вход в учебную систему")
    with st.form("login"):
        login=st.text_input("Логин");password=st.text_input("Пароль",type="password")
        if st.form_submit_button("Войти"):
            user=authenticate(login,password)
            if user:st.session_state.user=user;st.session_state.logged_at=time.time();st.rerun()
            else:st.error("Неверный логин или пароль")
    st.caption("Демо: admin / admin123, engineer / engineer123, student / student123. Только для локального обучения.")
    st.stop()
user=st.session_state.user;role=user["role"]
st.title("Лабораторная №7 — "+role)
if st.button("Выйти"):st.session_state.user=None;st.rerun()
try:
    health=httpx.get(API+"/health",timeout=15).json()
    st.caption(f'База знаний: {health["articles"]} статей · Задач: {health["tasks"]}')
except Exception as e:st.error("API недоступен: "+str(type(e).__name__));st.stop()
tab1,tab2,tab3=st.tabs(["RAG-помощник","Заявки","График и экспорт"])
with tab1:
    query=st.text_input("Вопрос по предметной области")
    if st.button("Найти ответ") and query:
        try:
            result=httpx.post(API+"/ask",json={"query":query,"k":3},timeout=65).json()
            st.write(result["answer"]);st.caption("Источник ответа: "+result["answer_source"]+"; модель: "+str(result["llm_model"]))
            if result["llm_error"]:st.warning("LLM недоступна: "+result["llm_error"]+". Использован шаблон.")
            if result["unknown_cited_ids"]:st.warning("Неизвестные ID ссылок: "+str(result["unknown_cited_ids"]))
            st.json(result["sources"])
        except Exception as e:st.error("Ошибка запроса: "+type(e).__name__)
with tab2:
    st.dataframe(httpx.get(API+"/tasks",timeout=15).json(),use_container_width=True)
    if allowed(role,"create"):
        with st.form("newtask"):
            title=st.text_input("Название новой задачи");priority=st.selectbox("Приоритет",["low","medium","high","critical"]);duration=st.slider("Длительность",1,4,1)
            if st.form_submit_button("Создать"):
                if title.strip():
                    resp=httpx.post(API+"/tasks",json={"title":title,"priority":priority,"duration":duration},timeout=15)
                    st.success("Создано" if resp.is_success else "Ошибка: "+resp.text)
                else:st.error("Название обязательно")
    else:st.info("Роль student не может создавать заявки")
with tab3:
    horizon=st.slider("Горизонт планирования, часов",4,16,8)
    if st.button("Построить расписание"):
        st.session_state.schedule=httpx.get(API+"/schedule",params={"horizon":horizon},timeout=30).json()
    if "schedule" in st.session_state:
        data=st.session_state.schedule
        st.write("Статус:",data["status"],"; неназначено:",len(data["unassigned"]))
        st.plotly_chart(build_gantt(data),use_container_width=True)
        st.dataframe(data["assignments"],use_container_width=True)
        st.download_button("Excel (.xlsx)",excel(data),"schedule.xlsx")
        st.download_button("PDF",pdf(data),"schedule.pdf",mime="application/pdf")
        st.download_button("JSON",json_bytes(data),"schedule.json",mime="application/json")
