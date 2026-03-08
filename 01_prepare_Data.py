import pandas as pd
from langdetect import detect, DetectorFactory
import re

DetectorFactory.seed=0
def clean_text(text):
    text= re.sub(r'<[^>]+>','',text)
    text=" ".join(text.split())
    return text
def is_eng(title,body):
    title=clean_text(title)
    body=clean_text(body)
    text=title+" "+body
    try:
        if len(text)<50:
            return False
        non_ascii=len(re.sub(r'[a-zA-Z0-9\s\.,!\?\(\)\'\"-]',r'',str(text)))
        if non_ascii/len(str(text)) > 0.1:
            return False
        return detect(body)=='en'
    except:
        return False
    
# path to input file
input_file="Data/github_issues.csv"
#output file directory
output_file="Data/miniversion_issues1.csv"
df=pd.read_csv(input_file,nrows=5)
df.to_csv("temp.txt")
print("done")
df=pd.read_csv(input_file,nrows=10000)
df=df.dropna(subset=['body','issue_title'])
bot_keywords=["Czekolada", "HW/issues", "minhas-aulas"]
for key in bot_keywords:
    df =df[~df['issue_url'].str.contains(key,case=False)]

mask=df.apply(lambda row: is_eng(row['issue_title'],row['body']),axis=1)
df=df[mask].copy()
df=df[~df['body'].str.contains("&#",na=False)]
df=df[~df['issue_title'].str.contains("test|testing|issue 1",case=False,na=False)]
final_df=df.head(200)
final_df['body']=final_df['body'].apply(clean_text)
final_df['issue_title']=final_df['issue_title'].apply(clean_text)
final_df[['issue_url',"issue_title",'body','created_at']].to_csv(output_file,index=False)