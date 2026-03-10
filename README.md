# 🧠 Cloud-Native Book Recommendation System

An end-to-end, cloud-native recommendation platform built with **FastAPI**, **React**, and **Pandas**, deployed entirely on **Amazon Elastic Kubernetes Service (EKS)**. 

What began as a lightweight Content-Based and Collaborative Filtering API has evolved into a robust, distributed microservices architecture complete with a modern frontend, a managed database, and a full observability stack.

---

## 🚀 Key Features

* **Hybrid Recommendation Engine:** Leverages Pandas and scikit-learn to serve both Content-Based (CB) and Collaborative Filtering (CF) algorithms. Similarity is calculated using cosine similarity vectors: $\cos(\theta) = \frac{\mathbf{A} \cdot \mathbf{B}}{\|\mathbf{A}\| \|\mathbf{B}\|}$.
* **Modern Interactive UI:** A responsive **React** frontend that consumes the recommendation endpoints and displays tailored book suggestions to the user.
* **Distributed Cloud Architecture:** Containerized using **Docker** and orchestrated via **Kubernetes (AWS EKS)** for high availability and scalable microservices.
* **Automated Traffic Routing:** Exposed to the internet via an **AWS Network Load Balancer (NLB)** configured through the AWS Load Balancer Controller.
* **Relational Data Storage:** Utilizes a **PostgreSQL** database managed within the Kubernetes cluster, mapped via **SQLModel** and SQLAlchemy.
* **Enterprise Observability:** Fully monitored via the **Kube-Prometheus-Stack**, featuring real-time cluster metrics, custom FastAPI endpoints scraping, and dynamic **Grafana** dashboards.

---

## 🧩 The Tech Stack

| Domain | Technologies |
| :--- | :--- |
| **Frontend** | React, HTML/CSS, JavaScript |
| **Backend API** | FastAPI, Python 3.11, Uvicorn, SQLModel |
| **Data & ML** | Pandas, scikit-learn (KNN, Cosine Similarity) |
| **Database** | PostgreSQL |
| **Containerization** | Docker, AWS Elastic Container Registry (ECR) |
| **Orchestration** | Kubernetes, Helm, Kustomize |
| **Cloud Provider** | Amazon Web Services (EKS, EC2, NLB, IAM) |
| **Observability** | Prometheus, Grafana, Alertmanager, ELK, Jaeger|

---

## 🏗️ Infrastructure & Deployment

This project utilizes a modern GitOps/Infrastructure-as-Code approach for deployment. The Kubernetes manifests (`k8s/`) are logically divided:

1.  **`k8s/app/`**: Contains the Deployments and Services for the React Frontend, FastAPI Backend, and PostgreSQL database. Environment variables and database connections are dynamically injected into the pods.
2.  **`k8s/monitoring/`**: Contains the Helm chart values and ServiceMonitors to automatically track the health, CPU/Memory usage, and request latency of the API pods.

### Traffic Flow
Client $\rightarrow$ AWS Network Load Balancer $\rightarrow$ EKS Worker Nodes $\rightarrow$ React Pods $\rightarrow$ FastAPI Pods $\rightarrow$ PostgreSQL Pod
