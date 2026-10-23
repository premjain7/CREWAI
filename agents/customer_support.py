"""Agent 5: Customer Support Flow.

Preserved from Project_5_Customer_Support_Flow.ipynb.
"""

from typing import Dict, Any

from pydantic import BaseModel
from crewai.flow.flow import Flow, start, listen, router, or_

from services.gemini import get_llm


class TicketState(BaseModel):
    ticket_text: str = ""
    category: str = ""
    priority: str = ""
    resolution: str = ""


class CustomerSupportFlow(Flow[TicketState]):
    """Flow that classifies tickets and applies priority and resolution rules."""

    def __init__(self, initial_ticket: str = ""):
        super().__init__()
        self.initial_ticket = initial_ticket

    @start()
    def receive_ticket(self):
        ticket = self.initial_ticket.strip()
        if not ticket:
            raise ValueError("Support ticket cannot be empty.")
        self.state.ticket_text = ticket

    @listen(receive_ticket)
    def categorize_ticket(self):
        llm = get_llm(temperature=0.1)

        prompt = f"""
You are a customer support ticket classifier.

Classify the following customer ticket into exactly ONE category:
- billing: payments, refunds, invoices, charges
- account_access: login problems, passwords, account lockouts
- other: technical issues, feature requests, all other problems

Return ONLY the category name.
Do not explain your answer.

Customer ticket:
{self.state.ticket_text}
"""
        response = llm.call(prompt)
        category = str(response).strip().lower()

        if "billing" in category:
            category = "billing"
        elif "account_access" in category or "account access" in category:
            category = "account_access"
        else:
            category = "other"

        self.state.category = category

    @router(categorize_ticket)
    def route_by_category(self):
        category = self.state.category
        if category == "billing":
            return "billing"
        elif category == "account_access":
            return "account_access"
        else:
            return "other"

    @listen("billing")
    def handle_billing(self):
        self.state.priority = "High"
        self.state.resolution = (
            "Billing Support: Verify the transaction, review the invoice, "
            "and investigate any refund or incorrect charge."
        )

    @listen("account_access")
    def handle_access(self):
        self.state.priority = "High"
        self.state.resolution = (
            "Account Access Support: Help the customer reset their "
            "password, resolve login problems, or unlock their account."
        )

    @listen("other")
    def handle_other(self):
        self.state.priority = "Medium"
        self.state.resolution = (
            "General Support: Investigate the technical issue or feature "
            "request and provide troubleshooting or escalation steps."
        )

    @listen(or_(handle_billing, handle_access, handle_other))
    def resolve_ticket(self):
        return {
            "ticket": self.state.ticket_text,
            "category": self.state.category,
            "priority": self.state.priority,
            "resolution": self.state.resolution,
        }


def run_customer_support(ticket_text: str) -> Dict[str, Any]:
    """Runs the CustomerSupportFlow and returns category, priority, and resolution."""
    clean_text = ticket_text.strip()
    if not clean_text:
        raise ValueError("Customer support ticket description cannot be empty.")

    flow = CustomerSupportFlow(initial_ticket=clean_text)
    result = flow.kickoff()

    return {
        "ticket": result.get("ticket", clean_text),
        "category": result.get("category", flow.state.category),
        "priority": result.get("priority", flow.state.priority),
        "resolution": result.get("resolution", flow.state.resolution),
    }
