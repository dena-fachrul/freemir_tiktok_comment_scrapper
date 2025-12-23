import streamlit as st
import os
import re
import pandas as pd
import json
import base64
import time
from datetime import datetime
from collections import Counter
from apify_client import ApifyClient
from deep_translator import GoogleTranslator

# ==========================================
# CONFIGURATION & PAGE SETUP
# ==========================================
st.set_page_config(
    page_title="freemir Brand - TikTok Analysis",
    page_icon="📊",
    layout="centered"
)

# INITIALIZE SESSION STATE (PENTING: Agar data tidak hilang saat klik download)
if 'analysis_done' not in st.session_state:
    st.session_state['analysis_done'] = False
if 'excel_data' not in st.session_state:
    st.session_state['excel_data'] = None
if 'html_str' not in st.session_state:
    st.session_state['html_str'] = None
if 'df_result' not in st.session_state:
    st.session_state['df_result'] = None
if 'total_comments' not in st.session_state:
    st.session_state['total_comments'] = 0

# API CONFIGURATION
API_TOKEN = "apify_api_bU9GPfWGRakecXak2ejiE9xeEeClWJ3iIRNJ"
ACTOR_ID = "BDec00yAmCm1QbMEI"
MIN_CHAR_LENGTH = 3

# ==========================================
# CUSTOM CSS
# ==========================================
st.markdown("""
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        
        .stApp { background-color: #0e1117; font-family: 'Inter', sans-serif; }
        :root { --card-bg: #262730; --tiktok-cyan: #00f2ea; --tiktok-red: #ff0050; --text-primary: #fafafa; }

        .header-container { text-align: center; margin-bottom: 2rem; animation: float 3s ease-in-out infinite; }
        .tiktok-logo-icon { font-size: 3.5rem; margin-bottom: 0.5rem; color: white; text-shadow: 2px 2px 0px var(--tiktok-red), -2px -2px 0px var(--tiktok-cyan); }
        h1 { font-family: 'Inter', sans-serif !important; font-weight: 800 !important; font-size: 2.5rem !important; background: -webkit-linear-gradient(45deg, var(--tiktok-cyan), #fff, var(--tiktok-red)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0 !important; }
        .subtitle { color: #9799a4; font-size: 1rem; font-weight: 300; margin-top: 5px; letter-spacing: 1px; }

        [data-testid="stForm"] { background-color: var(--card-bg); padding: 2.5rem; border-radius: 1rem; box-shadow: 0 4px 20px rgba(0,0,0,0.4); border: 1px solid #333; }
        .stTextInput input, .stNumberInput input { background-color: #0e1117 !important; border: 1px solid #444 !important; color: white !important; border-radius: 8px !important; }
        .stTextInput input:focus, .stNumberInput input:focus { border-color: var(--tiktok-red) !important; box-shadow: 0 0 8px rgba(255, 0, 80, 0.3) !important; }

        div.stButton > button { width: 100%; background: linear-gradient(90deg, #00f2ea, #ff0050) !important; border: none !important; color: white !important; font-weight: 700 !important; text-transform: uppercase; letter-spacing: 1px; padding: 0.75rem 1rem !important; border-radius: 8px !important; margin-top: 10px; }
        div.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(255, 0, 80, 0.4) !important; }
        
        .stSuccess { background-color: rgba(0, 242, 234, 0.1) !important; border: 1px solid var(--tiktok-cyan) !important; color: white !important; }
        .footer { text-align: center; margin-top: 4rem; color: #555; font-size: 0.8rem; border-top: 1px solid #333; padding-top: 20px; }
        @keyframes float { 0% { transform: translateY(0px); } 50% { transform: translateY(-5px); } 100% { transform: translateY(0px); } }
        .label-icon { margin-right: 8px; color: var(--tiktok-cyan); }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. DICTIONARIES & LOGIC (PRESERVED)
# ==========================================
SLANG_DICT = {
    'yg':'yang','yng':'yang','ygk':'yang','ygj':'yang','gmn':'bagaimana',
    'gmna':'bagaimana','gimna':'bagaimana','gmnk':'bagaimana','gmn?':'bagaimana',
    'knp':'kenapa','kenp':'kenapa','knapa':'kenapa','knaoa':'kenapa','gk':'tidak',
    'ga':'tidak','g':'tidak','nggak':'tidak','ngak':'tidak','ndak':'tidak',
    'engga':'tidak','enggak':'tidak','dri':'dari','dr':'dari','drh':'darah',
    'darii':'dari','dri?':'dari','sbnr':'sebenarnya','sbner':'sebenarnya',
    'sebnernya':'sebenarnya','sbnrny':'sebenarnya','sbnarnya':'sebenarnya',
    'skrg':'sekarang','skrang':'sekarang','skrng':'sekarang','skrn':'sekarang',
    'skarng':'sekarang','skg':'sekarang','tdk':'tidak','tkn':'tekan',
    'tknya':'tekanannya','jd':'jadi','jdi':'jadi','jdii':'jadi','jd?':'jadi',
    'jdnya':'jadinya','jdny':'jadinya','sis':'sisa','sisah':'sisa','sisanya':'sisanya',
    'sisa2':'sisa-sisa','bgt':'banget','bget':'banget','bgtt':'banget',
    'bangt':'banget','bnget':'banget','bnyak':'banyak','bnyk':'banyak',
    'banyk':'banyak','byk':'banyak','bmyk':'banyak','dl':'dulu','dlu':'dulu',
    'dlh':'dulu','duluu':'dulu','dluu':'dulu','kl':'kalau','klo':'kalau',
    'klw':'kalau','klau':'kalau','klao':'kalau','sm':'sama','sma':'sama',
    'smua':'semua','smw':'semua','smuanya':'semuanya','smunya':'semuanya',
    'sm2':'semua','aja':'saja','aj':'saja','ajaa':'saja','sja':'saja',
    'sprti':'seperti','spti':'seperti','sprti?':'seperti','sprtii':'seperti',
    'speti':'seperti','trs':'terus','trus':'terus','tros':'terus','trss':'terus',
    'trs2':'terus-terusan','trusny':'terusnya','udh':'sudah','ud':'sudah',
    'uda':'sudah','udahh':'sudah','udh2':'sudah-sudah','udh?':'sudah',
    'dh':'sudah','dah':'sudah','sdh':'sudah','ak':'aku','aq':'aku','q':'aku',
    'gw':'aku','gue':'aku','gua':'aku','km':'kamu','kmu':'kamu','kam':'kamu',
    'lu':'kamu','loe':'kamu','loe2':'kamu','plis':'please','plizz':'please',
    'pliiz':'please','pliss':'please','pls':'please','btw':'by the way',
    'btul':'betul','btl':'betul','bener':'benar','benr':'benar','bnr':'benar',
    'y':'ya','iy':'iya','yo':'ya','ok':'oke','okk':'oke','oky':'oke','okeh':'oke',
    'cm':'cuma','cma':'cuma','cman':'cuma','cuman':'cuma','mw':'mau','mauu':'mau',
    'mauuu':'mau','ngap':'kenapa','ngapa':'kenapa','ngapain':'kenapa',
    'gausah':'tidak usah','gusah':'tidak usah','gabisa':'tidak bisa',
    'gabisaa':'tidak bisa','gbs':'tidak bisa','gabise':'tidak bisa',
    'gabis':'tidak bisa','tau':'tahu','gtau':'tidak tahu','gatau':'tidak tahu',
    'gtw':'tidak tahu','taun':'tahu','tauu':'tahu','ksh':'kasih','kasihh':'kasih',
    'msh':'masih','masi':'masih','msih':'masih','msi':'masih','td':'tadi',
    'tdi':'tadi','drtd':'dari tadi','tdnya':'tadinya','kmrn':'kemarin',
    'kmren':'kemarin','kemaren':'kemarin','kmarin':'kemarin','mkn':'makan',
    'mkan':'makan','mknya':'makannya','makan2':'makan-makan','minum2':'minum-minum',
    'mnum':'minum','minumh':'minum','msk':'masuk','msuke':'masuk ke',
    'bkn':'bukan','bkan':'bukan','bknya':'bukannya','lbh':'lebih','lbih':'lebih',
    'krg':'kurang','tll':'terlalu','trllu':'terlalu','jdwl':'jadwal',
    'tmpt':'tempat','tmpat':'tempat','tmptny':'tempatnya','tmpt2':'tempat-tempat',
    'tmn':'teman','tmnn':'teman','temen':'teman','temenn':'teman','bt':'bantu',
    'bntu':'bantu','bntuin':'bantuin','blm':'belum','blum':'belum','lgi':'lagi',
    'lg':'lagi','lgii':'lagi','lg2':'lagi-lagi','ny':'nya','nyaa':'nya',
    'nyg':'yang','da':'sudah','udhah':'sudah','skrngny':'sekarangnya',
    'skt':'sakit','skit':'sakit','sktny':'sakitnya','pke':'pakai','pkai':'pakai',
    'pake':'pakai','pakenya':'pakainya','pkonya':'pokoknya','ngk':'tidak',
    'gnk':'tidak','kgn':'kangen','kgnn':'kangen','gitukan':'begitukan',
    'gtkan':'begitukan','bekuin':'dibekukan','beq':'beku','microwve':'microwave',
    'microwa':'microwave','ush':'usah','prasaan':'perasaan','perasn':'perasaan',
    'lmbek':'lembek','lemek':'lembek','ank':'anak','anakk':'anak','anak2':'anak-anak',
    'pngukus':'pengukus','pnh':'penuh','pnuh':'penuh','iner':'inner','inerpot':'inner pot',
    'paksu':'suami','ushh':'usah','tgk':'tengok','tngok':'tengok','bole':'boleh',
    'blh':'boleh','sne':'sana','sni':'sini','airny':'airnya','mndidih':'mendidih',
    'duk':'duduk','duuk':'duduk','dug':'dukung','nasiny':'nasinya','nsi':'nasi',
    'bsi':'basi','best':'bagus','baguss':'bagus','try':'coba','cloudkitchen':'cloud kitchen',
    'ratarata':'rata-rata','rata2':'rata-rata','huhu':'sedih','duuh':'aduh',
    'bolehh':'boleh','yaa':'ya','kk':'kakak','thn':'tahun','rekomen':'rekomendasi',
    'sbb':'sebab','ikut2':'ikut-ikut','ltran':'literan','enteng':'ringan',
    'diluar':'di luar','simpen':'simpan','same':'sampai','lngsung':'langsung',
    'ditaro':'ditaruh','soalnya':'karena','dimasukin':'dimasukkan', 'org':'orang',
    'diangetin':'dihangatkan','pda':'pada','kbuang':'kebuang','yh':'ya',
    'mnding':'mending','drmh':'di rumah','kels':'kelas','krj':'kerja','plg':'pulang',
    'dpemanas':'di pemanas','pdhl':'padahal','mssi':'masih','dbuang':'dibuang',
    'nene':'nenek','ampe':'sampai','tar':'nanti','seminggu':'satu minggu',
    'majikan':'majikan','nasgor':'nasi goreng','racikan':'racikan','aqu':'aku',
    'siihh':'sih','gag':'tidak','blg':'bilang','jgk':'juga','krn':'karena',
    'bs':'bisa','angi':'angin','pntg':'penting','ka':'kak','angetin':'hangatkan',
    'endoll':'enak','jg':'juga','w':'aku','taro':'simpan','betuul':'betul',
    'kdg':'kadang','bund':'bunda','gj':'juga','hr':'hari','hri':'hari',
    'sy':'saya','pk':'pakai','pki':'pakai','pk youngma':'pakai','mateng':'matang',
    'matiin':'mematikan','mubadzir':'mubazir','mubazir':'mubazir','jga':'juga',
    'namnya':'namanya','max':'maksimal','2jam':'2 jam','di cabut':'dicabut',
    'dicabut':'dicabut','br':'baru','bngt':'banget','bun':'bunda','basik':'basi',
    'uap nya':'uapnya','nasih':'nasi','menyembab':'menyebabkan',
    'menyembabkan':'menyebabkan','colokan nya':'colokannya','renggangkan':'renggangkan',
    'mejikom':'magic com','emg':'memang','dll':'dan lain-lain','brg':'barang',
    'smpe':'sampai','tonggolannya':'tombolnya','besokin':'besoknya',
    'wlpn':'walaupun','prodak':'produk','poll':'sekali','jeglek':'jatuh',
    'diemin':'diamkan','mnt':'menit','mntn':'menit','amin':'ada yang',
    'nyisa':'tersisa','frizer':'freezer','pn':'pun','nang':'ke','riview':'review',
    'nih':'ini','pya':'punya','th':'tahun','colokin':'colokkan','sya':'saya',
    'trgantung':'tergantung','sampe':'sampai','besttt':'terbaik','usahain':'usahakan',
    '2kali':'dua kali','zonk':'kecewa','aman2':'aman-aman','telor':'telur',
    '15menit':'15 menit','hbis':'habis','bngeet':'banget','tur':'terus',
    'kepake':'kepakai','sayng':'sayang','apapaun':'apapun','digituin':'diperlakukan begitu',
    'pawon':'dapur','apik':'bagus','nasix':'nasi','malem':'malam','maka nya':'makanya',
    'tergos':'tergores','gadi':'ganti','awettt':'awet','stelah':'setelah',
    'matan':'matang','trgntg':'tergantung','berasny':'berasnya','dirumah':'di rumah',
    'ttp':'tetap','tinggak':'tinggal','minyaj':'minyak','stsinlis':'stainless',
    'gak':'tidak','emang':'memang','tpi':'tapi','bgus':'bagus','kyk':'kayak',
    'pnya':'punya','akuuu':'aku','lngsng':'langsung','busukkk':'busuk',
    'cabutt':'cabut','pencer':'pencet','tu':'itu','philip':'Philips',
    'youngma':'YongMa','yongma':'YongMa','yong ma':'YongMa','kosmos':'Cosmos',
    'cosmos':'Cosmos','cpt':'cepat','bgs':'bagus','nyolok':'colok','tak':'tidak',
    'dlm':'dalam','krna':'karena','mf':'maaf','nginep':'menginap','ktnya':'katanya',
    'matng':'matang','clokanya':'colokannya','type':'tipe','24jam':'24 jam',
    'tnpa':'tanpa','semporna':'sempurna','didlm':'di dalam','kuwalitas':'kualitas',
    'magicoom':'magic com','gpp':'tidak apa-apa','pd':'pada','megicom':'magic com',
    'utk':'untuk','bner':'benar','bukn':'bukan','merendhkn':'merendahkan',
    'bermerk':'bermerek','akn':'akan','cepet':'cepat','kucek':'mengucek',
    'mamahku':'ibuku','airn':'air','gmpang':'gampang','stlah':'setelah',
    'mnikah':'menikah','mam':'mama','mf':'maaf','klo':'kalau','didlm':'di dalam',
    'pd':'pada','bukn':'bukan','kwalitas':'kualitas','magicoom':'magic com','tp':'tapi'
}

ASKING_WORDS = {'gimana', 'bagaimana', 'apa', 'apakah', 'kah', 'berapa', 'brp', 'kapan', 'mana', 'dimana', 'boleh', 'bisa', 'aman', 'kenapa', 'kok'}
AGREEMENT_WORDS = {'betul', 'bener', 'benar', 'setuju', 'sepakat', 'valid', 'memang', 'yoi', 'tepat', 'real', 'iya', 'emang', 'terima kasih', 'makasih'}
POSITIVE_WORDS = {'enak', 'sedap', 'bagus', 'mantap', 'suka', 'sehat', 'awet', 'praktis', 'cepat', 'berguna', 'pulen', 'ok', 'oke', 'solusi', 'bantu', 'info', 'jelas', 'hemat', 'murah', 'aman', 'cocok', 'keren', 'cantik'}
NEGATIVE_WORDS = {'tidak', 'jangan', 'bukan', 'gak', 'ga', 'basi', 'bau', 'keras', 'hambar', 'sakit', 'racun', 'bahaya', 'takut', 'mahal', 'ribet', 'susah', 'lembek', 'benyek', 'dingin', 'aneh', 'rugi', 'boncos', 'kurang', 'jelek', 'rusak', 'kecewa'}
STOPWORDS = {'yang', 'dan', 'di', 'ke', 'dari', 'ini', 'itu', 'aku', 'kamu', 'saya', 'dia', 'kita', 'kakak', 'kak', 'ka', 'sudah', 'belum', 'bisa', 'ada', 'mau', 'lagi', 'aja', 'saja', 'kok', 'sih', 'ya', 'dong', 'kan', 'pun', 'tapi', 'kalau', 'karena', 'untuk', 'buat'}

# ================= HELPER FUNCTIONS =================
def clean_text(text: str) -> str:
    if not isinstance(text, str): return ""
    text_clean = re.sub(r'[^a-zA-Z0-9\s.,?!-]', '', text)
    text_clean = re.sub(r'\s+', ' ', text_clean).strip()
    words = text_clean.split()
    cleaned_words = []
    for word in words:
        m = re.match(r'^([A-Za-z0-9-]+)([?.!,]*)$', word)
        if m: base = m.group(1).lower(); punct = m.group(2) or ''
        else: base = word.lower(); punct = ''
        
        if base in SLANG_DICT: 
            cleaned_words.append(SLANG_DICT[base] + punct)
        else: 
            cleaned_words.append(base + punct if base != word else word)
            
    return " ".join(cleaned_words).capitalize()

def get_keywords_list(text: str):
    if not isinstance(text, str): return []
    clean_for_key = re.sub(r'[^\w\s]', '', text.lower())
    words = clean_for_key.split()
    return [w.capitalize() for w in words if w not in STOPWORDS and len(w) > 2]

def categorize_comment(text: str) -> str:
    if not isinstance(text, str): return "Neutral"
    if "?" in text or any(w in text.lower().split() for w in ASKING_WORDS): return "Question"
    if any(w in text.lower().split() for w in AGREEMENT_WORDS): return "Statement"
    
    score = 0
    words = re.sub(r'[^\w\s]', '', text.lower()).split()
    skip_next = False
    
    for i, word in enumerate(words):
        if skip_next: skip_next = False; continue
        if word in ['tidak','jangan','bukan','gak','ga','kurang'] and i+1 < len(words):
            if words[i+1] in POSITIVE_WORDS: score -= 2; skip_next = True
            elif words[i+1] in NEGATIVE_WORDS: score += 1; skip_next = True
        else:
            if word in POSITIVE_WORDS: score += 1
            elif word in NEGATIVE_WORDS: score -= 1
            
    if score > 0: return "Positive"
    elif score < 0: return "Negative"
    return "Neutral"

# --- SAFE TRANSLATOR (ANTI-CRASH) ---
def safe_translate(translator, text):
    """Mencoba translate, jika gagal kembali ke text asli agar tidak crash"""
    if not text or len(str(text)) < 2:
        return text
    try:
        return translator.translate(text)
    except Exception:
        return text  # Fail-safe: kembalikan teks asli

# ==========================================
# 2. SCRAPER FUNCTION
# ==========================================
def scrape_tiktok_comments(video_url, max_comments, max_replies):
    
    client = ApifyClient(API_TOKEN)
    
    run_input = {
        "postURLs": [video_url],
        "commentsPerPost": max_comments,
        "maxRepliesPerComment": max_replies,
        "resultsPerPage": 100,
        "excludePinnedPosts": False,
    }

    try:
        run = client.actor(ACTOR_ID).call(run_input=run_input)
    except Exception as e:
        return None, f"Apify Connection Failed: {e}"

    if run.get("status") == "SUCCEEDED":
        dataset_id = run["defaultDatasetId"]
        # Gunakan list comprehension agar tidak memakan memori berlebih jika sangat besar
        data = list(client.dataset(dataset_id).iterate_items())

        if not data:
            return None, "No comments found in dataset."

        # --- PREPARING DATAFRAME ---
        df = pd.DataFrame(data)

        if 'uniqueId' in df.columns:
            df['Profile Link'] = "https://www.tiktok.com/@" + df['uniqueId'].astype(str)
        else:
            df['Profile Link'] = ""

        rename_map = {
            'createTimeISO': 'Create Time',
            'uid': 'User ID',
            'uniqueId': 'Username',
            'text': 'Comment',
            'diggCount': 'Likes',
            'replyCommentTotal': 'Reply'
        }
        df.rename(columns=rename_map, inplace=True)

        # Basic cleanup
        if 'Comment' in df.columns:
            df['Comment'] = df['Comment'].astype(str).str.replace(r'[\n\r\t]', ' ', regex=True).str.strip()
            df['Comment'] = df['Comment'].str.replace(r'\s+', ' ', regex=True)

        desired_columns = ['Create Time', 'User ID', 'Username', 'Comment', 'Likes', 'Reply', 'Profile Link']
        available_columns = [col for col in desired_columns if col in df.columns]
        df = df[available_columns]

        if 'Likes' in df.columns:
            df['Likes'] = pd.to_numeric(df['Likes'], errors='coerce').fillna(0).astype(int)
            df = df.sort_values(by='Likes', ascending=False)
        
        return df, None

    else:
        return None, "Scraping failed at Apify end."

# ==========================================
# 3. ANALYZER & EXCEL GENERATOR (WITH STATUS UPDATE)
# ==========================================
def analyze_and_get_excel_bytes(df_main, video_url):
    # Initialize Translators
    ts_en = GoogleTranslator(source='auto', target='en')
    ts_cn = GoogleTranslator(source='auto', target='zh-CN')

    output_sheets = {}

    # --- SHEET 0: Scrape-Basic ---
    df_basic = pd.DataFrame([video_url], columns=['Source'])
    output_sheets['Scrape-Basic'] = df_basic

    # --- SHEET 1: Scrape-Main ---
    output_sheets['Scrape-Main'] = df_main

    # --- PROCESSING FOR CLEAN & KEYWORDS ---
    analyzed_rows = []
    all_keywords = []

    # Iterasi biasa agar aman
    for index, row in df_main.iterrows():
        username = row['Username'] if 'Username' in row else "Unknown"
        raw_comment = row['Comment'] if 'Comment' in row else ""
        likes = row['Likes'] if 'Likes' in row else 0

        # Cleaning & Logic
        clean_com = clean_text(str(raw_comment))
        if len(clean_com) < MIN_CHAR_LENGTH: continue
        
        kw_list = get_keywords_list(clean_com)
        all_keywords.extend(kw_list)
        sentiment = categorize_comment(clean_com)
        
        kw_string = ", ".join(sorted(list(set(kw_list)), key=len, reverse=True)[:3])

        analyzed_rows.append({
            'No': len(analyzed_rows) + 1,
            'Username': username,
            'Comment': clean_com,
            'Liked': likes,
            'Sentiment': sentiment,
            'Keywords Preview': kw_string
        })

    # --- SHEET 2: Scrape-Clean ---
    df_clean = pd.DataFrame(analyzed_rows)
    output_sheets['Scrape-Clean'] = df_clean

    # --- SHEET 3: Scrape-Keyword (No Translate) ---
    keyword_counts = Counter(all_keywords)
    df_kw_full = pd.DataFrame(keyword_counts.items(), columns=['Keyword', 'Frequency'])
    df_kw_full = df_kw_full.sort_values(by='Frequency', ascending=False).reset_index(drop=True)
    df_kw_full.insert(0, 'No', range(1, len(df_kw_full) + 1))
    
    output_sheets['Scrape-Keyword'] = df_kw_full

    # --- SHEET 4: Scrape-Summary (With Translation) ---
    # A. TOP 10 COMMENTS
    df_top10 = df_clean.sort_values(by='Liked', ascending=False).head(10).copy()
    df_top10['No'] = range(1, len(df_top10) + 1)
    
    # SAFE TRANSLATION LOOP (Agar tidak error jika gagal satu)
    # Kita pakai safe_translate yang sudah dibuat di atas
    df_top10['Comment (EN)'] = df_top10['Comment'].apply(lambda x: safe_translate(ts_en, x))
    df_top10['Comment (CN)'] = df_top10['Comment'].apply(lambda x: safe_translate(ts_cn, x))
        
    df_top10 = df_top10[['No', 'Username', 'Comment', 'Comment (EN)', 'Comment (CN)', 'Liked']]

    # B. TOP 10 KEYWORDS
    df_kw_top10 = df_kw_full.head(10).copy()
    if not df_kw_top10.empty:
        df_kw_top10['Keyword (EN)'] = df_kw_top10['Keyword'].apply(lambda x: safe_translate(ts_en, x))
        df_kw_top10['Keyword (CN)'] = df_kw_top10['Keyword'].apply(lambda x: safe_translate(ts_cn, x))
    
    df_kw_top10 = df_kw_top10.rename(columns={'Keyword': 'Keyword (ID)'})
    cols_kw = ['No', 'Keyword (ID)', 'Keyword (EN)', 'Keyword (CN)', 'Frequency']
    df_kw_top10 = df_kw_top10[[c for c in cols_kw if c in df_kw_top10.columns]]

    # C. SENTIMENT STATS
    sent_counts = df_clean['Sentiment'].value_counts().reset_index()
    sent_counts.columns = ['Label (ID)', 'Count']
    
    sent_counts['Label (EN)'] = sent_counts['Label (ID)'].apply(lambda x: safe_translate(ts_en, x))
    sent_counts['Label (CN)'] = sent_counts['Label (ID)'].apply(lambda x: safe_translate(ts_cn, x))

    cols_sent = ['Label (ID)', 'Label (EN)', 'Label (CN)', 'Count']
    sent_counts = sent_counts[[c for c in cols_sent if c in sent_counts.columns]]

    # D. ASSEMBLE SUMMARY
    df_top10[' || '] = ''
    df_kw_top10[' ||| '] = ''
    
    df_summary = pd.concat([
        df_top10.reset_index(drop=True),
        df_top10[[' || ']].reset_index(drop=True),
        df_kw_top10.reset_index(drop=True),
        pd.DataFrame([''] * len(df_kw_top10), columns=[' ||| ']), 
        sent_counts.reset_index(drop=True)
    ], axis=1)

    output_sheets['Scrape-Summary'] = df_summary

    # --- SAVE TO TEMP FILE ---
    temp_filename = "temp_analysis_result.xlsx"
    with pd.ExcelWriter(temp_filename, engine='openpyxl') as writer:
        for sheet_name, df_out in output_sheets.items():
            df_out.to_excel(writer, sheet_name=sheet_name, index=False)
            
    return temp_filename

# ==========================================
# 4. REPORT GENERATOR (HTML)
# ==========================================
def generate_html_report_string(excel_path):
    try:
        xls = pd.ExcelFile(excel_path)
        df_summary = pd.read_excel(xls, 'Scrape-Summary')
        df_main = pd.read_excel(xls, 'Scrape-Main')
        
        try:
            df_basic = pd.read_excel(xls, 'Scrape-Basic', header=None)
            source_link = df_basic.iloc[1, 0]
        except:
            source_link = "#"
    except Exception as e:
        return f"Error loading Excel: {e}"

    # --- DATA PROCESSING ---
    df_comments = df_summary.iloc[:, 0:6].copy()
    df_comments.columns = ['No', 'Username', 'Comment', 'Comment_EN', 'Comment_CN', 'Liked']
    df_comments = df_comments.dropna(subset=['Username'])

    df_keywords = df_summary.iloc[:, 9:13].copy()
    df_keywords.columns = ['Keyword_ID', 'Keyword_EN', 'Keyword_CN', 'Frequency']
    df_keywords = df_keywords.dropna(subset=['Keyword_ID'])

    df_sentiment = df_summary.iloc[:, 15:19].copy()
    df_sentiment.columns = ['Label_ID', 'Label_EN', 'Label_CN', 'Count']
    df_sentiment = df_sentiment.dropna(subset=['Label_ID'])

    # Profile Link Lookup
    try:
        df_main.columns = [str(c).strip() for c in df_main.columns]
        link_col = next((c for c in df_main.columns if 'Link' in c), None)
        user_col = next((c for c in df_main.columns if 'User' in c and 'ID' not in c), None)
        
        if link_col and user_col:
            df_lookup = df_main[[user_col, link_col]].copy()
            df_lookup.columns = ['Username', 'Profile_Link']
            df_lookup = df_lookup.drop_duplicates(subset=['Username'])
            
            df_comments = pd.merge(df_comments, df_lookup, on='Username', how='left')
            df_comments['Profile_Link'] = df_comments['Profile_Link'].fillna('#')
        else:
            df_comments['Profile_Link'] = '#'
    except:
        df_comments['Profile_Link'] = '#'

    total_comments = int(df_sentiment['Count'].sum())
    analysis_date = datetime.now().strftime("%d %B %Y")

    # --- VISUALIZATION PREP ---
    color_map = {
        'Neutral': '#B0B0B0', 'Statement': '#FFC107', 
        'Positive': '#00C853', 'Negative': '#FF1744', 'Question': '#6200EA'
    }
    sent_display_labels = (df_sentiment['Label_EN'].astype(str) + " / " + df_sentiment['Label_CN'].astype(str)).tolist()
    sent_counts_list = df_sentiment['Count'].tolist()
    sent_ids = df_sentiment['Label_ID'].tolist()
    sent_colors = [color_map.get(label, '#9E9E9E') for label in sent_ids]

    top_kw = df_keywords.head(10).sort_values(by='Frequency', ascending=False)
    kw_labels = top_kw['Keyword_ID'].tolist()
    kw_data = top_kw['Frequency'].tolist()
    kw_tooltips = (top_kw['Keyword_ID'].astype(str) + " | " + top_kw['Keyword_EN'].astype(str) + " | " + top_kw['Keyword_CN'].astype(str)).tolist()

    # --- HTML GENERATION ---
    table_rows = ""
    for _, row in df_comments.iterrows():
        short_comment = str(row['Comment'])
        if len(short_comment) > 130: short_comment = short_comment[:127] + "..."
        
        if row['Profile_Link'] != "#":
            user_html = f'<a href="{row["Profile_Link"]}" target="_blank" class="user-link">@{row["Username"]} ↗</a>'
        else:
            user_html = f'<span class="user-link">@{row["Username"]}</span>'
            
        table_rows += f"""
        <tr>
            <td style="color:#555;">{int(row['No'])}</td>
            <td>{user_html}</td>
            <td>
                <div class="main-text">{short_comment}</div>
                <div class="sub-text" style="color:#666;">{str(row['Comment_EN'])[:90]}</div>
                <div class="sub-text" style="color:#888;">{str(row['Comment_CN'])[:90]}</div>
            </td>
            <td class="text-center" style="color:#6200EA; font-weight:bold;">{int(row['Liked'])} ❤</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>freemir Brand Analysis</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
            :root {{ --bg-body: #F0F4F8; --primary: #6200EA; --accent: #00B0FF; --text-main: #333333; --text-sub: #666666; --card-bg: #FFFFFF; --header-bg: linear-gradient(135deg, #FFFFFF 0%, #E3F2FD 100%); }}
            body {{ font-family: 'Plus Jakarta Sans', sans-serif; background-color: var(--bg-body); color: var(--text-main); margin: 0; padding: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; display: block; }}
            .main-content {{ display: flex; flex-direction: column; gap: 25px; }}
            .header {{ background: var(--header-bg); border: 1px solid #D1C4E9; border-radius: 24px; padding: 40px; text-align: center; box-shadow: 0 10px 30px rgba(98, 0, 234, 0.08); position: relative; }}
            .copyright-top {{ position: absolute; top: 15px; right: 20px; font-size: 0.75rem; color: #999; font-weight: 600; }}
            h1 {{ margin: 0; font-size: 2.5rem; font-weight: 800; background: linear-gradient(90deg, var(--primary), var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
            .subtitle {{ color: var(--text-sub); letter-spacing: 2px; text-transform: uppercase; font-size: 0.9rem; font-weight: 700; margin-top: 5px; }}
            .meta-tag {{ display: inline-flex; align-items: center; gap: 15px; background: rgba(98, 0, 234, 0.05); padding: 10px 25px; border-radius: 50px; margin-top: 25px; font-size: 0.9rem; color: #555; border: 1px solid rgba(98, 0, 234, 0.2); }}
            .meta-tag a {{ color: var(--primary); text-decoration: none; border-bottom: 1px dotted var(--primary); font-weight: 600; }}
            .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 25px; }}
            .card {{ background: var(--card-bg); border: 1px solid #E0E0E0; border-radius: 20px; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); position: relative; overflow: hidden; }}
            .card::before {{ content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 4px; background: linear-gradient(90deg, var(--accent), var(--primary)); }}
            h2 {{ font-size: 1.2rem; color: #222; margin: 0 0 25px 0; font-weight: 700; }}
            .chart-container {{ position: relative; height: 300px; width: 100%; }}
            .table-responsive {{ overflow-x: auto; border-radius: 12px; border: 1px solid #EEE; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; color: #333; }}
            th {{ text-align: left; padding: 18px; background: #F5F7FA; color: #555; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 1px; font-weight: 700; }}
            td {{ padding: 18px; border-bottom: 1px solid #EEE; vertical-align: top; }}
            tr:hover {{ background: #FAFAFA; }}
            .user-link {{ color: var(--primary); text-decoration: none; font-weight: 700; }}
            .main-text {{ line-height: 1.6; margin-bottom: 5px; color: #222; font-weight: 500; }}
            .sub-text {{ font-size: 0.85rem; font-style: italic; display: block; }}
            .footer {{ text-align: center; font-size: 0.85rem; color: #888; padding: 30px; border-top: 1px solid #DDD; margin-top: 20px; font-weight: 600; }}
            @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
        </style>
    </head>
    <body>
    <div class="container">
        <div class="main-content">
            <div class="header">
                <div class="copyright-top">PT Dachin Etech Global © All Rights Reserved</div>
                <h1>freemir Brand</h1>
                <div class="subtitle">TikTok Video Comment Analysis</div>
                <div class="meta-tag">
                    <span>📅 {analysis_date}</span>
                    <span style="opacity:0.3">|</span>
                    <span>💬 {total_comments} Comments</span>
                    <span style="opacity:0.3">|</span>
                    <a href="{source_link}" target="_blank">View Video ↗</a>
                </div>
            </div>
            <div class="grid">
                <div class="card">
                    <h2>Sentiment Analysis</h2>
                    <div class="chart-container"><canvas id="chartSentiment"></canvas></div>
                </div>
                <div class="card">
                    <h2>Top Keywords (Hover for Translation)</h2>
                    <div class="chart-container"><canvas id="chartKeyword"></canvas></div>
                </div>
            </div>
            <div class="card">
                <h2>Top Engaging Comments</h2>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th width="5%">No</th>
                                <th width="20%">Username</th>
                                <th>Comment Analysis (ID / EN / CN)</th>
                                <th width="10%" class="text-center">Likes</th>
                            </tr>
                        </thead>
                        <tbody>{table_rows}</tbody>
                    </table>
                </div>
            </div>
            <div class="footer">© Created by freemir Data Analyst</div>
        </div>
    </div>
    <script>
        Chart.defaults.color = '#666'; Chart.defaults.borderColor = '#EEE'; Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";
        new Chart(document.getElementById('chartSentiment'), {{
            type: 'doughnut',
            data: {{ labels: {json.dumps(sent_display_labels)}, datasets: [{{ data: {json.dumps(sent_counts_list)}, backgroundColor: {json.dumps(sent_colors)}, borderWidth: 2, borderColor: '#fff', hoverOffset: 15 }}] }},
            options: {{ responsive: true, maintainAspectRatio: false, layout: {{ padding: 10 }}, cutout: '70%', plugins: {{ legend: {{ position: 'right', labels: {{ color: '#333', boxWidth: 12, usePointStyle: true }} }} }} }}
        }});
        var keywordTooltips = {json.dumps(kw_tooltips)};
        new Chart(document.getElementById('chartKeyword'), {{
            type: 'bar',
            data: {{ labels: {json.dumps(kw_labels)}, datasets: [{{ data: {json.dumps(kw_data)}, backgroundColor: 'rgba(98, 0, 234, 0.7)', borderColor: '#6200EA', borderWidth: 1, borderRadius: 6, barThickness: 20 }}] }},
            options: {{ indexAxis: 'y', responsive: true, maintainAspectRatio: false, scales: {{ x: {{ display: false }}, y: {{ ticks: {{ color: '#444', font: {{ weight: 600 }} }}, grid: {{ display: false }} }} }}, plugins: {{ legend: {{ display: false }}, tooltip: {{ backgroundColor: 'rgba(0,0,0,0.8)', callbacks: {{ title: function(context) {{ var index = context[0].dataIndex; return keywordTooltips[index]; }} }} }} }} }}
        }});
    </script>
    </body>
    </html>
    """
    return html_content

# ==========================================
# 5. STREAMLIT UI LAYOUT
# ==========================================

# --- HEADER SECTION (HTML) ---
st.markdown("""
<div class="header-container">
    <i class="fab fa-tiktok tiktok-logo-icon"></i>
    <h1>freemir Brand</h1>
    <div class="subtitle">TikTok Video Comment Analysis Dashboard</div>
</div>
""", unsafe_allow_html=True)

# --- FORM SECTION (STYLED AS CARD) ---
with st.form("scrape_form"):
    st.markdown('<label style="color:#fafafa; font-weight:600; font-size:0.9rem; margin-bottom:5px; display:block;"><i class="fas fa-link label-icon"></i> TikTok Video URL</label>', unsafe_allow_html=True)
    video_url = st.text_input("URL", placeholder="Paste link video TikTok di sini (https://...)", label_visibility="collapsed")
    
    st.write("") # Spacer

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<label style="color:#fafafa; font-weight:600; font-size:0.9rem; margin-bottom:5px; display:block;"><i class="fas fa-comments label-icon"></i> Max Comments</label>', unsafe_allow_html=True)
        max_comments = st.number_input("Max Comments", min_value=1, value=100, label_visibility="collapsed")
    with c2:
        st.markdown('<label style="color:#fafafa; font-weight:600; font-size:0.9rem; margin-bottom:5px; display:block;"><i class="fas fa-reply-all label-icon"></i> Max Replies</label>', unsafe_allow_html=True)
        max_replies = st.number_input("Max Replies", min_value=0, value=0, label_visibility="collapsed")

    st.write("") # Spacer
    
    # Custom Styled Button triggered by submit
    submitted = st.form_submit_button("ROBOT START! 🚀")

# --- EXECUTION LOGIC (CHECKLIST & PROGRESS) ---
# --- EXECUTION LOGIC (CHECKLIST & PROGRESS) ---
if submitted:
    if not video_url:
        st.error("⚠️ Please enter a valid TikTok URL.")
    else:
        # PENGGUNAAN STATUS CONTAINER (CHECKLIST STEP BY STEP)
        with st.status("🤖 Processing data...", expanded=True) as status:
            
            # STEP 1: SCRAPING
            st.write("📡 Step 1: Connecting to TikTok & Scraping Data...")
            df_result, error_msg = scrape_tiktok_comments(video_url, max_comments, max_replies)
            
            if df_result is not None:
                st.write(f"✅ Scraping Successful! {len(df_result)} comments found.")
                
                # STEP 2: CLEANING & TRANSLATING
                st.write("🧹 Step 2: Cleaning text, Sentiment Analysis & Translating (Summary Only)...")
                # Kita gunakan try-except besar disini agar jika translate error, tidak crash total
                try:
                    excel_filename = analyze_and_get_excel_bytes(df_result, video_url)
                    st.write("✅ Analysis & Translation complete.")
                except Exception as e:
                    st.error(f"⚠️ Error during analysis: {e}")
                    status.update(label="An error occurred!", state="error")
                    st.stop()
                
                # STEP 3: FILE GENERATION
                st.write("📄 Step 3: Generating Excel & HTML reports...")
                
                # Read Excel as bytes for session state
                with open(excel_filename, "rb") as f:
                    excel_bytes = f.read()

                # Generate HTML
                html_str = generate_html_report_string(excel_filename)
                
                # SAVE TO SESSION STATE
                st.session_state['df_result'] = df_result
                st.session_state['excel_data'] = excel_bytes
                st.session_state['html_str'] = html_str
                st.session_state['total_comments'] = len(df_result)
                st.session_state['analysis_done'] = True
                
                # Cleanup temp file
                try: os.remove(excel_filename)
                except: pass
                
                st.write("✅ All processes completed!")
                status.update(label="Done! Data is ready to download.", state="complete", expanded=False)
                
                # Rerun agar tombol download muncul di bawah form (UI refresh)
                time.sleep(1)
                st.rerun()

            else:
                st.error(f"❌ Error during Scraping: {error_msg}")
                status.update(label="Scraping Failed!", state="error")

# --- RESULT SECTION (PERSISTENT / TIDAK RESET) ---
# Bagian ini ditaruh DI LUAR 'if submitted' agar tetap muncul setelah klik download
if st.session_state['analysis_done']:
    st.success(f"✅ Analysis Complete! {st.session_state['total_comments']} comments processed.")
    
    st.markdown("---")
    
    # Download Buttons Area
    col_d1, col_d2 = st.columns(2)
    
    with col_d1:
        st.download_button(
            label="📥 Download Excel Report",
            data=st.session_state['excel_data'],
            file_name="Freemir_Analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col_d2:
        st.download_button(
            label="🌏 Download HTML Dashboard",
            data=st.session_state['html_str'],
            file_name="Freemir_Dashboard.html",
            mime="text/html",
            use_container_width=True
        )

# --- FOOTER ---
st.markdown('<div class="footer">© 2025 freemir Intelligence Team. All Rights Reserved.</div>', unsafe_allow_html=True)
