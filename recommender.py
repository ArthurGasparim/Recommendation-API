import pandas as pd

def read_products_csv():
    return pd.read_csv("books.csv")

#Cleaning products_df so it doesnst have the url
products_df = read_products_csv()
products_df = products_df.drop(columns={"url"})
