Lead Follow-Up Agent

An AI-powered Python workflow that reads new website leads, uses
Google's Gemini to qualify and score them, and creates a personalized
Gmail draft for human review.

The goal is simple: help sales teams respond to promising leads quickly
without removing the human from the final decision. The agent handles
lead analysis and email drafting; a salesperson reviews the draft and
decides whether to send it.

Why This Exists

Sales teams at 50--300 person businesses can lose opportunities because
leads do not receive a timely response.

This project closes that gap by automating the repetitive first step:

Read a new lead.

Analyze the lead with Gemini.

Assign a score and priority.

Identify the customer's problem and likely requirement.

Generate a personalized follow-up email.

Create the email as a Gmail draft.

Leave the final decision to a human.

The system is designed to assist salespeople, not replace them.

Features

AI lead qualification using Google Gemini

Lead scoring from 0--100

Priority classification: HIGH, MEDIUM, or LOW

Personalized follow-up email generation

Structured AI output validated with Pydantic

Hallucination-aware prompting that separates explicit facts from
inference

Duplicate protection using processed_leads.json

Retry handling for temporary Gemini/API failures

Safe dry-run mode for testing without Gmail

Gmail draft creation through the Gmail API

Audit trail through lead_reviews.json

Console and file logging through run.log

Human-in-the-loop workflow --- emails are drafted, not
automatically sent by this application

Project Workflow

                    leads.csv
                        |
                        v
                New Lead Detected
                        |
                        v
                Gemini AI Analysis
                        |
                        v
              Structured JSON Output
                        |
                        v
                Pydantic Validation
                        |
              +---------+---------+
              |                   |
          Valid Output        Invalid Output
              |                   |
              v                   v
       Score & Priority       Log Error
              |                   |
              v                   v
       Generate Email          Skip Lead
              |
              v
       +------+------+
       |             |
   DRY_RUN=true  DRY_RUN=false
       |             |
       v             v
   Print Draft    Gmail Draft
                     |
                     v
               Human Review
                     |
                     v
              Human Decides
                 to Send

Setup

1. Install Dependencies

pip install -r requirements.txt

2. Configure Gemini

Create a .env file from .env.example:

cp .env.example .env

On Windows PowerShell, you can also create/copy the file manually.

Add your Gemini API key:

GOOGLE_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.6-flash
SALES_INBOX_EMAIL=your-email@gmail.com
DRY_RUN=true

Get a Gemini API key from Google AI Studio.

Never commit your .env file or expose your API key publicly.

Gmail Setup

Gmail integration is only required when DRY_RUN=false.

1. Create or Select a Google Cloud Project

Open Google Cloud Console and create or select a project.

2. Enable the Gmail API

Go to:

Google Cloud Console → APIs & Services → Library → Gmail API →
Enable

3. Configure OAuth

Go to:

Google Auth Platform → Clients

Create an OAuth client with:

Application type: Desktop app

Client name: any name you choose

Download the OAuth client JSON file and save it in the project directory
as:

credentials.json

For a personal Gmail account, if the OAuth application is in testing
mode, add the Gmail account as a test user under the OAuth
application's audience/testing settings.

4. First Run

When running in live mode for the first time:

python main.py

the application opens a browser for Google OAuth authorization.

After authorization, Google returns an access/refresh token that the
application stores locally in:

token.json

Do not commit credentials.json or token.json to Git.

Gmail OAuth and Permissions

The application uses Google's installed-app OAuth flow.

The code requests the Gmail gmail.compose scope because the workflow
needs to create Gmail drafts.

The application itself does not call Gmail's send operation. Its
workflow stops after creating a draft, so a salesperson remains
responsible for reviewing and sending the email.

The OAuth credentials are stored locally:

credentials.json --- OAuth client credentials

token.json --- locally cached OAuth authorization token

Both files must remain private and should be excluded from version
control.

How AI Output Is Validated

Gemini is instructed to return structured JSON and is called with JSON
response mode.

The response is then parsed and validated using the Pydantic
LeadAnalysis model.

The validation enforces:

lead_score must be an integer between 0 and 100

priority must be exactly HIGH, MEDIUM, or LOW

Required fields must be present

Fields must contain the expected data types

If the AI response cannot be parsed as JSON, the application retries the
request once.

If parsing or schema validation still fails, the lead is logged and
skipped rather than being passed to Gmail.

This creates a safety boundary between the AI-generated output and the
email-drafting step.

Hallucination Prevention

The prompt instructs Gemini to:

Use only facts provided by the lead

Avoid inventing budgets, timelines, requirements, or other customer
information

Keep inferred information separate from explicit information

Record missing information when the lead has not provided it

Avoid aggressive sales messaging when the lead explicitly asks not
to be contacted or is only researching

Duplicate Lead Protection

Every successfully processed lead_id is recorded in:

processed_leads.json

Before processing a lead, the application checks this file.

If the lead has already been processed, it is skipped:

[L001] Already processed — skipping.

This prevents the same lead from being analyzed and drafted repeatedly
when the script is run again.

New rows can be added to leads.csv without reprocessing previously
completed leads.

Error Handling

Failure                             Behavior

Missing GOOGLE_API_KEY            Script exits with a clear error

Missing lead_id or email        Lead is skipped and a warning is
logged

Gemini API/network error            Request is retried with backoff

Invalid AI JSON                     Response is retried once, then
skipped

Pydantic validation failure         Error is logged and lead is skipped

Missing credentials.json in live  Clear Gmail setup error
mode

Gmail draft creation failure        Error is logged with the lead ID;
other leads can continue

Already processed lead              Lead is skipped

All important events are written to:

run.log

and also displayed in the console.

Dry-Run Mode

For safe development and testing, use:

DRY_RUN=true

In dry-run mode:

Leads are loaded from the CSV

Gemini analyzes the leads

AI output is validated

Duplicate protection is applied

Results are printed/logged

No Gmail draft is created

This is the recommended mode while developing or testing prompts.

Live Gmail Mode

To create actual Gmail drafts:

DRY_RUN=false

Then run:

python main.py

The workflow will create Gmail drafts for newly processed leads.

The application does not automatically send those drafts.

For testing, use a personal/test Gmail account rather than a production
sales inbox.

Test Dataset

The included leads.csv contains fictional lead data designed to test
different situations:

High-intent leads

Medium-intent leads

Low-intent leads

Incomplete submissions

Spam/test-like submissions

Leads with specific business problems

Leads that are researching but not ready to buy

Leads that explicitly request no sales calls

This helps verify that the AI changes its scoring and response based on
the lead's actual message instead of generating the same response for
everyone.

Example Live Test

A live Gmail test was performed using a separate fictional test lead.

The successful run demonstrated:

Loaded 11 leads.
[L011] Analyzing lead: Test Lead @ Demo Company
[L011] Calling Gemini (gemini-3.6-flash)...
[L011] Gemini response received.
[L011] Schema validation passed (score=40, priority=LOW)
[L011] Gmail draft created
Run complete.

The resulting personalized email was verified in the Gmail Drafts
folder.

The email was not automatically sent.

Audit Files

processed_leads.json

Stores lead IDs that have already been successfully processed.

lead_reviews.json

Stores the AI analysis and review information for processed leads.

This provides an audit trail that can be reviewed by a salesperson.

run.log

Contains application events, processing status, errors, retries, and
Gmail draft creation results.

What to Demonstrate

For a project submission or demo, the following screenshots are useful:

leads.csv
Show the fictional leads with different intent levels.

Dry-run terminal output
Show Gemini analyzing leads and producing different
scores/priorities.

Validation failure
Demonstrate that malformed AI output is caught and skipped.

Duplicate protection
Run the application again and show:

Already processed — skipping.

Audit files
Show run.log and lead_reviews.json.

Gmail Drafts
Show a newly created draft in Gmail.

Opened Gmail draft
Show the personalized subject and email body.

Recommended Demo GIF

A short 15--20 second demo can show the complete workflow:

Run python main.py
        ↓
Lead analyzed
        ↓
Schema validation passed
        ↓
Gmail draft created
        ↓
Open Gmail Drafts
        ↓
Open personalized email

This demonstrates the complete AI-to-Gmail workflow while making it
clear that the final send decision remains with the salesperson.

Project Structure

lead-followup-agent/
│
├── main.py                  # Main workflow
├── leads.csv                # Fictional test leads
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
├── README.md                # Project documentation
│
├── credentials.json         # Private Google OAuth credentials
├── token.json               # Private OAuth token
│
├── processed_leads.json     # Duplicate-processing state
├── lead_reviews.json        # AI review/audit data
└── run.log                  # Application log

Files That Must NOT Be Committed

Add these to .gitignore:

.env
credentials.json
token.json
__pycache__/
*.pyc

Never upload API keys, OAuth client secrets, or personal access tokens
to GitHub.

Technologies Used

Python

Google Gemini API

Google Gmail API

Pydantic

Google OAuth 2.0

CSV

JSON

python-dotenv

Safety and Design Principles

This project follows a human-in-the-loop approach:

AI analyzes and drafts.

Structured validation happens before Gmail integration.

Duplicate leads are detected before processing.

Failed AI responses are not sent to Gmail.

Gmail drafts are created instead of automatically sending emails.

Customer information is not invented by the prompt.

OAuth credentials and API keys remain local and private.

License

This project is intended for educational, demonstration, and portfolio
purposes.