import subprocess
from folder_constants import *

methods = ['credit_card', 'savings', 'checking', 'fidelity']

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
