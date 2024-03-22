#import setup
from folder_constants import *

#Pull from google sheets
worksheet = spreadsheet.worksheet('Setup')
data = worksheet.get('B:C')
goals_df = pd.DataFrame(data, columns=['Category', 'Bucket', 'Monthly'])

#setup goals_df
goals_df['Monthly'] = pd.to_numeric(goals_df['Monthly'].replace('[\$,]', '', regex=True), errors='coerce')
goals_df = goals_df.dropna(subset=['Monthly'])

goals_df = goals_df[goals_df['Category'] != "Yearly"].reset_index(drop=True) #remove this so all rows are monthly
goals_df.loc[goals_df['Category'] == 'Monthly', 'Category'] = 'Paycheck' #change this to Paycheck

goals_df['Yearly'] = pd.to_numeric(goals_df['Monthly'], errors='coerce') * 12 #shows total for the year


#create "General" column that buckets all the categories into the 4 main options: Investing, Savings, Needs, Wants
investing_list = ['Retirement','Extra Investing','Crypto']
savings_list = ['Cash Savings']
needs_list = ['Needs']
wants_list = ['Wants']

def categorize_general(row):
    if row['Category'] in investing_list:
        return 'Investing'
    elif row['Category'] in savings_list:
        return 'Savings'
    elif row['Category'] in needs_list:
        return 'Needs'
    elif row['Category'] in wants_list:
        return 'Wants'
    elif row['Category'] == 'Paycheck' and row['Bucket'] == 'Total':
        return 'Gross Pay'
    else:
        return ''
    
goals_df['General'] = goals_df.apply(categorize_general, axis=1)
# goals_df['General'] = goals_df['Category'].apply(categorize_general)
column_order = ['General'] + [col for col in goals_df.columns if col != 'General']
goals_df = goals_df[column_order]



#create overview df, this totals yearly amounts, grouped by general
overview_df = goals_df[goals_df['General'] != ''][['General', 'Yearly']].copy()
overview_df = overview_df.rename(columns={'General':'Category'})
overview_df = overview_df.groupby('Category')['Yearly'].sum().reset_index()

#calculate
gross_pay_index = overview_df[overview_df['Category'] == 'Gross Pay'].index[0]
overview_df['Percentage'] = overview_df['Yearly'] / overview_df.loc[gross_pay_index, 'Yearly'] * 100

# Drop the 'Gross Pay' row
overview_df = overview_df[overview_df['Category'] != 'Gross Pay']

