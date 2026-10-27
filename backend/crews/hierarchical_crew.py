
from crewai import Crew, Process, Task

from backend.agents.manager_agent import create_manager_agent
from backend.agents.registry_agent import create_registry_agent
from backend.agents.web_presence_agent import create_web_presence_agent
from backend.agents.communication_agent import create_communication_agent
from backend.agents.scoring_agent import create_scoring_agent


def create_hierarchical_crew() -> Crew:
    """Create the manager-led JobShield specialist investigation crew."""

    manager = create_manager_agent()

    registry_agent = create_registry_agent()
    web_agent = create_web_presence_agent()
    communication_agent = create_communication_agent()
    scoring_agent = create_scoring_agent()

    investigation_task = Task(
        description=(
            "Produce an evidence-grounded investigation report from the "
            "provided investigation input:\n\n"
            "{investigation_input}\n\n"
            "Start by inspecting the submitted information, initial evidence, "
            "authoritative scoring, and limitations.\n\n"
            "Decide adaptively which specialist work is necessary. The "
            "initial evidence has already been collected by deterministic "
            "tools. Do not repeat checks by default. Delegate only to answer "
            "a specific question that materially affects the investigation. "
            "If no useful follow-up is needed, synthesize the available "
            "evidence without unnecessary delegation.\n\n"
            "When delegating, provide a clear task AND the relevant context "
            "to the selected specialist. Do not issue a vague delegation.\n\n"
            "For company registration, use the Registry Specialist. For "
            "online presence and domain evidence, use the Web Presence "
            "Investigator. For offer-language evidence, use the Communication "
            "Analyst. For score interpretation, use the Scoring Analyst, "
            "but treat the supplied score as authoritative and do not ask "
            "the analyst to calculate a replacement score.\n\n"
            "A search tool status of 'found' means results were returned; "
            "it does not by itself establish that the exact company was "
            "found. Check the identity and relevance of the returned results. "
            "Do not present unrelated companies as evidence about the target.\n\n"
            "Only configured findings from the deterministic offer scan "
            "contribute to the numeric risk score. Do not add your own "
            "suspected red flags to that score. Preserve the supplied numeric "
            "score and risk level exactly. If either is missing, state that "
            "it was not supplied rather than inventing it.\n\n"
            "Never interpret a failed lookup or missing match as proof of "
            "fraud. Distinguish facts, tool errors, uncertainty, and "
            "recommendations. Do not claim a follow-up check occurred unless "
            "a specialist actually performed it."
        ),
        expected_output=(
            "A structured report with these sections:\n"
            "1. Summary of the submitted case.\n"
            "2. Company identity and registration evidence.\n"
            "3. Online presence and domain evidence, if available.\n"
            "4. Configured job-offer red flags, if an offer was provided.\n"
            "5. The supplied deterministic score and risk level, unchanged.\n"
            "6. Evidence gaps, lookup failures, and uncertainty.\n"
            "7. Practical recommendations.\n\n"
            "Clearly distinguish verified findings from interpretations. "
            "Do not invent results, matches, tool calls, or scores."
        ),
    )

    return Crew(
        agents=[
            registry_agent,
            web_agent,
            communication_agent,
            scoring_agent,
        ],
        tasks=[investigation_task],
        process=Process.hierarchical,
        manager_agent=manager,
        verbose=True,
        max_rpm=10,
    )
