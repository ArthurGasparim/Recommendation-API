import pandas as pd

def read_products_csv():
    booksDirty_df = pd.read_csv("data/books.csv")
    ratings_df = pd.read_csv("data/ratings.csv")
    tags_df = pd.read_csv("data/tags.csv")
    to_read_df = pd.read_csv("data/to_read.csv")
    books_tags_df = pd.read_csv("data/book_tags.csv")
    books_tags_df = create_useful_book_dataframe(booksDirty_df,tags_df,books_tags_df)
    print(books_tags_df)

def create_useful_book_dataframe(booksDirty_df : pd.DataFrame, tags_df : pd.DataFrame, books_tags_df : pd.DataFrame):
    books_df = pd.DataFrame()
    books_df["id"] = booksDirty_df["book_id"]
    books_df["title"] = booksDirty_df["original_title"]
    books_df["authors"] = booksDirty_df["authors"]
    books_df["average_rating"] = booksDirty_df["average_rating"]
    books_merge_tags = pd.merge(books_df,books_tags_df,left_on='id', right_on='goodreads_book_id', how='inner')
    books_merge_tags_name = pd.merge(books_merge_tags,tags_df,on = 'tag_id',how='inner')
    tags_final = books_merge_tags_name.groupby('id')['tag_name'].agg(list)
    books_df = pd.merge(books_df,tags_final,on='id',how='inner')
    return books_df

read_products_csv()
