from typing import Annotated, TypedDict, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from dataclasses import dataclass, asdict

from app.config.config import get_settings
from app.providers.llm import LLMType, get_llm
from app.utils.prompts import REPORT_PLANNER_QUERY_WRITER, REPORT_PLANNER_INSTRUCTIONS
#from app.utils.state import ReportState, Section, Queries, Sections
from app.services.tavilyService import tavily_search_async, deduplicate_and_format_sources
import logging

from app.utils.state import ReportState, Queries, Sections

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define una estructura más clara para el estado
class State(TypedDict):
    messages: Annotated[list, add_messages]
    report_state: ReportState
    search_results: str
    queries: List[dict]  # Aseguramos que queries sea una lista de diccionarios
    sections: List[dict]

def query_generator(state: State) -> State:
    """Node to generate search queries"""
    settings = get_settings()
    try:
        llm_type = LLMType(settings.default_llm_type)
        llm = get_llm(llm_type)
        logger.info(f"Using LLM: {llm_type}")
    except ValueError as e:
        logger.warning(f"Invalid LLM type in configuration, falling back to GPT-4o-mini: {e}")
        llm = get_llm(LLMType.GPT_4O_MINI)

    structured_llm = llm.with_structured_output(Queries)
    system_instructions = REPORT_PLANNER_QUERY_WRITER.format(
        topic=state["report_state"].topic,
        report_organization=settings.report_structure,
        number_of_queries=settings.number_of_queries
    )

    results = structured_llm.invoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Generate search queries for planning the report sections.")
    ])

    # Convertir los resultados a una lista de diccionarios
    queries = [{"search_query": q.search_query} for q in results.queries]
    
    return {
        **state,
        "messages": state["messages"] + [SystemMessage(content=f"Generated queries: {queries}")],
        "queries": queries
    }

async def search_executor(state: State) -> State:
    """Node to execute searches"""
    settings = get_settings()
    
    # Verificar y extraer las queries de manera segura
    queries = state.get("queries", [])
    if not queries:
        logger.warning("No queries found in state")
        return {
            **state,
            "search_results": ""
        }
    
    # Extraer las search_queries de manera segura
    query_list = [q.get("search_query") for q in queries if q.get("search_query")]
    
    if not query_list:
        logger.warning("No valid search queries found")
        return {
            **state,
            "search_results": ""
        }

    search_docs = await tavily_search_async(
        query_list,
        settings.tavily_topic,
        settings.tavily_days
    )
    
    source_str = deduplicate_and_format_sources(
        search_docs,
        max_tokens_per_source=1000,
        include_raw_content=False
    )

    return {
        **state,
        "search_results": source_str
    }

def section_planner(state: State):
    """Node to plan report sections"""
    settings = get_settings()
    try:
        llm_type = LLMType(settings.default_llm_type)
        llm = get_llm(llm_type)
    except ValueError:
        llm = get_llm(LLMType.GPT_4O_MINI)

    structured_llm = llm.with_structured_output(Sections)
    system_instructions = REPORT_PLANNER_INSTRUCTIONS.format(
        topic=state["report_state"].topic,
        report_organization=settings.report_structure,
        context=state["search_results"]
    )

    report_sections = structured_llm.invoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Generate the report sections based on the research.")
    ])

    return {
        **state,
        "sections": report_sections.sections
    }

async def plan_report(state: ReportState):
    """Generate a dynamic report plan using LangGraph"""
    # Initialize graph
    graph_builder = StateGraph(State)
    memory = MemorySaver()

    # Add nodes
    graph_builder.add_node("query_generator", query_generator)
    graph_builder.add_node("search_executor", search_executor)
    graph_builder.add_node("section_planner", section_planner)

    # Set the entry point
    graph_builder.set_entry_point("query_generator")

    # Add edges to define workflow
    graph_builder.add_edge("query_generator", "search_executor")
    graph_builder.add_edge("search_executor", "section_planner")
    
    # Set the end condition
    graph_builder.set_finish_point("section_planner")

    # Compile graph
    graph = graph_builder.compile(checkpointer=memory)

    # Initialize state and run graph
    initial_state = {
        "messages": [],
        "report_state": state,
        "search_results": "",
        "queries": [],
        "sections": []
    }

    # Execute graph
    final_state = await graph.ainvoke(initial_state)

    return {"sections": final_state.get("sections", [])}
