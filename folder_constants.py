#google sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

#popup
import pyinputplus as pyip

#general
import pandas as pd
import numpy as np
import pytz
import re
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

#set working directory and pull in hidden variables
import os
current_directory = os.getcwd()
while os.path.basename(current_directory) != 'GitHub':
    parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
    os.chdir(parent_directory)
    current_directory = parent_directory
    
from personal_finance_private.config import *


#read google sheets
creds_file = google_sheets_json_file
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
client = gspread.authorize(creds)

spreadsheet = client.open(workbook_name)

#################### DATAFRAMES FROM CONFIG ####################
#tiers df
worksheet = spreadsheet.worksheet('Config')
range_to_pull = 'A1:C'
data = worksheet.get(range_to_pull)
tiers_df = pd.DataFrame(data[1:], columns=data[0])
tiers_df['Level 3'] = tiers_df['Level 3'].fillna('')

#mapping df
worksheet = spreadsheet.worksheet('Config')
range_to_pull = 'E1:F'
data = worksheet.get(range_to_pull)
mapping_df = pd.DataFrame(data[1:], columns=data[0])

#ally bucket percentages df
worksheet = spreadsheet.worksheet('Config')
range_to_pull = 'H1:K'
data = worksheet.get(range_to_pull)
bucket_df = pd.DataFrame(data[1:], columns=data[0])

#budget percentages df
worksheet = spreadsheet.worksheet('Config')
range_to_pull = 'M1:O'
data = worksheet.get(range_to_pull)
budget_df = pd.DataFrame(data[1:], columns=data[0])
budget_df['Budget'] = budget_df['Budget'].str.replace('[\$,]', '', regex=True).astype(float).fillna(0)

#credit card cycle dates df
worksheet = spreadsheet.worksheet('Config')
range_to_pull = 'Q1:S'
data = worksheet.get(range_to_pull)
important_dates_df = pd.DataFrame(data[1:], columns=data[0])
important_dates_df['Date'] = pd.to_numeric(important_dates_df['Date'], errors='coerce').astype('Int64')


#################### GOOGLE SHEETS OUTPUT INFO ####################
#output ranges, used for original output and new output
sheets_info_dict = {
    'credit_card': ['A3','A3:J'],
    'savings': ['M3','M3:P'],
    'checking': ['S3','S3:Y'],
    'fidelity': ['AB3','AB3:AI'],
    'bills': ['AM3','AL3:AO'],
    'ira_graph': ['AR3','AR3:AZ'],
    'taxable_graph':['BA3','BA3:BF']
}

##################### UPLOAD DATAFRAMES ####################
#function to pull columns from section on Outputs sheet
def extract_section_data(data, section):
    item_number = 0
    for i, item in enumerate(data[0]):
        if item == section:
            item_number = i
            break
    start_index = item_number

    blank_count = 0
    for item in data[0][item_number + 1:]:
        if item == '':
            blank_count += 1
        elif item != '':
            break
    end_index = start_index + blank_count + 1

    extracted_data = data[1][start_index:end_index]

    if '' in extracted_data:
        end_index = end_index - extracted_data.count('')
        first_blank_index = extracted_data.index('')
        extracted_data = extracted_data[:first_blank_index]

    return start_index, end_index, extracted_data


#function to remove blank rows
def remove_blank_rows(df):
    df = df.replace('', pd.NA)
    df = df.dropna(how='all').reset_index(drop=True)
    df = df.fillna('')
    return df

#checking upload df
section = 'CHASE CHECKING'
worksheet = spreadsheet.worksheet('Uploads')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
checking_df = pd.DataFrame(data[2:], columns=data[1])
checking_df = checking_df.iloc[:, start_index:end_index]
checking_df = remove_blank_rows(checking_df)
checking_df = checking_df.drop(columns=['Details','Type','Check or Slip #'])

#credit card upload df
section = 'CHASE CREDIT CARD'
worksheet = spreadsheet.worksheet('Uploads')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
credit_card_df = pd.DataFrame(data[2:], columns=data[1])
credit_card_df = credit_card_df.iloc[:, start_index:end_index]
credit_card_df = remove_blank_rows(credit_card_df)

credit_card_df['Transaction Date'] = pd.to_datetime(credit_card_df['Transaction Date']) #comment out if date format breaks something
credit_card_df = credit_card_df.rename(columns={'Amount':'Spent'})
credit_card_df = credit_card_df.drop(columns=['Post Date','Category','Memo'])
credit_card_df['Description'] = credit_card_df['Description'].apply(lambda x: x.title())
credit_card_df['Type'] = credit_card_df['Type'].replace('Sale', 'Buy')
credit_card_df['Spent'] = credit_card_df['Spent'].astype(float) * -1

#savings upload df
section = 'ALLY SAVINGS'
worksheet = spreadsheet.worksheet('Uploads')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
savings_df = pd.DataFrame(data[2:], columns=data[1])
savings_df = savings_df.iloc[:, start_index:end_index]
savings_df = remove_blank_rows(savings_df)
savings_df = savings_df.drop(columns=['Time'])

#fidelity upload df
section = 'FIDELITY - ALL ACCOUNTS'
worksheet = spreadsheet.worksheet('Uploads')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
fidelity_df = pd.DataFrame(data[2:], columns=data[1])
fidelity_df = fidelity_df.iloc[:, start_index:end_index]
fidelity_df = remove_blank_rows(fidelity_df)
fidelity_df = fidelity_df.drop(columns=['Security Type','Security Description','Commission ($)','Fees ($)', 'Accrued Interest ($)','Settlement Date'])
columns_to_rename = {
    'Run Date': 'Date',
    'Price ($)': 'Price',
    'Amount ($)': 'Amount'
}
for old_name, new_name in columns_to_rename.items():
    if old_name in fidelity_df.columns:
        fidelity_df.rename(columns={old_name: new_name}, inplace=True)
fidelity_df['Date'] = pd.to_datetime(fidelity_df['Date'])

#electric upload df
section = 'ELECTRIC (SRP)'
worksheet = spreadsheet.worksheet('Uploads')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
electric_df = pd.DataFrame(data[2:], columns=data[1])
electric_df = electric_df.iloc[:, start_index:end_index]
electric_df = remove_blank_rows(electric_df)
electric_df = electric_df.rename(columns={'Bill date':'Date','New charges':'Electric'})
electric_df = electric_df[['Date','Electric']]

#gas upload df
section = 'GAS'
worksheet = spreadsheet.worksheet('Uploads')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
gas_df = pd.DataFrame(data[2:], columns=data[1])
gas_df = gas_df.iloc[:, start_index:end_index]
gas_df = remove_blank_rows(gas_df)

#water upload df
section = 'WATER'
worksheet = spreadsheet.worksheet('Uploads')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
water_df = pd.DataFrame(data[2:], columns=data[1])
water_df = water_df.iloc[:, start_index:end_index]
water_df = remove_blank_rows(water_df)
water_df = water_df.rename(columns={'Bill Date':'Date','Bill Total':'Water'})

#dan 401k from NCSA upload df
section = 'Dan 401k - Empower RET'
worksheet = spreadsheet.worksheet('Uploads')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
dan_ncsa_401k_df = pd.DataFrame(data[2:], columns=data[1])
dan_ncsa_401k_df = dan_ncsa_401k_df.iloc[:, start_index:end_index]
dan_ncsa_401k_df = remove_blank_rows(dan_ncsa_401k_df)

#net worth upload df
section = 'Net Worth'
worksheet = spreadsheet.worksheet('Uploads')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
net_worth_df = pd.DataFrame(data[2:], columns=data[1])
net_worth_df = net_worth_df.iloc[:, start_index:end_index]
net_worth_df = remove_blank_rows(net_worth_df)


#put into dictionary so we can reference as variables in scripts
upload_df_dictionary = {
    'checking': checking_df,
    'credit_card': credit_card_df,
    'savings': savings_df,
    'fidelity': fidelity_df,
    'electric': electric_df,
    'gas': gas_df,
    'water': water_df,
    'dan_ncsa_401k': dan_ncsa_401k_df,
    'net_worth': net_worth_df
}


######### ORIGINAL OUTPUT DATAFRAMES #########
#original output data for NFCU CREDIT CARD
section = 'NFCU CREDIT CARD'
worksheet = spreadsheet.worksheet('Outputs')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
credit_card_original_output_data = pd.DataFrame(data[2:], columns=data[1])
credit_card_original_output_data = credit_card_original_output_data.iloc[:, start_index:end_index]
credit_card_original_output_data['Transaction Date'] = pd.to_datetime(credit_card_original_output_data['Transaction Date'])
credit_card_original_output_data = credit_card_original_output_data.dropna() #remove empty rows

#original output data for ALLY SAVINGS
section = 'ALLY SAVINGS'
worksheet = spreadsheet.worksheet('Outputs')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
savings_original_output_data = pd.DataFrame(data[2:], columns=data[1])
savings_original_output_data = savings_original_output_data.iloc[:, start_index:end_index]
savings_original_output_data['Date'] = pd.to_datetime(savings_original_output_data['Date'])
savings_original_output_data = savings_original_output_data.dropna() #remove empty rows

#original output data for ALLY CHECKING
section = 'ALLY CHECKING'
worksheet = spreadsheet.worksheet('Outputs')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
checking_original_output_data = pd.DataFrame(data[2:], columns=data[1])
checking_original_output_data = checking_original_output_data.iloc[:, start_index:end_index]
checking_original_output_data['Date'] = pd.to_datetime(checking_original_output_data['Date'])
checking_original_output_data = checking_original_output_data.dropna() #remove empty rows

#original output data for FIDELITY
section = 'FIDELITY'
worksheet = spreadsheet.worksheet('Outputs')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
fidelity_original_output_data = pd.DataFrame(data[2:], columns=data[1])
fidelity_original_output_data = fidelity_original_output_data.iloc[:, start_index:end_index]
fidelity_original_output_data['Date'] = pd.to_datetime(fidelity_original_output_data['Date'])
fidelity_original_output_data = fidelity_original_output_data.dropna() #remove empty rows

#original output data for BILLS
section = 'BILLS'
worksheet = spreadsheet.worksheet('Outputs')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
bills_original_output_data = pd.DataFrame(data[2:], columns=data[1])
bills_original_output_data = bills_original_output_data.iloc[:, start_index:end_index]
bills_original_output_data['Date'] = pd.to_datetime(bills_original_output_data['Date'], format="%b '%y")
bills_original_output_data = bills_original_output_data.dropna() #remove empty rows

#original output data for IRA GRAPH
section = 'IRA - GRAPH'
worksheet = spreadsheet.worksheet('Outputs')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
ira_graph_output_data = pd.DataFrame(data[2:], columns=data[1])
ira_graph_output_data = ira_graph_output_data.iloc[:, start_index:end_index]
ira_graph_output_data['Date'] = pd.to_datetime(ira_graph_output_data['Date'])
ira_graph_output_data = ira_graph_output_data.dropna() #remove empty rows

#original output data for TAXABLE GRAPH
section = 'TAXABLE - GRAPH'
worksheet = spreadsheet.worksheet('Outputs')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
taxable_graph_output_data = pd.DataFrame(data[2:], columns=data[1])
taxable_graph_output_data = taxable_graph_output_data.iloc[:, start_index:end_index]
taxable_graph_output_data['Date'] = pd.to_datetime(taxable_graph_output_data['Date'])
taxable_graph_output_data = taxable_graph_output_data.dropna() #remove empty rows

#put into dictionary so we can reference as variables in scripts
original_output_dataframes = {
    'credit_card': credit_card_original_output_data,
    'savings': savings_original_output_data,
    'checking': checking_original_output_data,
    'fidelity': fidelity_original_output_data,
    'bills': bills_original_output_data,
    'ira_graph': ira_graph_output_data,
    'taxable_graph': taxable_graph_output_data
}


######### Functions to remove the existing data from the uploads #########
def clean_df(original_output_df, columns_to_sum=None):
    for col in columns_to_sum:
            original_output_df[col] = pd.to_numeric(original_output_df[col].replace('[\$,]', '', regex=True), errors='coerce')
    test_df = original_output_df.copy()
    test_df['Amount'] = test_df[columns_to_sum].sum(axis=1)
    test_df.drop(columns=columns_to_sum, inplace=True) 
    return test_df
    
def remove_data_we_already_have(original_output_df, upload_df):
    merged_df = upload_df.merge(original_output_df[['Date', 'Amount']], how='left', on='Date')
    # Rename the 'Amount' column from original_output_df to 'Original Amount'
    for column in merged_df.columns:
        if column.endswith("_x"):
            merged_df.rename(columns={column: "New " + column[:-2]}, inplace=True)
        elif column.endswith("_y"):
            merged_df.rename(columns={column: "Original " + column[:-2]}, inplace=True)
    new_upload_df = merged_df[merged_df['New Amount'] != merged_df['Original Amount']]
    return new_upload_df

def format_and_combo(original_output_df,upload_df):
    # Clean Amount column if needed
    original_amount_column = 'Amount' if 'Amount' in original_output_df.columns else (
        'Spent' if 'Spent' in original_output_df.columns else None
    )
    upload_amount_column = 'Amount' if 'Amount' in upload_df.columns else 'Spent'
    original_date_column = 'Date' if 'Date' in original_output_df.columns else 'Transaction Date'
    upload_date_column = 'Date' if 'Date' in upload_df.columns else 'Transaction Date'

    original_output_df[original_amount_column] = original_output_df[original_amount_column].replace('[\$,]', '', regex=True)
    original_output_df[original_amount_column] = pd.to_numeric(original_output_df[original_amount_column]).map('{:.2f}'.format).astype(str)
    upload_df[upload_amount_column] = pd.to_numeric(upload_df[upload_amount_column]).map('{:.2f}'.format).astype(str)

    # Reformat Date to string
    original_output_df[original_date_column] = original_output_df[original_date_column].astype(str)
    upload_df[original_date_column] = upload_df[original_date_column].astype(str)

    # Create combo column
    if 'Store' in original_output_df.columns:
        original_output_df['combo'] = original_output_df[original_date_column] + original_output_df['Store'] + original_output_df[original_amount_column]
        upload_df['combo'] = upload_df[upload_date_column] + upload_df['Store'] + upload_df[upload_amount_column]
    else:
        original_output_df['combo'] = original_output_df[original_date_column] + original_output_df[original_amount_column]
        upload_df['combo'] = upload_df[upload_date_column] + upload_df[upload_amount_column]
    upload_df['combo'] = upload_df['combo'].astype(str).str.strip()

    return original_output_df,upload_df

# remove rows already stored in google sheets
def remove_rows_already_saved(original_output_df, upload_df):
    
    # Remove rows from upload_df if they are in original_output_df, we don't want to upload duplicates
    upload_df = upload_df[~upload_df['combo'].isin(original_output_df['combo'])]

    # Drop combo columns
    original_output_df = original_output_df.drop(columns='combo')
    upload_df = upload_df.drop(columns='combo').reset_index(drop=True)
    
    return upload_df


### bill dates
water_bill_date = 25
electric_bill_date = 12



################## BUCKETS_DF FROM SETUP PAGE ##################
worksheet = spreadsheet.worksheet('Setup')
range_to_pull = 'B2:D'
data = worksheet.get(range_to_pull)
filtered_data = [row for row in data if len(row) == 3]

# Create a DataFrame
goals_df = pd.DataFrame(filtered_data, columns=['Category', 'Item', 'Amount'])
goals_df = goals_df.rename(columns={'Category': 'Bucket', 'Item': 'Category'})
# goals_df = goals_df[~goals_df['Category'].str.contains(r'(\$|Gross)', na=False)].reset_index(drop = True)
goals_df = goals_df[~goals_df['Category'].str.contains(r'(\$|Gross|Taxes)', na=False)].reset_index(drop = True)
mask = (goals_df['Bucket'] == 'Monthly') & (goals_df['Category'] == 'Total')
goals_df.loc[mask, 'Category'] = 'Gross'


#get net pay
net_pay_data = [row for row in data if row and 'Net Pay (into Chase)' in row[0]]
net_df_temp = pd.DataFrame(net_pay_data, columns=['Category', 'Amount'])
net_df_temp['Bucket'] = 'Monthly'
net_df_temp = net_df_temp[['Bucket','Category','Amount']]

#concat df's
goals_df = pd.concat([goals_df,net_df_temp],ignore_index = True)
row_19 = goals_df.iloc[19]
goals_df = pd.concat([goals_df.iloc[:1], goals_df.iloc[-1:], goals_df.iloc[1:-1]], ignore_index=True)






##########################################################################
##########################################################################
##########################################################################
#import setup
from folder_constants import *

#pick the needed df's from folder_constants.py
method = 'savings'
original_output_data = original_output_dataframes[method]
upload_df = upload_df_dictionary[method]

def output_col_list(method):
    if method == 'credit_card':
        required_columns = ['']
    elif method == 'savings' or method == 'checking' or method == 'fidelity':
        required_columns = ['Date','Amount']
    # elif method == 'fidelity':
    #     required_columns = ['Date','Amount']
    #     ira_graph_required_columns = ['Date','Holder','Account','Month','Year']
    #     taxable_graph_required_columns = ['Date','Holder','Account','Monthly Total','YTD']
    elif method == 'bills':
        required_columns = ['Date','Electric','Water']
    return required_columns
    # if method == 'fidelity':
    #     return required_columns, ira_graph_required_columns, taxable_graph_required_columns
    # else:
    #     return required_columns


def df_column_alignment(required_columns,original_output_data,upload_df):
    #some columns are called "Transaction Date" or "Run Date" etc. this renames those to "Date"
    for column in upload_df.columns:
        if column.lower() != 'date' and 'date' in column.lower():
            upload_df.rename(columns={column: 'Date'}, inplace=True)
    #similar to above, change columns called Debit, Spent, etc. to "Amount"
    for column in upload_df.columns:
        if column.lower() == 'debit' or column.lower() == 'amount ($)':
            upload_df.rename(columns={column: 'Amount'}, inplace=True)
    #make copy of the dataframes with only needed columns
    original_output_data_aligned = original_output_data[required_columns].copy()
    upload_df_aligned = upload_df[required_columns].copy()
    return original_output_data_aligned, upload_df_aligned

required_columns = output_col_list(method)
original_output_data_df_aligned, upload_df_aligned = df_column_alignment(required_columns, original_output_data, upload_df)

#creates the combo column between the two dataframes
def create_combo(original_output_data, upload_df):
    #convert to datetime datatype
    original_output_data['Date'] = pd.to_datetime(original_output_data['Date'])
    upload_df['Date'] = pd.to_datetime(upload_df['Date'])

    #this helps remove the time component (00:00:00) when creating combo
    original_output_data['Date'] = original_output_data['Date'].dt.strftime('%Y-%m-%d')
    upload_df['Date'] = upload_df['Date'].dt.strftime('%Y-%m-%d')

    #create combo column, add '; ' between each concatenation
    original_output_data['combo'] = original_output_data.apply(lambda row: '; '.join(map(str, row)), axis=1)
    upload_df['combo'] = upload_df.apply(lambda row: '; '.join(map(str, row)), axis=1)
create_combo(original_output_data, upload_df)

#remove data from upload_df that is already found in original_output_df
def remove_data_we_already_have(original_output_data, upload_df):
    merged_df = upload_df.merge(original_output_data, how='left', on='combo')
    # Rename the 'Amount' column from original_output_data to 'Original Amount'
    for column in merged_df.columns:
        if column.endswith("_x"):
            merged_df.rename(columns={column: "New " + column[:-2]}, inplace=True)
        elif column.endswith("_y"):
            merged_df.rename(columns={column: "Original " + column[:-2]}, inplace=True)
    new_upload_df = merged_df[merged_df['New Amount'] != merged_df['Original Amount']]
    return new_upload_df



######### Functions to remove the existing data from the uploads #########
def clean_df(original_output_df, columns_to_sum=None):
    for col in columns_to_sum:
            original_output_df[col] = pd.to_numeric(original_output_df[col].replace('[\$,]', '', regex=True), errors='coerce')
    test_df = original_output_df.copy()
    test_df['Amount'] = test_df[columns_to_sum].sum(axis=1)
    test_df.drop(columns=columns_to_sum, inplace=True) 
    return test_df
    
def remove_data_we_already_have(original_output_df, upload_df):
    merged_df = upload_df.merge(original_output_df[['Date', 'Amount']], how='left', on='Date')
    # Rename the 'Amount' column from original_output_df to 'Original Amount'
    for column in merged_df.columns:
        if column.endswith("_x"):
            merged_df.rename(columns={column: "New " + column[:-2]}, inplace=True)
        elif column.endswith("_y"):
            merged_df.rename(columns={column: "Original " + column[:-2]}, inplace=True)
    new_upload_df = merged_df[merged_df['New Amount'] != merged_df['Original Amount']]
    return new_upload_df

def format_and_combo(original_output_df,upload_df):
    # Clean Amount column if needed
    original_amount_column = 'Amount' if 'Amount' in original_output_df.columns else (
        'Spent' if 'Spent' in original_output_df.columns else None
    )
    upload_amount_column = 'Amount' if 'Amount' in upload_df.columns else 'Spent'
    original_date_column = 'Date' if 'Date' in original_output_df.columns else 'Transaction Date'
    upload_date_column = 'Date' if 'Date' in upload_df.columns else 'Transaction Date'

    original_output_df[original_amount_column] = original_output_df[original_amount_column].replace('[\$,]', '', regex=True)
    original_output_df[original_amount_column] = pd.to_numeric(original_output_df[original_amount_column]).map('{:.2f}'.format).astype(str)
    upload_df[upload_amount_column] = pd.to_numeric(upload_df[upload_amount_column]).map('{:.2f}'.format).astype(str)

    # Reformat Date to string
    original_output_df[original_date_column] = original_output_df[original_date_column].astype(str)
    upload_df[original_date_column] = upload_df[original_date_column].astype(str)

    # Create combo column
    if 'Store' in original_output_df.columns:
        original_output_df['combo'] = original_output_df[original_date_column] + original_output_df['Store'] + original_output_df[original_amount_column]
        upload_df['combo'] = upload_df[upload_date_column] + upload_df['Store'] + upload_df[upload_amount_column]
    else:
        original_output_df['combo'] = original_output_df[original_date_column] + original_output_df[original_amount_column]
        upload_df['combo'] = upload_df[upload_date_column] + upload_df[upload_amount_column]
    upload_df['combo'] = upload_df['combo'].astype(str).str.strip()

    return original_output_df,upload_df

# remove rows already stored in google sheets
def remove_rows_already_saved(original_output_df, upload_df):
    
    # Remove rows from upload_df if they are in original_output_df, we don't want to upload duplicates
    upload_df = upload_df[~upload_df['combo'].isin(original_output_df['combo'])]

    # Drop combo columns
    original_output_df = original_output_df.drop(columns='combo')
    upload_df = upload_df.drop(columns='combo').reset_index(drop=True)
    
    return upload_df


### bill dates
water_bill_date = 25
electric_bill_date = 12