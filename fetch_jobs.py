import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
from jobspy import scrape_jobs

SEEN_JOBS_FILE = "seen_jobs.json"

# 1. Load previously sent job IDs/URLs
if os.path.exists(SEEN_JOBS_FILE):
    with open(SEEN_JOBS_FILE, "r") as f:
        try:
            seen_jobs = set(json.load(f))
        except Exception:
            seen_jobs = set()
else:
    seen_jobs = set()

# 2. Scrape latest listings (last 12 hours)
queries = [
    "Generative AI Engineer",
    "RAG LangChain Python",
    "Computer Vision OCR"
]
all_jobs = []

for query in queries:
    try:
        jobs = scrape_jobs(
            site_name=["linkedin", "indeed", "glassdoor"],
            search_term=query,
            location="India",
            results_wanted=40,
            hours_old=12,
            country_indeed="India"
        )
        if isinstance(jobs, pd.DataFrame) and not jobs.empty:
            all_jobs.append(jobs)
    except Exception as e:
        print(f"Error scraping {query}: {e}")

if not all_jobs:
    print("No jobs fetched.")
    exit(0)

combined_df = pd.concat(all_jobs, ignore_index=True)
combined_df.drop_duplicates(subset=["job_url"], inplace=True)

# 3. Filter out jobs that were already mailed in prior runs
new_jobs = []
for _, row in combined_df.iterrows():
    url = str(row.get("job_url", "")).strip()
    if url and url not in seen_jobs:
        new_jobs.append(row)
        seen_jobs.add(url)

if not new_jobs:
    print("No new unique jobs found since the last run.")
    exit(0)

new_jobs_df = pd.DataFrame(new_jobs).head(100)

# 4. Construct HTML Digest
table_rows = ""
for _, row in new_jobs_df.iterrows():
    title = row.get("title", "N/A")
    company = row.get("company", "N/A")
    location = row.get("location", "India")
    url = row.get("job_url", "#")
    site = row.get("site", "Web")
    table_rows += f"""
    <tr>
        <td style='padding: 8px; border: 1px solid #ddd;'>{site.capitalize()}</td>
        <td style='padding: 8px; border: 1px solid #ddd;'><b>{company}</b></td>
        <td style='padding: 8px; border: 1px solid #ddd;'>{title}</td>
        <td style='padding: 8px; border: 1px solid #ddd;'>{location}</td>
        <td style='padding: 8px; border: 1px solid #ddd;'><a href='{url}' target='_blank'>Apply</a></td>
    </tr>
    """

html = f"""
<html>
<body>
    <h2>Top New Job Matches ({len(new_jobs_df)} Fresh Openings)</h2>
    <table style='border-collapse: collapse; width: 100%; font-family: Arial, sans-serif;'>
        <tr style='background-color: #f2f2f2;'>
            <th style='padding: 8px; border: 1px solid #ddd;'>Source</th>
            <th style='padding: 8px; border: 1px solid #ddd;'>Company</th>
            <th style='padding: 8px; border: 1px solid #ddd;'>Role</th>
            <th style='padding: 8px; border: 1px solid #ddd;'>Location</th>
            <th style='padding: 8px; border: 1px solid #ddd;'>Link</th>
        </tr>
        {table_rows}
    </table>
</body>
</html>
"""

# 5. Send Email
sender = os.getenv("SENDER_EMAIL")
receiver = os.getenv("RECEIVER_EMAIL")
password = os.getenv("SENDER_APP_PASSWORD").replace(" ", "")  # Strips any accidental whitespace

msg = MIMEMultipart("alternative")
msg["Subject"] = f"Job Digest: {len(new_jobs_df)} New Matches Found"
msg["From"] = sender
msg["To"] = receiver
msg.attach(MIMEText(html, "html"))

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(sender, password)
    server.sendmail(sender, receiver, msg.as_string())

# 6. Save updated seen jobs history (keep only the last 2,000 IDs)
trimmed_history = list(seen_jobs)[-2000:]
with open(SEEN_JOBS_FILE, "w") as f:
    json.dump(trimmed_history, f)
