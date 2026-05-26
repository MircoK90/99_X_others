import logging
from langchain_core.messages import AIMessage
from src.state import AgentState

logger = logging.getLogger(__name__)

def handle_urgent_node(state: AgentState):
    # Handles alerts with "urgent" severity — escalates faster than medium, slower than critical
    logger.info(f"Node 'handle_urgent': Urgent alert ({state['alert_info']}). Fast-track response.")
    final_msg = "URGENT alert detected. Fast-track escalation to on-call team within 15 min."
    return {"messages": [AIMessage(content=final_msg)], "final_result": final_msg}