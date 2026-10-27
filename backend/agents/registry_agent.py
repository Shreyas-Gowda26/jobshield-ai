
"""
agents/registry_agent.py

CrewAI agent for checking company registration details
using the existing MCA lookup tool.
"""

from crewai import Agent, Task
from crewai.tools import tool

from backend.tools.registry.mca_lookup_tool import (
    lookup_company,
    lookup_cin,
)
from backend.utils.llm import get_llm


@tool("Lookup company in MCA records")
def mca_company_lookup(company_name: str) -> str:
    """Search configured MCA company records using a company name."""
    return str(lookup_company(company_name))


@tool("Lookup CIN in MCA records")
def mca_cin_lookup(cin: str) -> str:
    """Validate and search MCA company records using a Corporate
    Identification Number (CIN).
    """
    return str(lookup_cin(cin))


def create_registry_agent() -> Agent:
    """Create the company-registration verification agent."""
    return Agent(
        role="Company Registry Verification Specialist",
        goal=(
            "Check whether a company can be matched against available "
            "MCA records and clearly report the evidence and lookup status."
        ),
        backstory=(
            "You verify company registration claims using official company "
            "registry lookup results. You distinguish confirmed matches, "
            "no matches, invalid CINs, and lookup failures. You never treat "
            "an API failure as proof that a company is fraudulent."
        ),
        tools=[mca_company_lookup, mca_cin_lookup],
        llm=get_llm(temperature=0.1),
        verbose=True,
        allow_delegation=False,
    )


def create_registry_task(agent: Agent, company_name: str, cin: str = "") -> Task:
    """Create a registry verification task for a company."""
    cin_instruction = (
        f"Also check this supplied CIN: {cin}."
        if cin.strip()
        else "No CIN was supplied; perform the company-name lookup."
    )

    return Task(
        description=(
            f"Verify the registration evidence for the company "
            f"'{company_name}'. {cin_instruction}\n\n"
            "Use the available MCA lookup tools. Report the lookup status, "
            "matching company details, and any errors. Do not invent missing "
            "details. A lookup error or no match alone does not prove fraud."
            "IMPORTANT EVIDENCE RULES:\n"
            "- A status of 'not_found' means the lookup did not find a matching "
            "record in the sources and variations it checked.\n"
            "- Never conclude that the company is unregistered, fraudulent, fake, "
            "or illegitimate solely because a lookup returns 'not_found'.\n"
            "- Report the exact lookup status and any returned matches or errors.\n"
            "- Distinguish 'no matching record found' from 'confirmed registration'.\n"
            "- If the evidence is incomplete, explicitly state that the company's "
            "registration status remains unverified.\n"
            "- Never invent a CIN, registration record, or company identity.\n"
        ),
        expected_output=(
            "A concise report containing the company name, lookup status, "
            "matching registry details when available, errors or limitations, "
            "and a clear statement of what the evidence does and does not prove."
        ),
        agent=agent,
    )
