from langchain_core.messages import SystemMessage, HumanMessage

from app.config.config import get_settings
from app.providers.llm import LLMType, get_llm
from app.services.tavilyService import tavily_search_async, deduplicate_and_format_sources
from app.utils.prompts import RESEARCH_QUERY_WRITER, SECTION_WRITER
from app.utils.state import ResearchState, SectionState, Queries
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def generate_queries(state: SectionState):
    settings = get_settings()
    number_of_queries = settings.number_of_queries
    # Get state
    section = state["section"]
    # Get LLM instance based on configuration
    try:
        llm_type = LLMType(settings.default_llm_type)
        llm = get_llm(llm_type)
        logger.info(f"Using LLM: {llm_type}")
    except ValueError as e:
        logger.warning(f"Invalid LLM type in configuration, falling back to GPT-4o-mini: {e}")
        llm = get_llm(LLMType.GPT_4O_MINI)

    structured_llm = llm.with_structured_output(Queries)

    # Format system instructions
    system_instructions = RESEARCH_QUERY_WRITER.format(section_topic=section.description,
                                                       number_of_queries=number_of_queries)
    # Generate queries
    queries = structured_llm.invoke([SystemMessage(content=system_instructions)] + [
        HumanMessage(content="Generate search queries on the provided topic.")])
    # Logic to generate search queries based on the topic
    return {"search_queries": queries.queries}


def retrieve_documents(state: ResearchState):
    # Logic to retrieve documents from a search
    state.documents.append("Retrieved document 1")
    state.documents.append("Retrieved document 2")
    return state


async def search_web(state: SectionState):
    """ Search the web for each query, then return a list of raw sources and a formatted string of sources."""
    settings = get_settings()
    tavily_topic = settings.tavily_topic
    tavily_days = settings.tavily_days
    # Get state
    search_queries = state["search_queries"]

    # Web search
    query_list = [query.search_query for query in search_queries]
    search_docs = await tavily_search_async(query_list, tavily_topic, tavily_days)

    # Deduplicate and format sources
    source_str = deduplicate_and_format_sources(search_docs, max_tokens_per_source=5000, include_raw_content=True)

    return {"source_str": source_str}


def write_section(state: SectionState):
    """ Write a section of the report """
    settings = get_settings()
    # Get state
    section = state["section"]
    source_str = state["source_str"]

    # Format system instructions
    system_instructions = SECTION_WRITER.format(section_title=section.name,
                                                section_topic=section.description, context=source_str)

    # Get LLM instance based on configuration
    try:
        llm_type = LLMType(settings.default_llm_type)
        llm = get_llm(llm_type)
        logger.info(f"Using LLM: {llm_type}")
    except ValueError as e:
        logger.warning(f"Invalid LLM type in configuration, falling back to GPT-4o-mini: {e}")
        llm = get_llm(LLMType.GPT_4O_MINI)

    # Generate section
    section_content = llm.invoke([SystemMessage(content=system_instructions)] + [
        HumanMessage(content="Generate a report section based on the provided sources.")])

    # Write content to the section object
    section.content = section_content.content

    # Write the updated section to completed sections
    return {"completed_sections": [section]}
