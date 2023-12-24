#import setup
from folder_constants import *

#pick the needed df's from folder_constants.py
method = 'electric'
original_output_data = original_output_dataframes['bills']
upload_df = upload_df_dictionary[method]
electric_upload_df = upload_df.copy()
electric_upload_df['Date'] = pd.to_datetime(electric_upload_df['Date'])

method = 'water'
# original_output_data = upload_df_dictionary[bills_method]
upload_df = upload_df_dictionary[method]
water_upload_df = upload_df.copy()
water_upload_df['Date'] = pd.to_datetime(water_upload_df['Date'])

#merge tables together
bills_df = pd.merge(electric_upload_df,
                     water_upload_df,
                     left_on=pd.to_datetime(electric_upload_df['Date']).dt.to_period("M"),
                     right_on=pd.to_datetime(water_upload_df['Date']).dt.to_period("M"),
                     how='left',
                     suffixes=('_electric', '_water'))
bills_df = bills_df.sort_values(by='key_0')
bills_df = bills_df.drop(columns=bills_df.filter(like='Date_').columns)
bills_df = bills_df.rename(columns={'key_0':'Date'})
bills_df['Electric'] = bills_df['Electric'].str.replace('[\$,]', '', regex=True).astype(float).fillna('')
bills_df['Water'] = bills_df['Water'].str.replace('[\$,]', '', regex=True).astype(float).fillna('')


# clean original_output_df, compare to new df, remove already existing rows from new upload, upload the rest
cols = ['Electric','Water']
original_output_data_check = clean_df(original_output_data,columns_to_sum=cols)
bills_df_check = clean_df(bills_df,columns_to_sum=cols)

# format date columns, then remove rows that are already in output sheet
original_output_data_check['Date'] = pd.to_datetime(original_output_data_check['Date'])
bills_df_check['Date'] = pd.to_datetime(bills_df_check['Date'].astype('datetime64[M]'))
upload_df = remove_data_we_already_have(original_output_data_check,bills_df_check)


#output df
if len(upload_df) > 0:
    #remove rows from original output dataframe that have matching month
    original_output_data = original_output_data[~original_output_data['Date'].isin(upload_df['Date'])]

    #select months from bills_df that match upload_df
    upload_df['Date'] = upload_df['Date'].dt.strftime('%Y-%m').astype(str)
    bills_df['Date'] = bills_df['Date'].astype(str)
    upload_df = pd.merge(bills_df, upload_df[['Date']], on='Date', how='inner')
    
    #combine original output dataframe with upload df
    original_output_data['Date'] = original_output_data['Date'].dt.strftime('%Y-%m')
    upload_df = pd.concat([original_output_data, upload_df], ignore_index=True)

    #sort by date
    upload_df = upload_df.sort_values(by='Date')

    #format
    upload_df['Date'] = upload_df['Date'].astype(str)
    upload_df = upload_df.fillna('')
        
    #upload
    method = 'bills'
    worksheet = spreadsheet.worksheet('Outputs')
    worksheet.range(sheets_info_dict[method][1]).clear()
    data = upload_df.values.tolist()
    worksheet.update(sheets_info_dict[method][0], data, value_input_option='USER_ENTERED')