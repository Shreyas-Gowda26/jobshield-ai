
"""
agents/web_presence_agent.py

CrewAI agent for investigating a company's online presence
using web search and WHOIS evidence.
"""

from crewai import Agent, Task
from crewai.tools import tool

from backend.tools.web_presence.search_presence_tool import (
    search_company_presence,
)
from backend.tools.web_presence.whois_tool import lookup_domain
from backend.utils.llm import get_llm


@tool("Search company online presence")
def company_web_search(company_name: str) -> str:
    """Search the web for a company's official website and online presence."""
    return str(search_company_presence(company_name))


@tool("Lookup website domain registration")
def company_domain_lookup(domain: str) -> str:
    """Retrieve WHOIS registration details for a company website domain."""
    return str(lookup_domain(domain))


def create_web_presence_agent() -> Agent:
    """Create the online-presence investigation agent."""
    return Agent(
        role="Company Online Presence Investigator",
        goal=(
            "Collect and assess evidence about a company's online presence, "
            "official website, and domain registration."
        ),
        backstory=(
            "You investigate company websites and domain-registration "
            "details. You distinguish observed evidence from assumptions, "
            "report unavailable data honestly, and never treat a missing "
            "website or a WHOIS lookup failure alone as proof of fraud."
        ),
        tools=[company_web_search, company_domain_lookup],
        llm=get_llm(temperature=0.1),
        verbose=True,
        allow_delegation=False,
    )


def create_web_presence_task(
    agent: Agent,
    company_name: str,
    website: str = "",
) -> Task:
    """Create an online-presence investigation task."""
    website_instruction = (
        f"Investigate this supplied website or domain: {website}."
        if website.strip()
        else (
            "Search for the company's official website first. If a domain "
            "is identified, investigate its registration details."
        )
    )

    return Task(
        description=(
            f"Investigate the online presence of '{company_name}'. "
            f"{website_instruction}\n\n"
            "Use the available tools to gather evidence. Summarize relevant "
            "URLs, source details, and domain-registration information when "
            "available. Distinguish official sources from third-party "
            "mentions. Do not invent evidence or infer fraud solely from "
            "missing results, privacy-protected WHOIS details, or API errors."
        ),
        expected_output=(
            "A concise evidence report containing the company name, relevant "
            "web sources and URLs, domain-registration details when available, "
            "lookup limitations, and a cautious assessment of the evidence."
        ),
        agent=agent,
    )
