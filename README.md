# Gmail Actions - Rule-Based Email Processing

A standalone Python script that integrates with Gmail API to fetch emails, store them in a database, and process them based on configurable rules.

## Features

- **Gmail API Integration**: Authenticates using OAuth2 and fetches emails from your inbox
- **Database Storage**: Stores emails in SQLite3 database for efficient querying
- **Rule-Based Processing**: Process emails based on flexible rules defined in JSON
- **Multiple Actions**: Mark as read/unread, move messages to different labels
- **Flexible Conditions**: Support for various field types (From, To, Subject, Message, Date) with multiple predicates

## Requirements

- Python 3.9 or higher
- Google Cloud Project with Gmail API enabled
- OAuth2 credentials file (`client_secret.json`) from Google Cloud Console

## Installation

1. **Clone or download this repository**

2. **Install Poetry** (if not already installed):

   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

   Or using pip:

   ```bash
   pip install poetry
   ```

3. **Install dependencies using Poetry**:

   ```bash
   poetry install
   ```

   Alternatively, if you prefer using pip:

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Google Cloud Project and OAuth2 credentials**:

   To create `client_secret.json` from Google Cloud Console:

   a. **Go to Google Cloud Console**:
      - Visit [Google Cloud Console](https://console.cloud.google.com/)
      - Sign in with your Google account

   b. **Create or Select a Project**:
      - Click on the project dropdown at the top
      - Click "New Project" to create a new project, or select an existing one
      - Give your project a name (e.g., "Gmail Actions")
      - Click "Create"

   c. **Enable Gmail API**:
      - In the left sidebar, go to "APIs & Services" > "Library"
      - Search for "Gmail API" in the search bar
      - Click on "Gmail API" from the results
      - Click the "Enable" button

   d. **Create OAuth 2.0 Credentials**:
      - Go to "APIs & Services" > "Credentials"
      - Click "Create Credentials" at the top
      - Select "OAuth client ID"
      - If prompted, configure the OAuth consent screen first:
        - Choose "External" (unless you have a Google Workspace account)
        - Fill in the required app information (App name, User support email, Developer contact email)
        - Click "Save and Continue" through the scopes and test users steps
      - Back in Credentials, select "Desktop app" as the application type
      - Give it a name (e.g., "Gmail Actions Client")
      - Click "Create"
      - You'll see a dialog with your **Client ID** and **Client Secret**

   e. **Download the Credentials File**:
      - Click "Download JSON" button in the credentials dialog
      - Save the downloaded file as `client_secret.json` in the project root directory
      - Alternatively, you can manually create `client_secret.json` with this structure:

        ```json
        {
          "installed": {
            "client_id": "your-client-id.apps.googleusercontent.com",
            "client_secret": "your-client-secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["http://localhost"]
          }
        }
        ```

   **Note**: The `client_secret.json` file is gitignored for security. Never commit real credentials to version control.

## Usage

### Step 1: Fetch Emails

First, fetch emails from your Gmail inbox and store them in the database:

**Using Poetry:**

```bash
poetry run python fetch_emails.py
```

**Or using Python directly:**

```bash
python fetch_emails.py
```

This will:

- Authenticate with Gmail API (opens browser for first-time authentication)
- Fetch emails from your inbox
- Store them in `gmail_actions.db` SQLite database

**Note**: On first run, you'll be prompted to authorize the application. The authentication token will be saved in `token.json` for future use.

### Step 2: Define Rules

Create or edit `rules.json` to define your email processing rules. The file should follow this structure:

```json
{
  "rules": [
    {
      "name": "Rule Name",
      "predicate": "All",
      "conditions": [
        {
          "field": "Subject",
          "predicate": "Contains",
          "value": "newsletter"
        },
        {
          "field": "Received Date",
          "predicate": "Greater than",
          "value": "30 days"
        }
      ],
      "actions": [
        {
          "action": "Mark as Read"
        },
        {
          "action": "Move Message",
          "destination": "IMPORTANT"
        }
      ]
    }
  ]
}
```

#### Rule Structure

- **name**: A descriptive name for the rule
- **predicate**: Either `"All"` (all conditions must match) or `"Any"` (at least one condition must match)
- **conditions**: Array of condition objects
- **actions**: Array of action objects to execute when conditions match

#### Supported Fields

- `From`: Sender email address
- `To`: Recipient email address
- `Subject`: Email subject line
- `Message`: Email body content
- `Received Date` / `Received Date/Time` / `Date Received`: Email received timestamp

#### Supported Predicates

**For string fields** (From, To, Subject, Message):

- `Contains`: Field contains the value
- `Does not Contain`: Field does not contain the value
- `Equals`: Field exactly equals the value
- `Does not Equal`: Field does not equal the value

**For date field** (Received Date):

- `Less than`: Date is less than the specified value
- `Greater than`: Date is greater than the specified value

**Date values** can be specified as:

- `"30 days"` - 30 days ago
- `"3 months"` - 3 months ago
- Or any valid date string

#### Supported Actions

- `Mark as Read`: Marks the email as read
- `Mark as Unread`: Marks the email as unread
- `Move Message`: Moves the email to a different label/folder
  - Requires `destination` field specifying the label name (e.g., "IMPORTANT", "TRASH", "SPAM")

### Step 3: Process Emails

Run the rule processor to apply your rules:

**Using Poetry:**

```bash
poetry run python rule_processor.py
```

**Or using Python directly:**

```bash
python rule_processor.py
```

Or specify a custom rules file:

```bash
poetry run python rule_processor.py custom_rules.json
# or
python rule_processor.py custom_rules.json
```

This will:

- Load rules from the JSON file
- Fetch emails from the database
- Evaluate each email against each rule
- Execute actions for matching emails

## Example Rules

See `rules.json` for example rules including:

- Moving old newsletters to archive
- Marking urgent emails as read
- Filtering spam-like emails

## Database Schema

The application uses SQLite3 with the following schema:

```sql
CREATE TABLE emails (
    id TEXT PRIMARY KEY,
    thread_id TEXT,
    from_address TEXT,
    to_address TEXT,
    subject TEXT,
    message_body TEXT,
    received_date TIMESTAMP,
    is_read INTEGER DEFAULT 0,
    labels TEXT,
    raw_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## Configuration

Edit `config.py` to customize:

- `DATABASE_PATH`: Path to SQLite database file (default: `gmail_actions.db`)
- `MAX_EMAILS_TO_FETCH`: Maximum number of emails to fetch (default: 100, set to `None` for all)
- `CREDENTIALS_FILE`: Path to OAuth2 credentials file (default: `client_secret.json`)
- `TOKEN_FILE`: Path to store authentication token (default: `token.json`)

## Testing

Run the test suite:

**Using Poetry:**

```bash
poetry run pytest tests/
```

**Or using pytest directly:**

```bash
pytest tests/
```

Or run with verbose output:

```bash
poetry run pytest tests/ -v
# or
pytest tests/ -v
```

## File Structure

```
gmail-actions/
├── config.py              # Configuration settings
├── database.py            # Database operations
├── gmail_auth.py          # Gmail API authentication
├── fetch_emails.py        # Script to fetch and store emails
├── rule_processor.py      # Script to process emails based on rules
├── rules.json             # Example rules file
├── pyproject.toml         # Poetry configuration and dependencies
├── requirements.txt       # Python dependencies (alternative to Poetry)
├── README.md             # This file
├── tests/                # Test files
│   ├── test_database.py
│   ├── test_rule_processor.py
│   └── test_integration.py
└── client_secret.json   # OAuth2 credentials (not in repo)
```

## Troubleshooting

### Authentication Issues

- Ensure `client_secret.json` is in the project root
- Delete `token.json` and re-authenticate if you get permission errors
- Make sure Gmail API is enabled in your Google Cloud Project

### Database Issues

- The database file is created automatically on first run
- To start fresh, delete `gmail_actions.db` and run `fetch_emails.py` again

### Rule Processing Issues

- Check that `rules.json` is valid JSON
- Verify field names match exactly (case-sensitive)
- Ensure date values are in the correct format

## Security Notes

- Never commit `client_secret.json` or `token.json` to version control
- These files are already in `.gitignore`
- Keep your OAuth2 credentials secure

## License

This project is provided as-is for the assignment purpose.
