# Project Report
## ML Analysis Platform — Full Stack Web Application

---

## 1. Project Overview

This project is a full-stack web application that enables users to upload CSV datasets and apply machine learning techniques to analyse data, discover patterns, and generate predictions — all through an intuitive browser-based interface. The platform is structured around a project management system where each project stores its associated dataset, problem statement, model configurations, and analysis results persistently in a database.

The application features a complete user authentication and authorisation system with three distinct roles. Users register and log in with individual credentials, and admins can manage user access through a dedicated management interface.

---

## 2. Objectives

- Provide a no-code interface for running machine learning analysis on tabular CSV data
- Support both supervised and unsupervised learning paradigms with configurable hyperparameters
- Persist all user data, uploaded files, and analysis results across sessions
- Implement JWT-based authentication with individual user accounts stored in MongoDB
- Enforce role-based authorisation (admin, developer, guest_user) across the application
- Allow admins to manage user roles and accounts from a dedicated interface
- Enable custom input prediction so users can test trained models on new data points

---

## 3. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React (Vite) | UI framework |
| Routing | React Router v6 | Page navigation and auth guards |
| Icons | React Icons (FontAwesome) | UI icons |
| Backend | FastAPI (Python) | REST API server |
| Authentication | python-jose + bcrypt | JWT tokens + password hashing |
| ML Engine | scikit-learn, pandas, NumPy | Machine learning |
| Database | MongoDB Atlas | Cloud NoSQL database |
| File Storage | MongoDB GridFS | Binary file storage for CSVs |
| Async DB Driver | Motor | Async MongoDB driver for FastAPI |
| Environment | python-dotenv | Configuration management |
| Server | Uvicorn | ASGI server |

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND (React)                  │
│  Login/Register → Dashboard → Project Page          │
│  Auth Guard (JWT in localStorage)                   │
│  (Vite dev server on localhost:5173)                 │
└───────────────────────┬─────────────────────────────┘
                        │ HTTP REST (JSON / FormData)
                        │ Authorization: Bearer <token>
                        ↓
┌─────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI)                   │
│  main.py    — API routes and request handling        │
│  auth.py    — JWT creation/decoding, bcrypt hashing  │
│  ml_engine.py — ML logic and preprocessing           │
│  (Uvicorn on localhost:8000)                         │
└───────────────────────┬─────────────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         ↓              ↓              ↓
┌──────────────┐ ┌────────────┐ ┌──────────────────┐
│  projects    │ │  users     │ │  MongoDB GridFS  │
│  collection  │ │  collection│ │  (file storage)  │
└──────────────┘ └────────────┘ └──────────────────┘
```

---

## 5. Authentication & Authorisation

### 5.1 User Registration and Login

Users register with a username, email, and password. Passwords are hashed using `bcrypt` before storage — the plain-text password is never saved.

On successful login, the backend issues a **JWT (JSON Web Token)** containing the user ID, username, role, and expiry time. The token is signed with a secret key using the HS256 algorithm.

```
POST /register  →  creates user, returns JWT
POST /login     →  verifies credentials, returns JWT
GET  /me        →  returns current user info from token
```

The **first registered user** is automatically assigned the `admin` role.

### 5.2 Token Storage and Usage

The JWT token is stored in `localStorage` and attached to every API request as:
```
Authorization: Bearer <token>
```

The frontend includes an auth guard component that redirects unauthenticated users to the login page.

### 5.3 Role-Based Authorisation

Three roles are defined, each with different permissions:

| Permission | admin | developer | guest_user |
|---|:---:|:---:|:---:|
| View projects | ✅ | ✅ | ✅ |
| Create projects | ✅ | ✅ | ❌ |
| Delete projects | ✅ | ✅ | ❌ |
| Upload data files | ✅ | ✅ | ❌ |
| Save problem statement | ✅ | ✅ | ❌ |
| Run ML analysis | ✅ | ✅ | ✅ |
| Manage users | ✅ | ❌ | ❌ |
| Change user roles | ✅ | ❌ | ❌ |

Role checks are enforced both on the **frontend** (buttons are hidden/disabled) and **backend** (endpoints return 403 if the role is insufficient).

### 5.4 User Management (Admin)

Admins have access to a dedicated User Management page at `/users`:
- View all registered users with their username, email, join date, and current role
- Change any user's role using a role selector (cannot change own role)
- Delete any user (cannot delete own account)

---

## 6. Application Modules

### 6.1 Login and Registration

A single page handles both login and registration with a mode toggle. The form adapts dynamically — registration shows an additional email field. Inline validation, error messages with shake animation, and Enter-key submission are supported.

### 6.2 Dashboard

A unified dashboard for all users at `/dashboard`, with role-appropriate controls:

- Project cards in a responsive grid
- Create and rename projects (admin/developer only)
- Star/favourite projects (admin/developer only)
- Delete projects with confirmation dialog (admin/developer only)
- Search projects by name
- Role badge in the header showing current role
- "Manage Users" link in the user menu (admin only)
- Logout

### 6.3 Project Page

Each project has a dedicated analysis page at `/project/:id`. The page is divided into three panels — sidebar, main results, and suggestion panel. Full details in Section 7.

### 6.4 User Management Page (`/users`)

Admin-only page with a table of all users, inline role selectors, and delete buttons. Protected by both the frontend route guard and the backend endpoint check.

---

## 7. Machine Learning Engine

All ML logic is in `ml_engine.py`.

### 7.1 Preprocessing Pipeline

Every technique passes through a shared pipeline:
1. Drop columns with >80% missing values
2. Fill missing values — median for numeric, mode for categorical
3. Label-encode categorical columns with ≤50 unique values
4. Drop high-cardinality text columns (>50 unique values, e.g. names)

### 7.2 Target Detection

For supervised techniques:
1. User-specified target column (from Model Settings panel)
2. Keyword match from problem statement
3. Fallback: last column in dataset

### 7.3 Supervised Learning Techniques

#### Classification — Random Forest
- Ensemble of 100 decision trees with majority-vote prediction
- **Outputs**: Accuracy, cross-validation score, feature importance bar chart
- **Configurable**: Target column

#### Regression — Ridge Regression
- Linear model with L2 regularisation; StandardScaler applied
- **Outputs**: R², MAE, RMSE, feature coefficients, actual vs predicted table
- **Configurable**: Target column

#### Decision Tree
- If/else rule tree with configurable depth
- **Outputs**: Accuracy, tree depth, leaf nodes, feature importance
- **Configurable**: Target column, max tree depth (2–20 or auto)

#### KNN — K-Nearest Neighbours
- Distance-based classifier; k auto-selected by cross-validation or user-specified
- **Outputs**: Accuracy, chosen k and source
- **Configurable**: Target column, k value (3–20 or auto)

### 7.4 Unsupervised Learning Techniques

#### K-Means Clustering
- Partitions data into k groups; k auto-selected via elbow method or user-specified
- **Outputs**: Cluster sizes, silhouette score, per-cluster average feature values table, elbow chart
- **Configurable**: Feature selection (checkboxes), k value (2–8 or auto)

#### DBSCAN
- Density-based clustering with automatic outlier identification
- **Outputs**: Cluster count, noise count, per-cluster averages, full outlier table
- **Configurable**: Feature selection, ε slider (0.1–3.0), minPts (2–20 or auto)

#### PCA — Principal Component Analysis
- Reduces dimensionality; scree chart shows variance per component
- **Outputs**: Variance explained per component, top contributing features
- **Dimension Reducer**: Download compressed CSV with chosen number of components

#### Anomaly Detection — Isolation Forest
- Flags statistically unusual records; contamination auto-adjusted
- **Outputs**: Anomaly count, anomaly %, full table of anomalous records with scores

### 7.5 Technique Validation

Before running, the system checks each technique against the data and problem statement:
- Column type compatibility (e.g. regression blocked if no numeric target)
- Minimum feature requirements (e.g. PCA needs ≥3 numeric columns)
- Problem statement intent (e.g. clustering blocked if PS says "predict")
- Returns `{applicable: bool, reason: str}` for all 8 techniques

### 7.6 Smart Suggestion Engine

Scores each technique against problem statement keywords and data profile, returns ranked recommendations with High/Medium/Low confidence and expandable reasoning.

---

## 8. Custom Input Prediction

### 8.1 Supervised Prediction

After analysis, a prediction panel shows input fields for all feature columns:
- **Categorical columns**: Dropdown with all original dataset values
- **Numeric columns**: Number input with min/max/mean as placeholder hint
- Blank fields filled with column median (listed in notice)

Backend retrains the model and predicts for the custom row. Returns:
- Classification: predicted class + confidence % + probability bar chart
- Regression: predicted value + top feature contributions

### 8.2 Cluster Assignment

For K-Means and DBSCAN, a cluster prediction panel assigns the custom input to a cluster:
- K-Means: assigned cluster + distances to all cluster centres
- DBSCAN: assigned cluster or "Noise/Outlier" based on ε threshold

---

## 9. Data Persistence

### 9.1 Users Collection

```json
{
  "_id":       "ObjectId",
  "username":  "alice",
  "email":     "alice@example.com",
  "password":  "$2b$12$...",
  "role":      "developer",
  "createdAt": "ISO timestamp"
}
```

### 9.2 Project Document Schema

```json
{
  "_id":              "ObjectId",
  "name":             "Project Name",
  "date":             "Jun 15, 2025",
  "sourceCount":      0,
  "starred":          false,
  "createdAt":        "ISO timestamp",
  "problemStatement": "Predict customer churn...",
  "fileName":         "customers.csv",
  "fileId":           "GridFS ObjectId",
  "fileSize":         4096,
  "uploadedAt":       "ISO timestamp",
  "lastTechnique":    "classification",
  "lastResults":      { ... },
  "lastAnalysedAt":   "ISO timestamp"
}
```

### 9.3 GridFS File Storage

Uploaded CSV files are stored in MongoDB GridFS, split into 255KB chunks. All project analysis, configs, and results are restored when a project is reopened.

---

## 10. API Endpoints

### Authentication
| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/register` | Public | Register new user |
| POST | `/login` | Public | Login, receive JWT |
| GET | `/me` | Authenticated | Get current user info |

### User Management
| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/users` | Admin | List all users |
| PUT | `/users/{id}/role` | Admin | Change user role |
| DELETE | `/users/{id}` | Admin | Delete user |

### Projects
| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/projects` | Authenticated | List all projects |
| POST | `/projects` | Admin/Developer | Create project |
| GET | `/projects/{id}` | Authenticated | Get project |
| PUT | `/projects/{id}` | Admin/Developer | Update project |
| DELETE | `/projects/{id}` | Admin/Developer | Delete project + file |

### Analysis & Files
| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/upload/{role}/{id}` | Admin/Developer | Upload CSV to GridFS |
| GET | `/download/{role}/{file_id}` | Authenticated | Download file |
| GET | `/csv-profile/{role}/{id}` | Authenticated | Get column metadata |
| PUT | `/save-problem/{role}/{id}` | Admin/Developer | Save problem statement |
| POST | `/analyse/{role}/{id}` | Authenticated | Run ML analysis |
| POST | `/predict-custom/{role}/{id}` | Authenticated | Supervised prediction |
| POST | `/predict-cluster/{role}/{id}` | Authenticated | Cluster prediction |
| POST | `/suggest/{role}/{id}` | Authenticated | Technique suggestions |
| POST | `/validate-techniques/{role}/{id}` | Authenticated | Check applicability |
| POST | `/pca-reduce/{role}/{id}` | Authenticated | Download reduced CSV |

---

## 11. Project Structure

```
Intern_Project/
├── backend/
│   ├── main.py          # FastAPI routes
│   ├── auth.py          # JWT + bcrypt utilities
│   ├── ml_engine.py     # ML algorithms and prediction logic
│   ├── requirements.txt # Python dependencies
│   └── .env             # MongoDB URL, JWT secret
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── login.jsx           # Login + Registration
│   │   │   ├── Dashboard.jsx       # Unified project dashboard
│   │   │   ├── ProjectPage.jsx     # ML analysis page
│   │   │   └── UserManagement.jsx  # Admin user management
│   │   ├── styles/
│   │   │   ├── login.css
│   │   │   ├── dashboard.css
│   │   │   ├── ProjectPage.css
│   │   │   └── UserManagement.css
│   │   ├── App.jsx      # Routes + auth guard
│   │   └── main.jsx     # Entry point
│   ├── package.json
│   └── vite.config.js
│
└── sample_data/
    └── customers.csv    # Sample dataset for testing
```

---

## 12. Key Design Decisions

**JWT over session cookies**: JWT is stateless — the server doesn't need to store sessions. The token carries all user info and is verified on every request using the secret key.

**bcrypt for passwords**: bcrypt is designed to be slow, making brute-force attacks computationally expensive. Salt is automatically included in the hash.

**First user = admin**: Avoids the chicken-and-egg problem of needing an admin account to create the first admin. Once the system is running, the admin can demote themselves if needed.

**Role checks on both frontend and backend**: Frontend checks provide good UX (hiding inaccessible buttons). Backend checks are the actual security layer — never trusting the client alone.

**Single unified dashboard**: Instead of separate admin/user dashboards, one dashboard adapts to the user's role. This reduces code duplication and makes the experience consistent.

**MongoDB for users + projects**: All data lives in the same database, making backup, replication, and connection management simpler.

---

## 13. Limitations and Future Enhancements

**Current limitations:**
- JWT tokens cannot be revoked before expiry (no logout blacklist)
- No email verification on registration
- No password reset flow
- All projects are shared (no per-user project ownership)

**Potential enhancements:**
- Token blacklist using Redis for proper logout
- Email verification via SMTP
- Password reset with expiring email links
- Per-user project namespacing
- Audit log of user actions (role changes, deletions)
- OAuth2 integration (Google, GitHub login)

---

## 14. How to Run

### Step 1 — Backend
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

### Step 2 — Frontend
```bash
cd frontend
npm install
npm run dev
```

### Step 3 — First use
1. Open `http://localhost:5173`
2. Click "Create Account" and register — you become the admin automatically
3. Register additional users — they default to `guest_user`
4. Log in as admin → click user icon → **Manage Users** → change roles

---

## 15. Conclusion

This project demonstrates the integration of modern web technologies with practical machine learning to build a production-ready data analysis platform. The application handles the full lifecycle of an ML project — from user authentication through data upload, model training, result visualisation, and custom prediction — while enforcing role-based access control throughout. The clean separation of concerns between the auth layer, API layer, ML engine, and database makes each component independently testable and extensible.
