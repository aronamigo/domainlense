
import streamlit as st
import pandas as pd
import time
import re
from urllib.parse import urlparse
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

# Try importing optional dependencies
try:
    import requests
    from bs4 import BeautifulSoup
    SCRAPING_AVAILABLE = True
except ImportError:
    SCRAPING_AVAILABLE = False
    st.warning("Web scraping features require 'requests' and 'beautifulsoup4'. Install them to enable full functionality.")

import warnings
warnings.filterwarnings('ignore')

# Page config
st.set_page_config(
    page_title="Domain Lens | Bulk Domain Analysis",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS matching the HTML design
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}

    .main {
        background: #F7F9FB;
        padding: 0;
    }

    .block-container {
        max-width: 1200px;
        padding: 2rem 2.5rem;
    }

    .top-app-bar {
        position: sticky;
        top: 0;
        z-index: 50;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1rem 2rem;
        background: white;
        border-bottom: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin: -2rem -2.5rem 2rem -2.5rem;
    }

    .logo {
        font-size: 1.25rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #2563EB;
    }

    .hero-section {
        text-align: center;
        margin-bottom: 3rem;
    }

    .hero-title {
        font-size: 2.25rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #191C1E;
        margin-bottom: 1rem;
        line-height: 1.2;
    }

    .hero-subtitle {
        font-size: 1rem;
        color: #434655;
        max-width: 42rem;
        margin: 0 auto;
        line-height: 1.5;
    }

    .main-card {
        background: white;
        border-radius: 0.75rem;
        border: 1px solid rgba(195, 198, 215, 0.3);
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.05);
        padding: 1.5rem;
        margin-bottom: 2rem;
    }

    .label-caps {
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #434655;
        margin-bottom: 1rem;
    }

    .stTextArea textarea {
        font-family: 'Consolas', 'Monaco', monospace !important;
        font-size: 0.875rem !important;
        line-height: 1.4 !important;
        border: 1px solid #C3C6D7 !important;
        background: #ECEEF0 !important;
        border-radius: 0.5rem !important;
        padding: 1rem !important;
        resize: none !important;
        transition: all 0.2s !important;
        min-height: 16rem !important;
    }

    .stTextArea textarea:focus {
        border-color: #004AC6 !important;
        box-shadow: 0 0 0 1px #004AC6 !important;
        outline: none !important;
    }

    .domain-counter {
        text-align: right;
        background: rgba(255, 255, 255, 0.9);
        padding: 0.25rem 0.75rem;
        border-radius: 0.375rem;
        border: 1px solid #C3C6D7;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #434655;
        margin-top: -0.5rem;
    }

    .helper-text {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.875rem;
        color: #434655;
        margin-bottom: 2rem;
    }

    .stTextInput input {
        border: 1px solid #C3C6D7 !important;
        background: white !important;
        border-radius: 0.5rem !important;
        padding: 0.75rem 1rem !important;
        font-size: 1rem !important;
        transition: all 0.2s !important;
    }

    .stTextInput input:focus {
        border-color: #004AC6 !important;
        box-shadow: 0 0 0 1px #004AC6 !important;
        outline: none !important;
    }

    .stTextInput label {
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
        color: #434655 !important;
        margin-bottom: 0.5rem !important;
    }

    .stButton > button {
        background: #004AC6 !important;
        color: white !important;
        padding: 1rem 1.5rem !important;
        border-radius: 0.5rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        border: none !important;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.2s !important;
    }

    .stButton > button:hover {
        background: rgba(0, 74, 198, 0.9) !important;
        transform: scale(0.98) !important;
    }

    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 1.5rem;
        margin-top: 2rem;
    }

    .feature-card {
        background: #ECEEF0;
        padding: 1.5rem;
        border-radius: 0.75rem;
        border: 1px solid rgba(195, 198, 215, 0.2);
        text-align: center;
    }

    .feature-icon {
        width: 3rem;
        height: 3rem;
        border-radius: 9999px;
        background: rgba(0, 74, 198, 0.1);
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 1rem auto;
        font-size: 1.5rem;
    }

    .feature-title {
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: #191C1E;
    }

    .feature-desc {
        font-size: 0.875rem;
        color: #434655;
        line-height: 1.5;
    }

    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #191C1E !important;
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
        color: #434655 !important;
    }

    .dataframe {
        border: 1px solid #C3C6D7 !important;
        border-radius: 0.75rem !important;
        overflow: hidden !important;
    }

    .dataframe thead tr th {
        background: #ECEEF0 !important;
        color: #191C1E !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        padding: 1rem !important;
        border-bottom: 2px solid #C3C6D7 !important;
    }

    .dataframe tbody tr td {
        padding: 1rem !important;
        border-bottom: 1px solid #E0E3E5 !important;
        font-size: 0.875rem !important;
        color: #191C1E !important;
    }

    .dataframe tbody tr:hover {
        background: #F7F9FB !important;
    }

    .stProgress > div > div {
        background: #004AC6 !important;
    }

    .stAlert {
        background: rgba(0, 74, 198, 0.1) !important;
        border: 1px solid rgba(0, 74, 198, 0.2) !important;
        border-radius: 0.5rem !important;
        color: #004AC6 !important;
    }

    .stDownloadButton > button {
        background: white !important;
        color: #004AC6 !important;
        border: 2px solid #004AC6 !important;
        padding: 1rem 1.5rem !important;
        border-radius: 0.5rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }

    .stDownloadButton > button:hover {
        background: rgba(0, 74, 198, 0.05) !important;
    }

    .streamlit-expanderHeader {
        background: #ECEEF0 !important;
        border: 1px solid #C3C6D7 !important;
        border-radius: 0.5rem !important;
        font-weight: 600 !important;
        padding: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'show_email_modal' not in st.session_state:
    st.session_state.show_email_modal = False
if 'active_email_data' not in st.session_state:
    st.session_state.active_email_data = None
if 'domain_input' not in st.session_state:
    st.session_state.domain_input = ""
if 'selected_categories' not in st.session_state:
    st.session_state.selected_categories = []
if 'selected_departments' not in st.session_state:
    st.session_state.selected_departments = []

# Sample data
SAMPLES = {
    "SaaS Competitors": "stripe.com\nvercel.com\nlinear.app\nnotion.so\nfigma.com",
    "Local Businesses": "starbucks.com\ntarget.com\nwalgreens.com\ncvs.com\nwalmart.com",
    "Universities": "harvard.edu\nstanford.edu\nmit.edu\nyale.edu\nprinceton.edu"
}

# Helper functions
def extract_domain_from_url(url_or_domain):
    """Extract clean domain from URL or domain string"""
    url_or_domain = str(url_or_domain).strip()
    url_or_domain = re.sub(r'^(https?://)?(www\.)?', '', url_or_domain, flags=re.IGNORECASE)
    url_or_domain = url_or_domain.split('/')[0].split('?')[0].split('#')[0].split(':')[0]
    return url_or_domain.lower()

def parse_input_domains(raw_input):
    """Parse and clean list of URLs/domains"""
    if not raw_input:
        return []
    # Split by comma, semicolon, space, or newline
    entries = re.split(r'[,;\s\n]+', str(raw_input))
    domains = []
    for entry in entries:
        entry = entry.strip()
        if entry and len(entry) > 3:
            domain = extract_domain_from_url(entry)
            if domain and '.' in domain:
                domains.append(domain)
    # Remove duplicates
    seen = set()
    unique_domains = []
    for domain in domains:
        if domain not in seen:
            seen.add(domain)
            unique_domains.append(domain)
    return unique_domains

def fetch_domain_content(domain, timeout=10):
    """Fetch HTML content from domain"""
    if not SCRAPING_AVAILABLE:
        return "", "", 0

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    urls_to_try = [f"https://{domain}", f"http://{domain}"]

    for url in urls_to_try:
        try:
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            if response.status_code == 200:
                return response.text, url, response.status_code
        except Exception:
            continue
    return "", "", 0

def extract_emails_from_html(html_content, domain):
    """Extract emails from HTML"""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, str(html_content))
    domain_clean = domain.replace('www.', '')
    valid_emails = []

    for email in emails:
        email_lower = email.lower()
        if any(skip in email_lower for skip in ['example.com', 'yourdomain.com', '.png', '.jpg']):
            continue
        if domain_clean in email_lower:
            valid_emails.append(email_lower)
    return list(set(valid_emails))

def scrape_contact_pages(domain, base_html):
    """Scrape contact pages for emails"""
    if not SCRAPING_AVAILABLE:
        return []

    all_emails = extract_emails_from_html(base_html, domain)
    contact_paths = ['/contact', '/contact-us', '/about']
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    for path in contact_paths:
        try:
            resp = requests.get(f"https://{domain}{path}", headers=headers, timeout=5)
            if resp.status_code == 200:
                all_emails.extend(extract_emails_from_html(resp.text, domain))
        except Exception:
            continue
    return list(set(all_emails))[:10]

def calculate_saas_score(domain, html_content=""):
    """Calculate SaaS score"""
    score = 0
    domain_lower = str(domain).lower()
    html_lower = str(html_content).lower()

    if any(sub in domain_lower for sub in ['app.', 'dashboard.', 'portal.']):
        score += 25
    if any(path in html_lower for path in ['/pricing', '/plans']):
        score += 10
    if any(path in html_lower for path in ['/docs', '/api']):
        score += 5
    if any(stack in html_lower for stack in ['stripe', 'paddle']):
        score += 10
    if any(kw in html_lower for kw in ['free trial', 'demo']):
        score += 15
    if domain_lower.endswith('.edu'):
        score -= 50

    return max(0, min(100, score))

def classify_domain(domain, html_content=""):
    """Classify domain"""
    domain_lower = str(domain).lower()

    if domain_lower.endswith('.edu'):
        return 'Education', 100
    if domain_lower.endswith(('.gov', '.mil')):
        return 'Government', 100
    if domain_lower.endswith('.org'):
        return 'Organization', 60

    saas_score = calculate_saas_score(domain, html_content)
    if saas_score >= 75:
        return 'SaaS (Confirmed)', saas_score
    elif saas_score >= 50:
        return 'SaaS (Probable)', saas_score

    return 'General', 20

def classify_email_department(email):
    """Classify email by department"""
    email_lower = str(email).lower().split('@')[0]

    if any(kw in email_lower for kw in ['sales', 'demo']):
        return 'Sales'
    if any(kw in email_lower for kw in ['support', 'help']):
        return 'Support'
    if any(kw in email_lower for kw in ['marketing', 'pr']):
        return 'Marketing'
    if any(kw in email_lower for kw in ['info', 'hello', 'contact']):
        return 'General/Info'
    return 'Other'

def process_single_domain(domain):
    """Process single domain"""
    try:
        html_content, final_url, status_code = fetch_domain_content(domain)
        if status_code == 0:
            return {
                'domain': domain,
                'status': 'Failed',
                'category': 'Error',
                'score': 0,
                'emails': []
            }

        category, score = classify_domain(domain, html_content)
        emails = scrape_contact_pages(domain, html_content)

        return {
            'domain': domain,
            'status': 'Success',
            'category': category,
            'score': score,
            'emails': emails
        }
    except Exception:
        return {
            'domain': domain,
            'status': 'Error',
            'category': 'Error',
            'score': 0,
            'emails': []
        }

# UI Components
st.markdown("""
<div class="top-app-bar">
    <div class="logo">Domain Lens</div>
    <div style="display: flex; gap: 2rem; align-items: center;">
        <a href="#" style="color: #64748B; text-decoration: none; font-weight: 600;">History</a>
        <div style="display: flex; gap: 1rem;">
            <span style="color: #64748B; cursor: pointer;">⚙️</span>
            <span style="color: #64748B; cursor: pointer;">👤</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-section">
    <h1 class="hero-title">Bulk Domain Analysis</h1>
    <p class="hero-subtitle">
        Paste thousands of URLs. Instantly discover what they do, their SEO authority, and the right people to contact.
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-card">', unsafe_allow_html=True)

col_label, col_samples = st.columns([1, 2])
with col_label:
    st.markdown('<div class="label-caps">Domains to Analyze</div>', unsafe_allow_html=True)
with col_samples:
    st.markdown('<div style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;"><span style="font-size: 0.875rem; color: #434655; font-weight: 500;">Try sample:</span>', unsafe_allow_html=True)
    cols = st.columns(3)
    for idx, (label, sample_text) in enumerate(SAMPLES.items()):
        with cols[idx]:
            if st.button(label, key=f"sample_{idx}"):
                st.session_state.domain_input = sample_text
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

domains_input = st.text_area(
    "domains",
    value=st.session_state.domain_input,
    height=256,
    placeholder="stripe.com\nvercel.com\nlinear.app\n...",
    label_visibility="collapsed"
)

domains_list = parse_input_domains(domains_input)
st.markdown(f'<div class="domain-counter">{len(domains_list)} domain{"s" if len(domains_list) != 1 else ""} detected</div>', unsafe_allow_html=True)

st.markdown("""
<div class="helper-text">
    <span style="font-size: 1rem;">ℹ️</span>
    Paste URLs or domains (one per line, comma or space separated). Or drag & drop a .txt/.csv file anywhere.
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    company_name = st.text_input("Your Company (Optional)", placeholder="e.g. Acme Inc")
with col2:
    outreach_purpose = st.text_input("Outreach Purpose (Optional)", placeholder="e.g. Partnership inquiry")

st.markdown("<br>", unsafe_allow_html=True)

analyze_button = st.button("🔍 Analyze Domains", disabled=len(domains_list) == 0, use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.results_df is None:
    st.markdown("""
    <div class="feature-grid">
        <div class="feature-card">
            <div class="feature-icon">⚡</div>
            <div class="feature-title">High-Speed Discovery</div>
            <div class="feature-desc">Process up to 5,000 domains in a single batch with millisecond latency.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">📊</div>
            <div class="feature-title">Enriched Data</div>
            <div class="feature-desc">Extract tech stacks, contact emails, social links, and domain authority automatically.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">📥</div>
            <div class="feature-title">Export Ready</div>
            <div class="feature-desc">One-click export to CSV, JSON, or sync directly to your CRM or outreach tools.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

if analyze_button and len(domains_list) > 0:
    st.markdown("---")
    st.markdown("### 🔄 Analyzing Domains...")

    progress_bar = st.progress(0)
    status_text = st.empty()

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_single_domain, domain): domain for domain in domains_list}
        processed = 0

        for future in as_completed(futures):
            results.append(future.result())
            processed += 1
            progress_bar.progress(processed / len(domains_list))
            status_text.markdown(f"**Processing...** ({processed}/{len(domains_list)} domains)")

    rows = []
    for res in results:
        email_details = []
        departments = []
        if res['emails']:
            for email in res['emails']:
                dept = classify_email_department(email)
                email_details.append(email)
                departments.append(dept)

        rows.append({
            'Domain': res['domain'],
            'Category': res['category'],
            'Score': res['score'],
            'Emails': email_details if email_details else ['No emails found'],
            'Departments': departments if departments else ['N/A'],
            'Status': res['status']
        })

    st.session_state.results_df = pd.DataFrame(rows)
    progress_bar.progress(1.0)
    status_text.success(f"✅ Analysis complete!")

if st.session_state.results_df is not None:
    df = st.session_state.results_df

    st.markdown("---")
    st.markdown("### 📊 Results")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("DOMAINS", len(df))
    with col2:
        total_emails = sum([len([e for e in emails if e != 'No emails found']) for emails in df['Emails']])
        st.metric("EMAILS", total_emails)
    with col3:
        all_depts = set()
        for depts in df['Departments']:
            all_depts.update([d for d in depts if d != 'N/A'])
        st.metric("DEPARTMENTS", len(all_depts))
    with col4:
        st.metric("AVG SCORE", f"{df['Score'].mean():.1f}")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("**Filter by Category:**")
    all_categories = sorted(df['Category'].unique())
    cols_cat = st.columns(len(all_categories))
    for idx, category in enumerate(all_categories):
        with cols_cat[idx]:
            btn_type = "primary" if category in st.session_state.selected_categories else "secondary"
            if st.button(category, key=f"cat_{category}", type=btn_type):
                if category in st.session_state.selected_categories:
                    st.session_state.selected_categories.remove(category)
                else:
                    st.session_state.selected_categories.append(category)
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Filter by Department:**")
    all_departments = set()
    for depts in df['Departments']:
        all_departments.update([d for d in depts if d != 'N/A'])
    all_departments = sorted(list(all_departments))

    if all_departments:
        cols_dept = st.columns(len(all_departments))
        for idx, dept in enumerate(all_departments):
            with cols_dept[idx]:
                dept_label = f"📧 {dept}"
                btn_type = "primary" if dept in st.session_state.selected_departments else "secondary"
                if st.button(dept_label, key=f"dept_{dept}", type=btn_type):
                    if dept in st.session_state.selected_departments:
                        st.session_state.selected_departments.remove(dept)
                    else:
                        st.session_state.selected_departments.append(dept)
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    filtered_df = df.copy()
    if st.session_state.selected_categories:
        filtered_df = filtered_df[filtered_df['Category'].isin(st.session_state.selected_categories)]
    if st.session_state.selected_departments:
        mask = filtered_df['Departments'].apply(
            lambda depts: any(d in st.session_state.selected_departments for d in depts)
        )
        filtered_df = filtered_df[mask]

    st.info(f"📊 Showing {len(filtered_df)} domain(s) after filtering")

    table_data = []
    for idx, row in filtered_df.iterrows():
        contact_details = []
        for email, dept in zip(row['Emails'], row['Departments']):
            if email != 'No emails found':
                contact_details.append(f"{email} 📧 {dept}")
            else:
                contact_details.append("No emails found")

        table_data.append({
            'Domain': f"[{row['Domain']}](https://{row['Domain']})",
            'Category': row['Category'],
            'Contact Details': "\n".join(contact_details),
            '_emails': row['Emails'],
            '_departments': row['Departments'],
            '_domain_raw': row['Domain']
        })

    if table_data:
        display_df = pd.DataFrame(table_data)[['Domain', 'Category', 'Contact Details']]
        st.markdown(display_df.to_markdown(), unsafe_allow_html=True)

        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("**💌 Click to Draft Emails:**")

        for idx, row_data in enumerate(table_data):
            domain_raw = row_data['_domain_raw']
            emails = row_data['_emails']
            depts = row_data['_departments']

            if emails and emails[0] != 'No emails found':
                st.markdown(f"**{domain_raw}:**")
                email_cols = st.columns(min(len(emails), 4))

                for email_idx, (email, dept) in enumerate(zip(emails, depts)):
                    with email_cols[email_idx % 4]:
                        if st.button(f"✉️ {email}", key=f"email_{idx}_{email_idx}"):
                            st.session_state.show_email_modal = True
                            st.session_state.active_email_data = {
                                'domain': domain_raw,
                                'email': email,
                                'department': dept,
                                'company': company_name if company_name else "Your Company",
                                'purpose': outreach_purpose if outreach_purpose else "collaboration"
                            }
                            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    export_rows = []
    for row in filtered_df.itertuples():
        for email, dept in zip(row.Emails, row.Departments):
            export_rows.append({
                'Domain': row.Domain,
                'Category': row.Category,
                'Score': row.Score,
                'Email': email,
                'Department': dept
            })

    export_df = pd.DataFrame(export_rows)
    csv = export_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Export Filtered Results (CSV)",
        csv,
        f"DomainLens_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
        "text/csv",
        use_container_width=True
    )

if st.session_state.show_email_modal and st.session_state.active_email_data:
    data = st.session_state.active_email_data

    with st.expander("✉️ Draft Outreach Email", expanded=True):
        st.info(f"**To:** {data['email']} | **Domain:** {data['domain']} | **Department:** {data['department']}")

        email_name = data['email'].split('@')[0].replace('.', ' ').title()

        subject = st.text_input("Subject Line", value=f"Quick {data['purpose']} opportunity for {data['domain']}")

        body_template = f"""Hi {email_name},

I came across {data['domain']} and was impressed by your content/product.

I'm reaching out from {data['company']} regarding a potential {data['purpose']} opportunity.

[Add your specific value proposition here]

Would you be open to a quick conversation about this?

Best regards,
Arun Chaudhary
Marketer at KrispCall"""

        body = st.text_area("Email Body", value=body_template, height=300)

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("📋 Copy to Clipboard", use_container_width=True):
                st.code(f"To: {data['email']}\nSubject: {subject}\n\n{body}")
                st.success("✅ Email content displayed above")
        with col_btn2:
            if st.button("❌ Close", use_container_width=True):
                st.session_state.show_email_modal = False
                st.session_state.active_email_data = None
                st.rerun()
