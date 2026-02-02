import pandas as pd


df = pd.DataFrame(
    {
        "chat_id":[],
        "chat_type":[],
        "status":[],
    }
)

df.to_csv("data/aa.csv")