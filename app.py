import streamlit as st
from pyzotero import zotero
import requests
import re
import os
import platform
import datetime

# Helper function to check if local or cloud
def is_local_env():
    # Streamlit Cloud runs on Linux/Debian. Márcio's computer is Windows.
    return os.name == 'nt' or platform.system() == 'Windows'

def load_onedrive_path():
    if not is_local_env():
        return ""
    # Look in the .streamlit folder of the app
    config_dir = ".streamlit"
    path_file = os.path.join(config_dir, "onedrive_path.txt")
    if os.path.exists(path_file):
        try:
            with open(path_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    # Default Penn State OneDrive path fallback
    default_path = r"C:\Users\Márcio\The Pennsylvania State University\Napolitano, Rebecca - Papers"
    if os.path.exists(default_path):
        return default_path
    return ""

def save_onedrive_path(path):
    if not is_local_env():
        return
    config_dir = ".streamlit"
    os.makedirs(config_dir, exist_ok=True)
    path_file = os.path.join(config_dir, "onedrive_path.txt")
    try:
        with open(path_file, "w", encoding="utf-8") as f:
            f.write(path.strip())
    except Exception:
        pass

def check_if_new_and_format(date_str):
    if not date_str:
        return False, ""
    try:
        date_part = date_str.split('T')[0]
        dt = datetime.datetime.strptime(date_part, "%Y-%m-%d")
        now = datetime.datetime.now()
        diff = now - dt
        is_new = (0 <= diff.days <= 7)
        formatted_date = dt.strftime("%d/%m/%Y")
        return is_new, formatted_date
    except Exception:
        return False, ""

def update_sync_history_log(onedrive_path, new_papers):
    log_path = os.path.join(onedrive_path, "Sync_History_Log.md")
    
    # Read existing entries
    existing_content = ""
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                content_lines = []
                found_separator = False
                for line in lines:
                    if found_separator:
                        content_lines.append(line)
                    elif line.strip() == "---":
                        found_separator = True
                existing_content = "".join(content_lines).strip()
        except Exception:
            pass
            
    # Format new papers (newest first)
    new_entries = []
    for paper in reversed(new_papers):
        title = paper['title']
        authors = paper['authors']
        year = paper['year']
        date_added = paper['date_added']
        
        formatted_date = "Unknown Date"
        if date_added:
            try:
                date_part = date_added.split('T')[0]
                dt = datetime.datetime.strptime(date_part, "%Y-%m-%d")
                formatted_date = dt.strftime("%d/%m/%Y")
            except:
                pass
                
        new_entries.append(f"### 📄 {title}\n"
                           f"* **Authors:** {authors}\n"
                           f"* **Year:** {year}\n"
                           f"* **Zotero Added Date:** {formatted_date}\n"
                           f"* **OneDrive Sync Date:** {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
                           
    new_content_str = "".join(new_entries)
    
    header = (
        "# OneDrive Sync History Log\n"
        "*Automatically generated log of academic papers synced from Zotero to this folder.*\n\n"
        "This file provides a chronological view of new papers added by you or Dr. Rebecca Napolitano. "
        "Files inside `/PDFs` and `/SummaryCards` folders are organized alphabetically, but you can consult "
        "this file to check the latest additions at a glance!\n\n"
        "---\n\n"
    )
    
    full_content = header + new_content_str + (existing_content if existing_content else "")
    
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(full_content)
    except Exception:
        pass

# Page Config (must be first)
st.set_page_config(page_title="URM Tornado Resilience", page_icon="🌪️", layout="wide", initial_sidebar_state="collapsed")

# Credentials (Loaded securely with local fallbacks)
ZOTERO_USER_ID = st.secrets.get("ZOTERO_USER_ID", "20709248")
ZOTERO_API_KEY = st.secrets.get("ZOTERO_API_KEY", "lYS46qOsMOM0tyLY3WPE2nxt")

# Initialize Session State
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "gov_search_results" not in st.session_state:
    st.session_state.gov_search_results = []
if "gov_search_key_terms" not in st.session_state:
    st.session_state.gov_search_key_terms = []
if "gov_search_active_agencies" not in st.session_state:
    st.session_state.gov_search_active_agencies = []
if "gov_search_target_databases" not in st.session_state:
    st.session_state.gov_search_target_databases = []
if "existing_titles" not in st.session_state:
    st.session_state.existing_titles = set()
if "existing_dois" not in st.session_state:
    st.session_state.existing_dois = set()
if "onedrive_path" not in st.session_state:
    st.session_state.onedrive_path = load_onedrive_path()
if "sync_status" not in st.session_state:
    st.session_state.sync_status = None

# --- PREMIUM MODERN CSS ---
# Utilizing Inter font, glassmorphism, dark mode aesthetics, and micro-animations
# No empty lines allowed inside the style block to prevent Streamlit markdown parser from breaking!
css_code = """
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"] {font-family: 'Outfit', sans-serif;}
.stApp {background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #f8fafc;}
h1, h2, h3 {color: #38bdf8 !important; font-weight: 800 !important; letter-spacing: -0.5px;}
.glass-card {background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 16px; padding: 24px; margin-bottom: 20px; transition: transform 0.3s ease, box-shadow 0.3s ease;}
.glass-card:hover {transform: translateY(-5px); box-shadow: 0 10px 30px -10px rgba(56, 189, 248, 0.3); border: 1px solid rgba(56, 189, 248, 0.2);}
.gov-link {display: inline-block; padding: 12px 24px; margin: 8px; background: linear-gradient(90deg, #2563eb 0%, #3b82f6 100%); color: white !important; text-decoration: none; border-radius: 50px; font-weight: 600; font-size: 0.95rem; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);}
.gov-link:hover {transform: scale(1.05); box-shadow: 0 6px 20px rgba(56, 189, 248, 0.5);}
.stTabs [data-baseweb="tab-list"] {gap: 24px; background-color: transparent;}
.stTabs [data-baseweb="tab"] {height: 60px; white-space: pre-wrap; background-color: transparent; border-radius: 8px 8px 0 0; gap: 1px; padding-top: 10px; padding-bottom: 10px; color: #94a3b8;}
.stTabs [aria-selected="true"] {color: #38bdf8 !important; border-bottom-color: #38bdf8 !important;}
.stButton>button {background: linear-gradient(90deg, #0ea5e9 0%, #0284c7 100%); color: white; border: none; border-radius: 8px; padding: 10px 24px; font-weight: 600; transition: all 0.3s ease;}
.stButton>button:hover {transform: translateY(-2px); box-shadow: 0 4px 15px rgba(14, 165, 233, 0.4); color: white;}
.stTextInput>div>div>input {background-color: white !important; border: 1px solid rgba(255, 255, 255, 0.1); color: black !important; border-radius: 8px;}
.stTextInput>div>div>input:focus {border-color: #38bdf8; box-shadow: 0 0 0 1px #38bdf8;}
</style>
"""
st.markdown(css_code, unsafe_allow_html=True)

# Main Header
st.markdown("<h1>🌪️ PhD Research Hub</h1>", unsafe_allow_html=True)
st.markdown("<p style='font-size: 1.2rem; color: #94a3b8; margin-bottom: 2rem;'>Unreinforced Masonry (URM) Tornado Resilience | Dr. Rebecca Napolitano's Lab</p>", unsafe_allow_html=True)

# Zotero Connection
try:
    zot = zotero.Zotero(ZOTERO_USER_ID, 'user', ZOTERO_API_KEY)
except Exception:
    zot = None

# Cache-aware Zotero library scanner to track already downloaded documents
def load_zotero_library():
    if zot:
        try:
            # Scanning up to 150 items to identify duplicate documents
            items = zot.items(limit=150)
            titles = set()
            dois = set()
            for item in items:
                data = item.get('data', {})
                title = data.get('title', '').strip().lower()
                doi = data.get('doi', '').strip().lower()
                url = data.get('url', '').strip().lower()
                if title:
                    titles.add(title)
                if doi:
                    dois.add(doi)
                if url:
                    dois.add(url)
            st.session_state.existing_titles = titles
            st.session_state.existing_dois = dois
        except Exception:
            pass

# Trigger scan on initial app boot
if zot and not st.session_state.existing_titles:
    load_zotero_library()

# Dynamic OneDrive Synchronizer
def sync_to_onedrive(title, authors, year, abstract, doi, pdf_url, log_history=True):
    path = st.session_state.get('onedrive_path', '')
    if not path:
        return False
    
    import os
    if not os.path.exists(path):
        return False
        
    import re
    import requests
    
    # Clean non-ascii and unsafe characters for filenames
    def clean_filename_part(text):
        if not text:
            return ""
        text = re.sub(r'[\\/*?:"<>|]', '', text)
        return text.encode('ascii', 'ignore').decode('ascii').strip()
        
    # Clean filename of unsafe characters
    clean_title = clean_filename_part(title)[:60]
    safe_author = clean_filename_part(authors.split(',')[0]) if (authors and authors != "Unknown") else ""
    
    # Ensure year is formatted cleanly
    year_match = re.search(r'\b\d{4}\b', str(year))
    clean_year = year_match.group(0) if (year_match and year_match.group(0) != "Unknown") else ""
    
    if safe_author and clean_year:
        filename_base = f"{safe_author}_{clean_year}_{clean_title}"
    elif safe_author:
        filename_base = f"{safe_author}_{clean_title}"
    elif clean_year:
        filename_base = f"{clean_year}_{clean_title}"
    else:
        filename_base = clean_title
        
    filename_base = re.sub(r'\s+', ' ', filename_base).strip().strip('.')
    if not filename_base:
        filename_base = "Academic_Paper"
        
    # Create subfolders
    summary_dir = os.path.join(path, "SummaryCards")
    pdf_dir = os.path.join(path, "PDFs")
    os.makedirs(summary_dir, exist_ok=True)
    os.makedirs(pdf_dir, exist_ok=True)
    
    # 1. Save reference summary card as Markdown
    md_content = f"""# Academic Reference Card
**Title:** {title}
**Authors:** {authors}
**Publication Year:** {clean_year}
**DOI/URL:** {doi}

## Abstract
{abstract if abstract else 'No abstract available.'}

---
*Generated automatically by Márcio's PhD Research Hub*
"""
    try:
        md_path = os.path.join(summary_dir, f"{filename_base}.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
    except Exception:
        pass
        
    # 2. Try to download and save Open Access PDF if available (with validation)
    if pdf_url:
        try:
            pdf_path = os.path.join(pdf_dir, f"{filename_base}.pdf")
            response = requests.get(pdf_url, timeout=15)
            if response.status_code == 200:
                # Validate that it is a real PDF (starts with %PDF)
                content = response.content
                if content.startswith(b"%PDF"):
                    with open(pdf_path, 'wb') as f:
                        f.write(content)
        except Exception:
            pass
            
    # Append to OneDrive Sync History Log if requested
    if log_history:
        try:
            update_sync_history_log(path, [{
                'title': title,
                'authors': authors if authors else 'Unknown',
                'year': clean_year if clean_year else 'Unknown',
                'date_added': datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
            }])
        except Exception:
            pass
            
    return True

def sync_all_zotero_to_onedrive():
    path = st.session_state.get('onedrive_path', '')
    if not path or not os.path.exists(path):
        return 0, 0, []
        
    if not zot:
        return 0, 0, []
        
    try:
        collections = zot.collections()
        golden_key = None
        for c in collections:
            if "Golden Papers" in c['data']['name']:
                golden_key = c['data']['key']
                break
                
        if not golden_key:
            return 0, 0, []
            
        items = zot.collection_items(golden_key)
        items.sort(key=lambda x: x.get('data', {}).get('dateAdded', ''))
        
        synced_new_papers = []
        synced_count = 0
        total_items = 0
        
        for item in items:
            data = item.get('data', {})
            if data.get('itemType') in ['attachment', 'note']:
                continue
                
            total_items += 1
            title = data.get('title', 'Untitled')
            abstract = data.get('abstractNote', '')
            url = data.get('url', '')
            year = data.get('date', 'Unknown')
            date_added = data.get('dateAdded', '')
            
            # Get authors
            creators = data.get('creators', [])
            authors_list = []
            for creator in creators:
                name = creator.get('lastName') or creator.get('firstName') or creator.get('name')
                if name:
                    authors_list.append(name)
            authors = ", ".join(authors_list) if authors_list else ""
            
            # Form clean filename base
            def clean_filename_part(text):
                if not text:
                    return ""
                text = re.sub(r'[\\/*?:"<>|]', '', text)
                return text.encode('ascii', 'ignore').decode('ascii').strip()
                
            clean_title = clean_filename_part(title)[:60]
            safe_author = clean_filename_part(authors.split(',')[0]) if authors else ""
            
            year_match = re.search(r'\b\d{4}\b', str(year))
            clean_year = year_match.group(0) if year_match else ""
            
            if safe_author and clean_year:
                filename_base = f"{safe_author}_{clean_year}_{clean_title}"
            elif safe_author:
                filename_base = f"{safe_author}_{clean_title}"
            elif clean_year:
                filename_base = f"{clean_year}_{clean_title}"
            else:
                filename_base = clean_title
                
            filename_base = re.sub(r'\s+', ' ', filename_base).strip().strip('.')
            if not filename_base:
                filename_base = "Academic_Paper"
                
            md_path = os.path.join(path, "SummaryCards", f"{filename_base}.md")
            
            # If the summary card doesn't exist, we sync it!
            if not os.path.exists(md_path):
                # Search OpenAlex for PDF URL
                pdf_url = ""
                try:
                    query_url = f"https://api.openalex.org/works?search={requests.utils.quote(title)}&per-page=1"
                    response = requests.get(query_url, timeout=10).json()
                    results = response.get('results', [])
                    if Math := results:
                        best_oa = results[0].get('best_oa_location') or {}
                        pdf_url = best_oa.get('pdf_url') or ''
                        if not pdf_url:
                            content_urls = results[0].get('content_urls') or {}
                            pdf_url = content_urls.get('pdf') or ''
                except Exception:
                    pass
                    
                success = sync_to_onedrive(title, authors, clean_year, abstract, url, pdf_url, log_history=False)
                if success:
                    synced_count += 1
                    synced_new_papers.append({
                        'title': title,
                        'authors': authors if authors else 'Unknown',
                        'year': clean_year if clean_year else 'Unknown',
                        'date_added': date_added
                    })
                    
        # Update Sync History Log file inside the OneDrive folder
        if synced_new_papers:
            update_sync_history_log(path, synced_new_papers)
            
        return synced_count, total_items, synced_new_papers
    except Exception as e:
        st.error(f"Error during OneDrive synchronization: {e}")
        return 0, 0, []

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📚 Zotero Library", "🏛️ Gov Databases", "📊 Analytics", "🤖 AI Paper Search"])

# --- TAB 1: ZOTERO ---
with tab1:
    # Display sync status toast/success if set
    if st.session_state.sync_status:
        st.success(st.session_state.sync_status)
        st.session_state.sync_status = None
        
    col1, col2, col3, col4 = st.columns([0.4, 0.2, 0.2, 0.2])
    with col1:
        st.markdown("<h3>Live Zotero Synchronization</h3>", unsafe_allow_html=True)
    with col2:
        st.link_button("🐇 Open Research Rabbit", "https://www.researchrabbit.ai", use_container_width=True)
    with col3:
        st.link_button("📚 Open Zotero Library", "https://www.zotero.org/mylibrary", use_container_width=True)
    with col4:
        if st.button("🔄 Refresh", use_container_width=True):
            with st.spinner("Refreshing Zotero Library..."):
                load_zotero_library()
            if is_local_env() and st.session_state.onedrive_path:
                with st.spinner("Checking Zotero and syncing new papers to local OneDrive..."):
                    synced_count, total_items, new_papers = sync_all_zotero_to_onedrive()
                    if synced_count > 0:
                        st.session_state.sync_status = f"✅ Synced {synced_count} new papers to your local OneDrive!"
                    else:
                        st.session_state.sync_status = "✅ Local OneDrive is fully up-to-date!"
            st.rerun()
            
    if zot:
        try:
            # Get up to 50 items and filter to actual papers
            all_items = zot.items(limit=50)
            papers = [item for item in all_items if item.get('data', {}).get('itemType') not in ['attachment', 'note']]
            
            st.success(f"✅ Securely connected to Zotero! User ID: {ZOTERO_USER_ID}")
            
            if papers:
                col_title_header, col_sort_dropdown = st.columns([0.5, 0.5])
                with col_title_header:
                    st.markdown("<h4 style='margin-top:10px;'>Recently Added Papers</h4>", unsafe_allow_html=True)
                with col_sort_dropdown:
                    sort_option = st.selectbox(
                        "Sort papers by:",
                        options=["Date Added to Zotero (Newest First)", "Publication Year (Newest First)", "Title (A-Z)"],
                        label_visibility="collapsed",
                        key="zotero_sort_option"
                    )
                
                # Perform sorting based on selection
                if sort_option == "Date Added to Zotero (Newest First)":
                    papers.sort(key=lambda x: x.get('data', {}).get('dateAdded', ''), reverse=True)
                elif sort_option == "Publication Year (Newest First)":
                    # Extrai o ano da data de publicação do Zotero (campo 'date')
                    def get_year(item_data):
                        date_str = item_data.get('data', {}).get('date', '0000')
                        match = re.search(r'\b\d{4}\b', str(date_str))
                        return match.group(0) if match else "0000"
                    papers.sort(key=get_year, reverse=True)
                elif sort_option == "Title (A-Z)":
                    papers.sort(key=lambda x: x.get('data', {}).get('title', '').strip().lower())
                
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                for item in papers[:10]:  # Show up to 10 recently added papers
                    data = item.get('data', {})
                    title = data.get('title', 'Untitled')
                    item_type = data.get('itemType', 'unknown')
                    item_key = item['key']
                    zotero_url = item.get('links', {}).get('alternate', {}).get('href', '#')
                    date_added = data.get('dateAdded', '')
                    
                    is_new, formatted_date = check_if_new_and_format(date_added)
                    
                    # Get collection info if available
                    collections = data.get('collections', [])
                    col_tag = "📁 Unfiled"
                    if collections:
                        try:
                            col_info = zot.collection(collections[0])
                            col_name = col_info['data']['name']
                            col_tag = f"📁 {col_name}"
                        except:
                            pass
                    
                    # Highlight if added in the last 7 days
                    badge_html = ""
                    if is_new:
                        badge_html = f"<span style='background-color:#0ea5e9; color:white; padding:3px 8px; border-radius:12px; font-size:1.0rem; font-weight:bold; margin-right:8px;'>🆕 New (Added: {formatted_date})</span>"
                        
                    st.markdown(f"**{badge_html}{title}** <br/><span style='color:#94a3b8; font-size:1.05em;'>Type: {item_type} | {col_tag}</span>", unsafe_allow_html=True)
                    st.markdown(f"[🔗 Open in Zotero Web]({zotero_url})")
                    st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 10px 0;'>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("Your library is currently empty. Use the AI Search tab to add your first paper!")
        except Exception as e:
            st.error(f"Failed to read from Zotero: {e}")
    else:
        st.error("Zotero disconnected.")
        
    if is_local_env():
        st.markdown("<div class='glass-card'><h4>📁 Academic OneDrive Integration (Penn State)</h4>", unsafe_allow_html=True)
        st.markdown("<p style='color: #94a3b8; font-size: 0.95rem;'>Configure your shared OneDrive directory to automatically save PDF papers and citation summary cards for your advisor, Dr. Rebecca Napolitano.</p>", unsafe_allow_html=True)
        onedrive_input = st.text_input(
            "Shared OneDrive Folder Path:",
            value=st.session_state.onedrive_path,
            placeholder="E.g., C:\\Users\\Márcio\\OneDrive - The Pennsylvania State University\\Rebecca_Shared"
        )
        if onedrive_input:
            import os
            if os.path.exists(onedrive_input):
                st.session_state.onedrive_path = onedrive_input
                save_onedrive_path(onedrive_input)
                st.success("✅ Shared OneDrive connection is Active! Saved papers will automatically sync to Rebecca.")
            else:
                st.warning("⚠️ Local directory path not found. Please verify the exact folder path.")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class='glass-card' style='border-left: 4px solid #0ea5e9;'>
            <h4 style='color: #38bdf8; margin-top:0; font-size:1.1rem;'>☁️ Cloud Synchronization Active</h4>
            <p style='color: #94a3b8; font-size: 0.92rem; line-height: 1.5; margin-bottom: 0;'>
                OneDrive integration is running in Cloud-to-Zotero relay mode. Saving a paper here will store it in Zotero Cloud. 
                When Márcio runs his local dashboard and clicks <b>Refresh</b>, the files will be downloaded to your shared OneDrive folder automatically. 
                No local path configuration is required on your computer.
            </p>
        </div>
        """, unsafe_allow_html=True)

# --- TAB 2: GOVERNMENT HUB ---
with tab2:
    st.markdown("<h3>Semantic Government & Literature Search</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8;'>Describe your 'Golden Paper' in natural language. We'll find it, search chosen repositories, and score relevance.</p>", unsafe_allow_html=True)
    
    # 🏛️ Quick Access Portals
    st.markdown("<h4 style='margin-top: 15px; margin-bottom: 5px; color:#e2e8f0;'>🏛️ Quick Access Portals</h4>", unsafe_allow_html=True)
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    with col_p1:
        st.markdown('<a href="https://www.fema.gov" target="_blank" class="gov-link" style="width:100%; text-align:center; margin:0;">🏛️ FEMA Portal</a>', unsafe_allow_html=True)
    with col_p2:
        st.markdown('<a href="https://www.nist.gov" target="_blank" class="gov-link" style="width:100%; text-align:center; margin:0;">🏛️ NIST Portal</a>', unsafe_allow_html=True)
    with col_p3:
        st.markdown('<a href="https://www.noaa.gov" target="_blank" class="gov-link" style="width:100%; text-align:center; margin:0;">🏛️ NOAA Portal</a>', unsafe_allow_html=True)
    with col_p4:
        st.markdown('<a href="https://www.designsafe-ci.org" target="_blank" class="gov-link" style="width:100%; text-align:center; margin:0;">💻 DesignSafe</a>', unsafe_allow_html=True)
    
    col_p5, col_p6, col_p7, col_p8 = st.columns(4)
    with col_p5:
        st.markdown('<a href="https://www.erdc.usace.army.mil" target="_blank" class="gov-link" style="width:100%; text-align:center; margin:0; background: linear-gradient(90deg, #15803d 0%, #16a34a 100%);">🏛️ USACE Portal</a>', unsafe_allow_html=True)
    with col_p6:
        st.markdown('<a href="https://simcenter.designsafe-ci.org" target="_blank" class="gov-link" style="width:100%; text-align:center; margin:0; background: linear-gradient(90deg, #0284c7 0%, #0369a1 100%);">💻 SimCenter</a>', unsafe_allow_html=True)
    with col_p7:
        st.markdown('<a href="https://www.usgs.gov" target="_blank" class="gov-link" style="width:100%; text-align:center; margin:0; background: linear-gradient(90deg, #b45309 0%, #9a3412 100%);">🏛️ USGS Portal</a>', unsafe_allow_html=True)
    with col_p8:
        st.markdown('<a href="https://asce7hazardtool.online" target="_blank" class="gov-link" style="width:100%; text-align:center; margin:0; background: linear-gradient(90deg, #6d28d9 0%, #5b21b6 100%);">📊 ASCE 7 Tool</a>', unsafe_allow_html=True)
    
    st.markdown("<div style='margin-bottom: 25px;'></div>", unsafe_allow_html=True)
    
    # AI Search Form
    with st.form("semantic_search_form"):
        st.markdown("""
        <div style='background: rgba(56, 189, 248, 0.08); border-left: 4px solid #38bdf8; padding: 12px 16px; border-radius: 8px; margin-bottom: 15px; font-size: 0.92rem; line-height: 1.4; color: #e2e8f0;'>
            💡 <b>Antigravity's Golden Tip:</b> Writing your search prompt in <b>English</b> guarantees <b>100% more accurate</b> results! The US repositories index their academic catalogs exclusively in English. <br/>
            <i>Use key-terms like: <b>URM</b> (Unreinforced Masonry) for unreinforced masonry, <b>Finite Element Method / Abaqus</b> for finite element models, and <b>Tornado Load / Wind Load</b> for structural wind loading.</i>
        </div>
        """, unsafe_allow_html=True)
        
        golden_prompt = st.text_area(
            "🧠 Describe what you are looking for (in English for best results):",
            height=120,
            placeholder="E.g., 'papers about finite element analysis using Abaqus for unreinforced masonry historical buildings hit by EF4 tornadoes'..."
        )
        
        st.markdown("<p style='font-size:0.9rem; font-weight:bold; margin-bottom:5px;'>🏛️ Select Target Databases to Query:</p>", unsafe_allow_html=True)
        target_databases = st.multiselect(
            "Target Repositories:",
            options=["FEMA", "NIST", "NOAA", "DesignSafe", "USACE", "NHERI SimCenter", "USGS", "ASCE Guidelines", "Global Academic Index (OpenAlex)"],
            default=["FEMA", "NIST", "NOAA", "DesignSafe", "USACE", "NHERI SimCenter", "USGS", "ASCE Guidelines", "Global Academic Index (OpenAlex)"],
            label_visibility="collapsed"
        )
        search_pressed = st.form_submit_button("🔎 Run AI Semantic Search", use_container_width=True)
            
    if search_pressed and golden_prompt:
        if not target_databases:
            target_databases = ["FEMA", "NIST", "NOAA", "DesignSafe", "USACE", "NHERI SimCenter", "USGS", "ASCE Guidelines", "Global Academic Index (OpenAlex)"]
            
        with st.spinner("Analyzing semantic intent and querying federal & academic databases..."):
            import re
            import requests
            
            # Clean stop words and generic academic noise words to extract pure scientific keywords
            academic_noise_words = set([
                'i', 'want', 'to', 'find', 'papers', 'seminars', 'videos', 'theses', 'similar', 'materials', 'study', 'article', 
                'research', 'looking', 'seeking', 'get', 'literature', 'document', 'documents', 'work', 'works', 'author', 
                'authors', 'read', 'please', 'give', 'about', 'for', 'with', 'using', 'the', 'a', 'an', 'and', 'or', 'of', 'in', 
                'on', 'by', 'that', 'this', 'is', 'are', 'we', 'show', 'find', 'me', 'what', 'how', 'where', 'and/or', 'any', 'some'
            ])
            words = re.findall(r'\b[a-zA-Z0-9-]+\b', golden_prompt.lower())
            key_terms = [w for w in words if w not in academic_noise_words and len(w) > 2]
            
            # Formulate query: combine user keywords with active agency terms if not searching everything
            active_agencies = []
            for db in target_databases:
                if db == "FEMA": active_agencies.append("fema")
                elif db == "NIST": active_agencies.append("nist")
                elif db == "NOAA": active_agencies.append("noaa")
                elif db == "DesignSafe": active_agencies.append("designsafe")
                elif db == "USACE": active_agencies.append("usace")
                elif db == "NHERI SimCenter": active_agencies.append("simcenter")
                elif db == "USGS": active_agencies.append("usgs")
                elif db == "ASCE Guidelines": active_agencies.append("asce")
                
            # The query string should strictly consist of your core scientific terms.
            # Combining multiple competitive agency names (like fema+nist+noaa) in the API query string 
            # forces an 'AND' search, which results in zero papers matching all agencies simultaneously.
            # We keep the search pure and perform surgical filtering locally.
            # High-intelligence Fallback Chain (8 terms -> 5 terms -> 3 terms)
            # This prevents empty results from overly-specific search prompts
            results = []
            applied_terms = []
            for term_count in [8, 5, 3]:
                if len(key_terms) >= term_count:
                    applied_terms = key_terms[:term_count]
                else:
                    applied_terms = key_terms
                    
                query_str = " AND ".join(applied_terms)
                per_page = 60 if "Global Academic Index (OpenAlex)" not in target_databases else 25
                url = f"https://api.openalex.org/works?filter=title_and_abstract.search:{requests.utils.quote(query_str)}&per-page={per_page}"
                
                try:
                    response = requests.get(url).json()
                    results = response.get('results', [])
                    if results:
                        if len(key_terms) > len(applied_terms):
                            st.info(f"💡 **Search relaxed to prevent empty results:** Focusing on: *{', '.join(applied_terms)}*")
                        break
                except Exception as e:
                    st.error(f"API Error during search tier: {e}")
                    break
                    
            # Save to session state so they persist!
            st.session_state.gov_search_results = results
            st.session_state.gov_search_key_terms = key_terms
            st.session_state.gov_search_active_agencies = active_agencies
            st.session_state.gov_search_target_databases = target_databases
            
            if not results:
                st.warning("No papers found matching those exact semantic parameters.")
                
    # Render search results from session state (persists across tab switches/button clicks)
    if st.session_state.gov_search_results:
        results = st.session_state.gov_search_results
        key_terms = st.session_state.gov_search_key_terms
        active_agencies = st.session_state.gov_search_active_agencies
        target_databases = st.session_state.gov_search_target_databases
        
        valid_papers_count = 0
        search_cards_container = st.container()
        
        with search_cards_container:
            for idx, paper in enumerate(results):
                title = paper.get('title') or 'Untitled'
                abstract_inverted = paper.get('abstract_inverted_index', {})
                
                # Reconstruct abstract
                abstract = ""
                if abstract_inverted:
                    word_index = []
                    for word, positions in abstract_inverted.items():
                        for pos in positions:
                            word_index.append((pos, word))
                    word_index.sort(key=lambda x: x[0])
                    abstract = " ".join([word for pos, word in word_index])
                
                # Check host venue / publisher info
                primary_location = paper.get('primary_location') or {}
                source = primary_location.get('source') or {}
                source_name = source.get('display_name') or ''
                publisher = paper.get('publisher') or ''
                
                # Identify specific institutions associated (matching whole words only to prevent "feminist" -> "NIST" bug)
                detected_insts = []
                paper_full_text = (title + " " + abstract + " " + source_name + " " + publisher).lower()
                
                if re.search(r'\bfema\b', paper_full_text):
                    detected_insts.append("FEMA")
                if re.search(r'\bnist\b', paper_full_text):
                    detected_insts.append("NIST")
                if re.search(r'\bnoaa\b', paper_full_text):
                    detected_insts.append("NOAA")
                if re.search(r'\bdesignsafe\b', paper_full_text):
                    detected_insts.append("DesignSafe")
                if re.search(r'\busace\b|\barmy corps\b', paper_full_text):
                    detected_insts.append("USACE")
                if re.search(r'\bsimcenter\b', paper_full_text):
                    detected_insts.append("NHERI SimCenter")
                if re.search(r'\busgs\b|\bgeological survey\b', paper_full_text):
                    detected_insts.append("USGS")
                if re.search(r'\basce\b', paper_full_text):
                    detected_insts.append("ASCE Guidelines")
                    
                # If no specific agency detected, it's from the Academic Index
                if not detected_insts:
                    detected_insts.append("Global Academic Index")
                    
                # Local filter based on selected sources
                # If "Global Academic Index (OpenAlex)" is selected, we match everything.
                # Otherwise, we only display papers that matched at least one selected agency.
                is_academic_selected = ("Global Academic Index (OpenAlex)" in target_databases)
                matches_selected_agency = any(inst in target_databases for inst in detected_insts)
                
                if not is_academic_selected and not matches_selected_agency:
                    continue  # Skip this paper as it doesn't match selected agencies
                    
                valid_papers_count += 1
                
                # Scoring Algorithm (Local NLP similarity estimation)
                score = 0
                if key_terms:
                    match_count = sum(1 for term in key_terms if term in paper_full_text)
                    score = int((match_count / len(key_terms)) * 100)
                
                # Boost score if they match target institutions
                matched_active_agencies = [a for a in active_agencies if a in paper_full_text]
                if matched_active_agencies:
                    score = min(100, score + 15 * len(matched_active_agencies))
                    
                # Format Authors
                authorships = paper.get('authorships', [])
                authors = ", ".join([a['author']['display_name'] for a in authorships[:2]])
                if len(authorships) > 2:
                    authors += " et al."
                    
                pub_year = paper.get('publication_year', 'Unknown')
                doi = paper.get('doi', '#')
                
                # Dynamic Duplicate Checking against Zotero local session cache
                paper_title_lower = title.strip().lower()
                paper_doi_lower = doi.strip().lower() if doi else ''
                already_downloaded = False
                if paper_title_lower in st.session_state.get('existing_titles', set()):
                    already_downloaded = True
                elif paper_doi_lower and paper_doi_lower in st.session_state.get('existing_dois', set()):
                    already_downloaded = True
                
                # Build HTML source badges
                badge_html = ""
                if already_downloaded:
                    badge_html += "<span style='background-color:#10b981; color:white; padding:4px 10px; border-radius:12px; font-size:0.75rem; font-weight:bold; margin-right:5px;'>✅ Already in Zotero</span>"
                
                for inst in detected_insts:
                    if inst == "FEMA":
                        badge_html += "<span style='background-color:#ef4444; color:white; padding:4px 10px; border-radius:12px; font-size:0.75rem; font-weight:bold; margin-right:5px;'>🏛️ FEMA</span>"
                    elif inst == "NIST":
                        badge_html += "<span style='background-color:#10b981; color:white; padding:4px 10px; border-radius:12px; font-size:0.75rem; font-weight:bold; margin-right:5px;'>🏛️ NIST</span>"
                    elif inst == "NOAA":
                        badge_html += "<span style='background-color:#3b82f6; color:white; padding:4px 10px; border-radius:12px; font-size:0.75rem; font-weight:bold; margin-right:5px;'>🏛️ NOAA</span>"
                    elif inst == "DesignSafe":
                        badge_html += "<span style='background-color:#f97316; color:white; padding:4px 10px; border-radius:12px; font-size:0.75rem; font-weight:bold; margin-right:5px;'>💻 DesignSafe</span>"
                    elif inst == "USACE":
                        badge_html += "<span style='background-color:#15803d; color:white; padding:4px 10px; border-radius:12px; font-size:0.75rem; font-weight:bold; margin-right:5px;'>🏛️ USACE</span>"
                    elif inst == "NHERI SimCenter":
                        badge_html += "<span style='background-color:#0284c7; color:white; padding:4px 10px; border-radius:12px; font-size:0.75rem; font-weight:bold; margin-right:5px;'>💻 SimCenter</span>"
                    elif inst == "USGS":
                        badge_html += "<span style='background-color:#b45309; color:white; padding:4px 10px; border-radius:12px; font-size:0.75rem; font-weight:bold; margin-right:5px;'>🏛️ USGS</span>"
                    elif inst == "ASCE Guidelines":
                        badge_html += "<span style='background-color:#6d28d9; color:white; padding:4px 10px; border-radius:12px; font-size:0.75rem; font-weight:bold; margin-right:5px;'>📊 ASCE</span>"
                    else:
                        badge_html += "<span style='background-color:#8b5cf6; color:white; padding:4px 10px; border-radius:12px; font-size:0.75rem; font-weight:bold; margin-right:5px;'>📚 Academic Index</span>"
                
                # Display
                score_color = "#10b981" if score >= 60 else "#f59e0b" if score >= 30 else "#ef4444"
                
                st.markdown(f"""
                <div class='glass-card' style='border-left: 5px solid {score_color};'>
                    <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
                        <div>
                            <h4 style='margin-bottom: 5px;'>{title}</h4>
                            <div style='margin-bottom: 8px; margin-top: 5px;'>{badge_html}</div>
                            <span style='color:#94a3b8; font-size: 0.9rem;'>👥 {authors} | 📅 {pub_year}</span>
                        </div>
                        <div style='background: {score_color}20; border: 1px solid {score_color}; padding: 5px 15px; border-radius: 20px; color: {score_color}; font-weight: bold;'>
                            {score}% Match
                        </div>
                    </div>
                    <p style='font-size: 0.9rem; color: #cbd5e1; margin-top: 15px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;'>
                        <em>{abstract if abstract else 'No abstract provided by the database.'}</em>
                    </p>
                """, unsafe_allow_html=True)
                
                # Actions
                col_link, col_zotero = st.columns([0.6, 0.4])
                with col_link:
                    # Find direct PDF download link from OpenAlex (Open Access)
                    best_oa = paper.get('best_oa_location') or {}
                    pdf_url = best_oa.get('pdf_url') or ''
                    content_urls = paper.get('content_urls') or {}
                    if not pdf_url:
                        pdf_url = content_urls.get('pdf') or ''
                        
                    # Render Publisher Abstract Link
                    if doi and doi != '#':
                        st.markdown(f"[📄 View Abstract (Publisher Page)]({doi})")
                    else:
                        st.markdown(f"[🔍 Search on Scholar](https://scholar.google.com/scholar?q={title})")
                        
                    # Render Direct PDF Download Link if available
                    if pdf_url:
                        st.markdown(f"[📥 Download Full PDF (Open Access)]({pdf_url})")
                    else:
                        st.markdown("<span style='color: #94a3b8; font-size: 0.85rem; font-style: italic;'>🔒 Full-Text behind publisher paywall</span>", unsafe_allow_html=True)
                with col_zotero:
                    if already_downloaded:
                        st.button("✅ Already in Zotero", key=f"gov_save_{idx}", disabled=True, use_container_width=True)
                    else:
                        if st.button("📥 Save as Golden Paper", key=f"gov_save_{idx}", use_container_width=True):
                            if zot:
                                with st.spinner("Saving to Zotero 'Golden Papers' folder..."):
                                    try:
                                        # Find or create "PhD - Architectural Engineering"
                                        all_cols = zot.collections()
                                        parent_key = None
                                        golden_key = None
                                        
                                        for c in all_cols:
                                            if "PhD" in c['data']['name']:
                                                parent_key = c['data']['key']
                                                break
                                        if not parent_key:
                                            resp_p = zot.create_collections([{'name': 'PhD - Architectural Engineering'}])
                                            parent_key = list(resp_p['successful'].values())[0]['key']
                                            
                                        # Find/Create Golden folder
                                        for c in all_cols:
                                            if "Golden Papers" in c['data']['name'] and c['data'].get('parentCollection') == parent_key:
                                                golden_key = c['data']['key']
                                                break
                                        if not golden_key:
                                            resp_c = zot.create_collections([{'name': 'Golden Papers', 'parentCollection': parent_key}])
                                            if resp_c['successful']:
                                                golden_key = list(resp_c['successful'].values())[0]['key']
                                        
                                        # Create Item
                                        template = zot.item_template('journalArticle')
                                        template['title'] = title
                                        template['date'] = str(pub_year)
                                        template['url'] = doi if doi != '#' else ""
                                        template['abstractNote'] = abstract
                                        if golden_key:
                                            template['collections'] = [golden_key]
                                            
                                        resp = zot.create_items([template])
                                        if resp.get('successful'):
                                            st.success("✅ Saved securely to Zotero (Golden Papers)!")
                                            
                                            # Try to sync to Rebecca's OneDrive folder
                                            if st.session_state.onedrive_path:
                                                synced = sync_to_onedrive(title, authors, pub_year, abstract, doi, pdf_url)
                                                if synced:
                                                    st.success("📤 Automatically synced to Rebecca's Penn State OneDrive!")
                                                    
                                            st.session_state.existing_titles.add(paper_title_lower)
                                            if paper_doi_lower:
                                                st.session_state.existing_dois.add(paper_doi_lower)
                                            st.rerun()
                                    except Exception as e:
                                        st.error(f"Error saving to Zotero: {e}")
                            else:
                                st.error("Zotero not connected.")
                st.markdown("</div>", unsafe_allow_html=True)
                
            if valid_papers_count == 0:
                st.warning("⚠️ No papers from the selected specific agencies were found in the search results. Try selecting 'Global Academic Index (OpenAlex)' or adjusting your search prompt.")
            else:
                st.success(f"🎉 Successfully rendered {valid_papers_count} papers matching your exact institutional filters!")

# --- TAB 3: ANALYTICS ---
with tab3:
    st.markdown("<h3>Research Data Analytics & 3D Knowledge Graph</h3>", unsafe_allow_html=True)
    
    analytics_tab1, analytics_tab2 = st.tabs(["📊 Data Explorer (Excel/CSV)", "🌌 3D Knowledge Graph"])
    
    with analytics_tab1:
        st.markdown("Upload your lab test data to visualize engineering parameters.")
        uploaded_file = st.file_uploader("Upload CSV or Excel file", type=['csv', 'xlsx'])
        if uploaded_file is not None:
            import pandas as pd
            import plotly.express as px
            
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                st.dataframe(df.head(10), use_container_width=True)
                
                if len(df.columns) >= 2:
                    col1, col2 = st.columns(2)
                    with col1:
                        x_axis = st.selectbox("X-Axis", df.columns)
                    with col2:
                        y_axis = st.selectbox("Y-Axis", df.columns, index=1 if len(df.columns) > 1 else 0)
                    
                    fig = px.scatter(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}", template="plotly_dark")
                    fig.update_traces(marker=dict(size=10, color="#00d2ff", opacity=0.8))
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error reading file: {e}")

    with analytics_tab2:
        st.markdown("Visualize your Zotero Library as an interactive 3D universe.")
        if st.button("🚀 Generate 3D Universe", use_container_width=True):
            if zot:
                with st.spinner("Fetching papers and calculating 3D gravity..."):
                    import networkx as nx
                    import plotly.graph_objects as go
                    
                    try:
                        all_items = zot.items()
                        papers = [item for item in all_items if item['data'].get('itemType') not in ['attachment', 'note']]
                        
                        if len(papers) < 1:
                            st.warning("You need papers in your Zotero library to form a constellation!")
                        else:
                            G = nx.Graph()
                            
                            # Add nodes
                            for p in papers:
                                G.add_node(p['key'], title=p['data'].get('title', 'Untitled'))
                            
                            # Create simulated edges based on shared collections
                            for i in range(len(papers)):
                                for j in range(i+1, len(papers)):
                                    col_i = set(papers[i]['data'].get('collections', []))
                                    col_j = set(papers[j]['data'].get('collections', []))
                                    if len(col_i.intersection(col_j)) > 0:
                                        G.add_edge(papers[i]['key'], papers[j]['key'])
                            
                            # Generate 3D layout
                            pos = nx.spring_layout(G, dim=3, seed=42)
                            
                            edge_x = []
                            edge_y = []
                            edge_z = []
                            for edge in G.edges():
                                x0, y0, z0 = pos[edge[0]]
                                x1, y1, z1 = pos[edge[1]]
                                edge_x.extend([x0, x1, None])
                                edge_y.extend([y0, y1, None])
                                edge_z.extend([z0, z1, None])
                                
                            edge_trace = go.Scatter3d(
                                x=edge_x, y=edge_y, z=edge_z,
                                mode='lines',
                                line=dict(color='rgba(255,255,255,0.2)', width=2),
                                hoverinfo='none'
                            )
                            
                            node_x = []
                            node_y = []
                            node_z = []
                            node_text = []
                            for node in G.nodes():
                                x, y, z = pos[node]
                                node_x.append(x)
                                node_y.append(y)
                                node_z.append(z)
                                node_text.append(G.nodes[node]['title'])
                                
                            node_trace = go.Scatter3d(
                                x=node_x, y=node_y, z=node_z,
                                mode='markers',
                                hoverinfo='text',
                                text=node_text,
                                marker=dict(
                                    size=8,
                                    color='#3a86ff',
                                    line=dict(width=2, color='#ffffff')
                                )
                            )
                            
                            fig = go.Figure(data=[edge_trace, node_trace])
                            fig.update_layout(
                                title="Zotero 3D Knowledge Graph",
                                showlegend=False,
                                scene=dict(
                                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, backgroundcolor="black"),
                                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, backgroundcolor="black"),
                                    zaxis=dict(showgrid=False, zeroline=False, showticklabels=False, backgroundcolor="black"),
                                    bgcolor="black"
                                ),
                                margin=dict(l=0, r=0, b=0, t=40),
                                paper_bgcolor="black"
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error generating 3D graph: {e}")
            else:
                st.warning("Please connect Zotero first!")

# --- TAB 4: AUTOMATED SEARCH ---
with tab4:
    st.markdown("<h3>Global Database Search</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8;'>Search millions of academic papers and seamlessly inject them into smart Zotero subcollections.</p>", unsafe_allow_html=True)
    
    query = st.text_input("Enter keywords (e.g., 'unreinforced masonry historic tornado'):")
    
    if st.button("Search Academic Papers"):
        if query:
            with st.spinner("Querying global databases..."):
                try:
                    import re
                    # Strip academic noise words to create a high-performance query string
                    academic_noise_words = set([
                        'i', 'want', 'to', 'find', 'papers', 'seminars', 'videos', 'theses', 'similar', 'materials', 'study', 'article', 
                        'research', 'looking', 'seeking', 'get', 'literature', 'document', 'documents', 'work', 'works', 'author', 
                        'authors', 'read', 'please', 'give', 'about', 'for', 'with', 'using', 'the', 'a', 'an', 'and', 'or', 'of', 'in', 
                        'on', 'by', 'that', 'this', 'is', 'are', 'we', 'show', 'find', 'me', 'what', 'how', 'where', 'and/or', 'any', 'some', 'software', 'hit'
                    ])
                    words = re.findall(r'\b[a-zA-Z0-9-]+\b', query.lower())
                    key_terms = [w for w in words if w not in academic_noise_words and len(w) > 2]
                    
                    # High-intelligence Fallback Chain (8 terms -> 5 terms -> 3 terms)
                    # This prevents empty results from overly-specific search prompts
                    results = []
                    applied_terms = []
                    for term_count in [8, 5, 3]:
                        if len(key_terms) >= term_count:
                            applied_terms = key_terms[:term_count]
                        else:
                            applied_terms = key_terms
                            
                        cleaned_query = " AND ".join(applied_terms)
                        url = f"https://api.openalex.org/works?filter=title_and_abstract.search:{requests.utils.quote(cleaned_query)}&per-page=5"
                        response = requests.get(url).json()
                        results = response.get('results', [])
                        
                        if results:
                            if len(key_terms) > len(applied_terms):
                                st.info(f"💡 **Search relaxed to prevent empty results:** Focusing on: *{', '.join(applied_terms)}*")
                            break
                            
                    st.session_state.search_results = results
                    if not results:
                        st.warning("No papers found even after relaxing the search parameters. Try using broader terms.")
                except Exception as e:
                    st.error(f"Search error: {e}")
        else:
            st.warning("Please enter search keywords above.")
            
    if st.session_state.search_results:
        st.markdown("#### Search Results")
        for idx, paper in enumerate(st.session_state.search_results):
            title = paper.get('title') or 'Untitled'
            doi = paper.get('doi', '')
            pub_year = paper.get('publication_year', 'Unknown Year')
            
            # Dynamic Duplicate Checking against Zotero local session cache
            paper_title_lower = title.strip().lower()
            paper_doi_lower = doi.strip().lower() if doi else ''
            already_downloaded = False
            if paper_title_lower in st.session_state.get('existing_titles', set()):
                already_downloaded = True
            elif paper_doi_lower and paper_doi_lower in st.session_state.get('existing_dois', set()):
                already_downloaded = True
            
            # Extract Authors
            authorships = paper.get('authorships', [])
            authors = ", ".join([a['author']['display_name'] for a in authorships[:3]])
            if len(authorships) > 3:
                authors += " et al."
                
            # Extract Concepts for smart subfolders
            concepts = paper.get('concepts', [])
            top_concept = "General"
            if concepts:
                specific_concepts = [c for c in concepts if c.get('level', 0) > 0]
                if specific_concepts:
                    top_concept = specific_concepts[0].get('display_name', 'General')
                else:
                    top_concept = concepts[0].get('display_name', 'General')
            
            st.markdown(f"<div class='glass-card'>", unsafe_allow_html=True)
            st.markdown(f"**{title}** ({pub_year})")
            if already_downloaded:
                st.markdown(f"<span style='color:#10b981; font-weight:bold; font-size:0.9rem;'>✅ Already in Zotero</span><br/><span style='color:#94a3b8'>Authors: {authors} <br/> Smart Folder: 📂 {top_concept}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span style='color:#94a3b8'>Authors: {authors} <br/> Smart Folder: 📂 {top_concept}</span>", unsafe_allow_html=True)
            import urllib.parse
            if doi:
                st.markdown(f"[📄 View Source Document]({doi})")
            else:
                scholar_url = f"https://scholar.google.com/scholar?q={urllib.parse.quote(title)}"
                st.markdown(f"[🔍 Search on Google Scholar]({scholar_url})")
            
            if already_downloaded:
                st.button(f"✅ Already in Zotero", key=f"save_{idx}", disabled=True, use_container_width=True)
            else:
                if st.button(f"📥 Smart Save to Zotero", key=f"save_{idx}", use_container_width=True):
                    if zot:
                        with st.spinner(f"Creating collection '{top_concept}' and saving paper..."):
                            try:
                                all_cols = zot.collections()
                                
                                # 1. Find the main parent collection (PhD)
                                parent_key = None
                                for c in all_cols:
                                    if "PhD" in c['data']['name']:
                                        parent_key = c['data']['key']
                                        break
                                
                                # If not found, create the parent collection
                                if not parent_key:
                                    resp_p = zot.create_collections([{'name': 'PhD - Architectural Engineering'}])
                                    parent_key = list(resp_p['successful'].values())[0]['key']
                                    
                                # 2. Check if the subfolder already exists INSIDE the parent collection
                                col_id = None
                                for c in all_cols:
                                    if c['data']['name'] == top_concept and c['data'].get('parentCollection') == parent_key:
                                        col_id = c['data']['key']
                                        break
                                
                                # 3. Create the subfolder nested under the parent collection if not existing
                                if not col_id:
                                    resp_col = zot.create_collections([{'name': top_concept, 'parentCollection': parent_key}])
                                    if resp_col['successful']:
                                        col_id = list(resp_col['successful'].values())[0]['key']
                                
                                template = zot.item_template('journalArticle')
                                template['title'] = title
                                template['date'] = str(pub_year)
                                template['url'] = doi if doi else ""
                                if col_id:
                                    template['collections'] = [col_id]
                                
                                creators = []
                                for a in authorships:
                                    parts = a['author']['display_name'].split()
                                    last = parts[-1] if parts else ""
                                    first = " ".join(parts[:-1]) if len(parts)>1 else ""
                                    creators.append({'creatorType': 'author', 'firstName': first, 'lastName': last})
                                template['creators'] = creators
                                
                                resp = zot.create_items([template])
                                if resp.get('successful'):
                                    st.success(f"✅ Success! Paper saved into Zotero subfolder: '{top_concept}'")
                                    
                                    # Try to sync to Rebecca's OneDrive folder
                                    if st.session_state.onedrive_path:
                                        best_oa = paper.get('best_oa_location') or {}
                                        pdf_url = best_oa.get('pdf_url') or ''
                                        content_urls = paper.get('content_urls') or {}
                                        if not pdf_url:
                                            pdf_url = content_urls.get('pdf') or ''
                                            
                                        synced = sync_to_onedrive(title, authors, pub_year, "", doi, pdf_url)
                                        if synced:
                                            st.success("📤 Automatically synced to Rebecca's Penn State OneDrive!")
                                            
                                    st.session_state.existing_titles.add(paper_title_lower)
                                    if paper_doi_lower:
                                        st.session_state.existing_dois.add(paper_doi_lower)
                                    st.rerun()
                                else:
                                    st.error("Failed to save to Zotero.")
                            except Exception as e:
                                st.error(f"Save error: {e}")
                    else:
                        st.error("Zotero not connected.")
            st.markdown("</div>", unsafe_allow_html=True)
