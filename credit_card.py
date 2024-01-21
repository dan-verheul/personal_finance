############################################## Setup ###############################################
#import setup
from folder_constants import *

#pick the needed df's from folder_constants.py
method = 'credit_card'
credit_card = 'Chase'
original_output_data = original_output_dataframes[method]
upload_df = upload_df_dictionary[method]
original_upload_df = upload_df.copy()

#create lookup_df
worksheet = spreadsheet.worksheet('Lookup')
data = worksheet.get_all_values()
columns_a_to_c = [row[:4] for row in data]
lookup_df = pd.DataFrame(columns_a_to_c, columns=['Store', 'Category', 'Sub Category','Description'])
lookup_df = lookup_df.drop(0)
lookup_df = lookup_df.sort_values(by=['Category','Store'])
lookup_df = lookup_df.reset_index(drop=True)



############################### Clean up description column one-offs ###############################
#get simplified store in upload_df
upload_df.loc[upload_df['Description'].str.lower().str.contains('amazon|amzn mkt', na=False), 'Description'] = 'Amazon' #anything that has lower(string)='amazon' just change it to 'amazon'
upload_df['Description'] = upload_df['Description'].str.replace('.com', '', case=False) #remove any .com's
upload_df.loc[upload_df['Description'].str.lower().str.contains('wholefds', na=False), 'Description'] = 'Whole Foods'
upload_df.loc[upload_df['Description'].str.lower().str.contains('american air', na=False), 'Description'] = 'American Air'
upload_df.loc[upload_df['Description'].str.lower().str.contains('frontier', na=False), 'Description'] = 'Frontier'
upload_df.loc[upload_df['Description'].str.lower().str.contains('thtribeclothing', na=False), 'Description'] = '12th Tribe'
upload_df.loc[upload_df['Description'].str.lower().str.contains('rwlv gatsbys', na=False), 'Description'] = 'Gatsbys Cocktail Lounge'
upload_df.loc[upload_df['Description'].str.lower().str.contains('d n wolfgang puck las', na=False), 'Description'] = 'Wolfgang Puck Bar'
upload_df.loc[upload_df['Description'].str.lower().str.contains('clubpilates', na=False), 'Description'] = 'Club Pilates'
upload_df.loc[upload_df['Description'].str.lower().str.contains('aim diamond h', na=False), 'Description'] = 'Diamond Head'
upload_df.loc[upload_df['Description'].str.lower().str.contains('dusk fest', na=False), 'Description'] = 'Dusk Music Festival'
upload_df.loc[upload_df['Description'].str.lower().str.contains('payment thank you-mobile', na=False), 'Description'] = 'Credit Card Paid'

frys_pattern = r'frys|fry\'s' #change strings with "Fry's" or "Frys" to simply "Frys"
upload_df.loc[upload_df['Description'].str.lower().str.contains('frys|fry\'s', na=False), 'Description'] = 'Frys'

#remove payment system abbreviations ("Sq *"= Square, "Tst*" = Toast) also do same thing for "Gilbert", "-Gilbert", "Gilber"
upload_df['Description'] = upload_df['Description'].str.replace(r'Tst\*|Sq \*|Til\*|- Gilbert|- Gilber', '', regex=True)



############################## Get Store, Category, Sub Category, etc ##############################
#get simplified store
upload_df['Description'] = upload_df['Description'].str.strip()
def partial_string_match(s1, s2):
    # return s1.lower() in s2.lower()
    return (s1.lower() in s2.lower()) or (s2.lower() in s1.lower())

#pull in Store, Category, Sub Category, and Notes columns
upload_df['Store'] = upload_df['Description'].apply(
    lambda x: lookup_df['Store'][lookup_df['Store'].apply(lambda y: partial_string_match(y, x))].iloc[0] if any(lookup_df['Store'].apply(lambda y: partial_string_match(y, x))) else '*****' + x)
upload_df['Category'] = upload_df['Description'].apply(
    lambda x: lookup_df['Category'][lookup_df['Store'].apply(lambda y: partial_string_match(y, x))].iloc[0] if any(lookup_df['Store'].apply(lambda y: partial_string_match(y, x))) else '*****' + x)
upload_df['Sub Category'] = upload_df['Description'].apply(
    lambda x: lookup_df['Sub Category'][lookup_df['Store'].apply(lambda y: partial_string_match(y, x))].iloc[0] if any(lookup_df['Store'].apply(lambda y: partial_string_match(y, x))) else '*****' + x)
upload_df['Notes'] = upload_df['Description'].apply(
    lambda x: lookup_df['Description'][lookup_df['Store'].apply(lambda y: partial_string_match(y, x))].iloc[0] if any(lookup_df['Store'].apply(lambda y: partial_string_match(y, x))) else '*****' + x)

#clean up "Paid Credit Card" values. Remove asterisks from Store column, remove the value found in the other columns
upload_df['Store'] = upload_df['Store'].str.replace('*****Credit Card Paid', 'Credit Card Paid')
columns_to_check = ['Category', 'Sub Category', 'Notes']
for column in columns_to_check:
    upload_df[column] = upload_df[column].apply(lambda x: '' if x == '*****Credit Card Paid' else x)



######################## Change Groceries to Gas if Between Certain Amounts ########################
mask = (upload_df['Store'] == 'Frys') & (upload_df['Spent'].between(45, 65)) #this assumes any purchase from Frys between these two numbers is for gas
upload_df.loc[mask, 'Category'] = 'Gas' #if top checks out then change to this
upload_df.loc[mask, 'Sub Category'] = None 



######################################### Add Travel Column  #######################################
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

# add to this list where you know categories and/or subcategories should not be included in travel expenses
not_travel_subcategories = ['Home Improvement','Etsy','Pet','Science Center','Games','Car Insurance']

#look at main_df, if category is in list and transaction date is in travel_df, then change to Travel category and move Category to Sub Category
upload_df = upload_df.merge(travel_df, left_on='Transaction Date', right_on='Date', how='left')
upload_df = upload_df.drop(columns=['Date'])
upload_df = upload_df.rename(columns={'Notes (required)':'Travel'})
upload_df['Travel'].fillna('', inplace=True)

#remove the value from Travel column if the category on that row is not in travel_categories list
condition = ~upload_df['Category'].isin(travel_categories) | (upload_df['Store'] == 'F45') # we include F45 here because it falls under Self Care for Fitness but isn't part of travel, just a one off
upload_df.loc[condition, 'Travel'] = ''

#if Travel Day = 'Yes' and Category in travel_categories, then make adjustments
condition = upload_df['Travel'] != ''
sub_category_present = upload_df['Sub Category'] != ''
not_in_not_travel_subcategories = upload_df['Sub Category'].isin(not_travel_subcategories)

upload_df.loc[condition & sub_category_present & ~not_in_not_travel_subcategories, 'Sub Category'] = upload_df['Category'] + ' - ' + upload_df['Sub Category']
upload_df.loc[condition & ~sub_category_present & ~not_in_not_travel_subcategories, 'Sub Category'] = upload_df['Category']
upload_df.loc[condition & ~not_in_not_travel_subcategories, 'Category'] = 'Travel'

#if non travel purchase made during travel, then remove value under Travel column
mask = (upload_df['Travel'].notnull()) & (upload_df['Category'] != 'Travel')
upload_df.loc[mask, 'Travel'] = ''



######################################## Clean New Upload DF #######################################
upload_df = upload_df[['Transaction Date','Store','Spent','Category','Sub Category','Notes','Travel']]

#stores that need to be added (ones that have "*****") have that same value across all columns, remove that value from the other columns
mask_store = upload_df['Store'].str.startswith('*****')
if mask_store.any():
    upload_df.loc[mask_store, 'Category'] = upload_df.loc[mask_store, 'Category'].apply(lambda x: '' if x.startswith('*****') else x)
    upload_df.loc[mask_store, 'Sub Category'] = upload_df.loc[mask_store, 'Sub Category'].apply(lambda x: '' if x.startswith('*****') else x)
    upload_df.loc[mask_store, 'Notes'] = upload_df.loc[mask_store, 'Notes'].apply(lambda x: '' if x.startswith('*****') else x)

#add refunded column
upload_df['Refunded'] = ''
negative_spent_mask = upload_df['Spent'] < 0
upload_df.loc[negative_spent_mask, 'Refunded'] = upload_df.loc[negative_spent_mask, 'Spent'].abs()
upload_df.loc[negative_spent_mask, 'Spent'] = ''
upload_df = upload_df[['Transaction Date','Store','Spent','Refunded','Category','Sub Category','Notes','Travel']]



############################ Create Cycle Totals and Rolling 12 Columns ############################
upload_df['Cycle'] = pd.to_datetime(upload_df['Transaction Date']).dt.to_period('M').astype(str)

# look at cycle_date_df, filter out all rows that don't match the variable above, then add that value to upload_df
filtered_cycle_date_df = important_dates_df[important_dates_df['Category'] == credit_card]
filtered_cycle_date = important_dates_df.loc[important_dates_df['Category'] == credit_card, 'Date'].values
upload_df['Cycle Date'] = filtered_cycle_date[0] if filtered_cycle_date else 0

#if the day # in transaction date > value in cycle date, then add 1 month to Cycle, otherwise keep it the same
upload_df['Cycle'] = upload_df.apply(lambda row: (row['Transaction Date'] + pd.DateOffset(months=1)).strftime('%Y-%m') if row['Transaction Date'].day > row['Cycle Date'] else row['Cycle'], axis=1)
upload_df = upload_df.drop('Cycle Date', axis=1)

#Rolling 12 column helps with pivot table formatting
upload_df['Transaction Date'] = pd.to_datetime(upload_df['Transaction Date'])
upload_df['MonthTrunc'] = upload_df['Transaction Date'].dt.to_period('M')
max_month = upload_df['MonthTrunc'].max()
upload_df['Rolling12'] = ['Yes' if (max_month - x).n <= 12 else 'No' for x in upload_df['MonthTrunc']]
upload_df = upload_df.drop(columns='MonthTrunc')



############################### Compare to What's Already in Sheets ################################
# format, add combo col
original_output_data, upload_df = format_and_combo(original_output_data, upload_df)

# remove rows already stored in output sheet so they're not uploaded twice
upload_df = remove_rows_already_saved(original_output_data,upload_df)




##################### Fix Amazon/Department Store Categories and Sub Categories ####################
#create a list of stores to include as Amazon/Department Stores
multi_store_list = ['Amazon', 'Costco', 'Target']

multi_store_df = upload_df[upload_df['Store'].isin(multi_store_list)].reset_index(drop=True)
upload_df = upload_df[~upload_df['Store'].isin(multi_store_list)].reset_index(drop=True)

multi_store_df['Sub Category'] = multi_store_df['Sub Category'].replace('Amazon','')

# Create a loop that requires user to assign number value for the Sub Category
distinct_categories = lookup_df['Category'][lookup_df['Category'] != ''][lookup_df['Category']!='Shopping'].drop_duplicates().tolist()
for index, row in multi_store_df.iterrows():
    date = pd.to_datetime(row['Transaction Date']).strftime('%m/%d/%y')
    # description = row['Description']
    spent = row['Spent']
    store = row['Store']
    distinct_categories = lookup_df['Category'][lookup_df['Category'] != ''][lookup_df['Category']!='Shopping'].drop_duplicates().tolist()

    print(f"\nOn {date}, there was a ${float(spent):.2f} charge on {store}. What kind of purchase was this?")
    for i, category in enumerate(distinct_categories):
        print(f"{i+1}. {category}")
    selected_index = input("Enter the number corresponding \nto your choice: ")
    selected_category = distinct_categories[int(selected_index) - 1]
    multi_store_df.at[index, 'Sub Category'] = selected_category

# Create a loop that requires user to input a Note for each Amazon transaction
multi_store_df['Notes'] = ''
for index, row in multi_store_df.iterrows():
    date = pd.to_datetime(row['Transaction Date']).strftime('%m/%d/%y')
    # description = row['Description']
    spent = row['Spent']
    store = row['Store']
    
    user_input = input(f"On {date}, there was a ${float(spent):.2f} charge on {store}. What was this? If no note needed, just press Enter with no text")
    multi_store_df.at[index,'Notes'] = user_input

#combine the two dataframes back together and order
upload_df = pd.concat([multi_store_df, upload_df], ignore_index=True)



######################################### Upload to Sheets #########################################
if len(upload_df) > 0:
    upload_df = pd.concat([upload_df,original_output_data],ignore_index=True) #combine new rows with what's in google sheets already
    upload_df['Spent'] = upload_df['Spent'].replace('nan', '')

    #format and sort
    upload_df = upload_df.sort_values(by=['Transaction Date','Travel']).reset_index(drop=True)
    upload_df['Transaction Date'] = upload_df['Transaction Date'].astype(str)
    upload_df['Cycle'] = upload_df['Cycle'].astype(str)

    if 'combo' in upload_df.columns:
        upload_df = upload_df.drop('combo', axis=1)

    #upload
    worksheet = spreadsheet.worksheet('Outputs')
    worksheet.range(sheets_info_dict[method][1]).clear()
    data = upload_df.values.tolist()
    worksheet.update(sheets_info_dict[method][0], data, value_input_option='USER_ENTERED')
