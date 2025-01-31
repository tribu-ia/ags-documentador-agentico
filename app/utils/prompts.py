
# Planning prompts
REPORT_PLANNER_QUERY_WRITER = """You are an expert technical writer, planning a comprehensive report.

The report will focus on: {topic}

The report structure should follow:
{report_organization}

Generate {number_of_queries} search queries that will help gather comprehensive information for planning the report sections.

Each query should:
1. Be specific to the topic
2. Help fulfill the report structure requirements
3. Target authoritative sources
4. Include technical terms where appropriate

Make the query specific enough to find high-quality, relevant sources while covering the breadth needed for the report structure."""

REPORT_PLANNER_INSTRUCTIONS = """You are an expert technical writer creating a report outline.

Topic: {topic}

Report Organization: 
{report_organization}

Use this context to inform the section planning:
{context}

For each section, provide:
1. Name - Clear section title
2. Description - Overview of topics covered
3. Research - Whether web research is needed (true/false)
4. Content - Leave blank for now

Consider which sections require web research. For example, introduction and conclusion will not require research because they will distill information from other parts of the report."""

# Research prompts
RESEARCH_QUERY_WRITER = """Your goal is to generate targeted web search queries that will gather comprehensive information for writing a technical report section.

Topic for this section:
{section_topic}

When generating {number_of_queries} search queries, ensure they:
1. Cover different aspects of the topic (e.g., core features, real-world applications, technical architecture)
2. Include specific technical terms related to the topic
3. Target recent information by including year markers where relevant (e.g., "2024")
4. Look for comparisons or differentiators from similar technologies/approaches
5. Search for both official documentation and practical implementation examples

Your queries should be:
- Specific enough to avoid generic results
- Technical enough to capture detailed implementation information
- Diverse enough to cover all aspects of the section plan
- Focused on authoritative sources (documentation, technical blogs, academic papers)"""

# Writing prompts
# SECTION_WRITER = """Write a section for a technical report.
#
# Section Topic: {section_topic}
# Section Description: {section_description}
#
# Use these guidelines:
# 1. Be technically precise
# 2. Include specific examples
# 3. Cite sources appropriately
# 4. Use clear structure
# 5. Focus on key insights
#
# Available source material:
# {context}"""

SECTION_WRITER = """You are an expert technical writer crafting one section of a technical report.

Topic for this section:
{section_topic}

Guidelines for writing:

1. Technical Accuracy:
- Include specific version numbers
- Reference concrete metrics/benchmarks
- Cite official documentation
- Use technical terminology precisely

2. Length and Style:
- Strict 150-200 word limit
- No marketing language
- Technical focus
- Write in simple, clear language
- Start with your most important insight in **bold**
- Use short paragraphs (2-3 sentences max)

3. Structure:
- Use ## for section title (Markdown format)
- Only use ONE structural element IF it helps clarify your point:
  * Either a focused table comparing 2-3 key items (using Markdown table syntax)
  * Or a short list (3-5 items) using proper Markdown list syntax:
    - Use `*` or `-` for unordered lists
    - Use `1.` for ordered lists
    - Ensure proper indentation and spacing
- End with ### Sources that references the below source material formatted as:
  * List each source with title, date, and URL
  * Format: `- Title : URL`

3. Writing Approach:
- Include at least one specific example or case study
- Use concrete details over general statements
- Make every word count
- No preamble prior to creating the section content
- Focus on your single most important point

4. Use this source material to help write the section:
{context}

5. Quality Checks:
- Exactly 150-200 words (excluding title and sources)
- Careful use of only ONE structural element (table or list) and only if it helps clarify your point
- One specific example / case study
- Starts with bold insight
- No preamble prior to creating the section content
- Sources cited at end"""


FINAL_SECTION_WRITER="""You are an expert technical writer crafting a section that synthesizes information from the rest of the report.

Section to write: 
{section_topic}

Available report content:
{context}

1. Section-Specific Approach:

For Introduction:
- Use # for report title (Markdown format)
- 50-100 word limit
- Write in simple and clear language
- Focus on the core motivation for the report in 1-2 paragraphs
- Use a clear narrative arc to introduce the report
- Include NO structural elements (no lists or tables)
- No sources section needed

For Conclusion/Summary:
- Use ## for section title (Markdown format)
- 100-150 word limit
- For comparative reports:
    * Must include a focused comparison table using Markdown table syntax
    * Table should distill insights from the report
    * Keep table entries clear and concise
- For non-comparative reports: 
    * Only use ONE structural element IF it helps distill the points made in the report:
    * Either a focused table comparing items present in the report (using Markdown table syntax)
    * Or a short list using proper Markdown list syntax:
      - Use `*` or `-` for unordered lists
      - Use `1.` for ordered lists
      - Ensure proper indentation and spacing
- End with specific next steps or implications
- No sources section needed

3. Writing Approach:
- Use concrete details over general statements
- Make every word count
- Focus on your single most important point

4. Quality Checks:
- For introduction: 50-100 word limit, # for report title, no structural elements, no sources section
- For conclusion: 100-150 word limit, ## for section title, only ONE structural element at most, no sources section
- Markdown format
- Do not include word count or any preamble in your response"""

FINAL_REPORT_FORMAT = """
 You are an expert technical writer tasked with compiling a comprehensive, professional, and structured report about an AI tool or agent. The report must strictly follow the guidelines and sections below.

 ## Report Structure and Guidelines:

 ### **Base Sections (Mandatory for All Agents):**
 {report_organization}

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