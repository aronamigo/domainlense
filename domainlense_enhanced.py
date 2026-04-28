
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
st.set_page_config(page_title="DomainLense", page_icon="🔍", layout="wide")

# Initialize session state
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'show_email_form' not in st.session_state:
    st.session_state.show_email_form = False
if 'active_row' not in st.session_state:
    st.session_state.active_row = None

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
    # Email regex pattern
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

    # Find all emails
    emails = re.findall(email_pattern, html_content)

    # Filter: only keep emails from the same domain
    domain_clean = domain.replace('www.', '')
    valid_emails = []

    for email in emails:
        email_lower = email.lower()
        # Skip common false positives
        if any(skip in email_lower for skip in ['example.com', 'yourdomain.com', 'email.com', 'domain.com']):
            continue
        # Skip image files
        if any(ext in email_lower for ext in ['.png', '.jpg', '.gif', '.svg']):
            continue
        # Keep only domain-specific emails
        if domain_clean in email_lower:
            valid_emails.append(email_lower)

    # Remove duplicates
    return list(set(valid_emails))

def scrape_contact_pages(domain, base_html):
    """Try to scrape contact/about pages for more emails"""
    soup = BeautifulSoup(base_html, 'html.parser')
    all_emails = []

    # Extract emails from homepage
    homepage_emails = extract_emails_from_html(base_html, domain)
    all_emails.extend(homepage_emails)

    # Look for contact/about page links
    contact_paths = ['/contact', '/contact-us', '/about', '/about-us', '/team', '/company']

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    for path in contact_paths:
        try:
            url = f"https://{domain}{path}"
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                page_emails = extract_emails_from_html(resp.text, domain)
                all_emails.extend(page_emails)
        except:
            continue

    return list(set(all_emails))[:10]  # Return max 10 unique emails

# ==================== DOMAIN CLASSIFICATION LOGIC ====================

def calculate_saas_score(domain, html_content=""):
    """Calculate SaaS probability score (0-100) based on weighted signals"""
    score = 0
    signals = []

    domain_lower = domain.lower()
    html_lower = html_content.lower()

    # A. Structural Signals (Max: 40 pts)
    if any(sub in domain_lower for sub in ['app.', 'dashboard.', 'portal.', 'console.']):
        score += 25
        signals.append("Subdomain Match (+25)")

    if any(path in html_lower for path in ['/pricing', '/plans', '/billing']):
        score += 10
        signals.append("Commercial Paths (+10)")

    if any(path in html_lower for path in ['/docs', '/api', '/developers', '/changelog']):
        score += 5
        signals.append("Developer Footprint (+5)")

    # B. Technical & Meta Signals (Max: 30 pts)
    if 'schema.org/softwareapplication' in html_lower:
        score += 15
        signals.append("Schema Markup (+15)")

    if any(stack in html_lower for stack in ['intercom', 'drift', 'segment.com', 'stripe', 'paddle']):
        score += 10
        signals.append("SaaS Stack (+10)")

    if any(kw in html_lower for kw in ['monthly', 'annual', 'per seat', 'tiered pricing']):
        score += 5
        signals.append("Subscription Logic (+5)")

    # C. Keyword Intent (Max: 30 pts)
    if any(kw in html_lower for kw in ['free trial', 'no credit card required', 'request demo', 'book a demo', 'start free trial']):
        score += 15
        signals.append("High Intent (+15)")

    if any(kw in html_lower for kw in ['integrations', 'workflow', 'automate', 'scalable platform', 'soc2 compliant', 'api access']):
        score += 15
        signals.append("Product Language (+15)")

    # Negative Constraints
    if domain_lower.endswith(('.edu', '.gov', '.mil')):
        score -= 50
        signals.append("Institutional Penalty (-50)")

    if any(kw in html_lower for kw in ['free shipping', 'add to cart', 'return policy', 'our store', 'shop now']):
        score -= 30
        signals.append("B2C/Retail Penalty (-30)")

    return max(0, min(100, score)), signals

def classify_domain(domain, html_content=""):
    """Classify domain into categories with scoring"""
    domain_lower = domain.lower()
    html_lower = html_content.lower()

    # Institutional (Rule-based auto-label)
    if domain_lower.endswith('.edu'):
        return 'Education', 100, ['TLD: .edu']
    if domain_lower.endswith('.gov'):
        return 'Government', 100, ['TLD: .gov']
    if domain_lower.endswith('.mil'):
        return 'Government', 100, ['TLD: .mil']
    if domain_lower.endswith('.org'):
        if any(kw in html_lower for kw in ['donate', '501(c)(3)', 'our mission', 'volunteer', 'non-profit']):
            return 'Organization', 80, ['Non-Profit Signal']
        return 'Organization', 60, ['TLD: .org']

    # Parked/Invalid
    if any(kw in html_lower for kw in ['this domain is for sale', 'buy this domain', 'coming soon', 'under construction', 'parked domain']):
        return 'Parked/Invalid', 80, ['Domain for sale/parked']

    # Calculate SaaS score
    saas_score, saas_signals = calculate_saas_score(domain, html_content)

    # Ecommerce signals
    ecom_score = 0
    ecom_signals = []
    if any(sub in domain_lower for sub in ['shop.', 'store.', 'checkout.']):
        ecom_score += 20
        ecom_signals.append("Ecommerce Subdomain (+20)")
    if any(path in html_lower for path in ['/cart', '/checkout', '/collections', '/products', '/shop']):
        ecom_score += 20
        ecom_signals.append("Shopping Paths (+20)")
    if any(platform in html_lower for platform in ['shopify', 'woocommerce', 'magento', 'bigcommerce', 'prestashop']):
        ecom_score += 20
        ecom_signals.append("Ecommerce Platform (+20)")
    if any(kw in html_lower for kw in ['add to cart', 'buy now', 'shipping policy', 'return policy', 'order tracking']):
        ecom_score += 20
        ecom_signals.append("Cart/Shopping Keywords (+20)")

    # Corporate/Service signals
    corp_score = 0
    corp_signals = []
    if any(path in html_lower for path in ['/services', '/solutions', '/our-work', '/what-we-do']):
        corp_score += 20
        corp_signals.append("Services Focus (+20)")
    if any(kw in html_lower for kw in ['contact us', 'get a quote', 'request a consultation', 'schedule a call']):
        corp_score += 15
        corp_signals.append("Consultation CTA (+15)")
    if any(path in html_lower for path in ['/portfolio', '/case-studies', '/case studies', '/our-clients', '/clients']):
        corp_score += 15
        corp_signals.append("Case Studies (+15)")
    if any(kw in html_lower for kw in ['consulting', 'agency', 'firm', 'expertise', 'professional services']):
        corp_score += 10
        corp_signals.append("Professional Keywords (+10)")

    # Content/Media signals
    media_score = 0
    media_signals = []
    if any(path in html_lower for path in ['/category/', '/news/', '/blog/', '/article/', '/post/']):
        media_score += 20
        media_signals.append("Content Hierarchy (+20)")
    if 'published on' in html_lower or 'written by' in html_lower or 'author:' in html_lower:
        media_score += 20
        media_signals.append("Date Stamps (+20)")
    if any(kw in html_lower for kw in ['subscribe to newsletter', 'trending', 'latest news', 'breaking news']):
        media_score += 15
        media_signals.append("Media Keywords (+15)")

    # Final classification based on highest score
    scores = {
        'SaaS': (saas_score, saas_signals),
        'Ecommerce': (ecom_score, ecom_signals),
        'Corporate/Service': (corp_score, corp_signals),
        'Content/Media': (media_score, media_signals)
    }

    # SaaS confidence mapping
    if saas_score >= 75:
        return 'SaaS (Confirmed)', saas_score, saas_signals
    elif saas_score >= 50:
        return 'SaaS (Probable)', saas_score, saas_signals

    # Otherwise pick highest score
    best_category = max(scores.items(), key=lambda x: x[1][0])
    if best_category[1][0] > 30:
        return best_category[0], best_category[1][0], best_category[1][1]

    return 'General', 20, ['Low signal strength']

# ==================== EMAIL CLASSIFICATION LOGIC ====================

def classify_email_department(email):
    """Classify email by department based on email prefix rules"""
    email_lower = email.lower().split('@')[0] if '@' in email else email.lower()

    # Sales
    sales_keywords = ['sales', 'deals', 'growth', 'revenue', 'inquiries', 'orders', 'commercial', 
                      'demo', 'trial', 'getstarted', 'quote', 'rfp', 'proposals',
                      'account-management', 'am', 'ae', 'partners', 'alliances', 'resellers',
                      'outreach', 'leads', 'prospective', 'market-expansion']
    if any(kw in email_lower for kw in sales_keywords):
        return 'Sales'

    # Support
    support_keywords = ['support', 'help', 'helpdesk', 'care', 'service', 'customer', 'success',
                        'tech-support', 'troubleshooting', 'tickets', 'issue', 'bugs', 'status',
                        'docs', 'knowledgebase', 'training', 'onboarding',
                        'feedback', 'complaints', 'experience', 'happiness', 'resolution']
    if any(kw in email_lower for kw in support_keywords):
        return 'Support'

    # Marketing (expanded with SEO-specific)
    marketing_keywords = ['marketing', 'mktg', 'press', 'media', 'pr', 'comms', 'communications',
                          'seo', 'search', 'serp', 'visibility', 'rankings', 'optimization',
                          'backlinks', 'linkbuilding', 'guestpost', 'collab', 'partnerships', 'editorial',
                          'growth', 'performance', 'acquisition', 'demandgen', 'paidmedia', 'ads', 'sem',
                          'content', 'copy', 'creative', 'blog', 'articles',
                          'newsletter', 'promo', 'offers', 'events', 'webinars', 'campaigns',
                          'branding', 'social', 'design',
                          'affiliate', 'sponsorships', 'influencers', 'advocacy']
    if any(kw in email_lower for kw in marketing_keywords):
        return 'Marketing'

    # Finance/Billing
    finance_keywords = ['billing', 'finance', 'accounting', 'accounts-payable', 'ap', 'accounts-receivable', 'ar',
                        'invoices', 'receipts', 'payments', 'wire', 'remittance', 'purchasing',
                        'audit', 'tax', 'treasury', 'payroll-finance', 'expenses', 'reimbursements']
    if any(kw in email_lower for kw in finance_keywords):
        return 'Finance/Billing'

    # HR
    hr_keywords = ['jobs', 'careers', 'hiring', 'recruiting', 'talent', 'resumes', 'cv', 'applications',
                   'hr', 'people', 'culture', 'wellness', 'benefits', 'payroll', 'onboarding',
                   'ethics', 'conduct', 'diversity', 'dei', 'employee-relations']
    if any(kw in email_lower for kw in hr_keywords):
        return 'HR'

    # Development/Engineering
    dev_keywords = ['dev', 'developers', 'engineering', 'eng', 'code', 'product', 'build',
                    'api', 'platform', 'integrations', 'webhooks', 'beta', 'sandbox',
                    'qa', 'testing', 'releases', 'deployment', 'version-control']
    if any(kw in email_lower for kw in dev_keywords):
        return 'Development'

    # IT/Operations
    it_keywords = ['it', 'itsupport', 'helpdesk-internal', 'sysadmin', 'admin',
                   'ops', 'operations', 'devops', 'infrastructure', 'cloud', 'network',
                   'security', 'soc', 'abuse', 'noc', 'infosec', 'privacy-ops',
                   'facilities', 'office', 'workplace', 'procurement', 'supply-chain']
    if any(kw in email_lower for kw in it_keywords):
        return 'IT/Operations'

    # Legal/Compliance
    legal_keywords = ['legal', 'counsel', 'law', 'contracts', 'agreements',
                      'compliance', 'privacy', 'dpo', 'gdpr', 'terms', 'tos', 'policy',
                      'trademarks', 'ip', 'copyright', 'patents', 'dmca']
    if any(kw in email_lower for kw in legal_keywords):
        return 'Legal/Compliance'

    # Executive
    exec_keywords = ['ceo', 'founder', 'founders', 'co-founder', 'president', 'md',
                     'cto', 'cfo', 'coo', 'cmo', 'cro', 'cpo', 'clo',
                     'executive', 'leadership', 'board', 'vps', 'directors',
                     'ea', 'pa', 'exec-assistant', 'office-of-the-ceo']
    if any(kw in email_lower for kw in exec_keywords):
        return 'Executive'

    # General/Info
    general_keywords = ['info', 'hello', 'hi', 'contact', 'general', 'inquiry']
    if any(kw in email_lower for kw in general_keywords):
        return 'General/Info'

    return 'Other'

# ==================== PROCESSING FUNCTIONS ====================

def process_single_domain(domain, progress_callback=None):
    """Process a single domain: fetch, classify, extract emails"""
    try:
        # Fetch content
        html_content, final_url, status_code = fetch_domain_content(domain)

        if status_code == 0:
            return {
                'domain': domain,
                'status': 'Failed to fetch',
                'category': 'Parked/Invalid',
                'score': 0,
                'emails': []
            }

        # Classify domain
        category, score, signals = classify_domain(domain, html_content)

        # Extract emails
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

# ==================== MAIN APP UI ====================

st.title("🔍 DomainLense")
st.markdown("**Bulk domain classification + email extraction for backlink outreach**")
st.markdown("---")

# Sidebar: Tips
with st.sidebar:
    st.markdown("### 💡 Backlink & Outreach Tips")
    tips = [
        "**Target editorial sites** with high domain authority for quality backlinks.",
        "**Personalize emails** with the recipient's name and reference their content.",
        "**Check domain metrics** (DA/Spam Score) before outreach to ensure quality.",
        "**Focus on relationships** over transactions—build partnerships, not just links.",
        "**Follow up once** after 5-7 days, but avoid being pushy or spammy.",
        "**Use specific anchors** like 'related to your article on X' for natural link insertion."
    ]
    for i, tip in enumerate(tips, 1):
        st.markdown(f"{i}. {tip}")

    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    max_workers = st.slider("Parallel processing threads", 1, 10, 5)
    timeout = st.slider("Request timeout (seconds)", 5, 30, 10)

# Input section
st.subheader("📥 Input Domains")

input_method = st.radio("Choose input method:", ["Paste URLs/Domains", "Upload File (CSV/TXT)"])

domains_list = []

if input_method == "Paste URLs/Domains":
    domains_input = st.text_area("Enter URLs or domains (one per line or comma-separated)", height=150,
                                  placeholder="example.com\nhttps://another-site.com\nthird-domain.org")
    if domains_input:
        domains_list = [d.strip() for d in re.split(r'[,\n]', domains_input) if d.strip()]
else:
    uploaded_file = st.file_uploader("Upload CSV or TXT file with domains/URLs", type=['csv', 'txt'])
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            df_upload = pd.read_csv(uploaded_file)
            domains_list = df_upload.iloc[:, 0].astype(str).tolist()
        else:
            content = uploaded_file.read().decode('utf-8')
            domains_list = [d.strip() for d in content.split('\n') if d.strip()]

# Clean domains
def clean_domain(url):
    """Extract clean domain from URL"""
    if not url.startswith('http'):
        url = 'http://' + url
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    return domain.replace('www.', '')

if len(domains_list) > 0:
    st.info(f"✅ {len(domains_list)} domains ready to analyze")

# Analysis button
if st.button("🚀 Start Analysis", type="primary", disabled=len(domains_list) == 0):
    domains_list = [clean_domain(d) for d in domains_list if d]
    domains_list = list(set(domains_list))  # Remove duplicates

    st.markdown("---")
    st.subheader("🔄 Processing...")

    # Progress containers
    progress_bar = st.progress(0)
    status_text = st.empty()
    step_status = st.empty()

    # Steps
    steps = [
        "1️⃣ Parsing input domains",
        "2️⃣ Fetching & classifying domains",
        "3️⃣ Extracting emails from pages",
        "4️⃣ Classifying emails by department",
        "5️⃣ Finalizing results"
    ]

    # Step 1
    step_status.markdown(f"### {steps[0]} ✅")
    time.sleep(0.5)
    progress_bar.progress(0.2)

    # Step 2-3: Process domains in parallel
    step_status.markdown(f"### {steps[1]} ⏳")

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
            status_text.text(f"Processed {processed_count}/{len(domains_list)} domains...")

    step_status.markdown(f"### {steps[1]} ✅")
    step_status.markdown(f"### {steps[2]} ✅")

    # Step 4: Classify emails
    step_status.markdown(f"### {steps[3]} ⏳")
    progress_bar.progress(0.8)

    rows = []
    for res in results:
        if res['emails']:
            for email in res['emails']:
                dept = classify_email_department(email)
                rows.append({
                    'Domain': res['domain'],
                    'Domain Category': res['category'],
                    'Domain Score': res['score'],
                    'Email': email,
                    'Department': dept,
                    'Status': res['status']
                })
        else:
            # Keep domain even if no emails found
            rows.append({
                'Domain': res['domain'],
                'Domain Category': res['category'],
                'Domain Score': res['score'],
                'Email': 'No emails found',
                'Department': 'N/A',
                'Status': res['status']
            })

    st.session_state.results_df = pd.DataFrame(rows)

    # Step 5: Complete
    step_status.markdown(f"### {steps[3]} ✅")
    step_status.markdown(f"### {steps[4]} ✅")
    progress_bar.progress(1.0)
    status_text.success(f"✅ Analysis complete! Processed {len(domains_list)} domains and found {len([r for r in rows if r['Email'] != 'No emails found'])} emails.")

# Display results
if st.session_state.results_df is not None:
    df = st.session_state.results_df

    st.markdown("---")
    st.subheader("📊 Results Dashboard")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Domains", df['Domain'].nunique())
    with col2:
        valid_emails = df[df['Email'] != 'No emails found']
        st.metric("Total Emails", len(valid_emails))
    with col3:
        st.metric("Departments Found", df['Department'].nunique())
    with col4:
        avg_score = df['Domain Score'].mean()
        st.metric("Avg Domain Score", f"{avg_score:.1f}")

    # Category breakdown
    st.markdown("### 📈 Domain Category Breakdown")
    category_counts = df['Domain Category'].value_counts()
    st.bar_chart(category_counts)

    # Filters
    st.markdown("---")
    st.markdown("### 🔍 Filter Results")
    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        selected_categories = st.multiselect(
            "Filter by Domain Category",
            options=sorted(df['Domain Category'].unique()),
            default=[]
        )

    with col_f2:
        selected_depts = st.multiselect(
            "Filter by Department",
            options=sorted(df['Department'].unique()),
            default=[]
        )

    with col_f3:
        min_score = st.slider("Minimum Domain Score", 0, 100, 0)

    # Apply filters
    filtered_df = df.copy()
    if selected_categories:
        filtered_df = filtered_df[filtered_df['Domain Category'].isin(selected_categories)]
    if selected_depts:
        filtered_df = filtered_df[filtered_df['Department'].isin(selected_depts)]
    filtered_df = filtered_df[filtered_df['Domain Score'] >= min_score]

    st.info(f"📧 Showing **{len(filtered_df)}** results after filtering")

    # Display table
    st.markdown("### 📋 Outreach Contacts")

    for idx, row in filtered_df.iterrows():
        if row['Email'] == 'No emails found':
            continue

        with st.expander(f"📧 {row['Email']} - {row['Domain']}"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**Domain:** {row['Domain']}")
                st.write(f"**Category:** {row['Domain Category']}")
                st.write(f"**Score:** ⭐ {row['Domain Score']}/100")
            with col_b:
                st.write(f"**Email:** {row['Email']}")
                st.write(f"**Department:** {row['Department']}")
                st.write(f"**Status:** {row['Status']}")

            if st.button("✉️ Write Link Insert Email", key=f"email_{idx}"):
                st.session_state.active_row = row
                st.session_state.show_email_form = True
                st.rerun()

    # Export button
    st.markdown("---")
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Results (CSV)",
        data=csv,
        file_name=f"DomainLense_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        type="primary"
    )

# Email form
if st.session_state.show_email_form and st.session_state.active_row is not None:
    row = st.session_state.active_row

    st.markdown("---")
    st.subheader("✉️ Link Insert Outreach Email")

    col_form1, col_form2 = st.columns([2, 1])

    with col_form1:
        recipient_name = st.text_input("Recipient Name", row['Email'].split('@')[0].title())

        subject = st.text_input(
            "Subject Line",
            f"Link Opportunity for {row['Domain']}"
        )

        body = st.text_area(
            "Email Body",
            f"""Hi {recipient_name},

I hope this email finds you well! I'm reaching out because I recently came across {row['Domain']} and was impressed by your content.

I have a resource that I believe would add significant value to your readers:

[Your resource title and brief description]
[Link to your resource]

I think this would be a great fit for [specific article or page on their site]. Would you be open to including a link to this resource in a relevant post?

I'm happy to discuss how we can make this mutually beneficial. Looking forward to hearing from you!

Best regards,
Arun Chaudhary
Marketer at KrispCall
""",
            height=300
        )

    with col_form2:
        st.markdown("**Contact Info:**")
        st.write(f"**Domain:** {row['Domain']}")
        st.write(f"**Email:** {row['Email']}")
        st.write(f"**Department:** {row['Department']}")
        st.write(f"**Category:** {row['Domain Category']}")
        st.write(f"**Score:** {row['Domain Score']}/100")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("📋 Copy Email to Clipboard", use_container_width=True):
            st.code(f"To: {row['Email']}\nSubject: {subject}\n\n{body}")
            st.success("✅ Email ready to copy!")

    with col_btn2:
        if st.button("❌ Close", use_container_width=True):
            st.session_state.show_email_form = False
            st.session_state.active_row = None
            st.rerun()
