"""
Lead Follow-Up Agent
--------------------
Reads new leads from a CSV (drop-in replacement for a Google Sheet),
sends each one to Gemini for structured qualification, validates the
AI output against a strict schema, and creates a Gmail DRAFT
(never auto-sends) for a human salesperson to review.

Run:
    python main.py
"""

import base64
import csv
import json
import logging
import os
import sys
import time
from email.mime.text import MIMEText
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from google import genai


# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------

load_dotenv()

LEADS_CSV = Path("leads.csv")
PROCESSED_FILE = Path("processed_leads.json")
REVIEW_LOG_FILE = Path("lead_reviews.json")
CREDENTIALS_FILE = Path("credentials.json")
TOKEN_FILE = Path("token.json")

# Least-privilege Gmail scope.
# This allows the app to create/modify drafts but not send mail.
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose"
]

DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

# Current Gemini model.
# Can be overridden in .env using GEMINI_MODEL.
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash"
)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("run.log")
    ],
)

log = logging.getLogger("lead_agent")


# --------------------------------------------------------------------------
# Structured output schema
# --------------------------------------------------------------------------

class LeadAnalysis(BaseModel):
    lead_score: int = Field(
        ge=0,
        le=100,
        description="Lead quality score from 0 to 100."
    )

    priority: Literal["HIGH", "MEDIUM", "LOW"]

    customer_problem: str

    likely_requirement: str

    relevant_service: str

    explicit_information: list[str]

    missing_information: list[str]

    recommended_action: str

    risk_flags: list[str]

    email_subject: str

    email_body: str


# --------------------------------------------------------------------------
# Lead loading + de-duplication
# --------------------------------------------------------------------------

def load_leads(csv_path: Path) -> list[dict]:
    """Load leads from CSV."""

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Lead source not found: {csv_path}"
        )

    with csv_path.open(
        newline="",
        encoding="utf-8"
    ) as f:
        return list(csv.DictReader(f))


def load_processed() -> set[str]:
    """Load IDs of leads that were already processed."""

    if PROCESSED_FILE.exists():
        return set(
            json.loads(
                PROCESSED_FILE.read_text(
                    encoding="utf-8"
                )
            )
        )

    return set()


def save_processed(processed: set[str]) -> None:
    """Save processed lead IDs."""

    PROCESSED_FILE.write_text(
        json.dumps(
            sorted(processed),
            indent=2
        ),
        encoding="utf-8"
    )


def append_review_log(entry: dict) -> None:
    """
    Store an audit trail containing:
    score, priority, risks, recommended action, etc.
    """

    log_data = []

    if REVIEW_LOG_FILE.exists():
        try:
            log_data = json.loads(
                REVIEW_LOG_FILE.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError:
            log.warning(
                "Review log was invalid JSON. Starting a new log."
            )
            log_data = []

    log_data.append(entry)

    REVIEW_LOG_FILE.write_text(
        json.dumps(
            log_data,
            indent=2
        ),
        encoding="utf-8"
    )


# --------------------------------------------------------------------------
# AI prompt
# --------------------------------------------------------------------------

ANALYSIS_PROMPT_TEMPLATE = """
You are a B2B sales qualification assistant.

Analyze the lead submission below.

Your job is to:
1. Understand the actual problem described by the lead.
2. Estimate how commercially relevant the lead is.
3. Identify what information is explicitly stated.
4. Identify what information is missing.
5. Recommend the next sales action.
6. Draft a professional, personalized follow-up email.

IMPORTANT SAFETY / ACCURACY RULES:

- Only use information the lead actually provided.
- Do NOT invent company facts.
- Do NOT invent budgets.
- Do NOT invent timelines.
- Do NOT invent business requirements.
- Do NOT claim that the company offers a service unless it is supported
  by the lead context.
- Clearly distinguish explicit facts from inferred requirements.
- Anything inferred should go into "likely_requirement".
- Do not put inferred information inside "explicit_information".
- If the lead is unclear, lower the score appropriately.
- If the lead asks not to be contacted, respect that.
- If the lead is spam-like, nonsensical, or extremely incomplete,
  give it a LOW priority and explain why in "risk_flags".
- Do not write an aggressive sales pitch.
- The email should be useful and concise.
- Never fabricate customer information.

LEAD INFORMATION

Name:
{name}

Company:
{company}

Employees:
{employees}

Email:
{email}

Message:
{message}

Return the required structured JSON object.
"""


# --------------------------------------------------------------------------
# Gemini AI analysis
# --------------------------------------------------------------------------

def create_gemini_client():
    """
    Create the current Google GenAI client.
    """

    if not GOOGLE_API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. "
            "Add it to your .env file."
        )

    return genai.Client(
        api_key=GOOGLE_API_KEY
    )


def call_gemini_for_analysis(
    client,
    lead: dict,
    max_retries: int = 2
) -> dict:
    """
    Send a lead to Gemini using the Interactions API.

    Gemini is forced to return JSON matching LeadAnalysis.schema.
    """

    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        name=lead.get("name", "Unknown"),
        company=lead.get("company", "Unknown"),
        employees=lead.get("employees", "Unknown"),
        email=lead.get("email", ""),
        message=lead.get("message", ""),
    )

    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):

        try:
            log.info(
                f"[{lead.get('lead_id')}] "
                f"Calling Gemini ({GEMINI_MODEL})..."
            )

            interaction = client.interactions.create(
                model=GEMINI_MODEL,
                input=prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": LeadAnalysis.model_json_schema(),
                },
            )

            # The Interactions API exposes the generated text here.
            raw_text = interaction.output_text.strip()

            if not raw_text:
                raise ValueError(
                    "Gemini returned an empty response."
                )

            log.info(
                f"[{lead.get('lead_id')}] "
                "Gemini response received."
            )

            # Parse JSON.
            parsed = json.loads(raw_text)

            if not isinstance(parsed, dict):
                raise ValueError(
                    "Gemini response was not a JSON object."
                )

            return parsed

        except json.JSONDecodeError as e:

            last_error = e

            log.warning(
                f"[{lead.get('lead_id')}] "
                f"Invalid JSON from Gemini "
                f"(attempt {attempt}): {e}"
            )

            # Invalid model output may be worth retrying.
            if attempt < max_retries:
                time.sleep(1)

        except Exception as e:

            last_error = e

            error_text = str(e)

            log.warning(
                f"[{lead.get('lead_id')}] "
                f"Gemini API call failed "
                f"(attempt {attempt}): {error_text}"
            )

            # Do NOT retry obvious configuration/model errors.
            non_retryable = (
                "404" in error_text
                or "not found" in error_text.lower()
                or "not available" in error_text.lower()
                or "invalid argument" in error_text.lower()
                or "authentication" in error_text.lower()
                or "api key" in error_text.lower()
                or "permission" in error_text.lower()
            )

            if non_retryable:
                log.error(
                    f"[{lead.get('lead_id')}] "
                    "Non-retryable Gemini error."
                )
                break

            if attempt < max_retries:
                time.sleep(2 ** attempt)

    raise RuntimeError(
        f"AI analysis failed after "
        f"{max_retries} attempts: {last_error}"
    )


# --------------------------------------------------------------------------
# AI output validation
# --------------------------------------------------------------------------

def validate_analysis(
    raw_json: dict,
    lead_id: str
) -> LeadAnalysis:

    try:
        analysis = LeadAnalysis(**raw_json)

        log.info(
            f"[{lead_id}] "
            f"Schema validation passed "
            f"(score={analysis.lead_score}, "
            f"priority={analysis.priority})"
        )

        return analysis

    except ValidationError as e:

        log.error(
            f"[{lead_id}] "
            f"AI output failed schema validation:\n{e}"
        )

        raise


# --------------------------------------------------------------------------
# Gmail draft creation
# --------------------------------------------------------------------------

def get_gmail_service():
    """
    Authenticate with Gmail using OAuth.
    """

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None

    # Existing token.
    if TOKEN_FILE.exists():

        creds = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            GMAIL_SCOPES
        )

    # Refresh or start OAuth flow.
    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:

            log.info("Refreshing Gmail OAuth token.")

            creds.refresh(Request())

        else:

            if not CREDENTIALS_FILE.exists():

                raise FileNotFoundError(
                    "credentials.json not found.\n"
                    "Download an OAuth Client ID (Desktop app) "
                    "from Google Cloud Console and save it as "
                    "credentials.json."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE),
                GMAIL_SCOPES
            )

            creds = flow.run_local_server(
                port=0
            )

        TOKEN_FILE.write_text(
            creds.to_json(),
            encoding="utf-8"
        )

    return build(
        "gmail",
        "v1",
        credentials=creds
    )


def create_gmail_draft(
    service,
    to_email: str,
    subject: str,
    body: str
) -> str:
    """
    Create a Gmail draft.
    """

    message = MIMEText(body)

    message["to"] = to_email
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    draft = service.users().drafts().create(
        userId="me",
        body={
            "message": {
                "raw": raw
            }
        }
    ).execute()

    return draft["id"]


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():

    # ----------------------------------------------------------------------
    # Check Gemini API key
    # ----------------------------------------------------------------------

    if not GOOGLE_API_KEY:

        log.error(
            "GOOGLE_API_KEY is not set."
        )

        log.error(
            "Create a .env file containing:"
        )

        log.error(
            "GOOGLE_API_KEY=your_api_key_here"
        )

        sys.exit(1)

    # ----------------------------------------------------------------------
    # Create Gemini client
    # ----------------------------------------------------------------------

    try:

        client = create_gemini_client()

        log.info(
            f"Gemini client initialized "
            f"using model: {GEMINI_MODEL}"
        )

    except Exception as e:

        log.error(
            f"Could not initialize Gemini client: {e}"
        )

        sys.exit(1)

    # ----------------------------------------------------------------------
    # Gmail
    # ----------------------------------------------------------------------

    gmail_service = None

    if not DRY_RUN:

        log.info(
            "DRY_RUN=false — Gmail drafts will be created."
        )

        try:

            gmail_service = get_gmail_service()

        except Exception as e:

            log.error(
                f"Gmail authentication failed: {e}"
            )

            sys.exit(1)

    else:

        log.info(
            "DRY_RUN=true — no Gmail drafts will be created, "
            "results will be printed only."
        )

    # ----------------------------------------------------------------------
    # Load leads
    # ----------------------------------------------------------------------

    try:

        leads = load_leads(
            LEADS_CSV
        )

    except Exception as e:

        log.error(
            f"Could not load leads: {e}"
        )

        sys.exit(1)

    processed = load_processed()

    log.info(
        f"Loaded {len(leads)} leads."
    )

    # ----------------------------------------------------------------------
    # Process leads
    # ----------------------------------------------------------------------

    for lead in leads:

        lead_id = lead.get(
            "lead_id",
            ""
        ).strip()

        email = lead.get(
            "email",
            ""
        ).strip()

        # Required fields.
        if not lead_id or not email:

            log.warning(
                f"Skipping row with missing "
                f"lead_id/email: {lead}"
            )

            continue

        # Duplicate protection.
        if lead_id in processed:

            log.info(
                f"[{lead_id}] "
                "Already processed — skipping."
            )

            continue

        log.info(
            f"[{lead_id}] "
            f"Analyzing lead: "
            f"{lead.get('name')} @ "
            f"{lead.get('company')}"
        )

        # ------------------------------------------------------------------
        # AI analysis
        # ------------------------------------------------------------------

        try:

            raw_json = call_gemini_for_analysis(
                client,
                lead
            )

            analysis = validate_analysis(
                raw_json,
                lead_id
            )

        except Exception as e:

            log.error(
                f"[{lead_id}] "
                f"Skipping lead due to unrecoverable error: {e}"
            )

            continue

        # ------------------------------------------------------------------
        # Audit log
        # ------------------------------------------------------------------

        append_review_log(
            {
                "lead_id": lead_id,
                "name": lead.get("name"),
                "company": lead.get("company"),
                "lead_score": analysis.lead_score,
                "priority": analysis.priority,
                "customer_problem": analysis.customer_problem,
                "likely_requirement": analysis.likely_requirement,
                "relevant_service": analysis.relevant_service,
                "explicit_information": analysis.explicit_information,
                "missing_information": analysis.missing_information,
                "risk_flags": analysis.risk_flags,
                "recommended_action": analysis.recommended_action,
                "email_subject": analysis.email_subject,
                "email_body": analysis.email_body,
            }
        )

        # ------------------------------------------------------------------
        # Dry run
        # ------------------------------------------------------------------

        if DRY_RUN:

            print()
            print("=" * 70)
            print(
                f"{lead_id} | "
                f"{analysis.priority} | "
                f"Score: {analysis.lead_score}"
            )
            print("=" * 70)

            print(
                f"Name: {lead.get('name')}"
            )

            print(
                f"Company: {lead.get('company')}"
            )

            print(
                f"Customer problem: "
                f"{analysis.customer_problem}"
            )

            print(
                f"Likely requirement: "
                f"{analysis.likely_requirement}"
            )

            print(
                f"Recommended action: "
                f"{analysis.recommended_action}"
            )

            print(
                f"Risk flags: "
                f"{analysis.risk_flags}"
            )

            print(
                f"Missing information: "
                f"{analysis.missing_information}"
            )

            print()
            print(
                f"Subject: "
                f"{analysis.email_subject}"
            )

            print()
            print(
                "EMAIL DRAFT:"
            )

            print(
                analysis.email_body
            )

            print("=" * 70)
            print()

        # ------------------------------------------------------------------
        # Real Gmail draft
        # ------------------------------------------------------------------

        else:

            try:

                draft_id = create_gmail_draft(
                    gmail_service,
                    email,
                    analysis.email_subject,
                    analysis.email_body
                )

                log.info(
                    f"[{lead_id}] "
                    f"Gmail draft created "
                    f"(id={draft_id}), "
                    f"priority={analysis.priority}, "
                    f"score={analysis.lead_score}"
                )

            except Exception as e:

                log.error(
                    f"[{lead_id}] "
                    f"Failed to create Gmail draft: {e}"
                )

                # Do not mark the lead as processed
                # if Gmail draft creation failed.
                continue

        # ------------------------------------------------------------------
        # Mark processed
        # ------------------------------------------------------------------

        processed.add(
            lead_id
        )

        save_processed(
            processed
        )

    log.info(
        "Run complete."
    )


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

if __name__ == "__main__":
    main()