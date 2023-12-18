#import setup
from folder_constants import *

#pick the needed df's from folder_constants.py
method = 'electric'
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
bills_df['Electric'] = bills_df['Electric'].str.replace('$', '').astype(float).fillna('')
bills_df['Water'] = bills_df['Water'].str.replace('$', '').astype(float).fillna('')

upload_df = bills_df.copy()
#output df
if len(upload_df) > 0:
    #format
    upload_df['Date'] = upload_df['Date'].astype(str)
    
    method = 'bills'
    worksheet = spreadsheet.worksheet('Outputs')
    worksheet.range(sheets_info_dict[method][1]).clear()
    data = upload_df.values.tolist()
    worksheet.update(sheets_info_dict[method][0], data, value_input_option='USER_ENTERED')