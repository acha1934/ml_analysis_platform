# ML Analysis Platform

A full-stack web application for uploading CSV datasets and applying machine learning techniques to analyse data, discover patterns, and generate predictions — all through an intuitive browser-based interface.

---

## Features

### Authentication & Authorisation
- JWT-based authentication with individual user accounts
- Password hashing using bcrypt
- Three roles: **Admin**, **Developer**, **Guest User**
- Admins can manage all users — change roles, delete accounts
- Admins control which projects are visible to others via starring

### Project Management
- Create, rename, star, and delete projects
- Projects persist with their full state (dataset, problem statement, results)
- Admins see all projects; developers and guests see only starred (shared) projects

### Machine Learning — 8 Techniques

**Supervised Learning**
| Technique | Algorithm | What it predicts |
|---|---|---|
| Classification | Random Forest | Categorical outcome (Yes/No, labels) |
| Regression | Ridge Regression | Continuous numeric value |
| Decision Tree | CART | Categorical with interpretable rules |
| KNN | K-Nearest Neighbours | Categorical based on similarity |

**Unsupervised Learning**
| Technique | Algorithm | What it finds |
|---|---|---|
| K-Means | K-Means Clustering | Natural groups/segments |
| DBSCAN | Density-Based Clustering | Irregular clusters + outliers |
| PCA | Principal Component Analysis | Key features + dimension reduction |
| Anomaly Detection | Isolation Forest | Unusual/suspicious records |

### Smart Suggestions
- Uses **spaCy NLP** (`en_core_web_md`) to analyse the problem statement
- Computes cosine similarity between the problem statement and reference phrases for each technique
- Combined with CSV data profiling (column types, target column characteristics)
- Returns ranked technique suggestions with High/Medium/Low confidence

### Custom Prediction
- After analysis, enter values for any new data point
- Categorical columns shown as dropdowns with original dataset values
- Numeric columns show min/max/avg as hints
- Returns predicted class/value + probability breakdown or feature contributions

### Persistent Storage
- All analysis results, model configs, and datasets saved to MongoDB
- Full state restored when a project is reopened
- CSV files stored in MongoDB GridFS

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite |
| Routing | React Router v6 |
| Backend | FastAPI (Python) |
| Auth | python-jose (JWT) + bcrypt |
| ML | scikit-learn, pandas, NumPy |
| NLP | spaCy (`en_core_web_md`) |
| Database | MongoDB Atlas |
| File Storage | MongoDB GridFS |
| Async DB | Motor |
| Server | Uvicorn |

---

## Project Structure

```
├── backend/
│   ├── main.py          # FastAPI routes and API endpoints
│   ├── auth.py          # JWT creation/verification, bcrypt hashing
│   ├── ml_engine.py     # All ML algorithms, NLP suggestions, predictions
│   ├── requirements.txt
│   └── .env.example     # Environment variable template
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── login.jsx           # Login + Registration
│   │   │   ├── Dashboard.jsx       # Project management dashboard
│   │   │   ├── ProjectPage.jsx     # ML analysis interface
│   │   │   └── UserManagement.jsx  # Admin user management
│   │   ├── styles/
│   │   └── App.jsx                 # Routes + auth guard
│   └── package.json
│
├── sample_data/
│   └── customers.csv    # Sample dataset for testing
└── README.md
```

---

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- MongoDB Atlas account (free tier works)

### 1 — Clone the repo

```bash
git clone https://github.com/YourUsername/ml-analysis-platform.git
cd ml-analysis-platform
```

### 2 — Backend setup

```bash
cd backend
pip install -r requirements.txt
```

Download the spaCy language model:
```bash
python -m spacy download en_core_web_md
```

Create your `.env` file:
```bash
cp .env.example .env
```

Edit `.env` and fill in your values:
```env
MONGODB_URL=mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=notebook_db
JWT_SECRET=your_long_random_secret_key
```

Start the backend:
```bash
python -m uvicorn main:app --reload --port 8000
```

### 3 — Frontend setup

```bash
cd frontend
npm install
npm run dev
```

### 4 — Open the app

Go to **http://localhost:5173**

- Click **Create Account** and register — the first registered user automatically becomes **Admin**
- Register more users — they default to **Guest User**
- Log in as admin → click the user icon → **Manage Users** → assign roles

---

## Role Permissions

| Feature | Admin | Developer | Guest |
|---|:---:|:---:|:---:|
| View starred projects | ✅ | ✅ | ✅ |
| View all projects | ✅ | ❌ | ❌ |
| Create / delete projects | ✅ | ✅ | ❌ |
| Upload data files | ✅ | ✅ | ❌ |
| Run ML analysis | ✅ | ✅ | ✅ |
| Manage users | ✅ | ❌ | ❌ |
| Change / remove other admins | ✅ | ❌ | ❌ |

> Admins share projects with others by **starring** them. Starred projects appear in all users' dashboards.

---

## Sample Dataset

A sample CSV (`sample_data/customers.csv`) is included with 60 rows and 11 columns including numeric, categorical, and name columns. It works with all 8 ML techniques.

**Recommended problem statement to test all techniques:**
> *"Analyse customer behaviour to predict churn, identify high-value segments, detect unusual spending patterns, and understand which features drive customer satisfaction score."*

---

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| POST | `/register` | Register new user |
| POST | `/login` | Login, receive JWT |
| GET | `/users` | List all users (admin) |
| PUT | `/users/{id}/role` | Change user role (admin) |
| GET | `/projects` | List projects (filtered by role) |
| POST | `/projects` | Create project |
| POST | `/upload/admin/{id}` | Upload CSV file |
| POST | `/analyse/admin/{id}` | Run ML analysis |
| POST | `/suggest/admin/{id}` | Get NLP-based suggestions |
| POST | `/predict-custom/admin/{id}` | Predict on custom input |
| POST | `/predict-cluster/admin/{id}` | Assign input to cluster |
| POST | `/pca-reduce/admin/{id}` | Download PCA-reduced CSV |

Full API docs available at **http://localhost:8000/docs** when the backend is running.

---

## License

This project was developed as part of an internship. For educational and demonstration purposes.
