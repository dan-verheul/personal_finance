#import setup
from folder_constants import *

import subprocess

worksheet = spreadsheet.worksheet('Uploads')

#credit card run
range_to_pull = 'A2:E'
data = worksheet.get(range_to_pull)
if len(data) > 0:
    subprocess.run(["python", "credit_card.py"])

#savings run
range_to_pull = 'G2:K'
data = worksheet.get(range_to_pull)
if len(data) > 0:
    subprocess.run(["python", "savings.py"])

#checking run
range_to_pull = 'M2:Q'
data = worksheet.get(range_to_pull)
if len(data) > 0:
    subprocess.run(["python", "checking.py"])