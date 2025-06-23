#imports
from openai import OpenAI
import json
import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
import streamlit as st
load_dotenv()
import numpy as np
#from fpdf import FPDF
import re
from typing import List, Dict

# Setup

#PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_KEY = st.secrets["api"]["PERPLEXITY_API_KEY"]

client = OpenAI(api_key=PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")



#load_dotenv()
#FMP_API_KEY = os.getenv("FMP_API_KEY")
#OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
#DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Load environment variables
FMP_API_KEY = st.secrets["api"]["FMP_API_KEY"]
OPENAI_API_KEY = st.secrets["api"]["OPENAI_API_KEY"]
DEEPSEEK_API_KEY = st.secrets["api"]["DEEPSEEK_API_KEY"]



#openai.api_key = OPENAI_API_KEY



#Initialize AI clients

openai_client = OpenAI(api_key=OPENAI_API_KEY)
deepseek_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)



# Using Transcript

# Fetch income statement growth data for a symbol


def get_income_statement_growth(symbol):
    url = f"https://financialmodelingprep.com/api/v3/income-statement-growth/{symbol}?apikey={FMP_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if len(data) > 0:
            return data[0]  # Return the latest growth data
    return None


def get_revenue_growth(symbol):
    data = get_income_statement_growth(symbol)
    # Convert the growth revenue to percentage
    growth_revenue = data.get('growthRevenue')
    if growth_revenue is not None:
        growth_revenue *= 100

    # Append a dictionary with all the needed information (adding 'symbol' for the merge)
    data_list = {
        'symbol': symbol,
        'growthRevenue': growth_revenue,
        'calendarYear': data.get('calendarYear'),
        'date': data.get('date')
    }
            
    return data_list

# Old code just for reference

def get_revenue_growth_old(symbol):
    
    url = f"https://financialmodelingprep.com/api/v3/income-statement/{symbol}?limit=2&apikey={FMP_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # will raise an HTTPError on failure
        data = response.json()
        # Validate that we got at least two periods of income statements
        if isinstance(data, list) and len(data) >= 2:
            latest_entry = data[0]
            previous_entry = data[1]
            # Extract revenue values
            latest_revenue = latest_entry.get('revenue')
            previous_revenue = previous_entry.get('revenue')
            
            if latest_revenue is not None and previous_revenue and previous_revenue != 0:
                growth = ((latest_revenue - previous_revenue) / previous_revenue) * 100
                return growth
            else:
                print(f"Revenue not found or previous revenue is zero for {symbol}.")
        else:
            print(f"Not enough income statement data returned for {symbol}: {data}")
    except requests.HTTPError as http_err:
        print(f"HTTP error for {symbol}: {http_err}")
    except Exception as err:
        print(f"Error processing data for {symbol}: {err}")
        
    return None

#Filter high growth companies based on revenue growth threshold

def filter_high_growth(df, revenue_growth_threshold=10):
    # Ensure numeric values and drop missing
    df = df[pd.to_numeric(df['revenueGrowth'], errors='coerce').notnull()]
    df['revenueGrowth'] = df['revenueGrowth'].astype(float)
    high_growth = df[df['revenueGrowth'] > revenue_growth_threshold]
    high_growth['high_growth_flag'] = True
    return high_growth

# CELL 4: Fetch earning call transcripts

def get_transcript(symbol):
    import pandas as pd


def get_transcript(symbol):
    """Check Excel for transcript; fetch from API and update Excel only if missing."""
    excel_path = "data/sp500_companies_growth.xlsx"
    df = pd.read_excel(excel_path, engine='openpyxl')
    if 'transcript' not in df.columns:
        df['transcript'] = ""
    mask = df['symbol'] == symbol
    # Check if transcript exists and is a non-empty string
    if mask.any():
        transcript_val = df.loc[mask, 'transcript'].iloc[0]
        if isinstance(transcript_val, str) and transcript_val.strip():
            return transcript_val
        if isinstance(transcript_val, float) and not np.isnan(transcript_val):
            # If it's a float but not nan, treat as empty
            return ""
    # If not present, fetch from API
    url = f"https://financialmodelingprep.com/api/v3/earning_call_transcript/{symbol}?apikey={FMP_API_KEY}"
    response = requests.get(url)
    transcript = ""
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            transcript = " ".join([entry.get('content', '') for entry in data if entry.get('content')])
        # Update Excel
        df.loc[mask, 'transcript'] = transcript
        df.to_excel(excel_path, index=False)
    return transcript




def extract_growth_chunks(transcript: str, window_size: int = 3) -> List[str]:
    """
    Extract transcript chunks mentioning organic or inorganic (M&A-driven) growth.
    
    Args:
        transcript: The earnings transcript as a string.
        window_size: Number of sentences to include around the target sentence.
    
    Returns:
        List of relevant transcript chunks (strings).
    """
    # Define keyword patterns
    growth_terms = [
        r'growth', r'revenue \w+', r'sales \w+', r'expand',
        r'increas(e|ing)', r'ris(e|ing)', r'surge', r'soar',
        r'jump', r'spike', r'swell', r'escalat(e|ing)'
    ]
    organic_indicators = [
        r'organic', r'same-store', r'comparable', r'like-for-like',
        r'existing operations', r'core business', r'underlying growth',
        r'without acquisition', r'excluding M&A', r'operational efficiency', r'price mix'
    ]
    inorganic_indicators = [
        r'acquis(ition|ed)', r'merger', r'consolidation', r'divestiture',
        r'buyout', r'takeover', r'purchase', r'deal', r'transaction',
        r'integration', r'synergy', r'goodwill', r'asset purchas(e|ing)',
        r'M&A', r'non-organic', r'external growth'
    ]
    # Compile regex patterns
    organic_pattern = re.compile(
        r'(' + '|'.join(growth_terms) + r').*?(' + '|'.join(organic_indicators) + r')',
        re.IGNORECASE | re.DOTALL
    )
    inorganic_pattern = re.compile(
        r'(' + '|'.join(growth_terms) + r').*?(' + '|'.join(inorganic_indicators) + r')',
        re.IGNORECASE | re.DOTALL
    )
    # Split transcript into sentences
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', transcript)
    chunks = []
    for i, sentence in enumerate(sentences):
        if organic_pattern.search(sentence) or inorganic_pattern.search(sentence):
            start = max(0, i - window_size)
            end = min(len(sentences), i + window_size + 1)
            chunk = ' '.join(sentences[start:end])
            chunks.append(chunk)
    # Remove duplicates while preserving order
    seen = set()
    unique_chunks = []
    for chunk in chunks:
        if chunk not in seen:
            unique_chunks.append(chunk)
            seen.add(chunk)
    return unique_chunks




def analyze_growth_with_ai(transcript, model="gpt-4o-mini", chunk_size=2000, overlap=200):
    """
    Analyze transcripts in chunks to handle long documents.
    Processes each chunk and aggregates final results.
    """
    # Split transcript into overlapping chunks to maintain context
    #chunks = extract_growth_chunks(transcript)
    """if not chunks:
        return {
            "inorganic_flag": False,
            "evidence": ["No relevant growth information found."],
            "confidence": 0.0
        }
    """
    chunks = [transcript[i:i+chunk_size] for i in range(0, len(transcript), chunk_size-overlap)]
    # Initialize result containers
    all_evidence = []
    inorganic_flag = []
    confidence = [-1]
    
    # Process each chunk iteratively
    for i, chunk in enumerate(chunks):
        prompt = f"""  
        Task: Analyze the provided transcript excerpt to determine if recent revenue growth was driven by Merger and Acquisition (M&A) activities. Follow these steps:  

        1. Keyword Search:  
           - Search for terms like "acquisition," "merger," "buyout," "takeover," or "M&A integration."  
           - Prioritize quantitative evidence (e.g., "Acquisition X contributed 15% of Q4 revenue growth") over qualitative claims.  

        2. Evidence Evaluation:  
           - If M&A-linked growth is explicitly stated (e.g., "Our 20% YoY revenue increase was primarily due to the ABC acquisition"), set `inorganic_flag = 1`.  
           - Exclude generic statements like "we focus on strategic growth" without numerical correlation.  

        3. Contextual Filtering:  
           - Focus on sections discussing:  
             - Post-acquisition revenue contributions.  
             - Integration timelines or synergies.  
             - Management commentary on growth drivers (e.g., "M&A remains central to our growth strategy") [[10]].  

     Return a output strictly in below format:     
        ## Output Format:  
    
        ## output:
        {{  
          "inorganic_growth": <INT>,  
          "evidence": [<str>],  
          "confidence_score": <float>  
        }}  
        ## end
        
        ## Transcript Excerpt:  
        {i+1}/{len(chunks)}  
        
        """
        
        try:
            # Select appropriate client based on model
            client = openai_client if model == "gpt-4o-mini" else deepseek_client
            
            response = client.chat.completions.create(
                model="gpt-4o-mini" if model == "gpt-4o-mini" else "deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a financial analyst specializing in growth analysis"},
                    {"role": "user", "content": f"{prompt}\n\n{chunk}"}
                ],
                timeout=30
            )
            print(response.choices[0].message.content)
            result = json.loads(response.choices[0].message.content.lower().split("output:")[1].split("##")[0].strip()) 
            inorganic_flag.append(result["inorganic_growth"])
            all_evidence.extend(result["evidence"])
            confidence.append(result["confidence_score"])
            if result["inorganic_growth"]== 1:
                break
            # Rate limit handling
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing chunk {i+1}: {str(e)}")
            #continue
        
            
            
    # Aggregate results across all chunks
    final_organic = any(inorganic_flag)  # Mark organic if any chunk shows organic growth
    final_evidence = list(set(all_evidence))  # Remove duplicates
    
    return {
        "inorganic_flag": final_organic,
        "inorganic_evidence": final_evidence,
        "inorganic_confidence": confidence[-1]
    }



def extract_roi_chunks(transcript: str, window_size: int = 2):
    """
    Extract relevant text chunks mentioning ROI/ROIC improvements from a transcript.
    
    Args:
        transcript: Full text of the transcript
        window_size: Number of sentences to include around the target sentence
    
    Returns:
        List of relevant text chunks with context
    """
    # Keywords and patterns to search for
    roi_keywords = [
        r'\bROI\b', r'\bROIC\b', r'return on invested capital',
        r'return on capital', r'capital efficiency', 
        r'capital allocation', r'capital returns'
    ]
    
    improvement_terms = [
        r'improve', r'increas(e|ing)', r'growth', r'expand', 
        r'enhan(ce|cing)', r'optimiz(e|ing)', r'boost', 
        r'higher', r'better', r'strengthen'
    ]

    # Create regex pattern
    pattern = re.compile(
        r'(' + '|'.join(roi_keywords) + r').*?(' + '|'.join(improvement_terms) + r')',
        re.IGNORECASE | re.DOTALL
    )

    # Split transcript into sentences
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', transcript)
    
    relevant_chunks = []
    
    # Find matches and collect context
    for i, sentence in enumerate(sentences):
        if pattern.search(sentence):
            start = max(0, i - window_size)
            end = min(len(sentences), i + window_size + 1)
            chunk = ' '.join(sentences[start:end])
            
            # Highlight key terms
            chunk = re.sub(
                pattern, 
                lambda m: f"**{m.group().strip()}**", 
                chunk
            )
            
            relevant_chunks.append(chunk)

    # Remove duplicate chunks
    seen = set()
    unique_chunks = [chunk for chunk in relevant_chunks 
                    if not (chunk in seen or seen.add(chunk))]
    
    return unique_chunks





def analyze_growth_roi(transcript, model="gpt-4o-mini", chunk_size=1500, overlap=200):
    """
    Analyze transcripts in chunks to handle long documents.
    Processes each chunk and aggregates final results.
    """
    # Ensure transcript is a string and not nan/float
    if not isinstance(transcript, str) or not transcript.strip():
        return {
            "inorganic_flag": False,
            "inorganic_evidence": ["Transcript missing or invalid."],
            "inorganic_confidence": 0.0
        }
    # Now safe to use len(transcript)
    #chunks = extract_roi_chunks(transcript)
    """if not chunks:
        return {
            "roi_flag": False,
            "roi_evidence": ["No relevant ROI/ROIC information found."],
            "confidence": 0.0
        }"""
    chunks = [transcript[i:i+chunk_size] for i in range(0, len(transcript), chunk_size-overlap)]
   # Initialize result containers
    all_evidence = []
    roi_flag = []
    confidence = [-1]

    # Process each chunk iteratively
    for i, chunk in enumerate(chunks):
        prompt = f"""  
        Task: Analyze the provided transcript excerpt to determine if the company has reported significant improvements in Return on Capital metrics (e.g., ROI, ROIC). Follow these steps:

        1. Keyword Search:
           - Search for terms like "ROI", "ROIC", "Return on Invested Capital", "Return on Capital", or "capital efficiency".
           - Prioritize quantitative evidence (e.g., "ROIC improved to 14% this quarter from 10% last year") over qualitative claims.

        2. Evidence Evaluation:
           - If explicit improvement or high levels of ROI/ROIC are stated (e.g., "Our ROI increased by 300 basis points"), set `roi_flag = 1`.
           - Exclude generic statements like "we focus on capital efficiency" without numerical correlation.

        3. Contextual Filtering:
           - Focus on sections discussing:
             - Year-over-year or quarter-over-quarter changes in ROI/ROIC.
             - Management commentary on capital allocation effectiveness.
             - Comparison to industry benchmarks or historical performance.

        Return output strictly in the below format:

        ## Output Format:

        ## output:
        {{
          "roi_flag": <INT>,  
          "roi_evidence": [<str>],  
          "confidence_score": <float>
        }}
        ## end

        ## Transcript Excerpt:
        {i+1}/{len(chunks)}
        """

        try:
            # Select appropriate client based on model
            client = openai_client if model == "gpt-4o-mini" else deepseek_client

            response = client.chat.completions.create(
                model="gpt-4o-mini" if model == "gpt-4o-mini" else "deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a financial analyst specializing in capital efficiency and ROI analysis."},
                    {"role": "user", "content": f"{prompt}\n\n{chunk}"}
                ],
                timeout=30
            )
            print(response.choices[0].message.content)
            # Parse output strictly between 'output:' and '##'
            result = json.loads(
                response.choices[0].message.content.lower().split("output:")[1].split("##")[0].strip()
            )
            roi_flag.append(result["roi_flag"])
            all_evidence.extend(result["roi_evidence"])
            confidence.append(result["confidence_score"])
            if result["roi_flag"] == 1:
                break
            # Rate limit handling
            time.sleep(1)

        except Exception as e:
            print(f"Error processing chunk {i+1}: {str(e)}")
            #continue

    # Aggregate results across all chunks
    final_roi = any(roi_flag)
    final_evidence = list(set(all_evidence))  # Remove duplicates

    return {
        "roi_flag": final_roi,
        "roi_evidence": final_evidence,
        "roi_confidence": confidence[-1]
    }


def using_transcript(ticker,model,check_non_organic,check_roi,threshold=0):
    transcript = get_transcript(ticker)
    result = None
    print(f"Using model: {model} for ticker: {ticker}")
    if model == "GPT-4o-Mini":
        if check_non_organic:
            result =  analyze_growth_with_ai(transcript, model="gpt-4o-mini", chunk_size=2000, overlap=200)   
        if check_roi:
            if result is None:
                result = analyze_growth_roi(transcript, model="gpt-4o-mini", chunk_size=2000, overlap=200)
                return result
            else:
                # If both checks are true, merge results
                inorganic_result = analyze_growth_with_ai(transcript, model="gpt-4o-mini", chunk_size=2000, overlap=200)
                roi_result = analyze_growth_roi(transcript, model="gpt-4o-mini", chunk_size=2000, overlap=200) 
                result = merge_on_ticker_and_prefix(roi_result, inorganic_result)
                return result
    else:
        if check_non_organic:
            # Use DeepSeek for non-organic growth analysis  
            result = analyze_growth_with_ai(transcript, model="deepseek", chunk_size=2000, overlap=200)
            
        if check_roi:
            if result is None:
                result = analyze_growth_roi(transcript, model="deepseek", chunk_size=2000, overlap=200)
                return result
            else:
                # If both checks are true, merge results
                inorganic_result = analyze_growth_with_ai(transcript, model="deepseek", chunk_size=2000, overlap=200)
                roi_result = analyze_growth_roi(transcript, model="deepseek", chunk_size=2000, overlap=200) 
                result = merge_on_ticker_and_prefix(roi_result, inorganic_result)
                return result

    #print(result)
    return result



# Perplexity

def perpx_organic(ticker,threshold):
    prompt = f"""
    **Role**: Act as a financial analyst and M&A researcher specializing in revenue growth attribution [[1]][[4]].
    
    **Task**: For {ticker}, determine whether recent revenue growth is primarily **inorganic** (driven by M&A) or **organic** (core operations). Follow these steps:
    
    ---
    
    ### Step 1: Revenue Growth Analysis  
    1. Identify the **total revenue growth percentage** for {ticker} in the most recent fiscal year (as of May 2025).  
    2. List **key drivers** of growth (e.g., internal sales, market expansion, pricing, or acquisitions).  
    
    ---
    
    ### Step 2: M&A Activity Search  
    1. Search for **documented mergers, acquisitions, or divestitures** during the same period. Include:  
       - Dates of the transaction.  
       - Transaction value (e.g., "$1.2B acquisition of XYZ Corp in Q3 2024").  
       - Source (e.g., SEC filings, investor transcripts, press releases) [[6]][[7]].  
    
    2. Prioritize evidence from:  
       - **Earnings call transcripts** (search for keywords like "acquisition," "M&A integration," or "revenue contribution").  
       - **SEC filings** (10-K/annual reports or 8-K filings for material transactions).  
       - **Reputable news outlets** (Bloomberg, Reuters, CNBC, Financial Times).  
    
    ---
    
    ### Step 3: Correlation & Evidence Strength  
    1. Analyze whether M&A activity directly correlates with revenue spikes. For example:  
       - Did acquired businesses contribute >10% of total revenue growth?  
       - Were there explicit statements in transcripts like, "Acquisition X drove Y% of our growth"?  
    2. Rank evidence quality (High/Medium/Low) based on source credibility and specificity.  
    
    ---
    
    ###  Step 4: Final Output Structure  
    Return output strictly in below format:  
    
    ```Output:
    {{
    "Ticker": "<STRING>",
    "Growth %": "<STRING>",
    "Inorganic Growth": "<Yes/No>",
    "Inorganic Evidence Summary": <LIST [Key M&A events or organic drivers]>,
    "Inorganic Source Links":  <LIST [Links to SEC filings, transcripts, or news]>
    }}
    ```end


    ---
    
    **Constraints**:  
    - Focus on **last 12 months** (May 2024–May 2025).  
    - Exclude speculative statements (e.g., "may contribute in the future").  
    - Prioritize quantitative data over qualitative claims.  
    """
    
    
    response = client.chat.completions.create(
        model="sonar-deep-research",
        #model = "sonar",
        messages=[{"role": "user", "content": prompt}],
        stream=False
    )
    
    result = response.choices[0].message.content.strip()
    print(result)
    result = json.loads(result.lower().split("output:")[1].split("```")[0].strip())
    #print(result)
    return result   



def perpx_roi(ticker):    
    prompt = f"""
    **Role**: Act as a financial analyst specializing in capital efficiency metrics.
    
    **Task**: For {ticker}, determine whether there are **explicit improvements in Return on Capital (ROIC/ROI)** metrics in recent earnings reports or presentations. Focus on management commentary or quantitative data supporting such claims. 
    Follow these steps:
    
    ---
    
    ### Step 1: Metric Identification  
    1. Identify the **latest ROIC/ROI percentage** for {ticker} in the most recent fiscal year (as of May 2025).  
    2. Compare it to the prior year to calculate the **improvement percentage**.  
    
    ---
    
    ### Step 2: Evidence Collection  
    1. Search for:  
       - Management statements explicitly mentioning ROIC/ROI improvements (e.g., "We increased ROIC to X% through Y strategy").  
       - Presentation slides or earnings call transcripts where such metrics are highlighted.  
       - SEC filings (e.g., 10-K/annual reports) or press releases documenting strategic actions (e.g., cost optimization, asset divestitures).  
    
    2. Prioritize evidence from:  
       - **Earnings call transcripts** (search for keywords like "capital efficiency," "ROIC improvement," or "return on investment").  
       - **Investor presentations** (focus on slides discussing financial ratios).  
       - **SEC filings** (10-K annual reports or 8-K filings for material changes).  
    
    ---
    
    ### Step 3: Correlation & Evidence Strength  
    1. Analyze whether improvements are linked to **strategic actions**:  
       - Cost-cutting initiatives.  
       - Divestitures of underperforming assets.  
       - Operational restructuring.  
    2. Rank evidence quality (High/Medium/Low) based on source credibility and specificity.  
    
    ---
    
    ###  Step 4: Final Output Structure  
    Return output strictly in below format: 
    
    ```Output:
    {{
    "Ticker": "<ticker>",
    "ROI Flag": "<YES/NO>",
    "ROI Metric": "<ROIC/ROI>",
    "ROI Improvement %": "<STRING>",
    "ROI Evidence Summary": [<list of evidence>],
    "ROI Source Links" : [<list of source links>]
    }}
    ```End
    
    ---
    
    **Constraints**:  
    - Focus on **last 12 months** (May 2024–May 2025).  
    - Exclude generic statements like "we focus on capital efficiency" without numbers.  
    - Prioritize quantitative data over qualitative claims.  
    """
    
    response = client.chat.completions.create(
        #model="sonar",
        model="sonar-deep-research",
        messages=[{"role": "user", "content": prompt}],
        stream=False
    )
    
    result = response.choices[0].message.content.strip()
    print(result)
    result = json.loads(result.lower().split("output:")[1].split("```")[0].strip())
    return result   


def merge_on_ticker_and_prefix(dict1, dict2):
    # Check if tickers match
    if dict1.get("Ticker") != dict2.get("Ticker"):
        return None  # or raise Exception, or handle as needed

    merged = {}

    # Prefix and add keys from dict1
    for key, value in dict1.items():
        if key != "Ticker":
            merged[key] = value
        else:
            merged[key] = value  # Keep Ticker as is

    # Prefix and add keys from dict2 (except Ticker, already added)
    for key, value in dict2.items():
        if key != "Ticker":
            merged[key] = value

    return merged


def perplexity(ticker, check_non_organic,check_roi, threshold):
    result = -1
    if check_non_organic:
        result = perpx_organic(ticker,threshold)
    if check_roi:
        if result == -1:
            result1 = perpx_roi(ticker)
            return result1
        else:
            result1 = perpx_roi(ticker)
            result = merge_on_ticker_and_prefix(result1, result)
            if result is None:
                return {"error": "Ticker mismatch in results"}
    return result


def main_fun(ticker, model, check_non_organic, check_roi, threshold=0):
    if model == "Perplexity":
        print("Using Perplexity for analysis...")
        results = perplexity(ticker,check_non_organic,check_roi,threshold)
        
        """results = {"Ticker": "Dummy Ticker",  # Replace with actual ticker
    "growth %": 15.0,  # Replace with actual growth percentage",
    "inorganic growth": "YES",
    "inorganic evidence summary": ["acz","dfz"],
    "inorganic source links":  ["abc"],
    "roi/roic metric": "<ROIC/ROI>",
    "roi/roic improvement %": 11.1,
    "roi flag": "YES",
    "roi/roic evidence summary": ["<list of evidence>"],
    "roi/roic source links" : ["<list of source links>"]
    }"""
        
    else:
        results = using_transcript(ticker,model,check_non_organic,check_roi,threshold)
        """results = {
            "inorganic_flag": "YES",
            "inorganic_evidence": ["No inorganic growth detected.","No M&A activity found."],
            "inorganic_Confidence": 0.0,
            "roi_flag": "NO",
            "roi_evidence": ["No ROI improvements detected."],
            "roi_Confidence": 0.0
        }"""
    #print(results)
    return results