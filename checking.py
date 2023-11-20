#import setup
from folder_constants import *

#pull original output data
worksheet = spreadsheet.worksheet('Checking Output')
data = worksheet.get_all_values()
if len(data) > 0:
    original_output_data = pd.DataFrame(data[1:], columns=data[0])
else:
    original_output_data = pd.DataFrame()

#Pull from google sheets
worksheet = spreadsheet.worksheet('Uploads')
range_to_pull = 'M2:Q'
data = worksheet.get(range_to_pull)
checking_df = pd.DataFrame(data[1:], columns=data[0])

#update values
def update_description(description):
    if description == 'BARCLAYCARD US CREDITCARD':
        return 'Hawaiian Air Credit Card'
    elif description == 'NATIONAL COLLEGI DIRECT DEP':
        return 'NCSA Paycheck'
    elif description == 'FID BKG SVC LLC MONEYLINE':
        return 'Fidelity'
    elif description == 'NFCU ACH PAYMENT':
        return 'NFCU Credit Card'
    elif description == 'BETMGM LLC BETMGM US':
        return 'BetMGM'
    elif description == 'VENMO PAYMENT':
        return 'Venmo'
    elif description == 'M1 PAYMENTS':
        return 'M1'
    elif 'to ALLY BANK Savings' in description or 'to Savings account XXXXXX3190' in description:
        return 'Ally Checking to Savings'
    elif 'from Savings account XXXXXX3190' in description:
        return 'Ally Savings to Checking'
    elif 'NAVY FEDERAL CREDIT UNION Checking 5307' in description:
        return 'NFCU Checking'
    elif any(substring in description for substring in ['ATM Fee Reimbursement', 
                                                        'Interest Paid']):
        return description
    else:
        return '**'+description+'**'

def update_df(df):
    for index, row in df.iterrows():
        df.at[index, 'Description'] = update_description(row['Description'])

update_df(checking_df)


#remove time column
checking_df = checking_df.drop(columns=['Time'])


#now we want to filter out rows that are already in the original_output_data df
#create combo columns
original_output_data['Amount'] = original_output_data['Amount'].replace('[\$,]', '', regex=True)
checking_df['Amount'] = pd.to_numeric(checking_df['Amount']).map('{:.2f}'.format).astype(str)
# checking_df['Date'] = pd.to_datetime(checking_df['Date'], format='%m/%d/%Y').astype(str)

checking_df['combo'] = ''
for index, row in checking_df.iterrows():
    checking_df.at[index, 'combo'] = row['Date'] + row['Amount']
original_output_data['combo'] = original_output_data['Date'] + original_output_data['Amount']
checking_df['combo'] = checking_df['combo'].astype(str)
original_output_data['combo'] = original_output_data['combo'].astype(str)
checking_df['combo'] = checking_df['combo'].str.strip()
original_output_data['combo'] = original_output_data['combo'].str.strip()

#if checking_df combo column value in original_output_data combo col, then remove the row
checking_df = checking_df[~checking_df['combo'].isin(original_output_data['combo'])]
#drop the cols
checking_df = checking_df.drop(columns='combo')
original_output_data = original_output_data.drop(columns='combo')


#add category column - column will be used in pivots/charts/summary stuff
checking_df['Category'] = ''

#update values
# def update_description(description):
#     if any(substring in description for substring in ['NCSA Paycheck', 
#                                                         'Interest Paid']):
#         return 'Input'
#     elif '' in description:
#         return 'NFCU Checking'
#     else:
#         return ''

# def update_df(df):
#     for index, row in df.iterrows():
#         df.at[index, 'Description'] = update_description(row['Description'])

# update_df(checking_df)


#append to google sheets
if len(checking_df) > 0:
    upload_df = pd.concat([checking_df,original_output_data],ignore_index=True)

    #format and sort
    upload_df['Date'] = pd.to_datetime(upload_df['Date'])
    upload_df = upload_df.sort_values(by=['Date']).reset_index(drop=True)
    upload_df['Date'] = upload_df['Date'].astype(str)

    #upload
    worksheet = spreadsheet.worksheet('Checking Output')
    worksheet.clear()
    data = [upload_df.columns.tolist()] + upload_df.values.tolist()
    worksheet.update('A1', data)