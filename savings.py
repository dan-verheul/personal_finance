#import setup
from folder_constants import *

#pull original output data
worksheet = spreadsheet.worksheet('Savings Output')
data = worksheet.get_all_values()
if len(data) > 0:
    original_output_data = pd.DataFrame(data[1:], columns=data[0])
else:
    original_output_data = pd.DataFrame()

#Pull from google sheets
worksheet = spreadsheet.worksheet('Uploads')
range_to_pull = 'G2:K'
data = worksheet.get(range_to_pull)
savings_df = pd.DataFrame(data[1:], columns=data[0])

#update values
def update_description(description):
    if any(substring in description for substring in ['Requested transfer from ALLY BANK Spending account XXXXXX8706', 
                                                      'Internet transfer from Spending account XXXXXX8706']):
        return 'Transfer from Ally Checking'
    if any(substring in description for substring in ['Requested transfer to ALLY BANK Spending account XXXXXX8706', 
                                                      'Internet transfer to Spending account XXXXXX8706']):
        return 'Transfer to Ally Checking'
    elif 'EOS FITNESS' in description:
        return 'EOS Gym'
    elif any(substring in description for substring in ['ATM Fee Reimbursement', 'Interest Paid']):
        return description
    elif description == 'NFCU ACH PAYMENT':
        return 'NFCU Credit Card Payment'
    else:
        return '**'+description+'**'

def update_df(df):
    for index, row in df.iterrows():
        df.at[index, 'Description'] = update_description(row['Description'])

update_df(savings_df)


#remove time column
savings_df = savings_df.drop(columns=['Time'])


#now we want to filter out rows that are already in the original_output_data df
#create combo columns
original_output_data['Amount'] = original_output_data['Amount'].replace('[\$,]', '', regex=True)
savings_df['Amount'] = pd.to_numeric(savings_df['Amount']).map('{:.2f}'.format).astype(str)
# savings_df['Date'] = pd.to_datetime(savings_df['Date'], format='%m/%d/%Y').astype(str)

savings_df['combo'] = ''
for index, row in savings_df.iterrows():
    savings_df.at[index, 'combo'] = row['Date'] + row['Amount']
original_output_data['combo'] = original_output_data['Date'] + original_output_data['Amount']

savings_df['combo'] = savings_df['combo'].astype(str)
savings_df['combo'] = savings_df['combo'].str.strip()
original_output_data['combo'] = original_output_data['combo'].astype(str)
original_output_data['combo'] = original_output_data['combo'].str.strip()

#if savings_df combo column value in original_output_data combo col, then remove the row
savings_df = savings_df[~savings_df['combo'].isin(original_output_data['combo'])]
#drop the cols
savings_df = savings_df.drop(columns='combo')
original_output_data = original_output_data.drop(columns='combo')


#append to google sheets
if len(savings_df) > 0:
    upload_df = pd.concat([savings_df,original_output_data],ignore_index=True)

    #format and sort
    upload_df['Date'] = pd.to_datetime(upload_df['Date'])
    upload_df = upload_df.sort_values(by=['Date']).reset_index(drop=True)
    upload_df['Date'] = upload_df['Date'].astype(str)

    #upload
    worksheet = spreadsheet.worksheet('Savings Output')
    worksheet.clear()
    data = [upload_df.columns.tolist()] + upload_df.values.tolist()
    worksheet.update('A1', data)
