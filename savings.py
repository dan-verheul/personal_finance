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

# now join the upload_df with the original_df to include original rows
upload_df = pd.concat([upload_df,original_output_data],ignore_index=True)
if 'combo' in upload_df.columns:
            upload_df = upload_df.drop('combo', axis=1)


#append leftover rows to google sheets
if len(upload_df) > 0:
    #format and sort
    upload_df['Date'] = pd.to_datetime(upload_df['Date'])
    upload_df = upload_df.sort_values(by=['Date']).reset_index(drop=True)
    upload_df['Date'] = upload_df['Date'].astype(str)

    # Update Google Sheets
    # clear
    worksheet = spreadsheet.worksheet('Outputs')
    range_to_clear = worksheet.range(sheets_info_dict[method][1])
    for cell in range_to_clear:
        cell.value = ''
    worksheet.update_cells(range_to_clear)
    #upload
    data = upload_df.values.tolist()
    worksheet.update(sheets_info_dict[method][0], data, value_input_option='USER_ENTERED')


    # summary df
    savings_month_summary = upload_df.copy()
    savings_month_summary = savings_month_summary[['Date','Amount','Type']]
    savings_month_summary['Date'] = pd.to_datetime(savings_month_summary['Date'])
    savings_month_summary['Month'] = savings_month_summary['Date'].dt.to_period('M')
    savings_month_summary['Month'] = savings_month_summary['Month'].astype(str)
    savings_month_summary['Amount'] = savings_month_summary['Amount'].astype(float)
    savings_month_summary = savings_month_summary[['Month','Amount','Type']]
    savings_month_summary = savings_month_summary.groupby(['Month','Type'])['Amount'].sum().reset_index()
