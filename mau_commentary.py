"""
=============================================================
 REGIONAL MAU SEASONALITY COMMENTARY — mau_commentary.py
=============================================================
 Produces: Global_Daily_Commentary.pdf (one page per country)

 DAILY USAGE (two steps):
   1. Download fresh MAU_Intramonth_Claude.xlsx from Looker
      and save it to ~/Documents/GitHub/profit-from-prophet/
   2. In Cursor terminal: python3 mau_commentary.py

 Date is set automatically to today — nothing else to change.

 FIRST-TIME SETUP (run once in terminal):
   pip install pandas weasyprint
   brew install pango        ← Mac
   # or: sudo apt-get install libpango-1.0-0   ← Linux

 OUTPUT:
   ~/Documents/GitHub/profit-from-prophet/Global_Daily_Commentary.pdf
=============================================================
"""
import datetime, warnings, os
warnings.filterwarnings('ignore')
import pandas as pd

# ── Auto-sets to today — no need to change daily ──────────
TODAY     = datetime.date.today()

# ── Set once: path to your project folder ──────────────────
PROJECT   = os.path.expanduser('~/Documents/GitHub/profit-from-prophet')
DATA_PATH = os.path.join(PROJECT, 'MAU_Intramonth_Claude.xlsx')
OUT_DIR   = os.path.join(PROJECT, 'Outputs_MAU_Commentary')
os.makedirs(OUT_DIR, exist_ok=True)

# ── Load & clean data ──────────────────────────────────────
raw = pd.read_csv(DATA_PATH)
raw['Date'] = pd.to_datetime(raw['Date'], dayfirst=True, errors='coerce')
raw = raw.dropna(subset=['Date']).sort_values('Date').reset_index(drop=True)
for c in raw.columns[1:]:
    raw[c] = pd.to_numeric(raw[c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

# ── Palette ────────────────────────────────────────────────
YEAR_COLORS = {2021:'#C0C8D0', 2022:'#8899AA', 2023:'#364452',
               2024:'#007A82', 2025:'#00B4BE', 2026:'#5EDCE4'}
# All annotation dots and labels use one colour for consistency
DOT_COLOR = '#D6006E'

# ── Moving-holiday date tables ─────────────────────────────
HOL = {
    'Easter': {2021:datetime.date(2021,4,4),  2022:datetime.date(2022,4,17),
               2023:datetime.date(2023,4,9),  2024:datetime.date(2024,3,31),
               2025:datetime.date(2025,4,20), 2026:datetime.date(2026,4,5)},
    'Easter UK': {2021:datetime.date(2021,4,5),  2022:datetime.date(2022,4,18),
                  2023:datetime.date(2023,4,10), 2024:datetime.date(2024,4,1),
                  2025:datetime.date(2025,4,21), 2026:datetime.date(2026,4,6)},
    'LNY': {2021:datetime.date(2021,2,12), 2022:datetime.date(2022,2,1),
            2023:datetime.date(2023,1,22), 2024:datetime.date(2024,2,10),
            2025:datetime.date(2025,1,29), 2026:datetime.date(2026,2,17)},
    'Tet': {2021:datetime.date(2021,2,12), 2022:datetime.date(2022,2,1),
            2023:datetime.date(2023,1,22), 2024:datetime.date(2024,2,10),
            2025:datetime.date(2025,1,29), 2026:datetime.date(2026,2,17)},
    'Ramadan': {2021:datetime.date(2021,4,13), 2022:datetime.date(2022,4,2),
                2023:datetime.date(2023,3,23), 2024:datetime.date(2024,3,11),
                2025:datetime.date(2025,3,1),  2026:datetime.date(2026,2,18)},
    'Eid al-Fitr': {2022:datetime.date(2022,5,2),  2023:datetime.date(2023,4,21),
                    2024:datetime.date(2024,4,10), 2025:datetime.date(2025,3,30),
                    2026:datetime.date(2026,3,20)},
    'Eid al-Adha': {2022:datetime.date(2022,7,9),  2023:datetime.date(2023,6,28),
                    2024:datetime.date(2024,6,16), 2025:datetime.date(2025,6,6),
                    2026:datetime.date(2026,5,27)},
    'Songkran':      {y:datetime.date(y,4,13) for y in range(2021,2027)},
    'Golden Week JP':{y:datetime.date(y,4,29) for y in range(2021,2027)},
    'Chuseok': {2021:datetime.date(2021,9,21), 2022:datetime.date(2022,9,10),
                2023:datetime.date(2023,9,29), 2024:datetime.date(2024,9,17),
                2025:datetime.date(2025,10,5), 2026:datetime.date(2026,9,25)},
    'Diwali': {2021:datetime.date(2021,11,4), 2022:datetime.date(2022,10,24),
               2023:datetime.date(2023,11,12),2024:datetime.date(2024,11,1),
               2025:datetime.date(2025,10,20),2026:datetime.date(2026,11,8)},
    'Carnival': {2021:datetime.date(2021,2,16), 2022:datetime.date(2022,3,1),
                 2023:datetime.date(2023,2,21), 2024:datetime.date(2024,2,13),
                 2025:datetime.date(2025,3,4),  2026:datetime.date(2026,2,17)},
    'Mid-Autumn': {2021:datetime.date(2021,9,21), 2022:datetime.date(2022,9,10),
                   2023:datetime.date(2023,9,29), 2024:datetime.date(2024,9,17),
                   2025:datetime.date(2025,10,6), 2026:datetime.date(2026,9,25)},
    # Italy/Spain: Ferragosto — Aug 15 is the core holiday, trough spans Aug 1-20
    'Ferragosto':  {y:datetime.date(y,8,15) for y in range(2021,2027)},
    # Sweden Midsommar = last Saturday of June
    'Midsommar': {2021:datetime.date(2021,6,26), 2022:datetime.date(2022,6,25),
                  2023:datetime.date(2023,6,24), 2024:datetime.date(2024,6,29),
                  2025:datetime.date(2025,6,28), 2026:datetime.date(2026,6,27)},
    # General EU summer start ~Jul 1
    'EU Summer':   {y:datetime.date(y,7,1) for y in range(2021,2027)},
    # Philippines academic year START dates (from screenshot)
    # 2022-23: Aug 22 2022 (COVID late), 2023-24: Aug 29 2023, 2024-25: Jul 29 2024
    # 2025-26: Jun 16 2025 (return to pre-pandemic), 2026-27: ~Jun 2026
    'PH Acad Start': {2022:datetime.date(2022,8,22), 2023:datetime.date(2023,8,29),
                      2024:datetime.date(2024,7,29), 2025:datetime.date(2025,6,16),
                      2026:datetime.date(2026,6,1)},
    # Philippines academic year END dates
    # 2022-23: Jul 7 2023, 2023-24: May 31 2024, 2024-25: May 16 2025, 2025-26: Mar 31 2026
    'PH Acad End':   {2023:datetime.date(2023,7,7),  2024:datetime.date(2024,5,31),
                      2025:datetime.date(2025,5,16), 2026:datetime.date(2026,3,31)},
    # Per-country growth deceleration markers
    'Decel Sep25':  {2025:datetime.date(2025,9,15)},
    'Decel Oct25':  {2025:datetime.date(2025,10,15)},
    'Decel Nov25':  {2025:datetime.date(2025,11,15)},
    'Decel Dec25':  {2025:datetime.date(2025,12,15)},
    'Decel Mar26':  {2026:datetime.date(2026,3,15)},
    # NAMER-specific
    'Thanksgiving US': {2022:datetime.date(2022,11,24), 2023:datetime.date(2023,11,23),
                        2024:datetime.date(2024,11,28), 2025:datetime.date(2025,11,27)},
    'Thanksgiving CA': {2022:datetime.date(2022,10,10), 2023:datetime.date(2023,10,9),
                        2024:datetime.date(2024,10,14), 2025:datetime.date(2025,10,13)},
    'Australia Day':   {2022:datetime.date(2022,1,26), 2023:datetime.date(2023,1,26),
                        2024:datetime.date(2024,1,26), 2025:datetime.date(2025,1,27),
                        2026:datetime.date(2026,1,26)},
}



# ─────────────────────────────────────────────────────────────────────────────


# REGION DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────
REGIONS = {}

# ═══════════════════════════════════════════════════════════════
# NAMER
# ═══════════════════════════════════════════════════════════════
REGIONS['NAMER'] = {
    'countries': [
        ('United States of America', 'United States of America'),
        ('Canada',                   'Canada'),
        ('Australia',                'Australia'),
    ],
    'holiday_table': {
        'United States of America': {
            'headers': ['Year', 'Easter', 'Thanksgiving'],
            'rows': [('2027','Mar 26 - Apr 1','Nov 25'),('2026','Apr 2-6','Nov 26'),
                     ('2025','Apr 17-21','Nov 27'),('2024','Mar 28 - Apr 1','Nov 28'),
                     ('2023','Apr 6-10','Nov 23'),('2022','Apr 14-18','Nov 24')],
        },
        'Canada': {
            'headers': ['Year', 'Easter', 'Thanksgiving'],
            'rows': [('2027','Mar 26 - Apr 1','Oct 11-13'),('2026','Apr 2-6','Oct 12-14'),
                     ('2025','Apr 17-21','Oct 13-15'),('2024','Mar 28 - Apr 1','Oct 14-16'),
                     ('2023','Apr 6-10','Oct 9-11'),('2022','Apr 14-18','Oct 10-12')],
        },
        'Australia': {
            'headers': ['Year', 'Easter', 'Summer School Break'],
            'rows': [('2027','Mar 26 - Apr 1','Jan - Feb'),('2026','Apr 2-6','Jan - Feb'),
                     ('2025','Apr 17-21','Jan - Feb'),('2024','Mar 28 - Apr 1','Jan - Feb'),
                     ('2023','Apr 6-10','Jan - Feb'),('2022','Apr 14-18','Jan - Feb')],
        },
    },
    'anns': {
        'United States of America': [
            {'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
            {'lb':'S1','t':'S','hol':'Easter',          'yrs':[2022,2023,2024,2025,2026]},
            {'lb':'S2','t':'S','hol':'Thanksgiving US', 'yrs':[2022,2023,2024,2025]},
            {'lb':'A11','t':'A','date':datetime.date(2026,1,15)},
            {'lb':'A16','t':'A','hol':'Decel Dec25','yrs':[2025]},
        ],
        'Canada': [
            {'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
            {'lb':'S1','t':'S','hol':'Easter',          'yrs':[2022,2023,2024,2025,2026]},
            {'lb':'S2','t':'S','hol':'Thanksgiving CA', 'yrs':[2022,2023,2024,2025]},
            {'lb':'A16','t':'A','hol':'Decel Nov25','yrs':[2025]},
        ],
        'Australia': [
            {'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
            {'lb':'S1','t':'S','hol':'Easter',        'yrs':[2022,2023,2024,2025,2026]},
            {'lb':'S3','t':'S','hol':'Australia Day', 'yrs':[2022,2023,2024,2025,2026]},
            {'lb':'A16','t':'A','hol':'Decel Nov25','yrs':[2025]},
        ],
    },
    'seasonal': {
        'United States of America': [
            ('S1','Easter','Shifts 2-5 weeks each year (Apr 2-5 in 2026 vs Apr 17-20 in 2025). Creates YoY distortion in the Apr window. 2026 Easter not yet reached.'),
            ('S2','Thanksgiving','Falls on 4th Thursday of November, shifting ~1 week each year. Creates a recurring late-Nov dip.'),
        ],
        'Canada': [
            ('S1','Easter','Shifts 2-5 weeks across Mar/Apr. Creates Apr/May YoY noise.'),
            ('S2','Thanksgiving (CA)','Canadian Thanksgiving in October, shifts ~1 week annually.'),
        ],
        'Australia': [
            ('S1','Easter','Mild Mar/Apr dip — less pronounced than Northern Hemisphere.'),
            ('S3','Summer School Break Start','Schools closed Jan-Feb drives deepest annual trough (~34% below annual average). Fully consistent every year.'),
        ],
    },
    'abnorm': {
        'United States of America': [
            ('A11','Weak Holiday Recovery',
             'Weakest post-holiday recovery on record (Jan-Mar 2026). Returning MAUs declining, not new signups. '
             '+16-22% YoY vs +31-33% in early 2025. Tigerteam monitoring.'),
            ('A16','Growth Rate Deceleration from Dec 2025',
             'YoY growth rate declined materially from Dec 2025 vs prior years by -13.2pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
            ('T2','Post-AI Normalisation',
             'After the 2023 AI step-change (Magic Write/Edit/Design + doubled brand spend), YoY growth has decelerated consistently across all markets. '
             'The inflated 2023 base is the single largest driver of apparent deceleration — default explanation before attributing slowdowns to other causes.'),
        ],
        'Canada': [
            ('A16','Growth Rate Deceleration from Nov 2025',
             'YoY growth rate declined materially from Nov 2025 vs prior years by -11.3pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
            ('T2','Post-AI Normalisation',
             'After the 2023 AI step-change, YoY growth rates have decelerated consistently. '
             'The inflated 2023 base is the primary driver of apparent deceleration.'),
        ],
        'Australia': [
            ('A16','Growth Rate Deceleration from Nov 2025',
             'YoY growth rate declined materially from Nov 2025 vs prior years by -14.0pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
            ('T2','Post-AI Normalisation',
             'After the 2023 AI step-change, YoY growth rates have decelerated consistently. '
             'The inflated 2023 base is the primary driver of apparent deceleration.'),
        ],
    },
}

# ═══════════════════════════════════════════════════════════════
# EUROPE
# ═══════════════════════════════════════════════════════════════
REGIONS['Europe'] = {
    'countries': [
        ('United Kingdom',  'United Kingdom'),
        ('Spain',           'Spain'),
        ('France',          'France'),
        ('Italy',           'Italy'),
        ('Sweden-Nordics',  'Sweden-Nordics'),
        ('Germany',         'Germany'),
        ('Poland',          'Poland'),
        ('Turkey',          'Turkiye'),
        ('Netherlands',     'Netherlands'),
        ('Czech Republic',  'Czech Republic'),
    ],
    'holiday_table': {
        'United Kingdom': {
            'headers': ['Year', 'Easter', 'Summer School Break Start'],
            'rows': [('2027','Mar 26 - Apr 1','mid Jul'),('2026','Apr 2-6','mid Jul'),
                     ('2025','Apr 17-21','mid Jul'),('2024','Mar 28 - Apr 1','mid Jul'),
                     ('2023','Apr 6-10','mid Jul'),('2022','Apr 14-18','mid Jul')],
        },
        'Spain': {
            'headers': ['Year', 'Easter (Semana Santa)', 'Ferragosto / Summer Shutdown'],
            'rows': [('2027','Mar 26 - Apr 1','Aug 1-31'),('2026','Apr 2-6','Aug 1-31'),
                     ('2025','Apr 17-21','Aug 1-31'),('2024','Mar 28 - Apr 1','Aug 1-31'),
                     ('2023','Apr 6-10','Aug 1-31'),('2022','Apr 14-18','Aug 1-31')],
        },
        'France': {
            'headers': ['Year', 'Easter', 'Summer School Break Start'],
            'rows': [('2027','Mar 26 - Apr 1','early Jul'),('2026','Apr 2-6','early Jul'),
                     ('2025','Apr 17-21','early Jul'),('2024','Mar 28 - Apr 1','early Jul'),
                     ('2023','Apr 6-10','early Jul'),('2022','Apr 14-18','early Jul')],
        },
        'Italy': {
            'headers': ['Year', 'Easter (Pasqua)', 'Ferragosto Shutdown'],
            'rows': [('2027','Mar 26 - Apr 1','Aug 1-20'),('2026','Apr 2-6','Aug 1-20'),
                     ('2025','Apr 17-21','Aug 1-20'),('2024','Mar 28 - Apr 1','Aug 1-20'),
                     ('2023','Apr 6-10','Aug 1-20'),('2022','Apr 14-18','Aug 1-20')],
        },
        'Sweden-Nordics': {
            'headers': ['Year', 'Easter', 'Midsommar'],
            'rows': [('2027','Mar 26 - Apr 1','Jun 26'),('2026','Apr 2-6','Jun 27'),
                     ('2025','Apr 17-21','Jun 28'),('2024','Mar 28 - Apr 1','Jun 29'),
                     ('2023','Apr 6-10','Jun 24'),('2022','Apr 14-18','Jun 25')],
        },
        'Germany': {
            'headers': ['Year', 'Easter', 'Summer School Break Start'],
            'rows': [('2027','Mar 26 - Apr 1','Jun-Jul (by state)'),('2026','Apr 2-6','Jun-Jul (by state)'),
                     ('2025','Apr 17-21','Jun-Jul (by state)'),('2024','Mar 28 - Apr 1','Jun-Jul (by state)'),
                     ('2023','Apr 6-10','Jun-Jul (by state)'),('2022','Apr 14-18','Jun-Jul (by state)')],
        },
        'Poland': {
            'headers': ['Year', 'Easter', 'Summer School Break Start'],
            'rows': [('2027','Mar 26 - Apr 1','late Jun'),('2026','Apr 2-6','late Jun'),
                     ('2025','Apr 17-21','late Jun'),('2024','Mar 28 - Apr 1','late Jun'),
                     ('2023','Apr 6-10','late Jun'),('2022','Apr 14-18','late Jun')],
        },
        'Turkey': {
            'headers': ['Year', 'Ramadan', 'Eid al-Fitr', 'Eid al-Adha'],
            'rows': [('2027','~Feb 18 - Mar 19','~Mar 20-22','~May 27-29'),
                     ('2026','Feb 18 - Mar 19','Mar 20-22','May 27-29'),
                     ('2025','Mar 1-29',        'Mar 30 - Apr 1','Jun 6-9'),
                     ('2024','Mar 11 - Apr 9',  'Apr 10-12','Jun 16-19'),
                     ('2023','Mar 23 - Apr 20', 'Apr 21-23','Jun 28 - Jul 1'),
                     ('2022','Apr 2 - May 1',   'May 2-4',  'Jul 9-12')],
        },
        'Netherlands': {
            'headers': ['Year', 'Easter', 'Summer School Break Start'],
            'rows': [('2027','Mar 26 - Apr 1','mid Jul'),('2026','Apr 2-6','mid Jul'),
                     ('2025','Apr 17-21','mid Jul'),('2024','Mar 28 - Apr 1','mid Jul'),
                     ('2023','Apr 6-10','mid Jul'),('2022','Apr 14-18','mid Jul')],
        },
        'Czech Republic': {
            'headers': ['Year', 'Easter', 'Summer School Break Start'],
            'rows': [('2027','Mar 26 - Apr 1','late Jun'),('2026','Apr 2-6','late Jun'),
                     ('2025','Apr 17-21','late Jun'),('2024','Mar 28 - Apr 1','late Jun'),
                     ('2023','Apr 6-10','late Jun'),('2022','Apr 14-18','late Jun')],
        },
    },
    'anns': {
        'United Kingdom':  [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                             {'lb':'S1','t':'S','hol':'Easter UK','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'S2','t':'S','hol':'EU Summer','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'A16','t':'A','hol':'Decel Oct25','yrs':[2025]}],
        'Spain':           [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                             {'lb':'S1','t':'S','hol':'Easter','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'S2','t':'S','hol':'Ferragosto','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'A16','t':'A','hol':'Decel Oct25','yrs':[2025]}],
        'France':          [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                             {'lb':'S1','t':'S','hol':'Easter','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'S2','t':'S','hol':'EU Summer','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'A16','t':'A','hol':'Decel Oct25','yrs':[2025]}],
        'Italy':           [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                             {'lb':'S1','t':'S','hol':'Easter','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'S2','t':'S','hol':'Ferragosto','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'A16','t':'A','hol':'Decel Dec25','yrs':[2025]}],
        'Sweden-Nordics':  [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                             {'lb':'S1','t':'S','hol':'Easter','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'S2','t':'S','hol':'Midsommar','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'A16','t':'A','hol':'Decel Oct25','yrs':[2025]}],
        'Germany':         [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                             {'lb':'S1','t':'S','hol':'Easter','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'S2','t':'S','hol':'EU Summer','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'A16','t':'A','hol':'Decel Oct25','yrs':[2025]}],
        'Poland':          [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                             {'lb':'S1','t':'S','hol':'Easter','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'S2','t':'S','hol':'EU Summer','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'A16','t':'A','hol':'Decel Dec25','yrs':[2025]}],
        'Turkey':          [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                             {'lb':'S1','t':'S','hol':'Ramadan','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'S2','t':'S','hol':'Eid al-Fitr','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'S3','t':'S','hol':'Eid al-Adha','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'A8','t':'A','date':datetime.date(2024,2,1)},
                             {'lb':'A16','t':'A','hol':'Decel Sep25','yrs':[2025]}],
        'Netherlands':     [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                             {'lb':'S1','t':'S','hol':'Easter','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'S2','t':'S','hol':'EU Summer','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'A16','t':'A','hol':'Decel Oct25','yrs':[2025]}],
        'Czech Republic':  [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                             {'lb':'S1','t':'S','hol':'Easter','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'S2','t':'S','hol':'EU Summer','yrs':[2022,2023,2024,2025,2026]},
                             {'lb':'A16','t':'A','hol':'Decel Nov25','yrs':[2025]}],
    },
    'seasonal': {
        'United Kingdom':  [('S1','Easter','Shifts 1-4 weeks each year (Apr 6 in 2026 vs Apr 21 in 2025). Creates Mar/Apr YoY noise.'),
                             ('S2','Summer School Break Start','Jul-Aug school break drives consistent annual trough. Start ~mid-Jul is stable year-over-year.'),],
        'Spain':           [('S1','Easter (Semana Santa)','One of the strongest Easter effects in Europe. Shifts 2-5 weeks creating large Apr YoY swings.'),
                             ('S2','Ferragosto / Summer Shutdown Start','Spain and Italy experience the deepest summer trough globally — MAU drops ~40-45% below annual average through August. Recovers sharply into Sep back-to-school.'),],
        'France':          [('S1','Easter (Pâques)','2-4 week shift creates Apr YoY noise.'),
                             ('S2','Summer School Break Start','Early Jul-Aug school holiday drives reliable annual trough then back-to-school lift Sep-Nov.'),],
        'Italy':           [('S1','Easter (Pasqua)','2-4 week shift creates Apr distortion in YoY comparisons.'),
                             ('S2','Ferragosto Shutdown Start','Extreme summer shutdown centred on Aug 15 — MAU drops ~40-45% below annual average. Deepest seasonal trough of any market globally. Recovers sharply into Sep.'),],
        'Sweden-Nordics':  [('S1','Easter','Moderate Easter effect.'),
                             ('S2','Midsommar Start','Last Saturday of June — marks start of summer holidays. Shifts 1-5 days annually (Jun 24-29 range).'),],
        'Germany':         [('S1','Easter','Easter holidays staggered by Bundesland; aggregate Apr dip shifts 2-4 weeks YoY.'),
                             ('S2','Summer School Break Start','Staggered by state (Jun-Sep). Creates a broad summer trough, milder than Spain/Italy.'),],
        'Poland':          [('S1','Easter','Strong Catholic Easter effect; shifts 2-4 weeks. Material YoY distortion Mar-May.'),
                             ('S2','Summer School Break Start','Late-Jun school break; Sep back-to-school lift reliable year-over-year.'),],
        'Turkey':          [('S1','Ramadan','Shifts ~11 days earlier each year. Creates roving MAU dip during fasting month. Requires calendar-adjusted YoY comparisons.'),
                             ('S2','Eid al-Fitr','3-day celebration immediately after Ramadan. Creates sharp spike vs Ramadan trough. Also shifts ~11 days earlier per year.'),
                             ('S3','Eid al-Adha','4-day sacrifice holiday ~70 days after Eid al-Fitr. Secondary annual dip. Also shifts ~11 days earlier per year.'),],
        'Netherlands':     [('S1','Easter','Shifts 2-4 weeks; moderate impact.'),
                             ('S2','Summer School Break Start','Mid-Jul school holiday break; consistent Sep back-to-school lift.'),],
        'Czech Republic':  [('S1','Easter','Easter Monday is a public holiday; 2-4 week shift creates YoY noise.'),
                             ('S2','Summer School Break Start','Late-Jun school break. Sep back-to-school lift reliable.'),],
    },
    'abnorm': {
        'United Kingdom':  [('A16','Growth Rate Deceleration from Oct 2025',
                              'YoY growth rate declined materially from Oct 2025 vs prior years by -16.3pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
                             ('T1','AI Features Step-Change (Mar 2023)',
                              'Magic Write, Magic Edit and Magic Design launched Mar 2023 with doubled brand spend. The 2023 line visibly separates above 2022.'),
                             ('T2','Post-AI Normalisation',
                              'YoY growth has decelerated since 2023 as the inflated base rolls through comparisons.')],
        'Spain':           [('A13','Accelerated H2 2023 Uplift',
                              'Southern European markets showed particularly strong AI step-change response in H2 2023. Spain elevated significantly above prior trend Jun-Oct 2023. Amplifies 2024+ apparent deceleration.'),
                             ('A16','Growth Rate Deceleration from Oct 2025',
                              'YoY growth rate declined materially from Oct 2025 vs prior years by -15.6pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
                             ('T2','Post-AI Normalisation',
                              'YoY growth has decelerated since 2023. The inflated 2023 base (further amplified by the H2 2023 southern Europe spike) is the primary driver.')],
        'France':          [('A16','Growth Rate Deceleration from Oct 2025',
                              'YoY growth rate declined materially from Oct 2025 vs prior years by -16.9pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
                             ('T1','AI Features Step-Change (Mar 2023)',
                              'Visible structural uplift across all months of 2023.'),
                             ('T2','Post-AI Normalisation',
                              'YoY growth has decelerated since 2023 as the inflated base rolls through comparisons.')],
        'Italy':           [('A13','Accelerated H2 2023 Uplift',
                              'Italy recorded +82% YoY in Jun 2023 (+40pp above prior trend). One of the strongest AI step-change responses in Europe. Amplifies 2024+ apparent deceleration.'),
                             ('A16','Growth Rate Deceleration from Dec 2025',
                              'YoY growth rate declined materially from Dec 2025 vs prior years by -12.9pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
                             ('T2','Post-AI Normalisation',
                              'YoY growth has decelerated since 2023. The inflated 2023 base is the primary driver.')],
        'Sweden-Nordics':  [('A16','Growth Rate Deceleration from Oct 2025',
                              'YoY growth rate declined materially from Oct 2025 vs prior years by -16.9pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
                             ('T2','Post-AI Normalisation',
                              'YoY growth has decelerated since 2023 as the inflated base rolls through comparisons.')],
        'Germany':         [('A16','Growth Rate Deceleration from Oct 2025',
                              'YoY growth rate declined materially from Oct 2025 vs prior years by -17.4pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
                             ('T2','Post-AI Normalisation',
                              'YoY growth has decelerated since 2023 as the inflated base rolls through comparisons.')],
        'Poland':          [('A16','Growth Rate Deceleration from Dec 2025',
                              'YoY growth rate declined materially from Dec 2025 vs prior years by -19.5pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
                             ('T2','Post-AI Normalisation',
                              'YoY growth has decelerated since 2023 as the inflated base rolls through comparisons.')],
        'Turkey':          [('A8','Canva Hub / Local Investment Spike (Jan-Mar 2024)',
                              'Growth accelerated from ~24-40% YoY in 2023 to +67-70% YoY in early 2024. Likely driven by Canva hub opening and local marketing step-up. '
                              'Creates extreme base reversal: Aug 2024 showed -69pp swing. Not structural deterioration.'),
                             ('A16','Growth Rate Deceleration from Sep 2025',
                              'YoY growth rate declined materially from Sep 2025 vs prior years by -17.9pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
                             ('T2','Post-AI Normalisation',
                              'Underlying YoY growth also decelerating post-2023 base, compounded by the 2024 hub-launch base effect.')],
        'Netherlands':     [('A16','Growth Rate Deceleration from Oct 2025',
                              'YoY growth rate declined materially from Oct 2025 vs prior years by -16.3pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
                             ('T2','Post-AI Normalisation',
                              'YoY growth has decelerated since 2023 as the inflated base rolls through comparisons.')],
        'Czech Republic':  [('A16','Growth Rate Deceleration from Nov 2025',
                              'YoY growth rate declined materially from Nov 2025 vs prior years by -24.3pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
                             ('T2','Post-AI Normalisation',
                              'YoY growth has decelerated since 2023 as the inflated base rolls through comparisons.')],
    },
}

# ═══════════════════════════════════════════════════════════════
# MENAP & SSA
# ═══════════════════════════════════════════════════════════════
REGIONS['MENAP_SSA'] = {
    'countries': [
        ('GCC',          'GCC'),
        ('South Africa', 'South Africa'),
    ],
    'holiday_table': {
        'GCC': {
            'headers': ['Year', 'Ramadan', 'Eid al-Fitr', 'Eid al-Adha'],
            'rows': [('2027','~Feb 18 - Mar 19','~Mar 20-22','~May 27-29'),
                     ('2026','Feb 18 - Mar 19', 'Mar 20-22', 'May 27-29'),
                     ('2025','Mar 1-29',         'Mar 30 - Apr 1','Jun 6-9'),
                     ('2024','Mar 11 - Apr 9',   'Apr 10-12','Jun 16-19'),
                     ('2023','Mar 23 - Apr 20',  'Apr 21-23','Jun 28 - Jul 1'),
                     ('2022','Apr 2 - May 1',    'May 2-4',  'Jul 9-12')],
        },
        'South Africa': {
            'headers': ['Year', 'Easter', 'Summer School Break'],
            'rows': [('2027','Mar 26 - Apr 1','Dec - Jan'),('2026','Apr 2-6','Dec - Jan'),
                     ('2025','Apr 17-21','Dec - Jan'),('2024','Mar 28 - Apr 1','Dec - Jan'),
                     ('2023','Apr 6-10','Dec - Jan'),('2022','Apr 14-18','Dec - Jan')],
        },
    },
    'anns': {
        'GCC':          [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                          {'lb':'S1','t':'S','hol':'Ramadan','yrs':[2022,2023,2024,2025,2026]},
                          {'lb':'S2','t':'S','hol':'Eid al-Fitr','yrs':[2022,2023,2024,2025,2026]},
                          {'lb':'S3','t':'S','hol':'Eid al-Adha','yrs':[2022,2023,2024,2025,2026]}],
        'South Africa': [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                          {'lb':'S1','t':'S','hol':'Easter','yrs':[2022,2023,2024,2025,2026]},
                          {'lb':'A16','t':'A','hol':'Decel Nov25','yrs':[2025]}],
    },
    'seasonal': {
        'GCC':          [('S1','Ramadan','Shifts ~11 days earlier every year. Creates a pronounced MAU dip during fasting hours. Requires calendar-adjusted YoY comparisons.'),
                          ('S2','Eid al-Fitr','3-day celebration immediately after Ramadan. Sharp engagement spike. Also shifts ~11 days earlier per year.'),
                          ('S3','Eid al-Adha','4-day sacrifice holiday ~70 days after Eid al-Fitr. Secondary annual dip. Also shifts ~11 days earlier per year.'),],
        'South Africa': [('S1','Easter','Long weekend (Good Friday + Easter Monday + Family Day) shifts 2-4 weeks. Creates Apr YoY distortion.'),],
    },
    'abnorm': {
        'GCC':          [('A15','Ramadan 2026 Early Arrival',
                          'Ramadan started Feb 28 2026 — combined with structural deceleration, MENAP Feb 2026 showed -27pp swing vs baseline. '
                          'Back-to-school Sep peak remains the most reliable positive seasonal signal for GCC each year.'),
                         ('T2','Post-AI Normalisation',
                          'YoY growth has decelerated since 2023 as the inflated base rolls through comparisons.')],
        'South Africa': [('A16','Growth Rate Deceleration from Nov 2025',
                          'YoY growth rate declined materially from Nov 2025 vs prior years by -6.1pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
                         ('A12','Data Pipeline Bug (Mar 9-13 2026)',
                          'A -7.1σ daily anomaly in SSA data from Mar 9-13 2026 was a Looker data mapping bug — SSA international mapping disappeared. '
                          'Fixed Mar 13 by William Chen. GSheets feed (Source_PLGMAU) fix to be confirmed with Steven Maikim. Do not treat as signal.'),
                         ('T2','Post-AI Normalisation',
                          'YoY growth has decelerated since 2023 as the inflated base rolls through comparisons.')],
    },
}

# ═══════════════════════════════════════════════════════════════
# CJKI
# ═══════════════════════════════════════════════════════════════
REGIONS['CJKI'] = {
    'countries': [
        ('China',       'China'),
        ('Japan',       'Japan'),
        ('South Korea', 'South Korea'),
        ('India',       'India'),
    ],
    'holiday_table': {
        'China': {
            'headers': ['Year', 'Lunar New Year', 'Mid-Autumn Festival', 'Golden Week'],
            'rows': [('2027','Feb 6-12',       'Oct 1','Oct 1-7'),
                     ('2026','Feb 17-23',       'Sep 25','Oct 1-7'),
                     ('2025','Jan 29 - Feb 4',  'Oct 6','Oct 1-7'),
                     ('2024','Feb 10-16',       'Sep 17','Oct 1-7'),
                     ('2023','Jan 22-28',       'Sep 29','Oct 1-7'),
                     ('2022','Feb 1-7',         'Sep 10','Oct 1-7')],
        },
        'Japan': {
            'headers': ['Year', 'Golden Week', 'Obon'],
            'rows': [('2027','Apr 29 - May 6','Aug 13-16'),('2026','Apr 29 - May 6','Aug 13-16'),
                     ('2025','Apr 29 - May 6','Aug 13-16'),('2024','Apr 27 - May 6','Aug 13-16'),
                     ('2023','Apr 29 - May 7','Aug 13-16'),('2022','Apr 29 - May 5','Aug 13-16')],
        },
        'South Korea': {
            'headers': ['Year', 'Lunar New Year (Seollal)', 'Chuseok'],
            'rows': [('2027','Jan 28-30','Sep 24-26'),('2026','Feb 16-18','Sep 24-26'),
                     ('2025','Jan 28-30','Oct 4-6'),   ('2024','Feb 9-12','Sep 16-18'),
                     ('2023','Jan 21-24','Sep 28-30'), ('2022','Jan 31 - Feb 2','Sep 9-12')],
        },
        'India': {
            'headers': ['Year', 'Diwali', 'Holi'],
            'rows': [('2027','Oct 28-29','Mar 13-14'),('2026','Nov 7-8','Mar 3-4'),
                     ('2025','Oct 20-21','Mar 13-14'),('2024','Oct 31 - Nov 1','Mar 24-25'),
                     ('2023','Nov 12-13','Mar 7-8'),  ('2022','Oct 24-25','Mar 17-18')],
        },
    },
    'anns': {
        'China':       [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                         {'lb':'S1','t':'S','hol':'LNY','yrs':[2022,2023,2024,2025,2026]},
                         {'lb':'S2','t':'S','hol':'Mid-Autumn','yrs':[2022,2023,2024,2025,2026]},
                         {'lb':'A3','t':'A','date':datetime.date(2024,1,15)},
                         {'lb':'A2','t':'A','date':datetime.date(2025,9,15)},
                         {'lb':'A16','t':'A','hol':'Decel Sep25','yrs':[2025]},
                         {'lb':'A1','t':'A','date':datetime.date(2026,2,17)}],
        'Japan':       [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                         {'lb':'S1','t':'S','hol':'Golden Week JP','yrs':[2022,2023,2024,2025,2026]},
                         {'lb':'A14','t':'A','date':datetime.date(2024,6,1)},
                         {'lb':'A16','t':'A','hol':'Decel Sep25','yrs':[2025]}],
        'South Korea': [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                         {'lb':'S1','t':'S','hol':'LNY','yrs':[2022,2023,2024,2025,2026]},
                         {'lb':'S2','t':'S','hol':'Chuseok','yrs':[2022,2023,2024,2025,2026]},
                         {'lb':'A6','t':'A','date':datetime.date(2023,5,1)},
                         {'lb':'A16','t':'A','hol':'Decel Mar26','yrs':[2026]}],
        'India':       [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                         {'lb':'S1','t':'S','hol':'Diwali','yrs':[2022,2023,2024,2025,2026]},
                         {'lb':'A7','t':'A','date':datetime.date(2024,1,15)},
                         {'lb':'A16','t':'A','hol':'Decel Oct25','yrs':[2025]}],
    },
    'seasonal': {
        'China':       [('S1','Lunar New Year (Spring Festival)','Shifts 2-5 weeks each year (Jan 29 in 2025 vs Feb 17 in 2026). 7-day national holiday drives deepest annual MAU trough. Creates large YoY distortion in Jan-Feb window.'),
                         ('S2','Mid-Autumn Festival','Shifts 2-5 weeks Sep-Oct each year. Creates a secondary seasonal dip. Golden Week (Oct 1-7) is a fixed-date trough immediately following.'),],
        'Japan':       [('S1','Golden Week (Apr 29 - May 6)','Cluster of national holidays creating a reliable early-May dip. Dates stable year-over-year. Obon (Aug 13-16) creates a secondary summer dip.'),],
        'South Korea': [('S1','Lunar New Year (Seollal)','Shifts 2-4 weeks Jan-Feb each year. Creates YoY distortion in the Jan-Mar window.'),
                         ('S2','Chuseok','Major autumn harvest holiday; shifts ~2 weeks Sep-Oct. Creates a recurring YoY noise period.'),],
        'India':       [('S1','Diwali','Shifts 2-4 weeks Oct-Nov each year. Creates a clear engagement spike (not dip) during the festival. YoY comparisons require Diwali-aligned windows.'),],
    },
    'abnorm': {
        'China':       [('A2','First-Ever YoY Declines (from Sep 2025)',
                         'China entered outright YoY contraction from Sep 2025: -3.6% Sep, -9.2% Oct, -15% Nov, -17% Dec, -10.7% Jan 2026, -14.6% Feb 2026. '
                         'Structural deterioration separate from LNY timing. Root cause not confirmed — likely competitive dynamics and organic traffic decline.'),
                        ('A16','Growth Rate Deceleration from Sep 2025',
                         'YoY growth rate declined materially from Sep 2025 vs prior years by -53.7pp, steeper than seasonal norms. Monitoring continues into Q1 2026. '
                         'Note: this figure is significantly inflated by LNY timing effects — underlying structural decline estimated at -10-15pp.'),
                        ('A1','LNY Timing: Extreme Optical -45.6% YoY Mar 2026',
                         'LNY 2026 fell Feb 17 vs Jan 29 in 2025 — 19-day shift. Mar 2026 remains in trough while Mar 2025 was already in full recovery, '
                         'creating ~-93pp optical distortion. Real decline estimated at -10-15% YoY. Timing artefact — not standalone business signal.'),
                        ('A3','LNY Timing: +45.5% YoY Spike Jan 2024',
                         'LNY 2024 fell Feb 10 vs Jan 22 in 2023 — inflated Jan 2024 (post-holiday) vs Jan 2023 (pre-holiday). Pure calendar artefact. '
                         'Creates inflated base depressing Jan 2025 comparison (only +12.2% YoY).'),
                        ('T2','Post-AI Normalisation',
                         'YoY growth has decelerated since 2023. In China this is compounded by structural decline from Sep 2025.')],
        'Japan':       [('A14','Sustained 2024 Boom (+64-76% YoY All Year)',
                         'Japan grew at unusually high rates throughout 2024 — higher than prior year despite post-AI base effect seen elsewhere. '
                         'Likely driven by local market investment and organic virality. Creates strong base for 2025-2026 (decelerating to +38-43% in early 2026).'),
                        ('A16','Growth Rate Deceleration from Sep 2025',
                         'YoY growth rate declined materially from Sep 2025 vs prior years by -17.4pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
                        ('S8','Positive Summer Signal (Jul-Aug)',
                         'Uniquely, Japan\'s summer is above annual average — school summer projects drive Canva usage. '
                         'Every other major market shows a summer trough; Japan shows a lift.')],
        'South Korea': [('A6','Extraordinary Growth Spike Apr-Jul 2023 (+127-152% YoY)',
                         'The most extreme acceleration event in the dataset — likely viral product-market fit and/or major local marketing. '
                         'Creates very high base compressing all subsequent YoY. 2024 growth (+75-103%) appears to decelerate sharply due solely to this base.'),
                        ('A16','Growth Rate Deceleration from Mar 2026',
                         'YoY growth rate declined materially from Mar 2026 vs prior years by -40.2pp, steeper than seasonal norms. Monitoring continues into Q1 2026. '
                         'Note: partially inflated by exam season base effect in Mar 2026 — interpret with caution.'),
                        ('T2','Post-AI Normalisation',
                         'YoY growth has decelerated since 2023, compounded by the exceptionally high Apr-Jul 2023 base unique to South Korea.')],
        'India':       [('A7','Unexplained Spike Jan 2024 (+86.5% YoY)',
                         'Major acceleration event in January 2024 with no confirmed cause — likely large marketing campaign or product event. '
                         'Creates heavily inflated base: Aug-Dec 2024 showed -62 to -105pp swings vs prior year. Partially reverting by Jan 2025 (+23.1% YoY).'),
                        ('A16','Growth Rate Deceleration from Oct 2025',
                         'YoY growth rate declined materially from Oct 2025 vs prior years by -22.2pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
                        ('T2','Post-AI Normalisation',
                         'YoY growth has decelerated since 2023, further amplified by the Jan 2024 spike base effect through mid-2025.')],
    },
}

# ═══════════════════════════════════════════════════════════════
# LATAM
# ═══════════════════════════════════════════════════════════════
REGIONS['LATAM'] = {
    'countries': [
        ('Brazil',    'Brazil'),
        ('Mexico',    'Mexico'),
        ('Argentina', 'Argentina'),
    ],
    'holiday_table': {
        'Brazil': {
            'headers': ['Year', 'Carnival', 'Easter'],
            'rows': [('2027','Feb 9-11',      'Mar 26 - Apr 1'),('2026','Feb 17-19','Apr 2-6'),
                     ('2025','Mar 4-6',       'Apr 17-21'),  ('2024','Feb 13-15','Mar 28 - Apr 1'),
                     ('2023','Feb 21-23',     'Apr 6-10'),    ('2022','Mar 1-3',  'Apr 14-18')],
        },
        'Mexico': {
            'headers': ['Year', 'Easter (Semana Santa)', 'Día de Muertos'],
            'rows': [('2027','Mar 26 - Apr 1','Nov 1-2'),('2026','Apr 2-6','Nov 1-2'),
                     ('2025','Apr 17-21','Nov 1-2'),  ('2024','Mar 28 - Apr 1','Nov 1-2'),
                     ('2023','Apr 6-10','Nov 1-2'),    ('2022','Apr 14-18','Nov 1-2')],
        },
        'Argentina': {
            'headers': ['Year', 'Carnival', 'Easter'],
            'rows': [('2027','Feb 8-9', 'Mar 26 - Apr 1'),('2026','Feb 16-17','Apr 2-6'),
                     ('2025','Mar 3-4', 'Apr 17-21'),  ('2024','Feb 12-13','Mar 28 - Apr 1'),
                     ('2023','Feb 20-21','Apr 6-10'), ('2022','Feb 28 - Mar 1','Apr 14-18')],
        },
    },
    'anns': {
        'Brazil':    [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                       {'lb':'S1','t':'S','hol':'Carnival','yrs':[2022,2023,2024,2025,2026]},
                       {'lb':'S2','t':'S','hol':'Easter','yrs':[2022,2023,2024,2025,2026]},
                       {'lb':'A9','t':'A','date':datetime.date(2026,1,15)},
                       {'lb':'A16','t':'A','hol':'Decel Dec25','yrs':[2025]}],
        'Mexico':    [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                       {'lb':'S1','t':'S','hol':'Easter','yrs':[2022,2023,2024,2025,2026]},
                       {'lb':'A16','t':'A','hol':'Decel Sep25','yrs':[2025]}],
        'Argentina': [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                       {'lb':'S1','t':'S','hol':'Carnival','yrs':[2022,2023,2024,2025,2026]},
                       {'lb':'S2','t':'S','hol':'Easter','yrs':[2022,2023,2024,2025,2026]},
                       {'lb':'A16','t':'A','hol':'Decel Nov25','yrs':[2025]}],
    },
    'seasonal': {
        'Brazil':    [('S1','Carnival','Shifts 2-4 weeks Feb-Mar each year (Feb 17 in 2026 vs Mar 4 in 2025). Creates engagement dip in pre-Carnival week, followed by post-Carnival rebound.'),
                      ('S2','Easter (Semana Santa)','Shifts 2-4 weeks Mar-Apr. Secondary seasonal effect after Carnival.'),],
        'Mexico':    [('S1','Semana Santa / Easter','Major holiday period; shifts 2-4 weeks Mar-Apr. Creates a pronounced MAU dip. Stronger effect than in NAMER.'),],
        'Argentina': [('S1','Carnival','Shifts 2-4 weeks Feb-Mar. Creates Feb-Mar dip similar to Brazil.'),
                      ('S2','Easter','Shifts 2-4 weeks; combined with Carnival creates complex Q1 seasonal pattern.'),],
    },
    'abnorm': {
        'Brazil':    [('A9','First-Ever Near-Zero / Negative YoY Growth (2026)',
                       'Brazil hit +4.6% YoY Jan 2026, +2.6% Feb 2026, -0.1% Mar 2026 — first time Brazil has recorded negative YoY MAU growth. '
                       'Post-Carnival recovery not materialising. Root cause under active investigation by Grace Wong\'s team — not explained by calendar or base effects.'),
                      ('A16','Growth Rate Deceleration from Dec 2025',
                       'YoY growth rate declined materially from Dec 2025 vs prior years by -13.1pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
                      ('T2','Post-AI Normalisation',
                       'YoY growth has decelerated since 2023. The 2026 Brazil deterioration appears to go beyond base effects.')],
        'Mexico':    [('A16','Growth Rate Deceleration from Sep 2025',
                       'YoY growth rate declined materially from Sep 2025 vs prior years by -15.4pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
                      ('T2','Post-AI Normalisation',
                       'YoY growth has decelerated since 2023 as the inflated base rolls through comparisons.')],
        'Argentina': [('A16','Growth Rate Deceleration from Nov 2025',
                       'YoY growth rate declined materially from Nov 2025 vs prior years by -17.0pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
                      ('T2','Post-AI Normalisation',
                       'YoY growth has decelerated since 2023 as the inflated base rolls through comparisons.')],
    },
}

# ═══════════════════════════════════════════════════════════════
# SEA
# ═══════════════════════════════════════════════════════════════
REGIONS['SEA'] = {
    'countries': [
        ('Indonesia',   'Indonesia'),
        ('Philippines', 'Philippines'),
        ('Thailand',    'Thailand'),
        ('Vietnam',     'Vietnam'),
    ],
    'holiday_table': {
        'Indonesia': {
            'headers': ['Year', 'Ramadan', 'Eid al-Fitr (Lebaran)', 'Eid al-Adha'],
            'rows': [('2027','~Feb 18 - Mar 19','~Mar 20-22','~May 27-29'),
                     ('2026','Feb 18 - Mar 19', 'Mar 20-22', 'May 27-29'),
                     ('2025','Mar 1-29',         'Mar 30 - Apr 1','Jun 6-9'),
                     ('2024','Mar 11 - Apr 9',   'Apr 10-12','Jun 16-19'),
                     ('2023','Mar 23 - Apr 20',  'Apr 21-23','Jun 28 - Jul 1'),
                     ('2022','Apr 2 - May 1',    'May 2-4',  'Jul 9-12')],
        },
        'Philippines': {
            'headers': ['Year', 'Easter (Holy Week)', 'Academic Year Start', 'Academic Year End'],
            'rows': [('2027','Mar 26 - Apr 1','~Jun 2026','~Mar-Apr 2027'),
                     ('2026','Apr 2-6',        'Jun 16 2025','Mar 31 2026'),
                     ('2025','Apr 17-21',      'Jul 29 2024','May 16 2025'),
                     ('2024','Mar 28 - Apr 1', 'Aug 29 2023','May 31 2024'),
                     ('2023','Apr 6-10',       'Aug 22 2022','Jul 7 2023'),
                     ('2022','Apr 14-18',      '—','—')],
        },
        'Thailand': {
            'headers': ['Year', 'Songkran', 'Loy Krathong'],
            'rows': [('2027','Apr 13-15','Nov 1'),('2026','Apr 13-15','Nov 20'),
                     ('2025','Apr 13-15','Nov 5'),('2024','Apr 13-15','Nov 15'),
                     ('2023','Apr 13-15','Nov 27'),('2022','Apr 13-15','Nov 8')],
        },
        'Vietnam': {
            'headers': ['Year', 'Tết (Lunar New Year)', 'Reunification Day'],
            'rows': [('2027','Jan 26 - Feb 1','Apr 30'),('2026','Feb 17-23','Apr 30'),
                     ('2025','Jan 29 - Feb 4','Apr 30'),('2024','Feb 10-16','Apr 30'),
                     ('2023','Jan 22-28','Apr 30'),('2022','Feb 1-7','Apr 30')],
        },
    },
    'anns': {
        'Indonesia':   [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                         {'lb':'S1','t':'S','hol':'Ramadan','yrs':[2022,2023,2024,2025,2026]},
                         {'lb':'S2','t':'S','hol':'Eid al-Fitr','yrs':[2022,2023,2024,2025,2026]},
                         {'lb':'S3','t':'S','hol':'Eid al-Adha','yrs':[2022,2023,2024,2025,2026]},
                         {'lb':'A5','t':'A','date':datetime.date(2026,2,17)},
                         {'lb':'A16','t':'A','hol':'Decel Sep25','yrs':[2025]}],
        'Philippines': [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                         {'lb':'S1','t':'S','hol':'Easter','yrs':[2022,2023,2024,2025,2026]},
                         {'lb':'S2','t':'S','hol':'PH Acad Start','yrs':[2022,2023,2024,2025,2026]},
                         {'lb':'S3','t':'S','hol':'PH Acad End','yrs':[2023,2024,2025,2026]},
                         {'lb':'A10','t':'A','date':datetime.date(2025,5,15)},
                         {'lb':'A16','t':'A','hol':'Decel Sep25','yrs':[2025]}],
        'Thailand':    [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                         {'lb':'S1','t':'S','hol':'Songkran','yrs':[2022,2023,2024,2025,2026]}],
        'Vietnam':     [{'lb':'T1','t':'T','date':datetime.date(2023,3,1)},
                         {'lb':'S1','t':'S','hol':'Tet','yrs':[2022,2023,2024,2025,2026]},
                         {'lb':'A4','t':'A','date':datetime.date(2026,2,17)},
                         {'lb':'A16','t':'A','hol':'Decel Mar26','yrs':[2026]}],
    },
    'seasonal': {
        'Indonesia':   [('S1','Ramadan','Shifts ~11 days earlier each year. Usage dip during fasting hours. Requires calendar-adjusted YoY comparisons.'),
                         ('S2','Eid al-Fitr (Lebaran)','Largest Indonesian holiday — multi-day celebration after Ramadan. Creates sharp spike then travel-driven dip. Also shifts ~11 days earlier per year.'),
                         ('S3','Eid al-Adha','4-day sacrifice holiday ~70 days after Eid al-Fitr. Secondary seasonal dip. Also shifts ~11 days earlier per year.'),],
        'Philippines': [('S1','Easter (Holy Week)','One of the strongest Easter effects globally — entire Holy Week (Mon-Sun) widely observed. Shifts 2-4 weeks Mar-Apr creating significant YoY distortion.'),
                         ('S2','Academic Year Start','Start date has shifted significantly each year due to post-COVID transition: Aug 22 (2022), Aug 29 (2023), Jul 29 (2024), Jun 16 (2025), ~Jun (2026). Creates a moving engagement lift that changes position by 1-2 months annually. Cannot be compared year-over-year without aligning to the academic calendar, not the calendar month.'),
                         ('S3','Academic Year End','End date also shifts: Jul 7 (2023), May 31 (2024), May 16 (2025), Mar 31 (2026). Each year-end creates a engagement trough as students finish. The Mar 31 2026 end is unusually early and may suppress Q1 2026 MAU.'),],
        'Thailand':    [('S1','Songkran (Thai New Year)','Fixed Apr 13-15 (extended to ~1 week in practice). Creates a reliable mid-Apr dip. Thailand is countercyclical — Jul-Sep is the annual peak (school projects), not a trough.'),],
        'Vietnam':     [('S1','Tết (Lunar New Year)','Largest holiday of the year. Shifts 2-4 weeks Jan-Feb (Jan 29 in 2025 vs Feb 17 in 2026). Creates deepest annual MAU trough. Jan-Mar YoY comparisons require Tết-aligned adjustment.'),],
    },
    'abnorm': {
        'Indonesia':   [('A5','LNY + Ramadan Compound Suppression (Feb 2026)',
                         'For first time, LNY (Feb 17) and Ramadan start (Feb 28) landed in same month. '
                         'Combined suppression created sharpest deceleration on record for Indonesia. '
                         'Recovery expected sharply post-Eid (~Mar 30). Not structural — compound holiday timing artefact.'),
                        ('A16','Growth Rate Deceleration from Sep 2025',
                         'YoY growth rate declined materially from Sep 2025 vs prior years by -11.2pp, steeper than seasonal norms. Monitoring continues into Q1 2026.'),
                        ('T2','Post-AI Normalisation',
                         'YoY growth has decelerated since 2023 as the inflated base rolls through comparisons.')],
        'Philippines': [('A10','Anomalous May 2025 Trough (-8.5% YoY, -56pp Swing)',
                         'No confirmed holiday or event explanation. Likely data/classification issue or inflated May 2024 base. '
                         'Jul 2025 spike (+67.6% YoY) is partial unwinding of this base effect — not a real acceleration.'),
                        ('A16','Growth Rate Deceleration from Sep 2025',
                         'YoY growth rate declined materially from Sep 2025 vs prior years by -47.0pp, steeper than seasonal norms. Monitoring continues into Q1 2026. '
                         'Note: significantly inflated by the May 2024 spike base effect — underlying deceleration is materially smaller.'),
                        ('S2b','Academic Year Multi-Year Calendar Shift',
                         'Philippines academic year has shifted significantly each year post-COVID: '
                         'Aug 22 start / Jul 7 end (2022-23), Aug 29 / May 31 (2023-24), Jul 29 / May 16 (2024-25), Jun 16 / Mar 31 (2025-26). '
                         'Each year the start moves ~1-2 months earlier, progressively shifting the engagement lift window forward. '
                         'The 2025-26 end date of Mar 31 2026 is unusually early and likely suppresses Q1 2026 MAU. '
                         'YoY comparisons require full academic-calendar alignment — calendar-month comparisons are unreliable for this market.'),
                        ('T2','Post-AI Normalisation',
                         'YoY growth has decelerated since 2023 as the inflated base rolls through comparisons.')],
        'Thailand':    [('S7','Songkran Countercyclical Pattern',
                         'Thailand is countercyclical — Jul-Sep is the annual peak (school winter projects), not a trough. '
                         'Do not apply Northern Hemisphere summer trough assumptions to Thailand.'),
                        ('T2','Post-AI Normalisation',
                         'YoY growth has decelerated since 2023 as the inflated base rolls through comparisons.')],
        'Vietnam':     [('A4','Tết Timing: -6.4% YoY Mar 2026 (-57pp Swing)',
                         'Tết 2026 fell Feb 17 vs Tết 2025 Jan 29 — 19-day shift. Mar 2026 still in trough while Mar 2025 had fully recovered. '
                         'Not structural — daily recovery visible from Mar 9 2026. Feb 2026 figure (+42.4% YoY) is the reverse inflation.'),
                        ('A16','Growth Rate Deceleration from Mar 2026',
                         'YoY growth rate declined materially from Mar 2026 vs prior years by -35.1pp, steeper than seasonal norms. Monitoring continues into Q1 2026. '
                         'Note: significantly inflated by Tết timing effects in Mar 2026 — not representative of underlying trend.'),
                        ('T2','Post-AI Normalisation',
                         'YoY growth has decelerated since 2023 as the inflated base rolls through comparisons.')],
    },
}



# ─────────────────────────────────────────────────────────────────────────────
# CHART & PAGE RENDERING
# ─────────────────────────────────────────────────────────────────────────────

def doy_to_frac(doy, yr):
    days = 366 if yr % 4 == 0 else 365
    return (doy - 1) / days


def make_svg_full(col_name, anns):
    # Taller canvas + padding so month labels and right-edge ticks aren’t clipped when
    # CSS scales the SVG (width:100%; height:auto). viewBox keeps aspect ratio uniform.
    W, H = 800, 420
    PL, PR, PT, PB = 58, 44, 22, 56

    series = {}
    for yr in [2021, 2022, 2023, 2024, 2025, 2026]:
        pts = []
        for _, row in raw.iterrows():
            d = row['Date'].date()
            if d.year != yr or d > TODAY:
                continue
            val = float(row[col_name])
            if val <= 0:
                continue
            frac = doy_to_frac(d.timetuple().tm_yday, yr)
            pts.append((frac, val / 1e6))
        if pts:
            series[yr] = sorted(pts)

    all_vals = [v for pts in series.values() for _, v in pts]
    if not all_vals:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet"/>'
        )
    vmin, vmax = min(all_vals) * 0.96, max(all_vals) * 1.04

    def fx(frac): return PL + frac * (W - PL - PR)
    def fy(v):    return PT + (1 - (v - vmin) / (vmax - vmin)) * (H - PT - PB)

    parts = []

    rng = vmax - vmin
    step = 10 if rng > 30 else (5 if rng > 15 else (2 if rng > 6 else 1))
    yticks = [v for v in range(0, 500, step) if vmin <= v <= vmax]
    for v in yticks:
        y = fy(v)
        parts.append(f'<line x1="{PL}" y1="{y:.1f}" x2="{W-PR}" y2="{y:.1f}" stroke="#f0f0f0" stroke-width="1"/>')
        parts.append(f'<text x="{PL-5}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="#888">{v}m</text>')

    months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec','Jan']
    axis_y = H - 18  # baseline inside viewBox (below plot, above svg bottom)
    for i, m in enumerate(months):
        x = fx(i / 12)
        parts.append(f'<line x1="{x:.1f}" y1="{PT}" x2="{x:.1f}" y2="{H-PB}" stroke="#f5f5f5" stroke-width="1"/>')
        parts.append(f'<text x="{x:.1f}" y="{axis_y}" text-anchor="middle" font-size="11" fill="#666">{m}</text>')

    parts.append(f'<rect x="{PL}" y="{PT}" width="{W-PL-PR}" height="{H-PT-PB}" fill="none" stroke="#e0e0e0" stroke-width="1"/>')

    for yr, pts in series.items():
        coords = ' '.join(f'{fx(f):.1f},{fy(v):.1f}' for f, v in pts)
        lw = 2.8 if yr >= 2025 else (2.2 if yr == 2024 else 1.8)
        opacity = 1.0 if yr >= 2024 else (0.85 if yr == 2023 else 0.6)
        parts.append(f'<polyline points="{coords}" fill="none" stroke="{YEAR_COLORS[yr]}" '
                     f'stroke-width="{lw}" stroke-opacity="{opacity}" '
                     f'stroke-linejoin="round" stroke-linecap="round"/>')

    def val_at(yr, target_frac):
        if yr not in series:
            return None
        pts = series[yr]
        best = min(pts, key=lambda p: abs(p[0] - target_frac))
        return best[1]

    for ann in anns:
        dot_points = []
        if 'hol' in ann:
            for yr in ann['yrs']:
                d = HOL[ann['hol']].get(yr)
                if d and d <= TODAY:
                    frac = doy_to_frac(d.timetuple().tm_yday, yr)
                    v = val_at(yr, frac)
                    if v:
                        dot_points.append((frac, v, yr, f"{ann['lb']} {yr}"))
        elif 'date' in ann:
            d = ann['date']
            if d <= TODAY:
                yr = d.year
                frac = doy_to_frac(d.timetuple().tm_yday, yr)
                v = val_at(yr, frac)
                if v:
                    dot_points.append((frac, v, yr, ann['lb']))

        for frac, v, yr, lbl in dot_points:
            x, y = fx(frac), fy(v)
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{DOT_COLOR}" stroke="white" stroke-width="1.5"/>')
            lx, ly = x + 7, y - 5
            parts.append(f'<rect x="{lx-1}" y="{ly-9}" width="{len(lbl)*6+4}" height="12" fill="white" opacity="0.85" rx="2"/>')
            parts.append(f'<text x="{lx}" y="{ly}" font-size="9.5" font-weight="bold" fill="{DOT_COLOR}">{lbl}</text>')

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" '
        f'style="background:white;max-width:100%;height:auto;display:block">{"".join(parts)}</svg>'
    )


def page_html(region_key, label, col_name):
    R = REGIONS[region_key]
    anns     = R['anns'][label]
    hol_cfg  = R['holiday_table'][label]
    seasonals = R['seasonal'].get(label, [])
    abnormals = R['abnorm'].get(label, [])

    svg = make_svg_full(col_name, anns)

    # Holiday table — supports variable column count
    headers = hol_cfg['headers']
    th_row  = ''.join(f'<th>{h}</th>' for h in headers)
    tbl = ''
    for i, r in enumerate(hol_cfg['rows']):
        cls = 'alt' if i % 2 else ''
        tbl += f'<tr class="{cls}">' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>'

    # Legend
    leg = ''.join(
        f'<span class="li"><span class="ll" style="background:{YEAR_COLORS[yr]}"></span>{yr}</span>'
        for yr in [2021, 2022, 2023, 2024, 2025, 2026]
    )

    # Commentary — all labels use one red class
    def comm():
        h = ''
        if abnormals:
            h += '<p class="ch">Abnormalities</p><ul>'
            for lbl2, short, detail in abnormals:
                h += (f'<li><span class="albl">{lbl2}</span> <strong>{short}</strong>'
                      f'<br><span class="det">{detail}</span></li>')
            h += '</ul>'
        if seasonals:
            h += '<p class="ch">Major Moving Holidays &amp; Seasonal</p><ul>'
            for lbl2, short, detail in seasonals:
                h += (f'<li><span class="albl">{lbl2}</span> <strong>{short}</strong>'
                      f'<br><span class="det">{detail}</span></li>')
            h += '</ul>'
        return h

    max_date = raw[raw['Date'].dt.date <= TODAY]['Date'].max().date()

    return f"""
<div class="page">
  <div class="ptitle">{label} - Daily MAU Seasonality: Variance Commentary</div>
  <div class="psub">Rolling 30-day MAU | Data to {max_date.strftime('%b %d %Y')} | Report: {TODAY.strftime('%b %d %Y')}</div>
  <div class="hol-wrap">
    <div class="hol-title">Major Moving Holidays</div>
    <table class="hol"><tr>{th_row}</tr>{tbl}</table>
  </div>
  <div class="leg-row"><span class="lt">Year:</span>{leg}</div>
  <div class="chart-wrap">{svg}</div>
  <div class="ann-key">
    <span>All chart annotations in red &nbsp;|&nbsp; <strong>A</strong> Abnormal &nbsp; <strong>S</strong> Seasonal &nbsp; <strong>T</strong> Structural trend</span>
  </div>
  <div class="comm">{comm()}</div>
</div>"""


CSS = """
@page{size:A4 portrait;margin:12mm 12mm 10mm 12mm;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:-apple-system,"Helvetica Neue",Arial,sans-serif;font-size:9pt;color:#222;}
.page{page-break-after:always;}.page:last-child{page-break-after:auto;}
.ptitle{font-size:13pt;font-weight:700;color:#111;margin-bottom:1px;}
.psub{font-size:8pt;color:#888;margin-bottom:6px;}
.hol-wrap{margin-bottom:6px;}
.hol-title{font-size:9pt;font-weight:700;color:#333;margin-bottom:3px;text-align:center;}
table.hol{margin:0 auto;border-collapse:collapse;font-size:7.5pt;}
table.hol th{background:#f0f0f0;font-weight:700;padding:3px 9px;border:1px solid #ddd;text-align:center;}
table.hol td{padding:2px 9px;border:1px solid #eee;text-align:center;}
table.hol tr.alt td{background:#fafafa;}
.leg-row{display:flex;align-items:center;gap:12px;margin-bottom:4px;font-size:8pt;}
.lt{font-weight:700;}
.li{display:flex;align-items:center;gap:4px;}
.ll{display:inline-block;width:20px;height:3px;border-radius:2px;}
.chart-wrap{margin-bottom:5px;border:1px solid #e8e8e8;border-radius:5px;overflow:visible;padding:2px 0 6px;}
.chart-wrap svg{width:100%;max-width:100%;height:auto;display:block;vertical-align:middle;}
.ann-key{font-size:7.5pt;color:#666;margin-bottom:5px;}
.comm{border:1px solid #e5e5e5;border-radius:5px;padding:8px 12px;background:#fafcff;}
.ch{font-size:8.5pt;font-weight:700;color:#222;margin:0 0 4px;border-bottom:1px solid #e8e8e8;padding-bottom:2px;}
ul{padding-left:14px;margin-bottom:5px;}
li{margin-bottom:4px;font-size:8pt;line-height:1.5;}
.albl{font-weight:700;color:#D6006E;}
.det{color:#555;font-size:7.5pt;}
"""


if __name__ == '__main__':
    all_pages = ''
    for region_key in REGIONS:
        print(f'\n=== Building: {region_key} ===')
        for label, col_name in REGIONS[region_key]['countries']:
            print(f'  Rendering: {label}')
            all_pages += page_html(region_key, label, col_name)

    html_str = f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{all_pages}</body></html>'
    html_path = os.path.join(OUT_DIR, 'Global_Daily_Commentary.html')
    out_path  = os.path.join(OUT_DIR, 'Global_Daily_Commentary.pdf')

    # Write HTML first (always works, useful as fallback)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_str)
    print(f'HTML saved -> {html_path}')

    # Try PDF via WeasyPrint, then via Chrome headless, then give up gracefully
    pdf_ok = False

    # Attempt 1: WeasyPrint
    try:
        from weasyprint import HTML
        HTML(string=html_str).write_pdf(out_path)
        print(f'PDF saved  -> {out_path}')
        pdf_ok = True
    except Exception as e:
        print(f'WeasyPrint failed ({e}), trying Chrome...')

    # Attempt 2: Chrome headless (works on any Mac with Chrome installed)
    if not pdf_ok:
        import subprocess, shutil
        chrome_paths = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/Applications/Chromium.app/Contents/MacOS/Chromium',
            shutil.which('chromium'), shutil.which('google-chrome'),
        ]
        chrome = next((p for p in chrome_paths if p and os.path.exists(p)), None)
        if chrome:
            result = subprocess.run([
                chrome,
                '--headless', '--disable-gpu', '--no-sandbox',
                f'--print-to-pdf={out_path}',
                '--print-to-pdf-no-header',
                f'file://{html_path}'
            ], capture_output=True, text=True)
            if os.path.exists(out_path):
                print(f'PDF saved  -> {out_path}  (via Chrome)')
                pdf_ok = True
            else:
                print(f'Chrome failed: {result.stderr[:200]}')
        else:
            print('Chrome not found.')

    if not pdf_ok:
        print(f'\nCould not generate PDF. Open the HTML file directly in Chrome and Print → Save as PDF:\n  {html_path}')