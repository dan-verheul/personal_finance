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
budget_df['Budget'] = budget_df['Budget'].str.replace('$', '').astype(float).fillna(0)


#################### GOOGLE SHEETS INFO ####################
sheets_info_dict = {
    'credit_card': ['A3','A3:J'],
    'savings': ['M3','M3:P'],
    'checking': ['S3','S3:Y'],
    'fidelity': ['AB3','AB3:AI']
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

#credit card upload df
section = 'NFCU CREDIT CARD'
worksheet = spreadsheet.worksheet('Uploads')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
credit_card_df = pd.DataFrame(data[2:], columns=data[1])
credit_card_df = credit_card_df.iloc[:, start_index:end_index]
credit_card_df = remove_blank_rows(credit_card_df)

credit_card_df['Transaction Date'] = pd.to_datetime(credit_card_df['Transaction Date']) #comment out if date format breaks something
credit_card_df = credit_card_df.rename(columns={'Debit':'Spent','Credit':'Refunded'})
credit_card_df = credit_card_df.drop(columns='Posted Date')

#savings upload df
section = 'ALLY SAVINGS'
worksheet = spreadsheet.worksheet('Uploads')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
savings_df = pd.DataFrame(data[2:], columns=data[1])
savings_df = savings_df.iloc[:, start_index:end_index]
savings_df = remove_blank_rows(savings_df)
savings_df = savings_df.drop(columns=['Time'])

#checking upload df
section = 'ALLY CHECKING'
worksheet = spreadsheet.worksheet('Uploads')
data = worksheet.get_all_values()
start_index, end_index, result_data = extract_section_data(data, section)
checking_df = pd.DataFrame(data[2:], columns=data[1])
checking_df = checking_df.iloc[:, start_index:end_index]
checking_df = remove_blank_rows(checking_df)
checking_df = checking_df.drop(columns=['Time'])

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


#put into dictionary so we can reference as variables in scripts
upload_df_dictionary = {
    'credit_card': credit_card_df,
    'savings': savings_df,
    'checking': checking_df,
    'fidelity': fidelity_df
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

#put into dictionary so we can reference as variables in scripts
original_output_dataframes = {
    'credit_card': credit_card_original_output_data,
    'savings': savings_original_output_data,
    'checking': checking_original_output_data,
    'fidelity': fidelity_original_output_data
}



######### Functions to remove the existing data from the uploads #########
def format_and_combo(original_output_df,upload_df):
    # Clean Amount column if needed
    original_amount_column = 'Amount' if 'Amount' in original_output_df.columns else 'Spent'
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
