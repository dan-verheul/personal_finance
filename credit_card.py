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

#1
spreadsheet = client.open('$$')
worksheet = spreadsheet.worksheet('Credit Card Upload')
data = worksheet.get_all_values()
credit_card_df = pd.DataFrame(data[1:], columns=data[0])
credit_card_df = credit_card_df.rename(columns={'Debit':'Spent','Credit':'Refunded'})
credit_card_df = credit_card_df.drop(columns='Posted Date')

#2
worksheet = spreadsheet.worksheet('Credit Card Output')
data = worksheet.get_all_values()
original_output_data = pd.DataFrame(data[1:], columns=data[0])

#3
worksheet = spreadsheet.worksheet('Lookup')
data = worksheet.get_all_values()
columns_a_to_c = [row[:3] for row in data]
lookup_df = pd.DataFrame(columns_a_to_c, columns=['Store', 'Category', 'Sub Category'])
lookup_df = lookup_df.drop(0)
lookup_df = lookup_df.sort_values(by=['Category','Store'])
lookup_df = lookup_df.reset_index(drop=True)
lookup_df = lookup_df.drop(0)
duplicates = lookup_df.duplicated(keep='first')
lookup_df = lookup_df[~duplicates]
lookup_df = lookup_df.reset_index(drop=True)
lookup_df['Occurrences'] = lookup_df.groupby('Store')['Store'].transform('count')


#common abbreviations
credit_card_df['Description'] = credit_card_df['Description'].apply(lambda x: x.lower() if isinstance(x, str) else x)
credit_card_df['Description'] = credit_card_df['Description'].apply(lambda x: 'Amazon' if 'amzn' in x.lower() else x)
credit_card_df['Description'] = credit_card_df['Description'].apply(lambda x: 'Amazon' if 'amazon' in x.lower() else x)
credit_card_df['Description'] = credit_card_df['Description'].apply(lambda x: 'El Guero Tacos in Tucson' if 'el guero' in x.lower() else x)
credit_card_df['Description'] = credit_card_df['Description'].apply(lambda x: 'Tacos Tucson (Street- Taco and Beer Co)' if 'tacos tucson az' in x.lower() else x)
credit_card_df['Description'] = credit_card_df['Description'].apply(lambda x: 'The Monica - Tucson' if 'the monica' in x.lower() else x)

#get simplified store
def partial_string_match(s1, s2):
    return s1.lower() in s2.lower()
result_df = credit_card_df.copy()
for column in lookup_df.columns:
    result_df[column] = credit_card_df['Description'].apply(lambda x: lookup_df['Store'][lookup_df['Store'].apply(lambda y: partial_string_match(y, x))].iloc[0] if any(lookup_df['Store'].apply(lambda y: partial_string_match(y, x))) else None)
result_df.drop(columns=['Category','Sub Category','Occurrences'],inplace=True) #Bring in all cols, just drop these since they're all the same
result_df['Store'].fillna("", inplace=True)

#now we want to filter out rows that are already in the original_output_data df
#create combo columns
original_output_data['Spent'] = original_output_data['Spent'].replace('[\$,]', '', regex=True)
result_df['Spent'] = pd.to_numeric(result_df['Spent']).map('{:.2f}'.format).astype(str)
result_df['Transaction Date'] = pd.to_datetime(result_df['Transaction Date'], format='%m/%d/%Y').astype(str)

result_df['combo'] = ''
for index, row in result_df.iterrows():
    if row['Store'] != "":
        result_df.at[index, 'combo'] = row['Transaction Date'] + row['Store'] + row['Spent']
    else:
        result_df.at[index, 'combo'] = row['Transaction Date'] + row['Description'] + row['Spent']
original_output_data['combo'] = original_output_data['Transaction Date'] + original_output_data['Store'] + original_output_data['Spent']
result_df['combo'] = result_df['combo'].astype(str)
original_output_data['combo'] = original_output_data['combo'].astype(str)
result_df['combo'] = result_df['combo'].str.strip()
original_output_data['combo'] = original_output_data['combo'].str.strip()

#if result_df combo column value in original_output_data combo col, then remove the row
result_df = result_df[~result_df['combo'].isin(original_output_data['combo'])]
#drop the cols
result_df = result_df.drop(columns='combo')
original_output_data = original_output_data.drop(columns='combo')


#left join to get Category and Sub Category
if len(result_df) > 0:
    result_df = pd.merge(result_df, lookup_df, on='Store', how='left')
    result_df['Category'].fillna("", inplace=True)
    result_df['Sub Category'].fillna("", inplace=True)
    duplicates = result_df.duplicated(keep='first')
    result_df = result_df[~duplicates]
    result_df = result_df.reset_index(drop=True)
    result_df['Transaction Date'] = pd.to_datetime(result_df['Transaction Date'])
    result_df['Spent'] = pd.to_numeric(result_df['Spent'], errors='coerce')
    result_df['Occurrences'] = pd.to_numeric(result_df['Occurrences'], errors='coerce')

    #create a df to filter out duplicate rows (ex: Frys gets duplicated b/c it's Food category and Gas)
    dups_df = result_df[(result_df['Occurrences'] != '') & (result_df['Occurrences'] != 1.0)]
    condition = ((dups_df['Category'] == 'Gas') & (dups_df['Spent'].between(40, 65))) | \
                ((dups_df['Category'] == 'Food') & ((dups_df['Spent'] < 40) | (dups_df['Spent'] > 65)))
    dups_fixed_df = dups_df[condition]

    #delete rows 
    result_df['Occurrences'].fillna("", inplace=True)
    result_df = result_df[(result_df['Occurrences'] == '') | (result_df['Occurrences'] == 1.0)]
    result_df = pd.concat([result_df, dups_fixed_df], ignore_index=True)
    result_df = result_df.sort_values(by=['Transaction Date','Store'], ascending=[False, True])
    result_df = result_df.reset_index(drop = True)
    result_df = result_df.drop(columns='Occurrences')

    #fix amazon categories, by default they are shopping but put these in another df and create a loop that updates each category value, then add back to df
    amazon_df = result_df[result_df['Store'] == 'Amazon'].reset_index(drop=True)
    result_df = result_df[result_df['Store'] != 'Amazon'].reset_index(drop=True)

    amazon_df['Sub Category'] = amazon_df['Sub Category'].replace('Amazon','')

    distinct_categories = lookup_df['Category'][lookup_df['Category'] != ''].drop_duplicates().tolist()

    for index, row in amazon_df.iterrows():
        date = pd.to_datetime(row['Transaction Date']).strftime('%m/%d/%y')
        description = row['Description']
        spent = row['Spent']
        store = row['Store']
        distinct_categories = lookup_df['Category'][lookup_df['Category'] != ''].drop_duplicates().tolist()

        print(f"\nOn {date}, there was a ${spent:.2f} charge on {store}. What kind of purchase was this?")
        for i, category in enumerate(distinct_categories):
            print(f"{i+1}. {category}")
        selected_index = input("Enter the number corresponding \nto your choice: ")

        selected_category = distinct_categories[int(selected_index) - 1]
        amazon_df.at[index, 'Sub Category'] = selected_category

    #add notes column
    amazon_df['Notes'] = ''
    for index, row in amazon_df.iterrows():
        date = pd.to_datetime(row['Transaction Date']).strftime('%m/%d/%y')
        description = row['Description']
        spent = row['Spent']
        store = row['Store']
        
        user_input = input(f"On {date}, there was a ${spent:.2f} charge on {store}. What was this? If no note needed, just press Enter with no text")
        amazon_df.at[index,'Notes'] = user_input


    # add notes column to main df
    main_df = result_df[['Transaction Date','Store','Spent','Refunded','Category','Sub Category']]
    main_df['Notes']=''
    main_df = pd.concat([main_df, amazon_df], ignore_index=True)
    main_df = main_df.drop(columns='Description')
    main_df = main_df.sort_values(by=['Transaction Date','Store'], ascending=[False, True]).reset_index(drop=True)
    #figure out best way to add notes

    # TRAVEL LOGIC
    worksheet = spreadsheet.worksheet('Travel Dates')
    data = worksheet.get_all_values()
    travel_df = pd.DataFrame(data[1:], columns=data[0])
    new_rows = []

    # Iterate through each row in the travel_df
    for index, row in travel_df.iterrows():
        start_date = pd.to_datetime(row['Start Date'], format='%a, %m/%d/%y')
        end_date = pd.to_datetime(row['End Date'], format='%a, %m/%d/%y')
        notes = row['Notes (required)']
        date_range = pd.date_range(start=start_date, end=end_date)
        for date in date_range:
            new_rows.append({'Date': date.strftime('%a, %m/%d/%y'), 'Notes (required)': notes})
    travel_df = pd.DataFrame(new_rows)
    travel_df['Date'] = pd.to_datetime(travel_df['Date'], format='%a, %m/%d/%y')
    travel_df = travel_df.sort_values(by=['Date']).reset_index(drop=True)


    #list of categories that can fall under travel
    travel_categories = ['Drinks','Event','Food','Gas','Self Care','Splurging','Travel','Hotel']

    # add to this list where you know subcategories should not be included in travel expenses
    not_travel_subcategories = ['Home Improvement','Etsy','Pet','Science Center','Games','Car Insurance']


    #look at main_df, if category is in list and transaction date is in travel_df, then change to Travel category and move Category to Sub Category
    main_df['Transaction Date'] = pd.to_datetime(main_df['Transaction Date'])
    travel_df['Date'] = pd.to_datetime(travel_df['Date'])

    main_df = main_df.merge(travel_df, left_on='Transaction Date', right_on='Date', how='left')
    main_df = main_df.drop(columns=['Date'])
    main_df = main_df.rename(columns={'Notes (required)':'Travel'})
    main_df['Travel'].fillna('', inplace=True)

    #if Travel Day = 'Yes' and Category in travel_categories, then make adjustments
    condition = main_df['Travel'] != ''
    sub_category_present = main_df['Sub Category'] != ''
    not_in_not_travel_subcategories = main_df['Sub Category'].isin(not_travel_subcategories)

    main_df.loc[condition & sub_category_present & ~not_in_not_travel_subcategories, 'Sub Category'] = main_df['Category'] + ' - ' + main_df['Sub Category']
    main_df.loc[condition & ~sub_category_present & ~not_in_not_travel_subcategories, 'Sub Category'] = main_df['Category']
    main_df.loc[condition & ~not_in_not_travel_subcategories, 'Category'] = 'Travel'

    #if non travel purchase made during travel, then remove value under Travel column
    mask = (main_df['Travel'].notnull()) & (main_df['Category'] != 'Travel')
    main_df.loc[mask, 'Travel'] = ''


    # get ready for Google Sheets upload
    #if we have a blank store, then pull in the description. Left join the transaction date, spent, and refunded columns to original df
    blank_store = main_df[main_df['Store'] == ''].copy().reset_index(drop=True)
    main_df = main_df[main_df['Store'] != ''].reset_index(drop=True)

    blank_store['Spent'] = pd.to_numeric(blank_store['Spent'], errors='coerce')
    blank_store['Refunded'] = pd.to_numeric(blank_store['Refunded'], errors='coerce')
    credit_card_df['Spent'] = pd.to_numeric(credit_card_df['Spent'], errors='coerce')
    credit_card_df['Refunded'] = pd.to_numeric(credit_card_df['Refunded'], errors='coerce')

    blank_store['Spent'] = blank_store['Spent'].astype(float)
    blank_store['Refunded'] = blank_store['Refunded'].astype(float)
    credit_card_df['Spent'] = credit_card_df['Spent'].astype(float)
    credit_card_df['Refunded'] = credit_card_df['Refunded'].astype(float)
    blank_store['Transaction Date'] = pd.to_datetime(blank_store['Transaction Date'])
    credit_card_df['Transaction Date'] = pd.to_datetime(credit_card_df['Transaction Date'], format='%m/%d/%Y')

    blank_store = pd.merge(blank_store, credit_card_df, on=['Transaction Date', 'Spent', 'Refunded'], how='left')
    blank_store['Store'] = blank_store['Description']
    blank_store = blank_store.drop(columns=['Description'])

    #combined df's back together and reorder and reset index
    main_df = pd.concat([main_df, blank_store], ignore_index=True)
    main_df['Transaction Date'] = pd.to_datetime(main_df['Transaction Date'])
    main_df = main_df.sort_values(by=['Transaction Date']).reset_index(drop=True)
    main_df = main_df.fillna('')



    # we want to combine these new rows with what we originally had pulled from "Credit Card Output", then replace everything in google sheets
    #combine original_output_data with main_df
    upload_df = pd.concat([main_df,original_output_data],ignore_index=True)

    #format and sort
    upload_df['Transaction Date'] = pd.to_datetime(upload_df['Transaction Date'])
    upload_df = upload_df.sort_values(by=['Transaction Date']).reset_index(drop=True)
    upload_df['Transaction Date'] = upload_df['Transaction Date'].astype(str)

    #upload
    worksheet = spreadsheet.worksheet('Credit Card Output')
    worksheet.clear()
    data = [upload_df.columns.tolist()] + upload_df.values.tolist()
    worksheet.update('A1', data)
