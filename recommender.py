import pandas as pd

def read_products_csv():
    booksDirty_df = pd.read_csv("data/books.csv")
    ratings_df = pd.read_csv("data/ratings.csv")
    tags_df = pd.read_csv("data/tags.csv")
    to_read_df = pd.read_csv("data/to_read.csv")
    books_tags_df = pd.read_csv("data/book_tags.csv")
    books_df = create_useful_book_dataframe(booksDirty_df,tags_df,books_tags_df)
    book = books_df.loc[books_df["title"] == "The Hunger Games"].iloc[0]
    df = get_recommendation_item_based(book=book,books_df=books_df)
    print(df)

def create_useful_book_dataframe(booksDirty_df : pd.DataFrame, tags_df : pd.DataFrame, books_tags_df : pd.DataFrame):
    #Create a books_DF with only useaful columns(Using the tag id)
    books_df = pd.DataFrame()
    books_df["id"] = booksDirty_df["book_id"]
    books_df["title"] = booksDirty_df["original_title"]
    books_df["authors"] = booksDirty_df["authors"]
    books_df["average_rating"] = booksDirty_df["average_rating"]
    books_merge_tags = pd.merge(books_df,books_tags_df,left_on='id', right_on='goodreads_book_id', how='inner')
    tags_final = books_merge_tags.groupby('id')['tag_id'].agg(list)
    books_df = pd.merge(books_df,tags_final,on='id',how='inner')
    return books_df

def get_recommendation_item_based(book: pd.Series, books_df: pd.DataFrame):
  column = []
  tags1 = book['tag_id']
  length_book_1 = len(tags1)
  set1 = set(tags1)
  for index, book2 in books_df.iterrows():
    line = []
    line.append(book2["title"])
    line.append(book2["authors"])
    #Allocating the String array of the tags names
    tags2 = book2['tag_id']
    length_book_2 = len(tags2)
    #Creating a Set to be able to merge the two of the
    set2 = set(tags2)
    #merging the Sets
    final_df = list(set1 & set2)
    equal_tags = len(final_df)
    distance = abs(length_book_2-length_book_1)
    bigger = (length_book_1 + length_book_2 + abs(length_book_1 - length_book_2)) / 2
    #Calculating similarity between tags as 60% of the final score
    initial_tags_simiilar_value = (equal_tags*0.7)/length_book_1
    #Nomalizing factor to minimize comparissons with vastly diferent sizes having a lot of percentages
    normalizing_factor = (1 - (distance/bigger))
    final_similarity_score = initial_tags_simiilar_value*normalizing_factor
    book_avg_rating_score = (book2['average_rating']/5)*0.3
    line.append(final_similarity_score)
    line.append(book_avg_rating_score)
    line.append(book_avg_rating_score+final_similarity_score)
    column.append(line)
  comparation_df = pd.DataFrame(column,columns=["name","authors","tag_similarity_rating","avg_score_rating","rating"])
  return comparation_df.sort_values(ascending=False ,by="rating")



read_products_csv()
