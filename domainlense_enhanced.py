
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

# Page config with modern theme
st.set_page_config(
    page_title="DomainLense | SEO Outreach Tool",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern design
st.markdown("""
<style>
    /* Main theme */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
    }

    /* Content container */
    .block-container {
        background: white;
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }

    /* Header styling */
    h1 {
        color: #667eea;
        font-weight: 800;
        font-size: 3rem !important;
        margin-bottom: 0.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Subheader */
    .subtitle {
        color: #6c757d;
        font-size: 1.2rem;
        margin-bottom: 2rem;
        font-weight: 400;
    }

    /* Cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        transition: transform 0.3s ease;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        color: white;
    }

    section[data-testid="stSidebar"] * {
        color: white !important;
    }

    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
    }

    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.5);
    }

    /* Input fields */
    .stTextArea textarea, .stTextInput input {
        border-radius: 10px;
        border: 2px solid #e9ecef;
        padding: 0.75rem;
        font-size: 1rem;
    }

    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }

    /* Expander */
    .streamlit-expanderHeader {
        background: #f8f9fa;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        font-weight: 600;
    }

    /* Progress bar */
    .stProgress > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }

    /* Info/Success boxes */
    .stAlert {
        border-radius: 10px;
        border-left: 4px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'show_email_form' not in st.session_state:
    st.session_state.show_email_form = False
if 'active_row' not in st.session_state:
    st.session_state.active_row = None

# ==================== URL/DOMAIN PARSING ====================

def extract_domain_from_url(url_or_domain):
    """Extract clean domain from URL or domain string"""
    url_or_domain = url_or_domain.strip()

    # Remove common prefixes if present
    url_or_domain = re.sub(r'^(https?://)?(www\.)?', '', url_or_domain, flags=re.IGNORECASE)

    # Remove path, query params, fragments
    url_or_domain = url_or_domain.split('/')[0]
    url_or_domain = url_or_domain.split('?')[0]
    url_or_domain = url_or_domain.split('#')[0]

    # Remove port if present
    url_or_domain = url_or_domain.split(':')[0]

    return url_or_domain.lower()

def parse_input_domains(raw_input):
    """Parse and clean list of URLs/domains from text input"""
    # Split by newlines, commas, semicolons, or spaces
    entries = re.split(r'[,;\s\n]+', raw_input)

    domains = []
    for entry in entries:
        entry = entry.strip()
        if entry:
            domain = extract_domain_from_url(entry)
            if domain and len(domain) > 3:  # Basic validation
                domains.append(domain)

    # Remove duplicates while preserving order
    seen = set()
    unique_domains = []
    for domain in domains:
        if domain not in seen:
            seen.add(domain)
            unique_domains.append(domain)

    return unique_domains

# ==================== WEB SCRAPING UTILITIES ====================

def fetch_domain_content(domain, timeout=10):
    """Fetch HTML content from domain with error handling"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    urls_to_try = [
        f"https://{domain}",
        f"http://{domain}",
        f"https://www.{domain}",
        f"http://www.{domain}"
    ]

    for url in urls_to_try:
        try:
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            if response.status_code == 200:
                return response.text, url, response.status_code
        except requests.exceptions.RequestException:
            continue

    return "", "", 0

def extract_emails_from_html(html_content, domain):
    """Extract emails from HTML content using regex"""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, html_content)

    domain_clean = domain.replace('www.', '')
    valid_emails = []

    for email in emails:
        email_lower = email.lower()
        if any(skip in email_lower for skip in ['example.com', 'yourdomain.com', 'email.com', 'domain.com']):
            continue
        if any(ext in email_lower for ext in ['.png', '.jpg', '.gif', '.svg']):
            continue
        if domain_clean in email_lower:
            valid_emails.append(email_lower)

    return list(set(valid_emails))

def scrape_contact_pages(domain, base_html):
    """Try to scrape contact/about pages for more emails"""
    all_emails = extract_emails_from_html(base_html, domain)

    contact_paths = ['/contact', '/contact-us', '/about', '/about-us', '/team']
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    for path in contact_paths:
        try:
            url = f"https://{domain}{path}"
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                page_emails = extract_emails_from_html(resp.text, domain)
                all_emails.extend(page_emails)
        except:
            continue

    return list(set(all_emails))[:10]

# ==================== DOMAIN CLASSIFICATION ====================

def calculate_saas_score(domain, html_content=""):
    """Calculate SaaS probability score"""
    score = 0
    signals = []

    domain_lower = domain.lower()
    html_lower = html_content.lower()

    if any(sub in domain_lower for sub in ['app.', 'dashboard.', 'portal.', 'console.']):
        score += 25
        signals.append("Subdomain Match (+25)")

    if any(path in html_lower for path in ['/pricing', '/plans', '/billing']):
        score += 10
        signals.append("Commercial Paths (+10)")

    if any(path in html_lower for path in ['/docs', '/api', '/developers', '/changelog']):
        score += 5
        signals.append("Developer Footprint (+5)")

    if 'schema.org/softwareapplication' in html_lower:
        score += 15
        signals.append("Schema Markup (+15)")

    if any(stack in html_lower for stack in ['intercom', 'drift', 'segment.com', 'stripe', 'paddle']):
        score += 10
        signals.append("SaaS Stack (+10)")

    if any(kw in html_lower for kw in ['monthly', 'annual', 'per seat', 'tiered pricing']):
        score += 5
        signals.append("Subscription Logic (+5)")

    if any(kw in html_lower for kw in ['free trial', 'no credit card required', 'request demo', 'book a demo']):
        score += 15
        signals.append("High Intent (+15)")

    if any(kw in html_lower for kw in ['integrations', 'workflow', 'automate', 'scalable platform', 'soc2 compliant']):
        score += 15
        signals.append("Product Language (+15)")

    if domain_lower.endswith(('.edu', '.gov', '.mil')):
        score -= 50
        signals.append("Institutional Penalty (-50)")

    if any(kw in html_lower for kw in ['free shipping', 'add to cart', 'return policy', 'shop now']):
        score -= 30
        signals.append("B2C/Retail Penalty (-30)")

    return max(0, min(100, score)), signals

def classify_domain(domain, html_content=""):
    """Classify domain into categories"""
    domain_lower = domain.lower()
    html_lower = html_content.lower()

    if domain_lower.endswith('.edu'):
        return 'Education', 100, ['TLD: .edu']
    if domain_lower.endswith('.gov'):
        return 'Government', 100, ['TLD: .gov']
    if domain_lower.endswith('.mil'):
        return 'Government', 100, ['TLD: .mil']
    if domain_lower.endswith('.org'):
        if any(kw in html_lower for kw in ['donate', '501(c)(3)', 'our mission', 'volunteer']):
            return 'Organization', 80, ['Non-Profit Signal']
        return 'Organization', 60, ['TLD: .org']

    if any(kw in html_lower for kw in ['this domain is for sale', 'buy this domain', 'coming soon', 'parked domain']):
        return 'Parked/Invalid', 80, ['Domain for sale/parked']

    saas_score, saas_signals = calculate_saas_score(domain, html_content)

    ecom_score = 0
    ecom_signals = []
    if any(sub in domain_lower for sub in ['shop.', 'store.', 'checkout.']):
        ecom_score += 20
        ecom_signals.append("Ecommerce Subdomain (+20)")
    if any(path in html_lower for path in ['/cart', '/checkout', '/collections', '/products']):
        ecom_score += 20
        ecom_signals.append("Shopping Paths (+20)")
    if any(platform in html_lower for platform in ['shopify', 'woocommerce', 'magento', 'bigcommerce']):
        ecom_score += 20
        ecom_signals.append("Ecommerce Platform (+20)")
    if any(kw in html_lower for kw in ['add to cart', 'buy now', 'shipping policy']):
        ecom_score += 20
        ecom_signals.append("Cart Keywords (+20)")

    corp_score = 0
    corp_signals = []
    if any(path in html_lower for path in ['/services', '/solutions', '/our-work']):
        corp_score += 20
        corp_signals.append("Services Focus (+20)")
    if any(kw in html_lower for kw in ['contact us', 'get a quote', 'request a consultation']):
        corp_score += 15
        corp_signals.append("Consultation CTA (+15)")
    if any(path in html_lower for path in ['/portfolio', '/case-studies', '/clients']):
        corp_score += 15
        corp_signals.append("Case Studies (+15)")
    if any(kw in html_lower for kw in ['consulting', 'agency', 'firm', 'expertise']):
        corp_score += 10
        corp_signals.append("Professional Keywords (+10)")

    media_score = 0
    media_signals = []
    if any(path in html_lower for path in ['/category/', '/news/', '/blog/', '/article/']):
        media_score += 20
        media_signals.append("Content Hierarchy (+20)")
    if 'published on' in html_lower or 'written by' in html_lower:
        media_score += 20
        media_signals.append("Date Stamps (+20)")
    if any(kw in html_lower for kw in ['subscribe to newsletter', 'trending', 'latest news']):
        media_score += 15
        media_signals.append("Media Keywords (+15)")

    scores = {
        'SaaS': (saas_score, saas_signals),
        'Ecommerce': (ecom_score, ecom_signals),
        'Corporate/Service': (corp_score, corp_signals),
        'Content/Media': (media_score, media_signals)
    }

    if saas_score >= 75:
        return 'SaaS (Confirmed)', saas_score, saas_signals
    elif saas_score >= 50:
        return 'SaaS (Probable)', saas_score, saas_signals

    best_category = max(scores.items(), key=lambda x: x[1][0])
    if best_category[1][0] > 30:
        return best_category[0], best_category[1][0], best_category[1][1]

    return 'General', 20, ['Low signal strength']

# ==================== EMAIL CLASSIFICATION ====================

def classify_email_department(email):
    """Classify email by department"""
    email_lower = email.lower().split('@')[0] if '@' in email else email.lower()

    sales_keywords = ['sales', 'deals', 'growth', 'revenue', 'demo', 'trial', 'quote', 'partners', 'leads']
    if any(kw in email_lower for kw in sales_keywords):
        return 'Sales'

    support_keywords = ['support', 'help', 'helpdesk', 'care', 'service', 'customer', 'success']
    if any(kw in email_lower for kw in support_keywords):
        return 'Support'

    marketing_keywords = ['marketing', 'mktg', 'press', 'media', 'pr', 'seo', 'backlinks', 'content', 'blog', 'editorial']
    if any(kw in email_lower for kw in marketing_keywords):
        return 'Marketing'

    finance_keywords = ['billing', 'finance', 'accounting', 'invoices', 'payments']
    if any(kw in email_lower for kw in finance_keywords):
        return 'Finance/Billing'

    hr_keywords = ['jobs', 'careers', 'hiring', 'recruiting', 'hr', 'people']
    if any(kw in email_lower for kw in hr_keywords):
        return 'HR'

    dev_keywords = ['dev', 'developers', 'engineering', 'api', 'tech']
    if any(kw in email_lower for kw in dev_keywords):
        return 'Development'

    it_keywords = ['it', 'admin', 'ops', 'operations', 'security']
    if any(kw in email_lower for kw in it_keywords):
        return 'IT/Operations'

    legal_keywords = ['legal', 'counsel', 'compliance', 'privacy']
    if any(kw in email_lower for kw in legal_keywords):
        return 'Legal/Compliance'

    exec_keywords = ['ceo', 'founder', 'cto', 'cfo', 'coo', 'executive']
    if any(kw in email_lower for kw in exec_keywords):
        return 'Executive'

    general_keywords = ['info', 'hello', 'hi', 'contact', 'general']
    if any(kw in email_lower for kw in general_keywords):
        return 'General/Info'

    return 'Other'

# ==================== PROCESSING ====================

def process_single_domain(domain, progress_callback=None):
    """Process single domain"""
    try:
        html_content, final_url, status_code = fetch_domain_content(domain)

        if status_code == 0:
            return {
                'domain': domain,
                'status': 'Failed to fetch',
                'category': 'Parked/Invalid',
                'score': 0,
                'emails': []
            }

        category, score, signals = classify_domain(domain, html_content)
        emails = scrape_contact_pages(domain, html_content)

        if progress_callback:
            progress_callback(domain)

        return {
            'domain': domain,
            'status': 'Success',
            'category': category,
            'score': score,
            'emails': emails,
            'signals': signals
        }

    except Exception as e:
        return {
            'domain': domain,
            'status': f'Error: {str(e)}',
            'category': 'Error',
            'score': 0,
            'emails': []
        }

# ==================== MAIN UI ====================

# Hero Section
col_hero1, col_hero2 = st.columns([2, 1])
with col_hero1:
    st.markdown("<h1>🔍 DomainLense</h1>", unsafe_allow_html=True)
    st.markdown('<p class="subtitle">AI-powered domain classification & email extraction for SEO outreach</p>', unsafe_allow_html=True)
with col_hero2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("✨ **New:** Now accepts full URLs and page links!")

st.markdown("---")

# Sidebar
with st.sidebar:
    st.markdown("## 💡 Pro Tips")
    tips = [
        "🎯 Target editorial sites with high DA",
        "✍️ Personalize every outreach email",
        "📊 Check domain metrics before reaching out",
        "🤝 Build relationships, not just links",
        "📧 Follow up once after 5-7 days",
        "🔗 Use natural link insertion anchors"
    ]
    for tip in tips:
        st.markdown(tip)

    st.markdown("---")
    st.markdown("## ⚙️ Settings")
    max_workers = st.slider("Parallel threads", 1, 10, 5)
    timeout = st.slider("Timeout (sec)", 5, 30, 10)

# Input Section
st.markdown("## 📥 Input URLs or Domains")
st.markdown("Enter full URLs (https://example.com/page) or just domains (example.com)")

input_method = st.radio("", ["✍️ Paste", "📁 Upload File"], horizontal=True)

domains_list = []

if input_method == "✍️ Paste":
    example_text = """https://stripe.com/pricing
hubspot.com
https://www.shopify.com/blog/ecommerce-seo"""

    domains_input = st.text_area(
        "Paste URLs or domains (one per line)",
        height=180,
        placeholder=example_text,
        help="Accepts: URLs, domains, or page links. Automatically extracts clean domains."
    )

    if domains_input:
        domains_list = parse_input_domains(domains_input)
        st.success(f"✅ **{len(domains_list)} unique domains** detected and ready to analyze")
        with st.expander("📋 View parsed domains"):
            st.write(domains_list)
else:
    uploaded_file = st.file_uploader("Upload CSV or TXT", type=['csv', 'txt'])
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            df_upload = pd.read_csv(uploaded_file)
            raw_entries = df_upload.iloc[:, 0].astype(str).tolist()
        else:
            content = uploaded_file.read().decode('utf-8')
            raw_entries = content.split('\n')

        domains_list = parse_input_domains('\n'.join(raw_entries))
        st.success(f"✅ **{len(domains_list)} unique domains** extracted from file")

# Analysis Button
if len(domains_list) > 0:
    if st.button("🚀 Start Analysis", type="primary", use_container_width=True):
        st.markdown("---")
        st.markdown("## 🔄 Processing Domains...")

        progress_bar = st.progress(0)
        status_text = st.empty()

        steps = [
            "1️⃣ Parsing & validating domains",
            "2️⃣ Fetching & classifying domains",
            "3️⃣ Extracting contact emails",
            "4️⃣ Classifying by department",
            "5️⃣ Finalizing results"
        ]

        status_text.markdown(f"**{steps[0]}** ✅")
        progress_bar.progress(0.2)
        time.sleep(0.5)

        status_text.markdown(f"**{steps[1]}** ⏳")

        results = []
        processed_count = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_single_domain, domain): domain for domain in domains_list}

            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                processed_count += 1

                progress = 0.2 + (0.5 * processed_count / len(domains_list))
                progress_bar.progress(progress)
                status_text.markdown(f"**{steps[1]}** ⏳ ({processed_count}/{len(domains_list)})")

        status_text.markdown(f"**{steps[3]}** ⏳")
        progress_bar.progress(0.8)

        rows = []
        for res in results:
            if res['emails']:
                for email in res['emails']:
                    dept = classify_email_department(email)
                    rows.append({
                        'Domain': res['domain'],
                        'Category': res['category'],
                        'Score': res['score'],
                        'Email': email,
                        'Department': dept,
                        'Status': res['status']
                    })
            else:
                rows.append({
                    'Domain': res['domain'],
                    'Category': res['category'],
                    'Score': res['score'],
                    'Email': 'No emails found',
                    'Department': 'N/A',
                    'Status': res['status']
                })

        st.session_state.results_df = pd.DataFrame(rows)
        progress_bar.progress(1.0)
        status_text.success(f"✅ **Complete!** Analyzed {len(domains_list)} domains, found {len([r for r in rows if r['Email'] != 'No emails found'])} emails")

# Results Display
if st.session_state.results_df is not None:
    df = st.session_state.results_df

    st.markdown("---")
    st.markdown("## 📊 Results")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🌐 Domains", df['Domain'].nunique())
    with col2:
        valid_emails = df[df['Email'] != 'No emails found']
        st.metric("📧 Emails", len(valid_emails))
    with col3:
        st.metric("🏷️ Departments", df['Department'].nunique())
    with col4:
        st.metric("⭐ Avg Score", f"{df['Score'].mean():.1f}")

    st.markdown("### 🔍 Filters")
    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        selected_categories = st.multiselect("Category", sorted(df['Category'].unique()))
    with col_f2:
        selected_depts = st.multiselect("Department", sorted(df['Department'].unique()))
    with col_f3:
        min_score = st.slider("Min Score", 0, 100, 0)

    filtered_df = df.copy()
    if selected_categories:
        filtered_df = filtered_df[filtered_df['Category'].isin(selected_categories)]
    if selected_depts:
        filtered_df = filtered_df[filtered_df['Department'].isin(selected_depts)]
    filtered_df = filtered_df[filtered_df['Score'] >= min_score]

    st.info(f"📧 **{len(filtered_df)}** contacts after filtering")

    st.markdown("### 📋 Contacts")
    for idx, row in filtered_df.iterrows():
        if row['Email'] == 'No emails found':
            continue

        with st.expander(f"📧 {row['Email']} • {row['Domain']} • {row['Category']}"):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.write(f"**Domain:** {row['Domain']}")
                st.write(f"**Category:** {row['Category']}")
            with col_b:
                st.write(f"**Email:** {row['Email']}")
                st.write(f"**Department:** {row['Department']}")
            with col_c:
                st.write(f"**Score:** ⭐ {row['Score']}/100")
                st.write(f"**Status:** {row['Status']}")

            if st.button("✉️ Draft Email", key=f"btn_{idx}"):
                st.session_state.active_row = row
                st.session_state.show_email_form = True
                st.rerun()

    st.markdown("---")
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Export Results (CSV)",
        csv,
        f"DomainLense_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
        "text/csv",
        type="primary",
        use_container_width=True
    )

# Email Form
if st.session_state.show_email_form and st.session_state.active_row is not None:
    row = st.session_state.active_row
    st.markdown("---")
    st.markdown("## ✉️ Outreach Email Draft")

    subject = st.text_input("Subject", f"Link Opportunity for {row['Domain']}")
    body = st.text_area("Body", f"""Hi {row['Email'].split('@')[0].title()},

I came across {row['Domain']} and was impressed by your content.

I have a resource that would add value to your readers:

[Your resource here]

Would you be open to including this in a relevant post?

Best,
Arun Chaudhary
Marketer at KrispCall""", height=250)

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("📋 Copy", use_container_width=True):
            st.code(f"To: {row['Email']}\nSubject: {subject}\n\n{body}")
    with col_btn2:
        if st.button("❌ Close", use_container_width=True):
            st.session_state.show_email_form = False
            st.rerun()
