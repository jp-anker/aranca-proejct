import streamlit as st
import pandas as pd
import time
from analysis import *
from datetime import datetime

# ========================
# Data Loading Functions
# ========================

def load_sp500_companies():
    """Mock S&P 500 data - replace with actual data source"""
    df  = pd.read_excel("Data/sp500_companies_growth.xlsx", engine='openpyxl')
    return df
 # Cache data for 1 hour
def load_sp500_companies():
    """Load S&P 500 data from Excel file"""
    df = pd.read_excel("Data/sp500_companies_growth.xlsx", engine='openpyxl')
    return df

def safe_int(val):
    try:
        return int(float(val))
    except Exception:
        return None

def update_company_data(df, ticker, analysis_results, model):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mask = df['symbol'] == ticker

    # Ensure all required columns exist with correct dtype
    if model == "Perplexity":
        col_types = {
            f"{model}_inorganic_flag": str,
            f"{model}_inorganic_evidence": list,
            f"{model}_inorganic_source_links": list,
            f"{model}_roi_metric": str,
            f"{model}_roi improvement %": str,
            f"{model}_roi_flag": str,
            f"{model}_roi_evidence": list,
            f"{model}_roi_source_links": list,
            f"{model}_last_updated": str,
            f"{model}_growth%": str
        }
    else:
        col_types = {
            f"{model}_inorganic_flag": str,
            f"{model}_inorganic_evidence": str,
            f"{model}_inorganic_confidence": str,
            f"{model}_roi_flag": str,
            f"{model}_roi_evidence": list,
            f"{model}_roi_confidence": list,
            f"{model}_last_updated": str
        }


    for col, typ in col_types.items():
        if col not in df.columns:
            df[col] = pd.Series([typ()]*len(df), dtype="object")
   
  
    if model == "Perplexity":
        df.loc[mask, f"{model}_inorganic_flag"] = str(analysis_results.get("inorganic growth", "NA"))
        df.loc[mask, f"{model}_growth%"] = str(analysis_results.get("growth %", "-"))
        df.loc[mask, f"{model}_inorganic_evidence"] = str(analysis_results.get("inorganic evidence summary", []))
        df.loc[mask, f"{model}_inorganic_source_links"] = str(analysis_results.get("inorganic source links", []))
        df.loc[mask, f"{model}_roi_metric"] = str(analysis_results.get("roi metric", "-"))
        df.loc[mask, f"{model}_roi_flag"] = str(analysis_results.get("roi flag", "NA"))
        df.loc[mask, f"{model}_roi improvement %"] = str(analysis_results.get("roi improvement %", "-"))
        df.loc[mask, f"{model}_roi_evidence"] = str(analysis_results.get("roi evidence summary", []))
        df.loc[mask, f"{model}_roi_source_links"] = str(analysis_results.get("roi source links", []))
        df.loc[mask, f"{model}_last_updated"] = now

    else:
        # Assign values with explicit casting
        df.loc[mask, f"{model}_inorganic_flag"] = str(analysis_results.get("inorganic_flag", "No"))
        df.loc[mask, f"{model}_inorganic_evidence"] = str(analysis_results.get("inorganic_evidence", []))
        df.loc[mask, f"{model}_inorganic_confidence"] = str(analysis_results.get("inorganic_confidence", "N/A"))
        df.loc[mask, f"{model}_roi_flag"] = str(analysis_results.get("roi_flag", "-"))
        df.loc[mask, f"{model}_roi_evidence"] = str(analysis_results.get("roi_evidence", []))
        df.loc[mask, f"{model}_roi_confidence"] = str(analysis_results.get("roi_confidence", "N/A"))
        df.loc[mask, f"{model}_last_updated"] = now

    return df

def clear_analysis_data(df, ticker):
    """Clear analysis data for specific company"""
    mask = df['symbol'] == ticker
    columns_to_clear = [
        'transcript',
        'DeepSeek_inorganic_flag', 'DeepSeek_inorganic_evidence',
        'DeepSeek_inorganic_confidence', 'DeepSeek_roi_flag',
        'DeepSeek_roi_evidence', 'DeepSeek_roi_confidence', 'DeepSeek_last_updated',
        'Perplexity_inorganic_flag', 'Perplexity_inorganic_evidence',
        'Perplexity_inorganic_confidence', 'Perplexity_roi_flag',
        'Perplexity_roi_evidence', 'Perplexity_roi_confidence',
        'GPT-4o-Mini_inorganic_flag', 'GPT-4o-Mini_inorganic_evidence',
        'GPT-4o-Mini_inorganic_confidence', 'GPT-4o-Mini_roi_flag',
        'GPT-4o-Mini_roi_evidence', 'GPT-4o-Mini_roi_confidence',
        'GPT-4o-Mini_last_updated',
        'Perplexity_inorganic_source_links', 'Perplexity_roi_metric',
        'Perplexity_roi improvement %', 'Perplexity_roi_source_links',
        'Perplexity_last_updated'
    ]
    
    # Only clear columns that exist in the dataframe
    existing_columns = [col for col in columns_to_clear if col in df.columns]
    if existing_columns:
        df.loc[mask, existing_columns] = None
    return df


# ========================
# Analysis Functions
# ========================
def analyze_companies(selected_tickers, model, check_non_organic, check_roi):
    """Analyze selected companies and update/retrieve results based on data freshness"""
    results = []
    sp500_df = load_sp500_companies()
    
    for ticker in selected_tickers:
        # Get current revenue growth and calendar year
        current_data = get_revenue_growth(ticker)
        current_revenue_growth = current_data.get('growthRevenue')
        current_calendar_year = current_data.get('calendarYear')
        
        mask = sp500_df['symbol'] == ticker
        company_row = sp500_df.loc[mask].iloc[0]
        company_name = company_row['name']
        
        # Check if revenue growth or calendar year has changed
        stored_revenue_growth = company_row.get('revenue_growth', None)
        stored_calendar_year = company_row.get('calendar_year', None)
        last_updated = company_row.get(f'{model}_last_updated',None)
        model_inorganic_flag = company_row.get(f'{model}_inorganic_flag', None)
        model_roi_flag = company_row.get(f'{model}_roi_flag', None)
        if check_non_organic:
            if check_roi:
                model_flag = None if (pd.isna(model_inorganic_flag) or pd.isna(model_roi_flag)) else True
            else:
                model_flag = model_inorganic_flag
        else:
            model_flag = model_roi_flag

        data_changed = (
            pd.isna(stored_revenue_growth) or 
            pd.isna(stored_calendar_year) or
            safe_int(stored_calendar_year) != safe_int(current_calendar_year) or
            abs(float(current_revenue_growth or 0) - float(stored_revenue_growth or 0)) > 0.01 
            #model_flag is None
        )
        print(f"Data changed for {ticker}: {data_changed}, Last Updated: {last_updated}")
       

        if data_changed:
            # Clear existing analysis data for this company
            sp500_df = clear_analysis_data(sp500_df, ticker)
            
            # Update revenue growth and calendar year
            sp500_df.loc[mask, 'revenue_growth'] = current_revenue_growth
            sp500_df.loc[mask, 'calendar_year'] = str(current_calendar_year)
            sp500_df.loc[mask, 'last_data_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Perform fresh analysis
            analysis_result = main_fun(ticker, model, check_non_organic, check_roi)
        
        elif not pd.isna(last_updated):
            # If data hasn't changed and we have previous analysis
            if check_non_organic and check_roi:
                # Return stored results if both analyses exist
                if all(col in sp500_df.columns for col in [
                    f'{model}_inorganic_flag', 
                    f'{model}_roi_flag'
                ]):
                    if model == "Perplexity":
                        # For Perplexity, we need to handle source links and evidence
                        analysis_result = {
                            'inorganic growth': company_row.get(f'{model}_inorganic_flag'),
                            'growth %': company_row.get(f'{model}_growth%'),
                            'inorganic evidence summary': (company_row.get(f'{model}_inorganic_evidence', '[]')),
                            'inorganic source links': (company_row.get(f'{model}_inorganic_source_links', '[]')),
                            'roi metric': company_row.get(f'{model}_roi_metric'),
                            'roi flag': company_row.get(f'{model}_roi_flag'),
                            'roi improvement %': company_row.get(f'{model}_roi improvement %'),
                            'roi evidence summary': (company_row.get(f'{model}_roi_evidence', '[]')),
                            'roi source links': (company_row.get(f'{model}_roi_source_links', '[]')),
                        }
                    else:
        
                        analysis_result = {
                            'inorganic_flag': company_row.get(f'{model}_inorganic_flag'),
                            'inorganic_evidence': company_row.get(f'{model}_inorganic_evidence', '[]'),
                            'inorganic_confidence': company_row.get(f'{model}_inorganic_confidence'),
                            'roi_flag': company_row.get(f'{model}_roi_flag'),
                            'roi_evidence': company_row.get(f'{model}_roi_evidence', '[]'),
                            'roi_confidence': company_row.get(f'{model}_roi_confidence')
                        }
                else:
                    # Perform fresh analysis if we don't have all required data
                    analysis_result = main_fun(ticker, model, check_non_organic, check_roi)
            
            elif check_non_organic:
                # Return stored inorganic growth results if they exist
                if f'{model}_inorganic_flag' in sp500_df.columns:
                    if model == "Perplexity":
                        analysis_result = {
                            'inorganic growth': company_row.get(f'{model}_inorganic_flag'),
                            'growth %': company_row.get(f'{model}_growth%'),
                            'inorganic evidence summary': eval(company_row.get(f'{model}_inorganic_evidence', '[]')),
                            'inorganic source links': eval(company_row.get(f'{model}_inorganic_source_links', '[]')),
                        }
                    else:
                        analysis_result = {
                            'inorganic_flag': company_row.get(f'{model}_inorganic_flag'),
                            'inorganic_evidence': company_row.get(f'{model}_inorganic_evidence', '[]'),
                            'inorganic_confidence': company_row.get(f'{model}_inorganic_confidence')
                        }
                else:
                    analysis_result = main_fun(ticker, model, check_non_organic, check_roi)
            
            elif check_roi:
                # Return stored ROI results if they exist
                if f'{model}_roi_flag' in sp500_df.columns:
                    if model == "Perplexity":
                        analysis_result = {
                            'roi metric': company_row.get(f'{model}_roi_metric'),
                            'roi flag': company_row.get(f'{model}_roi_flag'),
                            'roi improvement %': company_row.get(f'{model}_roi improvement %'),
                            'roi evidence summary': eval(company_row.get(f'{model}_roi_evidence', '[]')),
                            'roi source links': eval(company_row.get(f'{model}_roi_source_links', '[]')),
                        }
                    else:
                        analysis_result = {
                            'roi_flag': company_row.get(f'{model}_roi_flag'),
                            'roi_evidence': eval(company_row.get(f'{model}_roi_evidence', '[]')),
                            'roi_confidence': company_row.get(f'{model}_roi_confidence')
                        }
                else:
                    analysis_result = main_fun(ticker, model, check_non_organic, check_roi)
        else:
            # Perform fresh analysis if no previous data exists
            analysis_result = main_fun(ticker, model, check_non_organic, check_roi)
        
        # Format result for display
        if model == "Perplexity":
            result = {
                'Symbol': ticker,
                'Name': company_name,
                'Revenue Growth': current_revenue_growth,
                'Calendar Year': current_calendar_year
            }
            if check_non_organic:
                result.update({
                    'Inorganic Growth': analysis_result.get("inorganic growth", "NO"),
                    'Inorganic Evidence': analysis_result.get("inorganic evidence summary", []),
                    'Inorganic Source Links': analysis_result.get("inorganic source links", [])
                })
            if check_roi:
                result.update({
                    'ROI Metric': analysis_result.get('roi metric', "N/A"),
                    'ROI Flag': analysis_result.get("roi flag", "NO"),
                    'ROI Improvement': analysis_result.get("roi improvement %", 0.0),
                    'ROI Evidence': analysis_result.get("roi evidence summary", []),
                    'ROI Source Links': analysis_result.get("roi source links", [])
                })
        else:
            result = {
                'Symbol': ticker,
                'Name': company_name,
                'Revenue Growth': current_revenue_growth,
                'Calendar Year': current_calendar_year
            }
            if check_non_organic:
                result.update({
                    'Inorganic_Flag': analysis_result.get('inorganic_flag', False),
                    'Inorganic_Evidence': analysis_result.get('inorganic_evidence', []),
                    'Inorganic_Confidence': analysis_result.get('inorganic_confidence', 0.0)
                })
            if check_roi:
                result.update({
                    'ROI_Flag': analysis_result.get('roi_flag', False),
                    'ROI_Evidence': analysis_result.get('roi_evidence', []),
                    'ROI_Confidence': analysis_result.get('roi_confidence', 0.0)
                })
        
        result[f'{model}_last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        results.append(result)
        
        # Update Excel file if we performed new analysis
        if data_changed or pd.isna(last_updated):
            sp500_df = update_company_data(sp500_df, ticker, analysis_result, model)
    
    # Save updated dataframe back to Excel
    sp500_df.to_excel("data/sp500_companies_growth.xlsx", index=False)
    
    return pd.DataFrame(results)


# ========================
# UI Configuration
# ========================
st.set_page_config(page_title="S&P 500 Analyzer", layout="wide")
st.title("📈 S&P 500 Growth & ROI Analyzer")

# ========================
# Sidebar Controls
# ========================
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Model selection
    model = st.selectbox(
        "Analysis Model:",
        options=["GPT-4o-Mini", "DeepSeek", "Perplexity"],
        index=0
    )
    
    # Analysis options
    st.header("🔍 Analysis Options")
    check_non_organic = st.checkbox("Detect In-organic Growth", True)
    check_roi = st.checkbox("Calculate ROI/ROIC", True)

# ========================
# Main Interface
# ========================
sp500_df = load_sp500_companies()

# Company selection
selected_companies = st.multiselect(
    "Select Companies (Search by Ticker or Name):",
    options=[f"{row['symbol']} - {row['name']}" for _, row in sp500_df.iterrows()],
    default=[f"{sp500_df.iloc[0]['symbol']} - {sp500_df.iloc[0]['name']}"],
    help="Start typing to search from S&P 500 companies"
)

selected_tickers = [comp.split(" - ")[0] for comp in selected_companies]

# Action buttons
col1, col2 = st.columns([1, 2])
with col1:
    analyze_btn = st.button("🚀 Run Analysis", type="primary")
with col2:
    update_btn = st.button("🔄 Update All Companies")



# ========================
# Results Display
# ========================
if analyze_btn:
    if not selected_tickers:
        st.warning("⚠️ Please select at least one company")
    else:
        with st.spinner("Analyzing companies..."):
            results = analyze_companies(selected_tickers, model, check_non_organic, check_roi)
            
            st.success("✅ Analysis Complete!")
            
            # Define base columns that are always shown
            column_config = {
                "Symbol": "Ticker Symbol",
                "Name": "Company Name",
            }
            
            # Add inorganic growth columns if selected
            if check_non_organic:
                column_config.update({
                    "Inorganic_Flag": st.column_config.TextColumn(
                        "Inorganic Growth Flag",
                        help="True if inorganic growth detected"
                    ),
                    "Inorganic_Evidence": st.column_config.ListColumn(
                        "Inorganic Evidence",
                        help="Evidence supporting inorganic growth"
                    ),
                    "Inorganic_Confidence": st.column_config.NumberColumn(
                        "Inorganic Confidence",
                        format="%.2f",
                        min_value=0,
                        max_value=1
                    )
                })
            
            # Add ROI columns if selected
            if check_roi:
                column_config.update({
                    "ROI_Flag": st.column_config.TextColumn(
                        "ROI Flag",
                        help="True if ROI improvement detected"
                    ),
                    "ROI_Evidence": st.column_config.ListColumn(
                        "ROI Evidence",
                        help="Evidence supporting ROI analysis"
                    ),
                    "ROI_Confidence": st.column_config.NumberColumn(
                        "ROI Confidence",
                        format="%.2f",
                        min_value=0,
                        max_value=1
                    )
                })
            
            # Add Last Updated column
            column_config["Last_Updated"] = st.column_config.DatetimeColumn(
                "Last Updated",
                format="D MMM YYYY, HH:mm"
            )
            
            # Display results with dynamic columns
            st.dataframe(
                results,
                column_config=column_config,
                hide_index=True,
                use_container_width=True
            )        

def find_next_5_missing_companies(df, model):
    """
    Returns a list of up to 5 companies (dicts with symbol and name) that are missing analysis for the selected model.
    """
    required_cols = [
        f'{model}_inorganic_flag',
        f'{model}_roi_flag',
        f'{model}_last_updated'
    ]
    # Ensure all required columns exist
    for col in required_cols:
        if col not in df.columns:
            df[col] = None
    cols_to_check = [ 'symbol',
                     f'{model}_inorganic_flag',
        f'{model}_roi_flag',
        f'{model}_last_updated']
    missing_companies = []
    for _, row in df[cols_to_check].iterrows():
        if any(pd.isna(row[col]) for col in required_cols):
            print(row)
            missing_companies.append(row['symbol'])
            if len(missing_companies) == 5:
                break
    print("###########################MISSING COMPANIES###########################")
    print(missing_companies)
    return missing_companies

def update_all_sp500_companies():
    """
    Updates the next 5 companies missing analysis for the selected model,
    updates the Excel, and displays the update in the UI.
    """
    try:
        sp500_df = load_sp500_companies()
        companies_to_update = find_next_5_missing_companies(sp500_df, model)
        print(companies_to_update)
        if not companies_to_update:
            st.success(f"✅ All companies have complete analysis data for {model}!")
            return

        update_data = []
        with st.status("Updating companies...", expanded=True) as status:
            try:
                results = analyze_companies(companies_to_update, model, check_non_organic, check_roi)
            except Exception as e:
                st.error(f"Error during analysis: {e}")
                return

            st.success("✅ Analysis Complete!")
            
            # Define base columns that are always shown
            column_config = {
                "Symbol": "Ticker Symbol",
                "Name": "Company Name",
            }
            
            # Add inorganic growth columns if selected
            if check_non_organic:
                column_config.update({
                    "Inorganic_Flag": st.column_config.TextColumn(
                        "Inorganic Growth Flag",
                        help="True if inorganic growth detected"
                    ),
                    "Inorganic_Evidence": st.column_config.ListColumn(
                        "Inorganic Evidence",
                        help="Evidence supporting inorganic growth"
                    ),
                    "Inorganic_Confidence": st.column_config.NumberColumn(
                        "Inorganic Confidence",
                        format="%.2f",
                        min_value=0,
                        max_value=1
                    )
                })
            
            # Add ROI columns if selected
            if check_roi:
                column_config.update({
                    "ROI_Flag": st.column_config.TextColumn(
                        "ROI Flag",
                        help="True if ROI improvement detected"
                    ),
                    "ROI_Evidence": st.column_config.ListColumn(
                        "ROI Evidence",
                        help="Evidence supporting ROI analysis"
                    ),
                    "ROI_Confidence": st.column_config.NumberColumn(
                        "ROI Confidence",
                        format="%.2f",
                        min_value=0,
                        max_value=1
                    )
                })
            
            # Add Last Updated column
            column_config["Last_Updated"] = st.column_config.DatetimeColumn(
                "Last Updated",
                format="D MMM YYYY, HH:mm"
            )
            
            # Display results with dynamic columns
            try:
                st.dataframe(
                    results,
                    column_config=column_config,
                    hide_index=True,
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error displaying results: {e}")

    except Exception as e:
        st.error(f"An error occurred while updating companies: {e}")

if update_btn:
    update_all_sp500_companies()
    st.toast("Batch update complete!", icon="🎉")