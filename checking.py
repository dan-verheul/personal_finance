#import setup
from folder_constants import *

#pick the needed df's from folder_constants.py
method = 'checking'
original_output_data = original_output_dataframes[method]
upload_df = upload_df_dictionary[method]

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

update_df(upload_df)

#left join upload_df to mapping
upload_df = pd.merge(upload_df, mapping_df, left_on='Description', right_on='Description', how='left')
upload_df['Mapping'] = upload_df['Mapping'].fillna(upload_df['Description'])

#left join tiers_df on Level 3 = Description
upload_df = pd.merge(upload_df, tiers_df, left_on='Mapping', right_on='Level 3', how='left')
upload_df = pd.merge(upload_df, tiers_df, left_on='Mapping', right_on='Level 2', how='left', suffixes=('_level3', '_level2'))
upload_df = pd.merge(upload_df, tiers_df, left_on='Mapping', right_on='Level 1', how='left', suffixes=('_level3', '_level2', '_level1'))

upload_df['Final_Level 1'] = upload_df['Level 1_level3'].combine_first(upload_df['Level 1_level2']).combine_first(upload_df['Level 1'])
upload_df['Final_Level 2'] = upload_df['Level 2_level3'].combine_first(upload_df['Level 2_level2']).combine_first(upload_df['Level 2'])
upload_df['Final_Level 3'] = upload_df['Level 3_level3'].combine_first(upload_df['Level 3_level2']).combine_first(upload_df['Level 3'])

columns_to_drop = ['Level 1_level3', 'Level 2_level3', 'Level 3_level3',
                'Level 1_level2', 'Level 2_level2', 'Level 3_level2',
                'Level 1', 'Level 2', 'Level 3',
                'Mapping']
upload_df = upload_df.drop(columns=columns_to_drop)

upload_df = upload_df.rename(columns={'Final_Level 1':'Level 1',
                            'Final_Level 2':'Level 2',
                            'Final_Level 3':'Level 3',})
columns_to_fillna = ['Level 1', 'Level 2', 'Level 3']
upload_df[columns_to_fillna] = upload_df[columns_to_fillna].fillna('')

#Savings logic
#remove duplicate savings rows, getting dups because of the join
upload_df = upload_df[~((upload_df['Level 1'] == 'Savings') & upload_df.duplicated(subset=['Date', 'Amount', 'Level 1']))].reset_index(drop=True)
#remove L2 values from Savings
upload_df.loc[upload_df['Level 1'] == 'Savings', 'Level 2'] = ''
#convert bucket_df date col to date type, then delete rows where date started <> max(date staretd)
bucket_df['Date Started'] = pd.to_datetime(bucket_df['Date Started'])
max_date = bucket_df['Date Started'].max()
bucket_df = bucket_df[bucket_df['Date Started'] == max_date]

#left join
upload_df = pd.merge(upload_df, bucket_df, on='Level 1', how='left')
#cleanup
upload_df['Level 2'] = upload_df['Level 2'].mask(upload_df['Level 2'] == '', upload_df['Ally Bucket'])
upload_df = upload_df.drop(columns=['Date Started', 'Ally Bucket'])
upload_df['Level 2'] = upload_df['Level 2'].fillna('')
#apply percent allocation to amount column
upload_df['Amount'] = upload_df['Amount'].astype(float)
upload_df['Percent Allocation'] = upload_df['Percent Allocation'].astype(float)
upload_df.loc[upload_df["Level 1"] == "Savings", "Amount"] *= upload_df["Percent Allocation"]
upload_df = upload_df.drop(columns=['Percent Allocation'])

#Investing Logic
#if amount is 162.50 and L3 = Fidelity then Roth IRA
dan_ira_amount = 162.50
upload_df.loc[(upload_df["Description"] == "Fidelity"), "Level 1"] = "Investing"
upload_df.loc[(upload_df["Description"] == "Fidelity") & (upload_df["Amount"] == dan_ira_amount*-1), "Level 3"] = "Dan IRA"

upload_df.loc[(upload_df["Description"] == "Fidelity") & (upload_df["Level 3"].str.contains('401K|IRA', case=False, na=False)), "Level 2"] = "Retirement"


#Spending Logic
upload_df.loc[(upload_df["Description"].str.contains('Credit Card|BetMGM', case=False, na=False)), "Level 1"] = "Spending"


# format, add combo col
original_output_data, upload_df = format_and_combo(original_output_data, upload_df)

# remove rows already stored in output sheet so they're not uploaded twice
upload_df = remove_rows_already_saved(original_output_data,upload_df)

# now join the upload_df with the original_df to include original rows
if 'combo' in original_output_data.columns:
    original_output_data = original_output_data.drop('combo', axis=1)

if len(original_output_data) > 0:
    upload_df = pd.concat([upload_df,original_output_data],ignore_index=True)

if 'combo' in upload_df.columns:
    upload_df = upload_df.drop('combo', axis=1)

#update google sheets and excel
if len(upload_df) > 0:
    #format and sort
    upload_df['Date'] = pd.to_datetime(upload_df['Date'])
    upload_df = upload_df.sort_values(by=['Date']).reset_index(drop=True)
    # upload_df['Date'] = upload_df['Date'].astype(str)
    upload_df['Date'] = upload_df['Date'].dt.strftime('%Y-%m-%d')
    upload_df['Amount'] = upload_df['Amount'].astype(float)

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



    # Update excel
    # import openpyxl
    # if os.path.basename(current_directory) == 'GitHub':
    #     move_directory = os.path.abspath(os.path.join(current_directory, 'personal_finance'))
    #     os.chdir(move_directory)

    # workbook = openpyxl.load_workbook('$$.xlsx')
    # outputs_sheet = workbook['Outputs']

    # # Clear P3:V10000
    # for row in outputs_sheet.iter_rows(min_row=3, max_row=10000, min_col=16, max_col=22):
    #     for cell in row:
    #         cell.value = None

    # # Insert upload_df
    # start_cell = outputs_sheet.cell(row=3, column=16)
    # for row_index, row_data in enumerate(upload_df.values, start=start_cell.row):
    #     for col_index, cell_value in enumerate(row_data, start=start_cell.column):
    #         outputs_sheet.cell(row=row_index, column=col_index, value=cell_value)

    # workbook.save('$$.xlsx')