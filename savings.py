#import setup
from folder_constants import *

#pick the needed df's from folder_constants.py
method = 'savings'
original_output_data = original_output_dataframes[method]
upload_df = upload_df_dictionary[method]

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

update_df(upload_df)

# format, add combo col
original_output_data, upload_df = format_and_combo(original_output_data, upload_df)

# remove rows already stored in output sheet so they're not uploaded twice
upload_df = remove_rows_already_saved(original_output_data,upload_df)

#append leftover rows to google sheets
if len(upload_df) > 0:
    if 'combo' in original_output_data.columns:
        original_output_data = original_output_data.drop('combo', axis=1)
    upload_df = pd.concat([upload_df,original_output_data],ignore_index=True)

    #format and sort
    upload_df['Date'] = pd.to_datetime(upload_df['Date'])
    upload_df = upload_df.sort_values(by=['Date']).reset_index(drop=True)
    upload_df['Date'] = upload_df['Date'].astype(str)

    #upload
    worksheet = spreadsheet.worksheet('Outputs')
    worksheet.range(sheets_info_dict[method][1]).clear()
    data = upload_df.values.tolist()
    worksheet.update(sheets_info_dict[method][0], data)


