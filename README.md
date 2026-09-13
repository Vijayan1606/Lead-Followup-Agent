# 🤖 Lead Follow-Up Agent

An AI-powered lead qualification and follow-up system built with **Python, Google Gemini, Gmail API, Pydantic, and Streamlit**.

The application reads website leads from a CSV file, uses Gemini to analyze and score each lead, generates a personalized follow-up email, and creates the email as a **Gmail draft** for human review.

The system does **not automatically send emails**. A salesperson always has the final decision.

---

## 🎯 Why This Project Exists

Sales teams can lose potential customers simply because new leads are not followed up quickly enough.

This project automates the repetitive first stage of the sales process:

1. Read a new lead.
2. Analyze the lead using Gemini.
3. Score the lead from 0–100.
4. Assign a priority.
5. Identify the customer's problem and likely requirement.
6. Generate a personalized follow-up email.
7. Create a Gmail draft.
8. Let a salesperson review and decide whether to send it.

The goal is to improve response speed while keeping a **human-in-the-loop**.

---

## ✨ Features

- 🤖 AI-powered lead qualification using Google Gemini
- 📊 Lead scoring from **0–100**
- 🔥 Priority classification: `HIGH`, `MEDIUM`, or `LOW`
- ✉️ Personalized follow-up email generation
- 🧠 Structured AI output using Pydantic
- 🛡️ Hallucination-aware prompting
- 🔁 Duplicate lead protection
- ♻️ Retry handling for temporary API/network failures
- 🧪 Safe dry-run mode
- 📧 Gmail draft creation
- 👤 Human review before sending
- 📝 Audit trail using `lead_reviews.json`
- 📋 Processing state using `processed_leads.json`
- 📜 Application logging using `run.log`
- 🖥️ Streamlit dashboard for viewing lead scores and AI analysis

---

# 🔄 System Workflow

```text
                         leads.csv
                            │
                            ▼
                    ┌───────────────┐
                    │   New Lead    │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Google Gemini │
                    │  AI Analysis  │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Structured    │
                    │ JSON Output   │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   Pydantic    │
                    │  Validation   │
                    └───────┬───────┘
                            │
                    ┌───────┴────────┐
                    │                │
                  Valid            Invalid
                    │                │
                    ▼                ▼
             Score & Priority     Log Error
                    │                │
                    ▼                ▼
              Generate Email     Skip Lead
                    │
                    ▼
              ┌──────────────┐
              │  DRY_RUN?   │
              └──────┬───────┘
                     │
             ┌───────┴────────┐
             │                │
           TRUE             FALSE
             │                │
             ▼                ▼
        Print Result      Gmail Draft
                              │
                              ▼
                        Human Review
                              │
                              ▼
                       Manual Send
```

---

# 🖥️ Streamlit Dashboard

The project includes a simple Streamlit frontend for viewing processed leads and their AI analysis.

The dashboard displays:

- Total number of leads
- High-priority leads
- Medium-priority leads
- Low-priority leads
- Lead scores
- Lead priority
- Customer information
- Original lead message
- Customer problem
- Likely requirement
- Relevant service
- Explicit information
- Missing information
- Risk flags
- Recommended action
- AI-generated email subject
- AI-generated email body

### Start the dashboard

```bash
streamlit run app.py
```

Then open:

```text
http://localhost:8501
```

The dashboard reads the existing lead and AI review data instead of generating new Gemini requests whenever the page is opened.

---

# 🧰 Tech Stack

| Technology | Purpose |
|---|---|
| Python | Main application |
| Google Gemini | AI lead analysis and email generation |
| Gmail API | Gmail draft creation |
| Google OAuth 2.0 | Gmail authentication |
| Pydantic | AI response validation |
| Streamlit | Web dashboard |
| Pandas | CSV data processing |
| python-dotenv | Environment configuration |
| JSON | Audit and processing state |

---

# ⚙️ Setup

## 1. Clone the Repository

```bash
git clone https://github.com/Vijayan1606/Lead-Followup-Agent.git
cd Lead-Followup-Agent
```

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

## 3. Configure Gemini

Create a `.env` file in the project directory:

```env
GOOGLE_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.6-flash
SALES_INBOX_EMAIL=your-email@gmail.com
DRY_RUN=true
```

Get a Gemini API key from Google AI Studio.

**Never commit your `.env` file or expose your API key publicly.**

---

# 📧 Gmail API Setup

Gmail integration is required only when:

```env
DRY_RUN=false
```

## 1. Create or Select a Google Cloud Project

Create or select a project in Google Cloud Console.

## 2. Enable Gmail API

Go to:

```text
Google Cloud Console
→ APIs & Services
→ Library
→ Gmail API
→ Enable
```

## 3. Create OAuth Client

Go to:

```text
Google Auth Platform
→ Clients
```

Create an OAuth client with:

```text
Application type: Desktop app
```

Download the OAuth client JSON and save it in the project directory as:

```text
credentials.json
```

If the OAuth application is in testing mode, add the Gmail account used for testing as a **test user**.

---

# 🔐 Gmail OAuth and Permissions

The application uses Google's installed application OAuth flow.

The application requests the Gmail:

```text
gmail.compose
```

scope because it needs to create Gmail drafts.

The application does **not automatically send emails**.

The workflow ends at:

```text
AI-generated email
        ↓
Gmail Draft
        ↓
Human Review
        ↓
Manual Send
```

After the first successful authorization, Google OAuth creates a local:

```text
token.json
```

The token is reused on future runs.

The following files must remain private:

```text
.env
credentials.json
token.json
```

---

# 🧠 AI Lead Qualification

Each lead is sent to Gemini with instructions to analyze the information provided by the lead.

The AI produces structured information including:

- Lead score
- Priority
- Customer problem
- Likely requirement
- Relevant service
- Explicit information
- Missing information
- Recommended action
- Risk flags
- Email subject
- Email body

The prompt instructs Gemini to use only information provided by the lead and avoid inventing customer details.

---

# ✅ AI Output Validation

Gemini is instructed to return structured JSON.

The response is parsed and validated using the Pydantic `LeadAnalysis` model.

Validation ensures:

```text
lead_score → integer between 0 and 100

priority → HIGH / MEDIUM / LOW

required fields → present

field values → correct data types
```

If the AI response cannot be parsed correctly, the application retries the request.

If the response still fails validation, the lead is logged and skipped.

This creates a safety boundary between the AI response and the email-drafting step.

---

# 🛡️ Hallucination Prevention

The AI prompt instructs Gemini to:

- Use only facts provided by the lead.
- Avoid inventing budgets.
- Avoid inventing timelines.
- Avoid inventing requirements.
- Separate explicit information from inference.
- Identify missing information.
- Avoid aggressive sales messaging when a lead asks not to be contacted.
- Treat spam or test-like submissions appropriately.

---

# 🔁 Duplicate Lead Protection

Every successfully processed lead ID is stored in:

```text
processed_leads.json
```

Before processing a lead, the application checks this file.

Example:

```text
[L001] Already processed — skipping.
```

This prevents the same lead from being analyzed and drafted repeatedly.

New leads can be added to `leads.csv` without reprocessing existing leads.

---

# ⚠️ Error Handling

| Failure | Behavior |
|---|---|
| Missing `GOOGLE_API_KEY` | Application exits with a clear error |
| Missing `lead_id` or `email` | Lead is skipped and warning is logged |
| Gemini API/network error | Request is retried |
| Invalid AI JSON | Response is retried and then skipped |
| Pydantic validation failure | Error is logged and lead is skipped |
| Missing `credentials.json` | Gmail setup error is shown |
| Gmail draft creation failure | Error is logged with lead ID |
| Already processed lead | Lead is skipped |

All important events are written to:

```text
run.log
```

and displayed in the terminal.

---

# 🧪 Dry-Run Mode

For development and testing:

```env
DRY_RUN=true
```

The pipeline runs through:

```text
CSV
 ↓
Gemini
 ↓
Validation
 ↓
Scoring
 ↓
Audit Log
 ↓
Print Result
```

No Gmail draft is created.

Run:

```bash
python main.py
```

This is the recommended mode for testing prompt behavior and AI validation.

---

# 📬 Live Gmail Mode

To create actual Gmail drafts:

```env
DRY_RUN=false
```

Then run:

```bash
python main.py
```

The application creates Gmail drafts only for newly processed leads.

It does not automatically send them.

For testing, use fictional/test lead data and a test Gmail account.

---

# 📊 Example Lead Results

The test dataset contains leads with different levels of intent.

Example results:

| Lead | Score | Priority |
|---|---:|---|
| L001 | 92 | HIGH |
| L002 | 85 | HIGH |
| L003 | 40 | LOW |
| L004 | 72 | MEDIUM |
| L005 | 60 | MEDIUM |
| L006 | 25 | LOW |
| L007 | 88 | HIGH |
| L008 | 0 | LOW |
| L009 | 82 | HIGH |
| L010 | 25 | LOW |

These results demonstrate that the system changes its scoring and response based on the actual lead information.

---

# 📧 Live Gmail Test

A separate fictional test lead was added to verify the complete live workflow.

The successful test demonstrated:

```text
New Lead
   ↓
Gemini Analysis
   ↓
Schema Validation
   ↓
Score = 55
Priority = MEDIUM
   ↓
Gmail Draft Created
```

The generated personalized email was verified in the Gmail **Drafts** folder.

The email was not automatically sent.

---

# 📝 Audit Files

### `processed_leads.json`

Stores lead IDs that have already been successfully processed.

### `lead_reviews.json`

Stores the AI qualification and review information for processed leads.

### `run.log`

Contains application events including:

- Lead processing
- Gemini requests
- Validation results
- Errors
- Retries
- Gmail draft creation
- Duplicate detection

---

# 📸 Suggested Demonstration Screenshots

For a project submission, the following screenshots demonstrate the system clearly.

### 1. Lead Dataset

Show:

```text
leads.csv
```

with different test leads.

### 2. Streamlit Dashboard

Show:

```text
Total Leads
High Priority
Medium Priority
Low Priority
```

and the lead table.

### 3. AI Analysis

Select a lead and show:

```text
Lead Score
Priority
Customer Problem
Likely Requirement
Missing Information
Recommended Action
Risk Flags
```

### 4. Generated Email

Show:

```text
AI-Generated Follow-Up

Subject
Email Body
```

### 5. Gmail Draft

Show the generated draft in Gmail.

### 6. Duplicate Protection

Show the terminal output:

```text
Already processed — skipping.
```

### 7. Audit Trail

Show:

```text
processed_leads.json
lead_reviews.json
run.log
```

---

# 🎬 Recommended Demo GIF

A short 15–20 second GIF can demonstrate the complete workflow:

```text
Run python main.py
        ↓
Lead analyzed
        ↓
Gemini response received
        ↓
Schema validation passed
        ↓
Gmail draft created
        ↓
Open Gmail Drafts
        ↓
Open personalized email
```

This demonstrates the complete AI-to-Gmail workflow while keeping the final send decision with the salesperson.

---

# 📁 Project Structure

```text
lead-followup-agent/
│
├── main.py                 # Main AI workflow
├── app.py                  # Streamlit dashboard
├── leads.csv               # Fictional test leads
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── README.md               # Project documentation
│
├── credentials.json        # Private Google OAuth credentials
├── token.json              # Private OAuth token
│
├── processed_leads.json    # Duplicate-processing state
├── lead_reviews.json       # AI analysis and audit data
└── run.log                 # Application logs
```

---

# 🔒 Security

Never commit sensitive credentials to GitHub.

The following files should be excluded from version control:

```gitignore
.env
credentials.json
token.json
__pycache__/
*.pyc
```

Never publish:

- Gemini API keys
- OAuth client secrets
- OAuth access tokens
- Refresh tokens
- Other private credentials

---

# 🧑‍💻 Technologies Used

- Python
- Google Gemini API
- Google Gmail API
- Google OAuth 2.0
- Pydantic
- Streamlit
- Pandas
- python-dotenv
- CSV
- JSON

---

# 🛡️ Safety and Design Principles

This project follows a human-in-the-loop design:

- AI analyzes leads and drafts emails.
- Structured validation happens before Gmail integration.
- Duplicate leads are detected before processing.
- Failed AI responses are not passed to Gmail.
- Gmail drafts are created instead of automatically sending emails.
- Customer information is not invented by the prompt.
- OAuth credentials and API keys remain local and private.
- Test data is fictional.

---

# 📄 License

This project is intended for educational, demonstration, and portfolio purposes.
