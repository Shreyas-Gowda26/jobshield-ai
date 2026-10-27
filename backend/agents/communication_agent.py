
"""
agents/communication_agent.py

CrewAI agent for detecting suspicious language in job offers.
"""

from crewai import Agent, Task
from crewai.tools import tool

from backend.tools.communication.offer_scan_tool import scan_offer
from backend.utils.llm import get_llm


@tool("Scan job offer for suspicious language")
def job_offer_scan(offer_text: str) -> str:
    """Scan job offer text for predefined fraud-related red flags."""
    return str(scan_offer(offer_text))


def create_communication_agent() -> Agent:
    """Create the job-offer communication analysis agent."""
    return Agent(
        role="Job Offer Communication Analyst",
        goal=(
            "Identify suspicious language and explain the evidence "
            "found in job offers and recruiter communications."
        ),
        backstory=(
            "You examine job-offer messages for suspicious requests, "
            "unrealistic promises, payment demands, and pressure tactics. "
            "You rely on the scanning tool's findings and never claim "
            "that a message is fraudulent without sufficient evidence."
        ),
        tools=[job_offer_scan],
        llm=get_llm(temperature=0.1),
        verbose=True,
        allow_delegation=False,
    )


def create_communication_task(agent: Agent, offer_text: str) -> Task:
    """Create a task to analyze a job offer."""
    return Task(
        description=(
            "Analyze the following job-offer or recruiter message for "
            "potential red flags. Use the scanning tool and explain each "
            "finding using the returned evidence. Do not invent findings. "
            "A message with no detected rules is not automatically safe.\n\n"
            f"Message to analyze:\n{offer_text}"
            "IMPORTANT EVIDENCE RULES:\n"
            "- Treat the offer scanner's returned findings as the authoritative "
            "list of configured red flags.\n"
            "- Do not add new findings to that list based on your own interpretation.\n"
            "- You may describe other suspicious wording as an observation, but "
            "label it separately as an unverified concern.\n"
            "- Do not claim that a payment demand, missing CIN, placeholder name, "
            "or missing contact details were detected unless the supplied evidence "
            "actually supports that claim.\n"
            "- Do not invent severity levels or findings.\n"
            "- If no configured red flags are detected, state that this does not "
            "guarantee that the offer is legitimate.\n"
        ),
        expected_output=(
            "A report listing detected red flags, their severity, evidence, "
            "and recommendations. If no rules are triggered, explicitly "
            "state that no configured red flags were detected and that "
            "this does not guarantee the offer is legitimate."
        ),
        agent=agent,
    )
