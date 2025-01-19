from langchain_core.messages import SystemMessage, HumanMessage

from app.config.config import get_settings
from app.providers.llm import LLMType, get_llm
from app.utils.prompts import FINAL_SECTION_WRITER
from app.utils.state import ReportState, Section, SectionState
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def compile_report(state: ReportState):
    # Ensure all sections are properly compiled
    # compiled_content = f"# Final Report: {state.topic}\n\n"
    # for section in state.sections:
    #     compiled_content += f"## {section.name}\n{section.content if section.content else 'Content not available'}\n\n"
    # state.final_report = compiled_content
    sections = state["sections"]
    completed_sections = {s.name: s.content for s in state["completed_sections"]}
    # Update sections with completed content while maintaining original order
    for section in sections:
        section.content = completed_sections[section.name]

        # Compile final report
    all_sections = "\n\n".join([s.content for s in sections])

    return {"final_report": all_sections}


def gather_completed_sections(state: ReportState):
    """ Gather completed sections from research and format them as context for writing the final sections """

    # List of completed sections
    completed_sections = state["completed_sections"]

    # Format completed section to str to use as context for final sections
    completed_report_sections = format_sections(completed_sections)

    return {"report_sections_from_research": completed_report_sections}


def format_sections(sections: list[Section]) -> str:
    """ Format a list of sections into a string """
    formatted_str = ""
    for idx, section in enumerate(sections, 1):
        formatted_str += f"""
{'=' * 60}
Section {idx}: {section.name}
{'=' * 60}
Description:
{section.description}
Requires Research: 
{section.research}

Content:
{section.content if section.content else '[Not yet written]'}

"""
    return formatted_str


def write_final_sections(state: SectionState):
    """ Write final sections of the report, which do not require web search and use the completed sections as context """

    # Get state
    section = state["section"]
    completed_report_sections = state["report_sections_from_research"]

    # Format system instructions
    system_instructions = FINAL_SECTION_WRITER.format(section_title=section.name,
                                                      section_topic=section.description,
                                                      context=completed_report_sections)
    settings = get_settings()
    # Get LLM instance based on configuration
    try:
        llm_type = LLMType(settings.default_llm_type)
        llm = get_llm(llm_type)
    except ValueError as e:
        logger.warning(f"Invalid LLM type in configuration, falling back to GPT-4o-mini: {e}")
        llm = get_llm(LLMType.GPT_4O_MINI)
    # Generate section
    section_content = llm.invoke([SystemMessage(content=system_instructions)] + [
        HumanMessage(content="Generate a report section based on the provided sources.")])

    # Write content to section
    section.content = section_content.content

    # Write the updated section to completed sections
    return {"completed_sections": [section]}


def compile_final_report(state: ReportState):
    """ Compile the final report """

    # Get sections
    sections = state["sections"]
    completed_sections = {s.name: s.content for s in state["completed_sections"]}

    # Update sections with completed content while maintaining original order
    for section in sections:
        section.content = completed_sections[section.name]

    # Compile final report
    all_sections = "\n\n".join([s.content for s in sections])
    # Prompt para estructurar el reporte final
    final_report_prompt = f"""
    You are an expert technical writer tasked with compiling a comprehensive, professional, and structured report about an AI tool or agent. The report must strictly follow the guidelines and sections below.

    ## Report Structure and Guidelines:

    ### **Base Sections (Mandatory for All Agents):**
    1. **Introduction:**
        - Brief description of the agent: What it is and its purpose.
        - Provide links to official documentation or the product's website.
        - Context on why this agent was chosen.

    2. **Research/Testing Objectives:**
        - What was expected to be learned or validated with this agent?
        - Scope and specific goals.

    3. **Key Features:**
        - Main functionalities of the agent.
        - Types of problems it solves.
        - Integrations with other tools or APIs.

    4. **Prerequisites:**
        - Required languages, libraries, accounts, or subscriptions.
        - Recommended technical knowledge.

    5. **Installation/Initial Setup:**
        - Step-by-step instructions with exact commands.
        - Include environment variables, API keys, and account access details.

    6. **Practical Examples/Use Cases:**
        - A simple, reproducible case with clear instructions.
        - Include code snippets, screenshots, or diagrams (if applicable).

    7. **Advantages and Limitations:**
        - Strengths (e.g., ease of use, performance, scalability).
        - Weaknesses (e.g., complexity, technical limitations, costs).

    8. **Lessons Learned and Best Practices:**
        - Tips for using the tool effectively.
        - Challenges encountered and how they were overcome.

    9. **Next Steps/Future Development:**
        - Ideas for extending the tool, new use cases, or possible improvements.

    10. **References and Resources:**
        - Official documentation and functional links.
        - External tutorials, forums, or communities.

    ### **Specific Guidelines for Different Agent Types:**
    - For **Frameworks (e.g., LangChain, Haystack, Rasa):**
        - Detailed installation and dependencies (versions, libraries, recommended environments).
        - Explanation of internal architecture (e.g., chains, memories, tools).
        - Reproducible code snippets for running a basic agent.
        - Steps for integrating with LLMs or external services (e.g., OpenAI, Llama2).

    - For **Low-Code/No-Code Platforms (e.g., Zapier with AI, Bubble):**
        - Onboarding instructions for the platform (creating accounts, activating plugins).
        - Visual workflows with diagrams or screenshots.
        - Limitations of the visual environment (what can and cannot be done without coding).
        - A complete practical example of a visual workflow.

    - For **Products with Internal Agents (SaaS):**
        - Subscription plans and onboarding (e.g., Free, Pro).
        - Configuration options for internal AI (e.g., prompts or model parameters).
        - Testing key functionalities (e.g., internal chatbots, automated analysis).
        - Usability and UX evaluation (for non-technical users).
        - Pricing model and associated costs.

    ### **Writing Standards:**
    - **Clarity and Conciseness:** Avoid jargon; use clear, simple explanations.
    - **Markdown Formatting:** Use headings, lists, and bold text for better readability.
    - **Real Examples:** Include reproducible examples, not just theoretical concepts.
    - **Functional Links:** Verify all links are working.
    - **Periodic Updates:** Ensure the documentation remains up-to-date if the tool or process changes.

    ### Provided Context:
    {all_sections}

    Now, using the sections and context provided, compile the final report. Ensure the report adheres to the structure and quality standards outlined above, with clear headers and a professional tone.
    """

    settings = get_settings()
    # Get LLM instance based on configuration
    try:
        llm_type = LLMType(settings.default_llm_type)
        llm = get_llm(llm_type)
    except ValueError as e:
        logger.warning(f"Invalid LLM type in configuration, falling back to GPT-4o-mini: {e}")
        llm = get_llm(LLMType.GPT_4O_MINI)
    # Generar el reporte final usando el modelo
    final_report = llm.invoke(
        [
            SystemMessage(content="Generate a structured report."),
            HumanMessage(content=final_report_prompt),
        ]
    )
    return {"final_report": final_report.content}
