#google sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

#popup
import pyinputplus as pyip

#general
import pandas as pd
import numpy as np
import pytz
import re
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

#set working directory and pull in hidden variables
import os
current_directory = os.getcwd()
while os.path.basename(current_directory) != 'GitHub':
    parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))
    os.chdir(parent_directory)
    current_directory = parent_directory
from personal_finance_private.config import *


#read google sheets
creds_file = google_sheets_json_file
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
client = gspread.authorize(creds)

spreadsheet = client.open(workbook_name)

#tiers df
worksheet = spreadsheet.worksheet('Config')
range_to_pull = 'A1:C'
data = worksheet.get(range_to_pull)
tiers_df = pd.DataFrame(data[1:], columns=data[0])
tiers_df['Level 3'] = tiers_df['Level 3'].fillna('')

#mapping df
worksheet = spreadsheet.worksheet('Config')
range_to_pull = 'E1:F'
data = worksheet.get(range_to_pull)
mapping_df = pd.DataFrame(data[1:], columns=data[0])

#bucket percentages df
worksheet = spreadsheet.worksheet('Config')
range_to_pull = 'H1:K'
data = worksheet.get(range_to_pull)
bucket_df = pd.DataFrame(data[1:], columns=data[0])
