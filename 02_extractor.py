from groq import Groq
import pandas as pd
import json
import time
from config import GROQ_API_KEY
client = Groq(api_key=GROQ_API_KEY)

def extract(title,body):
    prompt=f"""
    Your task is to extract 'Long-Term Memory' from a Github Issue
    Issue Title:{title}
    Issue Body:{body}
    Extract the following things in a Strict JSON format:
    1.Entities: People, SOftware Tools, Originizations or versions mentioned
    2.Claims: Facts mentioned in the text.
    3.Evidence: For every claim,I want you to provide the exact quote from text as proof.
    
    JSON structure is as follows:
    {{
        "entities":[{{"name": "...", "type": "..."}}],
        "claims":[
        {{
        "claim": "...",
        "Evidence_quote": "...",
        "confidence_score: 0.0 to 1.0
        }}
        ]

    }}
    """
    for attempt in range(3):
        try:
            chat_completion=client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                response_format={"type": "json_object"}
            )
            return json.loads(chat_completion.choices[0].message.content)
        except Exception as e:
                print("Rate LIMIT HIT")
                time.sleep(30)

df=pd.read_csv("Data/miniversion_issues1.csv")
sample=df.head(200)
results=[]
for index , row in sample.iterrows():
    print(f"Processing issue:{index+1}")
    data=extract(row['issue_title'],row['body'])
    if data:
        if isinstance(data, list):
            print("data Type error index:",index+1)
            data = {"items": data}
        data['source_url']=row['issue_url']
        results.append(data)
    time.sleep(1)

with open("Data/extracted_memory.json","w") as f:
    json.dump(results, f,indent=4)