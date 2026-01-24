import pandas as pd
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def read_products_csv():
    booksDirty_df = pd.read_csv("data/books.csv")
    ratings_df = pd.read_csv("data/ratings.csv")
    tags_df = pd.read_csv("data/tags.csv")
    to_read_df = pd.read_csv("data/to_read.csv")
    books_tags_df = pd.read_csv("data/book_tags.csv")
    books_df = create_useful_book_dataframe(booksDirty_df,tags_df,books_tags_df)
    user_id = 98
    ratings_df = ratings_df.loc[ratings_df["book_id"].isin(books_df['id'])]
    #df = get_recommendation_user_based(user_id=1,ratings_df=ratings_df,books_df=books_df)
    df = get_recommendation_item_based(user_id=user_id,ratings_df=ratings_df,books_df=books_df,to_read_df=to_read_df)
    print(df)

def create_useful_book_dataframe(booksDirty_df : pd.DataFrame, tags_df : pd.DataFrame, books_tags_df : pd.DataFrame):
   #Create a books_DF with only useaful columns(Using the tag id)
    books_df = pd.DataFrame()
    books_df["id"] = booksDirty_df["id"]
    books_df["good_id"] = booksDirty_df["book_id"]
    books_df["title"] = booksDirty_df["original_title"]
    books_df["authors"] = booksDirty_df["authors"]
    books_df["average_rating"] = booksDirty_df["average_rating"]
    books_merge_tags =  pd.merge(books_df,books_tags_df,left_on='good_id', right_on='goodreads_book_id', how='inner')
    tags_final = books_merge_tags.groupby('id')['tag_id'].agg(list)
    books_df = pd.merge(books_df,tags_final,on='id',how='inner')
    books_df = books_df.drop(columns=["good_id"])
    return books_df

def get_recommendation_item_based(user_id:int,books_df: pd.DataFrame,ratings_df:pd.DataFrame,to_read_df:pd.DataFrame):
  column = []
  books = list(books_df.loc[ratings_df.sort_values(by="rating",ascending=False)["user_id"] == user_id]["id"][:5])
  user_to_read = to_read_df.loc[to_read_df["user_id"] == user_id]
  user_already_read = ratings_df.loc[ratings_df["user_id"] == user_id]
  user_to_read = user_to_read["book_id"]
  user_already_read = user_already_read["book_id"]
  for index, book2 in books_df.iterrows():
    line = []
    line.append(book2["id"])
    #Allocating the String array of the tags names
    tags2 = book2['tag_id']
    length_book_2 = len(tags2)
    #Creating a Set to be able to merge the two of the
    set2 = set(tags2)
    #merging the Sets
    final_score = 0
    to_read_score = 0
    #Atributting part of the score to the user wanting to read the book and the user not having read the book
    if(book2["id"] in (user_to_read)):
        to_read_score = 1
    already_read_score = 0
    if(not(book2["id"] in (user_already_read))):
        already_read_score = 1
    final_score = to_read_score + already_read_score
    #Putting a value to the avg score of the book in the final rating
    book_avg_rating_score = (book2['average_rating']/5)*0.3
    for book in books:
      tags1 = book['tag_id']
      set1 = set(tags1)
      length_book_1 = len(tags1)
      final_df = list(set1 & set2)
      equal_tags = len(final_df)
      distance = abs(length_book_2-length_book_1)
      bigger = (length_book_1 + length_book_2 + abs(length_book_1 - length_book_2)) / 2
      #Calculating similarity between tags as 60% of the final score
      initial_tags_simiilar_value = (equal_tags*0.7)/length_book_1
      #Nomalizing factor to minimize comparissons with vastly diferent sizes having a lot of percentages
      normalizing_factor = (1 - (distance/bigger))
      final_similarity_score = initial_tags_simiilar_value*normalizing_factor
      final_score += (book_avg_rating_score+final_similarity_score)
    line.append(final_score)
    column.append(line)
  comparation_df = pd.DataFrame(column,columns=["id","rating"])
  return list(comparation_df.sort_values(ascending=False ,by="rating")[:5]["id"])

def get_recommendation_user_based(user_id: int, ratings_df: pd.DataFrame, books_df:pd.DataFrame):
    #Filtering the dataset
    #Generating the sparce matrix
    rating_matrix = ratings_df.pivot_table(index='user_id', columns='book_id', values='rating').fillna(0)
    #Applying th cosine similarity method
    item_similarity = cosine_similarity(rating_matrix.T)
    #Finding user scores
    item_scores = rating_matrix.iloc[user_id].dot(item_similarity)
    n = 5
    #getting the top 5 books by user scores
    recommended_items = np.argsort(item_scores)[::-1][:n]
    return recommended_items

read_products_csv()
