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

# 2. Comprehensive Data Science, Engineering & AI Roles
search_queries = [
    {
        "term": "Data Analyst",
        "google_term": "Data Analyst jobs in India since yesterday"
    },
    {
        "term": "Data Engineer",
        "google_term": "Data Engineer jobs in India since yesterday"
    },
    {
        "term": "Data Scientist",
        "google_term": "Data Scientist jobs in India since yesterday"
    },
    {
        "term": "Prompt Engineer",
        "google_term": "Prompt Engineer Generative AI jobs in India since yesterday"
    },
    {
        "term": "Data Science Engineer",
        "google_term": "Data Science Engineer Machine Learning jobs in India since yesterday"
    },
    {
        "term": "Generative AI RAG LangChain",
        "google_term": "Generative AI RAG LangChain developer jobs in India since yesterday"
    },
    {
        "term": "Computer Vision OCR Engineer",
        "google_term": "Computer Vision OCR Python Engineer jobs in India since yesterday"
    }
]

all_jobs = []

# 3. Scrape from LinkedIn, Indeed, Glassdoor, Naukri, and Google Jobs
for q in search_queries:
    try:
        jobs = scrape_jobs(
            site_name=["linkedin", "indeed", "glassdoor", "naukri", "google"],
            search_term=q["term"],
            google_search_term=q["google_term"],
            location="India",
            results_wanted=25,
            hours_old=12,
            country_indeed="India"
        )
        if isinstance(jobs, pd.DataFrame) and not jobs.empty:
            all_jobs.append(jobs)
    except Exception as e:
        print(f"Error scraping '{q['term']}': {e}")

if not all_jobs:
    print("No jobs found in this run.")
    exit(0)

# Merge and deduplicate identical postings
combined_df = pd.concat(all_jobs, ignore_index=True)
combined_df.drop_duplicates(subset=["job_url"], inplace=True)

# 4. Filter out previously mailed jobs
new_jobs = []
for _, row in combined_df.iterrows():
    url = str(row.get("job_url", "")).strip()
    if url and url not in seen_jobs and url != "nan":
        new_jobs.append(row)
        seen_jobs.add(url)

if not new_jobs:
    print("No new unique jobs found since the last run.")
    exit(0)

new_jobs_df = pd.DataFrame(new_jobs).head(100)

# 5. Build Formatted HTML Table
table_rows = ""
for _, row in new_jobs_df.iterrows():
    title = str(row.get("title", "N/A"))
    company = str(row.get("company", "N/A"))
    location = str(row.get("location", "India"))
    url = str(row.get("job_url", "#"))
    site = str(row.get("site", "Direct / Portal")).replace("_", " ").title()

    table_rows += f"""
    <tr>
        <td style='padding: 8px; border: 1px solid #ddd; font-weight: bold;'>{site}</td>
        <td style='padding: 8px; border: 1px solid #ddd;'>{company}</td>
        <td style='padding: 8px; border: 1px solid #ddd;'>{title}</td>
        <td style='padding: 8px; border: 1px solid #ddd;'>{location}</td>
        <td style='padding: 8px; border: 1px solid #ddd;'><a href='{url}' target='_blank'>Apply</a></td>
    </tr>
    """

html = f"""
<html>
<body style='font-family: Arial, sans-serif;'>
    <h2>Data Science & AI Job Digest ({len(new_jobs_df)} Fresh Openings)</h2>
    <p>Target Roles: <b>Data Analyst, Data Engineer, Prompt Engineer, Data Scientist, Data Science Engineer & GenAI/OCR</b></p>
    <table style='border-collapse: collapse; width: 100%;'>
        <tr style='background-color: #f2f2f2;'>
            <th style='padding: 8px; border: 1px solid #ddd; text-align: left;'>Platform</th>
            <th style='padding: 8px; border: 1px solid #ddd; text-align: left;'>Company</th>
            <th style='padding: 8px; border: 1px solid #ddd; text-align: left;'>Role</th>
            <th style='padding: 8px; border: 1px solid #ddd; text-align: left;'>Location</th>
            <th style='padding: 8px; border: 1px solid #ddd; text-align: left;'>Action</th>
        </tr>
        {table_rows}
    </table>
</body>
</html>
"""

# 6. Send Email Digest
sender = os.getenv("SENDER_EMAIL")
receiver = os.getenv("RECEIVER_EMAIL")
password = os.getenv("SENDER_APP_PASSWORD").replace(" ", "")

msg = MIMEMultipart("alternative")
msg["Subject"] = f"Data Science & AI Job Alert: {len(new_jobs_df)} New Openings"
msg["From"] = sender
msg["To"] = receiver
msg.attach(MIMEText(html, "html"))

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(sender, password)
    server.sendmail(sender, receiver, msg.as_string())

# 7. Update History
trimmed_history = list(seen_jobs)[-3000:]
with open(SEEN_JOBS_FILE, "w") as f:
    json.dump(trimmed_history, f)
