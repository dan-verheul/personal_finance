#import setup
from folder_constants import *

#pick the needed df's from folder_constants.py
method = 'fidelity'
original_output_data = original_output_dataframes[method]
upload_df = upload_df_dictionary[method]
original_upload_df = upload_df.copy()

original_upload_df['Quantity'] = pd.to_numeric(original_upload_df['Quantity'], errors='coerce')
original_upload_df['Price'] = pd.to_numeric(original_upload_df['Price'], errors='coerce')
original_upload_df['Amount'] = pd.to_numeric(original_upload_df['Amount'], errors='coerce')

original_upload_df['Quantity'].fillna(0, inplace=True)
original_upload_df['Price'].fillna(0, inplace=True)
original_upload_df['Amount'].fillna(0, inplace=True)

original_upload_df['Quantity'] = original_upload_df['Quantity'].astype(float)
original_upload_df['Price'] = original_upload_df['Price'].astype(float)
original_upload_df['Amount'] = original_upload_df['Amount'].astype(float)

#rename accounts
value_mapping = {account_1: account_1_type, 
                 account_2: account_2_type, 
                 account_3: account_3_type, 
                 account_4: account_4_type
                 }
original_upload_df['Account'] = original_upload_df['Account'].replace(value_mapping)

#limit to 4 words for this portion, renaming values
original_upload_df['Action'] = original_upload_df['Action'].str.split().str[:4].str.join(' ').apply(lambda x: x.title())
#rename some actions
value_mapping = {'Electronic Funds Transfer Paid': 'Transfer Out','Electronic Funds Transfer Received': 'Transfer In'}
original_upload_df['Action'] = original_upload_df['Action'].replace(value_mapping)

#limit to 2 words now
original_upload_df['Action'] = original_upload_df['Action'].str.split().str[:2].str.join(' ').apply(lambda x: x.title())
#rename some actions
value_mapping = {'Dividend Received': 'Dividend Received',
                 'Reinvestment Fidelity': 'Dividend Reinvested',
                 'You Bought': 'Buy', 
                 'You Sold': 'Sell', 
                 'Cash Contribution': 'Added Money'
                 }
original_upload_df['Action'] = original_upload_df['Action'].replace(value_mapping)


#sort by account and date desc
original_upload_df = original_upload_df.sort_values(by=['Account', 'Date'], ascending=[True, True]).reset_index(drop=True)


#df that shows simplified view (ex: add cash row is removed and buy is flipped to positive number )
fidelity_simplified = original_upload_df.copy()
fidelity_simplified = fidelity_simplified[fidelity_simplified['Action'] != 'Dividend Reinvested'].reset_index(drop=True)
value_mapping = {'Dividend Received': 'Dividend Reinvested'}
fidelity_simplified['Action'] = fidelity_simplified['Action'].replace(value_mapping)

fidelity_simplified['Amount'] = fidelity_simplified.apply(lambda row: row['Amount'] * -1 if row['Action'] == 'Buy' else row['Amount'], axis=1)

# add account holder column
def determine_holder(account):
    if account.startswith('D - '):
        return 'Dan'
    elif account.startswith('R - '):
        return 'Rachel'
    else:
        return 'Both'

fidelity_simplified['Holder'] = fidelity_simplified['Account'].apply(determine_holder)
fidelity_simplified['Account'] = fidelity_simplified['Account'].str.replace('D - |R - ', '', regex=True)

fidelity_simplified = fidelity_simplified[['Date','Holder','Account','Action','Symbol','Quantity','Price','Amount']]

#get ytd
fidelity_simplified['Year'] = fidelity_simplified['Date'].dt.year
fidelity_simplified['YTD'] = fidelity_simplified.groupby(['Holder', 'Account', 'Action', 'Year'])['Amount'].cumsum()
fidelity_simplified = fidelity_simplified.drop(columns=['Year'])

#pivot charts wonky in google sheets, output a df that has it pre-setup so we just make a graph
pivot_df = fidelity_simplified.copy()
pivot_df.drop(['Symbol','Quantity','Price','YTD'], axis=1, inplace=True)

#get mtd total
pivot_df['Month'] = pivot_df['Date'].dt.to_period('M')
pivot_df['Monthly Total'] = pivot_df.groupby(['Month', 'Holder', 'Account', 'Action'])['Amount'].cumsum()
pivot_df = pivot_df[['Month','Holder','Account','Action','Monthly Total']]

#select max values
max_indices = pivot_df.groupby(['Month', 'Holder', 'Account', 'Action'])['Monthly Total'].idxmax()
pivot_df = pivot_df.loc[max_indices].sort_values(by=['Account','Month', 'Holder']).reset_index(drop=True)

#get ytd
pivot_df['Year'] = pivot_df['Month'].dt.year
pivot_df['YTD'] = pivot_df.groupby(['Year', 'Holder', 'Account', 'Action'])['Monthly Total'].cumsum()
pivot_df = pivot_df.drop('Year', axis=1)

#################################### ROTH DF ####################################
# Get column names (except the first one) and convert them to a list
roth_df = pivot_df.copy()
roth_df = roth_df[(roth_df['Account'] == 'Roth IRA') & (roth_df['Action'] == 'Added Money')].reset_index(drop=True)

#add rows to df so it ends on december
# roth_df['Month'] = pd.to_datetime(roth_df['Month'])
roth_df = roth_df.sort_values(by='Month')
initial_target = 6500/12
roth_df['Target'] = initial_target
for i in range(1, len(roth_df)):
    roth_df.loc[i, 'Target'] += roth_df.loc[i - 1, 'Target']

# Check if the last month in the DataFrame is not December
if roth_df['Month'].max().month % 12 != 0:
    # Calculate the 'Target' value for December
    dec_target = roth_df['Target'].max() + initial_target
    
    # Add a row for December with the calculated target value
    roth_df = pd.concat([
        roth_df,
        pd.DataFrame([[roth_df['Month'].max() + 1, '', '', '', '', '', dec_target]],
                    columns=roth_df.columns)
    ]).reset_index(drop=True)
roth_df = roth_df.sort_values(by='Month')
roth_df = roth_df.fillna('')


#################################### TAXABLE DF ####################################
# Get column names (except the first one) and convert them to a list
taxable_df = pivot_df.copy()
taxable_df = taxable_df[(taxable_df['Account'] == 'Taxable') & ((taxable_df['Action'] == 'Dividend Reinvested') | (taxable_df['Action'] == 'Transfer Out') | (taxable_df['Action'] == 'Transfer In'))].reset_index(drop=True)
taxable_df = taxable_df[['Month','Holder','Account','Monthly Total']]
#group totals by month, holder, and account
taxable_df['Month'] = taxable_df['Month'].dt.to_timestamp()
taxable_df = taxable_df.groupby(['Month', 'Holder', 'Account'])['Monthly Total'].sum().reset_index()

#recalculate ytd since we're combining actions for simplicity
taxable_df['Year'] = taxable_df['Month'].dt.year
taxable_df['YTD'] = taxable_df.groupby(['Holder', 'Account', 'Year'])['Monthly Total'].cumsum()
taxable_df = taxable_df.drop(columns=['Year'])

#add rows to df so it ends on december
taxable_df = taxable_df.sort_values(by='Month')
monthly_target = 100
taxable_df['Target'] = taxable_df['YTD'].shift(1) + monthly_target
taxable_df.loc[0, 'Target'] = monthly_target

taxable_df = taxable_df.fillna('')

upload_df = fidelity_simplified.copy()
#################################### Sheets upload ####################################
if len(upload_df) > 0:
    #format
    upload_df['Date'] = upload_df['Date'].astype(str)
    upload_df['Quantity'] = upload_df['Quantity'].replace(0, '')
    upload_df['Price'] = upload_df['Price'].replace(0, '')

    worksheet = spreadsheet.worksheet('Outputs')
    worksheet.range(sheets_info_dict[method][1]).clear()
    data = upload_df.values.tolist()
    worksheet.update(sheets_info_dict[method][0], data, value_input_option='USER_ENTERED')

    #pivot upload
    pivot_df['Month'] = pivot_df['Month'].astype(str)
    worksheet = spreadsheet.worksheet('Graph Data')
    range_to_clear = 'A2:F'+ str(len(pivot_df))
    worksheet.batch_clear([range_to_clear])
    data = pivot_df.values.tolist()
    worksheet.update('A2', data, value_input_option='USER_ENTERED')


    #roth upload
    roth_df['Month'] = roth_df['Month'].astype(str)
    worksheet = spreadsheet.worksheet('Graph Data')
    range_to_clear = 'H2:N'+ str(len(roth_df))
    worksheet.batch_clear([range_to_clear])
    data = roth_df.values.tolist()
    worksheet.update('H2', data, value_input_option='USER_ENTERED')

    #taxable upload
    taxable_df['Month'] = taxable_df['Month'].astype(str)
    worksheet = spreadsheet.worksheet('Graph Data')
    range_to_clear = 'P2:U'+ str(len(taxable_df))
    worksheet.batch_clear([range_to_clear])
    data = taxable_df.values.tolist()
    worksheet.update('P2', data, value_input_option='USER_ENTERED')