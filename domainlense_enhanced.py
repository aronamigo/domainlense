
import streamlit as st
import pandas as pd
import time
import re
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

# Page config
st.set_page_config(
    page_title="DomainLense | Domain Analysis Tool",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for modern SaaS design with table
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* Global styles */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Main background */
    .main {
        background: #F9FAFB;
        padding: 2rem 1rem;
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Main card container */
    .block-container {
        max-width: 1200px;
        margin: 0 auto;
        background: white;
        border-radius: 16px;
        padding: 3rem 3rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 10px 30px rgba(0,0,0,0.08);
    }

    /* Header */
    h1 {
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        color: #111827;
        margin-bottom: 1.5rem !important;
        letter-spacing: -0.02em;
    }

    /* Textarea */
    .stTextArea textarea {
        border: 2px solid #E5E7EB !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        font-size: 0.95rem !important;
        font-family: 'Inter', monospace !important;
        line-height: 1.6 !important;
        background: #FAFBFC !important;
        transition: all 0.2s !important;
        min-height: 200px !important;
    }

    .stTextArea textarea:focus {
        border-color: #5B7FFF !important;
        background: white !important;
        box-shadow: 0 0 0 3px rgba(91, 127, 255, 0.1) !important;
        outline: none !important;
    }

    /* Helper text */
    .helper-text {
        color: #6B7280;
        font-size: 0.875rem;
        margin-top: 0.5rem;
        line-height: 1.5;
    }

    /* Domain counter */
    .domain-counter {
        text-align: right;
        color: #9CA3AF;
        font-size: 0.875rem;
        margin-top: 0.5rem;
        font-weight: 500;
    }

    .domain-counter.active {
        color: #5B7FFF;
    }

    /* Text inputs */
    .stTextInput input {
        border: 2px solid #E5E7EB !important;
        border-radius: 10px !important;
        padding: 0.75rem 1rem !important;
        font-size: 0.95rem !important;
        background: #FAFBFC !important;
        transition: all 0.2s !important;
    }

    .stTextInput input:focus {
        border-color: #5B7FFF !important;
        background: white !important;
        box-shadow: 0 0 0 3px rgba(91, 127, 255, 0.1) !important;
        outline: none !important;
    }

    /* Labels */
    .stTextInput label, .stTextArea label {
        font-weight: 600 !important;
        color: #374151 !important;
        font-size: 0.9rem !important;
        margin-bottom: 0.5rem !important;
    }

    /* Subtext */
    .input-subtext {
        color: #9CA3AF;
        font-size: 0.8rem;
        margin-top: 0.25rem;
        font-style: italic;
    }

    /* Primary button */
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #5B7FFF 0%, #4F6EF7 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.9rem 2rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        box-shadow: 0 4px 12px rgba(91, 127, 255, 0.3) !important;
        transition: all 0.2s !important;
        letter-spacing: 0.01em !important;
        height: 56px !important;
    }

    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(91, 127, 255, 0.4) !important;
    }

    /* Section divider */
    .section-divider {
        border-top: 1px solid #F3F4F6;
        margin: 2rem 0;
    }

    /* Section headers */
    h3 {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        color: #374151 !important;
        margin-bottom: 1rem !important;
    }

    /* Success/Info messages */
    .stAlert {
        border-radius: 10px !important;
        border: 1px solid #E5E7EB !important;
        background: #F0F9FF !important;
        padding: 1rem !important;
    }

    /* Progress */
    .stProgress > div > div {
        background: linear-gradient(90deg, #5B7FFF 0%, #4F6EF7 100%);
        border-radius: 10px;
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #111827 !important;
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.875rem !important;
        color: #6B7280 !important;
        font-weight: 600 !important;
    }

    /* Filter chips */
    .filter-chip {
        display: inline-block;
        background: white;
        border: 1.5px solid #E5E7EB;
        border-radius: 20px;
        padding: 0.5rem 1rem;
        margin: 0.25rem;
        font-size: 0.875rem;
        color: #6B7280;
        cursor: pointer;
        transition: all 0.2s;
        font-weight: 500;
    }

    .filter-chip:hover {
        border-color: #5B7FFF;
        color: #5B7FFF;
        background: #F0F4FF;
    }

    .filter-chip.active {
        background: #5B7FFF;
        border-color: #5B7FFF;
        color: white;
    }

    /* Table styles */
    .dataframe {
        border: 1px solid #E5E7EB !important;
        border-radius: 12px !important;
        overflow: hidden !important;
    }

    .dataframe thead tr th {
        background: #F9FAFB !important;
        color: #374151 !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        padding: 1rem !important;
        border-bottom: 2px solid #E5E7EB !important;
    }

    .dataframe tbody tr td {
        padding: 1rem !important;
        border-bottom: 1px solid #F3F4F6 !important;
        font-size: 0.9rem !important;
        color: #374151 !important;
    }

    .dataframe tbody tr:hover {
        background: #F9FAFB !important;
    }

    /* Download button */
    .stDownloadButton > button {
        width: 100%;
        background: white !important;
        color: #5B7FFF !important;
        border: 2px solid #5B7FFF !important;
        border-radius: 12px !important;
        padding: 0.9rem 2rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        transition: all 0.2s !important;
        height: 56px !important;
    }

    .stDownloadButton > button:hover {
        background: #F0F4FF !important;
    }

    /* Icon before button text */
    .stButton > button::before {
        content: "🔍 ";
        margin-right: 0.5rem;
    }

    /* Modal styles */
    .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        z-index: 9999;
        display: flex;
        justify-content: center;
        align-items: center;
    }

    .modal-content {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        max-width: 600px;
        width: 90%;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
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
    "SaaS Competitors": """stripe.com
vercel.com
linear.app
notion.so
figma.com""",
    "Local Businesses": """starbucks.com
target.com
walgreens.com
cvs.com
walmart.com""",
    "Universities": """harvard.edu
stanford.edu
mit.edu
yale.edu
princeton.edu"""
}

# ==================== HELPER FUNCTIONS ====================

def extract_domain_from_url(url_or_domain):
    """Extract clean domain from URL or domain string"""
    url_or_domain = url_or_domain.strip()
    url_or_domain = re.sub(r'^(https?://)?(www\.)?', '', url_or_domain, flags=re.IGNORECASE)
    url_or_domain = url_or_domain.split('/')[0].split('?')[0].split('#')[0].split(':')[0]
    return url_or_domain.lower()

def parse_input_domains(raw_input):
    """Parse and clean list of URLs/domains"""
    entries = re.split(r'[,;\s\n]+', raw_input)
    domains = []
    for entry in entries:
        entry = entry.strip()
        if entry and len(entry) > 3:
            domain = extract_domain_from_url(entry)
            if domain:
                domains.append(domain)
    seen = set()
    unique_domains = []
    for domain in domains:
        if domain not in seen:
            seen.add(domain)
            unique_domains.append(domain)
    return unique_domains

def fetch_domain_content(domain, timeout=10):
    """Fetch HTML content from domain"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    urls_to_try = [f"https://{domain}", f"http://{domain}", f"https://www.{domain}", f"http://www.{domain}"]

    for url in urls_to_try:
        try:
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            if response.status_code == 200:
                return response.text, url, response.status_code
        except:
            continue
    return "", "", 0

def extract_emails_from_html(html_content, domain):
    """Extract emails from HTML"""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, html_content)
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
    all_emails = extract_emails_from_html(base_html, domain)
    contact_paths = ['/contact', '/contact-us', '/about', '/about-us', '/team']
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    for path in contact_paths:
        try:
            resp = requests.get(f"https://{domain}{path}", headers=headers, timeout=5)
            if resp.status_code == 200:
                all_emails.extend(extract_emails_from_html(resp.text, domain))
        except:
            continue
    return list(set(all_emails))[:10]

def calculate_saas_score(domain, html_content=""):
    """Calculate SaaS score"""
    score, signals = 0, []
    domain_lower, html_lower = domain.lower(), html_content.lower()

    if any(sub in domain_lower for sub in ['app.', 'dashboard.', 'portal.', 'console.']):
        score += 25
        signals.append("Subdomain Match (+25)")
    if any(path in html_lower for path in ['/pricing', '/plans', '/billing']):
        score += 10
        signals.append("Commercial Paths (+10)")
    if any(path in html_lower for path in ['/docs', '/api', '/developers']):
        score += 5
        signals.append("Developer Footprint (+5)")
    if 'schema.org/softwareapplication' in html_lower:
        score += 15
        signals.append("Schema Markup (+15)")
    if any(stack in html_lower for stack in ['intercom', 'drift', 'stripe', 'paddle']):
        score += 10
        signals.append("SaaS Stack (+10)")
    if any(kw in html_lower for kw in ['monthly', 'annual', 'per seat']):
        score += 5
        signals.append("Subscription Logic (+5)")
    if any(kw in html_lower for kw in ['free trial', 'request demo', 'book a demo']):
        score += 15
        signals.append("High Intent (+15)")
    if any(kw in html_lower for kw in ['integrations', 'workflow', 'automate']):
        score += 15
        signals.append("Product Language (+15)")
    if domain_lower.endswith(('.edu', '.gov', '.mil')):
        score -= 50
    if any(kw in html_lower for kw in ['add to cart', 'free shipping']):
        score -= 30

    return max(0, min(100, score)), signals

def classify_domain(domain, html_content=""):
    """Classify domain"""
    domain_lower = domain.lower()
    if domain_lower.endswith('.edu'):
        return 'Education', 100, []
    if domain_lower.endswith(('.gov', '.mil')):
        return 'Government', 100, []
    if domain_lower.endswith('.org'):
        return 'Organization', 60, []

    saas_score, saas_signals = calculate_saas_score(domain, html_content)
    if saas_score >= 75:
        return 'SaaS (Confirmed)', saas_score, saas_signals
    elif saas_score >= 50:
        return 'SaaS (Probable)', saas_score, saas_signals

    return 'General', 20, []

def classify_email_department(email):
    """Classify email by department"""
    email_lower = email.lower().split('@')[0]

    if any(kw in email_lower for kw in ['sales', 'demo', 'revenue']):
        return 'Sales'
    if any(kw in email_lower for kw in ['support', 'help', 'customer']):
        return 'Support'
    if any(kw in email_lower for kw in ['marketing', 'pr', 'seo', 'content']):
        return 'Marketing'
    if any(kw in email_lower for kw in ['info', 'hello', 'contact']):
        return 'General/Info'
    return 'Other'

def process_single_domain(domain):
    """Process single domain"""
    try:
        html_content, final_url, status_code = fetch_domain_content(domain)
        if status_code == 0:
            return {'domain': domain, 'status': 'Failed', 'category': 'Error', 'score': 0, 'emails': []}

        category, score, signals = classify_domain(domain, html_content)
        emails = scrape_contact_pages(domain, html_content)

        return {'domain': domain, 'status': 'Success', 'category': category, 'score': score, 'emails': emails}
    except Exception as e:
        return {'domain': domain, 'status': 'Error', 'category': 'Error', 'score': 0, 'emails': []}

# ==================== MAIN UI ====================

# Header with sample buttons
col_title, col_samples = st.columns([1, 1])

with col_title:
    st.markdown("<h1>Domains to Analyze</h1>", unsafe_allow_html=True)

with col_samples:
    cols = st.columns(3)
    for idx, (label, sample_text) in enumerate(SAMPLES.items()):
        with cols[idx]:
            if st.button(label, key=f"sample_{idx}", use_container_width=True):
                st.session_state.domain_input = sample_text
                st.rerun()

# Main input area
domains_input = st.text_area(
    "Input",
    value=st.session_state.domain_input,
    height=200,
    placeholder="""stripe.com
vercel.com
linear.app
shopify.com
hubspot.com""",
    label_visibility="collapsed",
    key="main_input"
)

# Helper text and domain counter
col_helper, col_counter = st.columns([3, 1])
with col_helper:
    st.markdown(
        '<p class="helper-text">💡 Paste URLs or domains (one per line, comma or space separated). '
        'Or drag & drop a .txt/.csv file.</p>',
        unsafe_allow_html=True
    )
with col_counter:
    domains_list = parse_input_domains(domains_input) if domains_input else []
    counter_class = "domain-counter active" if len(domains_list) > 0 else "domain-counter"
    st.markdown(
        f'<p class="{counter_class}">{len(domains_list)} domain{"s" if len(domains_list) != 1 else ""}</p>',
        unsafe_allow_html=True
    )

# File upload
uploaded_file = st.file_uploader(
    "upload",
    type=['txt', 'csv'],
    label_visibility="collapsed",
    help="Upload a CSV or TXT file with domains"
)

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df_upload = pd.read_csv(uploaded_file)
        raw_entries = df_upload.iloc[:, 0].astype(str).tolist()
    else:
        content = uploaded_file.read().decode('utf-8')
        raw_entries = content.split('\n')

    domains_input = '\n'.join(raw_entries)
    st.session_state.domain_input = domains_input
    domains_list = parse_input_domains(domains_input)
    st.rerun()

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# Optional fields section
st.markdown("<h3>Optional Details</h3>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    company_name = st.text_input(
        "Your Company",
        placeholder="e.g. DomainLense",
        help="Used for generating personalized outreach emails"
    )
    st.markdown(
        '<p class="input-subtext">Used for generating personalized outreach emails.</p>',
        unsafe_allow_html=True
    )

with col2:
    outreach_purpose = st.text_input(
        "Outreach Purpose",
        placeholder="e.g. guest post, partnership...",
        help="Tells the AI what the goal of your email is"
    )
    st.markdown(
        '<p class="input-subtext">Tells the AI what the goal of your email is.</p>',
        unsafe_allow_html=True
    )

st.markdown('<div class="spacing-lg"></div>', unsafe_allow_html=True)

# CTA Button
analyze_button = st.button(
    "Analyze Domains",
    type="primary",
    disabled=len(domains_list) == 0,
    use_container_width=True
)

# Analysis logic
if analyze_button and len(domains_list) > 0:
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown("<h3>🔄 Analyzing Domains...</h3>", unsafe_allow_html=True)

    progress_bar = st.progress(0)
    status_text = st.empty()

    status_text.markdown("**Fetching and classifying domains...**")

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_single_domain, domain): domain for domain in domains_list}
        processed = 0

        for future in as_completed(futures):
            results.append(future.result())
            processed += 1
            progress_bar.progress(processed / len(domains_list))
            status_text.markdown(f"**Processing...** ({processed}/{len(domains_list)} domains)")

    # Build results - one row per domain with all emails combined
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
    status_text.success(f"✅ Analysis complete! Analyzed {len(results)} domains.")

# Results display
if st.session_state.results_df is not None:
    df = st.session_state.results_df

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown("<h3>📊 Results</h3>", unsafe_allow_html=True)

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Domains", len(df))
    with col2:
        total_emails = sum([len([e for e in emails if e != 'No emails found']) for emails in df['Emails']])
        st.metric("Emails", total_emails)
    with col3:
        all_depts = set()
        for depts in df['Departments']:
            all_depts.update([d for d in depts if d != 'N/A'])
        st.metric("Departments", len(all_depts))
    with col4:
        st.metric("Avg Score", f"{df['Score'].mean():.1f}")

    st.markdown('<div class="spacing-lg"></div>', unsafe_allow_html=True)

    # Horizontal filter chips - Categories
    st.markdown("**Filter by Category:**")
    all_categories = sorted(df['Category'].unique())

    cols_cat = st.columns(len(all_categories))
    for idx, category in enumerate(all_categories):
        with cols_cat[idx]:
            if st.button(
                category,
                key=f"cat_{category}",
                type="primary" if category in st.session_state.selected_categories else "secondary"
            ):
                if category in st.session_state.selected_categories:
                    st.session_state.selected_categories.remove(category)
                else:
                    st.session_state.selected_categories.append(category)
                st.rerun()

    st.markdown('<div class="spacing-md"></div>', unsafe_allow_html=True)

    # Horizontal filter chips - Departments
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
                if st.button(
                    dept_label,
                    key=f"dept_{dept}",
                    type="primary" if dept in st.session_state.selected_departments else "secondary"
                ):
                    if dept in st.session_state.selected_departments:
                        st.session_state.selected_departments.remove(dept)
                    else:
                        st.session_state.selected_departments.append(dept)
                    st.rerun()

    st.markdown('<div class="spacing-lg"></div>', unsafe_allow_html=True)

    # Filter dataframe
    filtered_df = df.copy()

    if st.session_state.selected_categories:
        filtered_df = filtered_df[filtered_df['Category'].isin(st.session_state.selected_categories)]

    if st.session_state.selected_departments:
        # Filter by departments - check if any email has the selected department
        mask = filtered_df['Departments'].apply(
            lambda depts: any(d in st.session_state.selected_departments for d in depts)
        )
        filtered_df = filtered_df[mask]

    st.info(f"📊 Showing {len(filtered_df)} domain(s) after filtering")

    # Build table data
    table_data = []
    for idx, row in filtered_df.iterrows():
        domain = row['Domain']
        category = row['Category']

        # Build contact details column
        contact_details = []
        for email, dept in zip(row['Emails'], row['Departments']):
            if email != 'No emails found':
                contact_details.append(f"{email} 📧 {dept}")
            else:
                contact_details.append("No emails found")

        contact_str = "\n".join(contact_details)

        table_data.append({
            'Domain': f"[{domain}](https://{domain})",
            'Category': category,
            'Contact Details': contact_str,
            '_emails': row['Emails'],
            '_departments': row['Departments'],
            '_domain_raw': domain
        })

    # Display table
    if table_data:
        display_df = pd.DataFrame(table_data)[['Domain', 'Category', 'Contact Details']]
        st.markdown(display_df.to_markdown(), unsafe_allow_html=True)

        # Email buttons for each contact
        st.markdown('<div class="spacing-lg"></div>', unsafe_allow_html=True)
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

    st.markdown('<div class="spacing-lg"></div>', unsafe_allow_html=True)

    # Export button
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
        f"DomainLense_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
        "text/csv",
        use_container_width=True
    )

# Email Modal
if st.session_state.show_email_modal and st.session_state.active_email_data:
    data = st.session_state.active_email_data

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown("## ✉️ Draft Outreach Email")

    st.info(f"**To:** {data['email']} | **Domain:** {data['domain']} | **Department:** {data['department']}")

    email_name = data['email'].split('@')[0].replace('.', ' ').title()

    subject = st.text_input(
        "Subject Line",
        value=f"Quick {data['purpose']} opportunity for {data['domain']}"
    )

    body_template = f"""Hi {email_name},

I came across {data['domain']} and was impressed by your content/product.

I'm reaching out from {data['company']} regarding a potential {data['purpose']} opportunity.

[Add your specific value proposition here]

Would you be open to a quick conversation about this?

Best regards,
Arun Chaudhary
Marketer at KrispCall"""

    body = st.text_area(
        "Email Body",
        value=body_template,
        height=300
    )

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("📋 Copy to Clipboard", use_container_width=True):
            st.code(f"To: {data['email']}\nSubject: {subject}\n\n{body}")
            st.success("✅ Email content displayed above - copy manually")

    with col_btn2:
        if st.button("❌ Close", use_container_width=True):
            st.session_state.show_email_modal = False
            st.session_state.active_email_data = None
            st.rerun()
