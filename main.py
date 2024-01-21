# import subprocess
from folder_constants import *
from datetime import datetime

# check to see if you need to add any bills to Google sheets
electric_bill_date = important_dates_df.loc[important_dates_df['Category'] == 'Electric', 'Date'].values[0]
water_bill_date = important_dates_df.loc[important_dates_df['Category'] == 'Water', 'Date'].values[0]

current_date_number = datetime.now().day
current_month_number = datetime.now().month
if current_date_number > electric_bill_date:
    electric_df['Date'] = pd.to_datetime(electric_df['Date'], format='%m/%d/%y')
    max_electric_date_month_value = electric_df['Date'].max().month
    if current_month_number != max_electric_date_month_value:
        import ctypes  
        ctypes.windll.user32.MessageBoxW(0, "Add this month's electric bill to Google Sheets", "Add Electric Bill", 1)
if current_date_number > water_bill_date:
    water_df['Date'] = pd.to_datetime(water_df['Date'], format='%m/%d/%y')
    max_water_date_month_value = water_df['Date'].max().month
    if current_month_number != max_water_date_month_value:
        import ctypes  
        ctypes.windll.user32.MessageBoxW(0, "Add this month's water bill to Google Sheets", "Add Water Bill", 1)

#run all the files
methods = ['credit_card','savings', 'checking', 'fidelity']

for method in methods:
    if method != 'bills':
        df = upload_df_dictionary[method]
        if len(df) > 0:
            script_path = primary_file_path + method + ".py"
            with open(script_path, "r") as script_file:
                script_code = script_file.read()
                exec(script_code)

#bills run
method = 'bills'
script_path = primary_file_path + method + ".py"
with open(script_path, "r") as script_file:
    script_code = script_file.read()
    exec(script_code)
