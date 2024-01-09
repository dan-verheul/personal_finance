#import setup
from folder_constants import *

#pick the needed df's from folder_constants.py
method = 'credit_card'
original_output_data = original_output_dataframes[method]
upload_df = upload_df_dictionary[method]
original_upload_df = upload_df.copy()

#get simplified store in upload_df
upload_df['Store'] = upload_df['Description'].copy()
upload_df.loc[upload_df['Store'].str.lower().str.contains('amazon|amzn mkt', na=False), 'Store'] = 'Amazon' #anything that has lower(string)='amazon' just change it to 'amazon'
upload_df['Store'] = upload_df['Store'].str.replace('.com', '', case=False) #remove any .com's

frys_pattern = r'frys|fry\'s' #change strings with "Fry's" or "Frys" to simply "Frys"
upload_df.loc[upload_df['Store'].str.lower().str.contains('frys|fry\'s', na=False), 'Store'] = 'Frys'

#check for phone numbers
phone_number_pattern = r'\b\d{10}\b|\b\d{3}-\d{3}-\d{4}\b|\(\d{3}\)\d{3}-\d{4}|\(\d{3}\)\s?\d{3}-\d{4}'
upload_df['Store'] = upload_df['Store'].str.replace(phone_number_pattern, '', regex=True)


#using lookup_df from Google Sheets
test_df = original_upload_df.copy()

#create lookup_df
worksheet = spreadsheet.worksheet('Lookup')
data = worksheet.get_all_values()
columns_a_to_c = [row[:4] for row in data]
lookup_df = pd.DataFrame(columns_a_to_c, columns=['Store', 'Category', 'Sub Category','Description'])
lookup_df = lookup_df.drop(0)
lookup_df = lookup_df.sort_values(by=['Category','Store'])
lookup_df = lookup_df.reset_index(drop=True)
lookup_df = lookup_df.drop(0)