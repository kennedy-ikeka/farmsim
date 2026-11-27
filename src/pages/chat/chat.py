import streamlit as st
from src.workflows.support_agent import get_support_agent
from pages.chat.bot import Bot
from src.models.workflow import WorkflowSettings
from src.utils.knowledge import Knowledge
from src.utils.storage import Storage

def main():
    settings = st.session_state['settings']['Bot']
    km = Knowledge('finsight')
    store = Storage()
    agent = get_support_agent(settings=WorkflowSettings(online=settings['online'], temperature=settings['temperature']))
    
    chatbot = Bot(agent, km, store)
    chatbot.session()

if __name__ == '__main__':
    main()