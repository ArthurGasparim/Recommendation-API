# 🧠 Recommendation API (FastAPI + Pandas)

A simple yet powerful **Recommendation System API** built with **FastAPI** and **Pandas**, implementing both **Content-Based (CB)** and **Collaborative Filtering (CF)** approaches.  

This API allows you to serve personalized item recommendations (e.g., movies, books, or products) through lightweight REST endpoints.

---

## 🚀 Features

- 🔹 **Content-Based Filtering (CB):** Recommends items similar to those a user liked, using item features.
- 🔹 **Collaborative Filtering (CF):** Suggests items based on similarities between users.
- 🔹 **Hybrid Option (Optional):** Combine both CB and CF results.
- 🔹 **FastAPI** for high-performance, asynchronous REST API.
- 🔹 **Pandas** for efficient data manipulation.
- 🔹 **Easily Extendable** — plug in your own dataset or similarity metrics.

---

## 🧩 Tech Stack

| Component | Description |
|------------|--------------|
| **FastAPI** | Web framework for building APIs |
| **Pandas** | Data manipulation and preprocessing |
| **scikit-learn** | Similarity computation (cosine, etc.) |
| **Uvicorn** | ASGI server for running the FastAPI app |

---

## 📂 Project Structure

recommendation-api/
│
├── app/
│ ├── main.py # FastAPI entry point
│ ├── models.py # Data models (Pydantic schemas)
│ ├── recommender.py # Core recommendation logic
│ ├── data_loader.py # Loads and preprocesses dataset
│ ├── utils.py # Helper functions (similarity, normalization, etc.)
│ └── init.py
│
├── data/
│ └── items.csv # Sample dataset (item_id, title, features, ratings, etc.)
│
├── tests/
│ └── test_recommendations.py
│
├── requirements.txt
└── README.md