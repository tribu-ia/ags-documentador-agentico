from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.config.config import get_settings
from app.utils.prompts import REPORT_PLANNER_QUERY_WRITER, REPORT_PLANNER_INSTRUCTIONS
from app.utils.state import ReportState, Section, Queries, Sections
from app.services.tavilyService import tavily_search_async, deduplicate_and_format_sources
import logging

logging.basicConfig(level=logging.DEBUG)


async def plan_report(state: ReportState):
    """Generate a dynamic report plan using LLM and web research"""

    settings = get_settings()
    claude = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # Generate initial search queries
    structured_llm = claude.with_structured_output(Queries)
    system_instructions = REPORT_PLANNER_QUERY_WRITER.format(
        topic=state.topic,
        report_organization=settings.report_structure,
        number_of_queries=settings.number_of_queries
    )

    results = structured_llm.invoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Generate search queries for planning the report sections.")
    ])

    # Perform web searches in parallel
    query_list = [query.search_query for query in results.queries]
    search_docs = await tavily_search_async(
        query_list,
        settings.tavily_topic,
        settings.tavily_days
    )

    # Format search results
    source_str = deduplicate_and_format_sources(
        search_docs,
        max_tokens_per_source=1000,
        include_raw_content=False
    )

    # Generate sections based on research
    system_instructions = REPORT_PLANNER_INSTRUCTIONS.format(
        topic=state.topic,
        report_organization=settings.report_structure,
        context=source_str
    )
    structured_llm = claude.with_structured_output(Sections)
    report_sections = structured_llm.invoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content="Generate the report sections based on the research.")
    ])
    print(f"Response from LLM: {report_sections}")
    logging.debug(f"Response from LLM: {report_sections}")
    logging.debug(f"Response content: {report_sections.sections}")
    # Parse sections from response
    # sections = []
    # for section_data in response.content:
    #     sections.append(
    #         Section(
    #             name=section_data["name"],
    #             description=section_data["description"],
    #             research=section_data["research"],
    #             content=""
    #         )
    #     )

    return {"sections": report_sections.sections}
