from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from typing import Optional
from datetime import datetime
from bson import ObjectId
import os
import io
import numpy as np
from dotenv import load_dotenv
from ml_engine import run_analysis, suggest_techniques, validate_techniques
from auth import hash_password, verify_password, create_token, get_current_user, require_role

load_dotenv()

app = FastAPI()

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── MONGO ─────────────────────────────────────────────────────────────────────
MONGODB_URL    = os.getenv("MONGODB_URL",    "mongodb://localhost:27017")
DATABASE_NAME  = os.getenv("DATABASE_NAME",  "notebook_db")

client = AsyncIOMotorClient(MONGODB_URL)
db     = client[DATABASE_NAME]

# Collections
projects_collection      = db["projects"]       # admin projects
user_projects_collection = db["user_projects"]  # user projects
users_collection         = db["users"]          # registered users

# GridFS buckets (separate buckets keep files organised by owner)
admin_fs = AsyncIOMotorGridFSBucket(db, bucket_name="admin_files")
user_fs  = AsyncIOMotorGridFSBucket(db, bucket_name="user_files")


# ── MODELS ────────────────────────────────────────────────────────────────────
class Project(BaseModel):
    name: str
    date: str
    sourceCount: int = 0
    starred: bool = False

class ProjectUpdate(BaseModel):
    name:             Optional[str]  = None
    date:             Optional[str]  = None
    sourceCount:      Optional[int]  = None
    starred:          Optional[bool] = None
    problemStatement: Optional[str]  = None
    lastTechnique:    Optional[str]  = None
    lastResults:      Optional[dict] = None

class UserRegister(BaseModel):
    username: str
    email:    str
    password: str
    role:     str = "guest_user"   # admin | developer | guest_user

class UserLogin(BaseModel):
    username: str
    password: str

class RoleUpdate(BaseModel):
    role: str   # admin | developer | guest_user


# ── HELPERS ───────────────────────────────────────────────────────────────────
def _clean(doc: dict) -> dict:
    """Replace _id with id and stringify it."""
    doc["id"] = str(doc.pop("_id"))
    return doc

def _oid(project_id: str) -> ObjectId:
    try:
        return ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project ID")

def _sanitise(obj):
    """Recursively convert NumPy/pandas types to native Python for MongoDB."""
    if isinstance(obj, dict):
        return {k: _sanitise(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitise(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj

def _bucket(role: str):
    return admin_fs if role == "admin" else user_fs

def _collection(role: str):
    return projects_collection if role == "admin" else user_projects_collection


# ── AUTH ──────────────────────────────────────────────────────────────────────
@app.post("/register")
async def register(data: UserRegister):
    """Register a new user. First registered user is always admin."""
    existing = await users_collection.find_one({"username": data.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken.")

    existing_email = await users_collection.find_one({"email": data.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered.")

    # Validate role
    valid_roles = {"admin", "developer", "guest_user"}
    role = data.role if data.role in valid_roles else "guest_user"

    # First user ever → always admin
    count = await users_collection.count_documents({})
    if count == 0:
        role = "admin"

    user_doc = {
        "username":   data.username,
        "email":      data.email,
        "password":   hash_password(data.password),
        "role":       role,
        "createdAt":  datetime.utcnow().isoformat(),
    }
    result = await users_collection.insert_one(user_doc)
    token  = create_token(str(result.inserted_id), data.username, role)

    return {
        "success":  True,
        "token":    token,
        "username": data.username,
        "role":     role,
    }


@app.post("/login")
async def login(data: UserLogin):
    """Authenticate user and return JWT token."""
    user = await users_collection.find_one({"username": data.username})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = create_token(str(user["_id"]), user["username"], user["role"])
    return {
        "success":  True,
        "token":    token,
        "username": user["username"],
        "role":     user["role"],
    }


@app.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    """Return current user info from token."""
    return {
        "username": current_user["username"],
        "role":     current_user["role"],
        "user_id":  current_user["sub"],
    }


# ── USER MANAGEMENT (admin only) ──────────────────────────────────────────────
@app.get("/users")
async def list_users(current_user: dict = Depends(get_current_user)):
    """List all users — admin only."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    users = []
    async for u in users_collection.find({}, {"password": 0}):
        u["id"] = str(u.pop("_id"))
        users.append(u)
    return {"users": users}


@app.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    body: RoleUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Change a user's role — admin only. Cannot change own role."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    valid_roles = {"admin", "developer", "guest_user"}
    if body.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(valid_roles)}")

    if current_user["sub"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot change your own role.")

    result = await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"role": body.role}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"success": True, "message": f"Role updated to '{body.role}'."}


@app.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a user — admin only. Cannot delete own account."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    if current_user["sub"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account.")

    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"success": True}


# ── FILE UPLOAD ───────────────────────────────────────────────────────────────
@app.post("/upload/{role}/{project_id}")
async def upload_file(
    role: str,
    project_id: str,
    file: UploadFile = File(...)
):
    """
    Upload a data file (CSV / Excel / JSON / TXT) and attach it to a project.
    The file is stored in GridFS. The project document is updated with:
      - fileName   : original filename
      - fileId     : GridFS file ID
      - uploadedAt : timestamp
    """
    bucket     = _bucket(role)
    collection = _collection(role)
    oid        = _oid(project_id)

    contents = await file.read()

    # Delete previous file for this project if one exists
    project = await collection.find_one({"_id": oid})
    if project and project.get("fileId"):
        try:
            await bucket.delete(ObjectId(project["fileId"]))
        except Exception:
            pass  # file may have been deleted already

    # Upload new file to GridFS
    file_id = await bucket.upload_from_stream(
        file.filename,
        io.BytesIO(contents),
        metadata={"project_id": project_id, "content_type": file.content_type}
    )

    # Update project document
    await collection.update_one(
        {"_id": oid},
        {"$set": {
            "fileName":   file.filename,
            "fileId":     str(file_id),
            "fileSize":   len(contents),
            "uploadedAt": datetime.utcnow().isoformat(),
        }}
    )

    return {
        "success":  True,
        "fileId":   str(file_id),
        "fileName": file.filename,
        "fileSize": len(contents),
    }


# ── FILE DOWNLOAD ─────────────────────────────────────────────────────────────
@app.get("/download/{role}/{file_id}")
async def download_file(role: str, file_id: str):
    """Stream a file back from GridFS."""
    bucket = _bucket(role)
    try:
        stream = await bucket.open_download_stream(ObjectId(file_id))
        contents = await stream.read()
        return StreamingResponse(
            io.BytesIO(contents),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={stream.filename}"}
        )
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")


# ── SAVE PROBLEM STATEMENT ────────────────────────────────────────────────────
@app.put("/save-problem/{role}/{project_id}")
async def save_problem(
    role: str,
    project_id: str,
    problemStatement: str = Form(...),
    technique:        str = Form(default=""),
):
    """Save the problem statement (and optionally selected technique) to the project."""
    collection = _collection(role)
    oid        = _oid(project_id)

    update_data: dict = {"problemStatement": problemStatement}
    if technique:
        update_data["lastTechnique"] = technique

    result = await collection.update_one({"_id": oid}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True}


# ── CSV PROFILE (column names for UI selectors) ───────────────────────────────
@app.get("/csv-profile/{role}/{project_id}")
async def csv_profile(role: str, project_id: str):
    """Returns column info from the project's stored CSV for UI selectors."""
    from ml_engine import _load_csv, _preprocess
    import numpy as np

    collection = _collection(role)
    bucket     = _bucket(role)
    oid        = _oid(project_id)

    project = await collection.find_one({"_id": oid})
    if not project or not project.get("fileId"):
        return {"numeric_cols": [], "all_cols": [], "col_info": {}}

    try:
        stream    = await bucket.open_download_stream(ObjectId(project["fileId"]))
        file_data = await stream.read()
        df        = _load_csv(file_data)
        df_clean, _ = _preprocess(df)

        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()

        # Build per-column info from ORIGINAL df (before encoding)
        col_info = {}
        for col in df.columns:
            if df[col].dtype == object:
                unique_vals = sorted(df[col].dropna().unique().tolist())
                # High cardinality text (names etc.) — free text input
                if len(unique_vals) > 50:
                    col_info[col] = {"type": "text", "values": []}
                else:
                    col_info[col] = {"type": "categorical", "values": unique_vals}
            else:
                col_info[col] = {
                    "type": "numeric",
                    "min":  round(float(df[col].min()), 3),
                    "max":  round(float(df[col].max()), 3),
                    "mean": round(float(df[col].mean()), 3),
                }

        return {
            "numeric_cols":  numeric_cols,
            "all_cols":      df.columns.tolist(),       # original columns
            "clean_cols":    df_clean.columns.tolist(), # after preprocessing
            "col_info":      col_info,
            "n_rows":        len(df_clean),
        }
    except Exception as e:
        return {"numeric_cols": [], "all_cols": [], "col_info": {}, "error": str(e)}


# ── PCA REDUCE & DOWNLOAD ─────────────────────────────────────────────────────
@app.post("/pca-reduce/{role}/{project_id}")
async def pca_reduce(
    role:       str,
    project_id: str,
    n_components: int = Form(...),
):
    """
    Applies PCA to the project's stored CSV, reduces to n_components dimensions,
    and returns the transformed data as a downloadable CSV.
    """
    from ml_engine import _load_csv, _preprocess
    import numpy as np
    import pandas as pd
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA as SklearnPCA
    import io as _io

    collection = _collection(role)
    bucket     = _bucket(role)
    oid        = _oid(project_id)

    project = await collection.find_one({"_id": oid})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.get("fileId"):
        raise HTTPException(status_code=400, detail="No data file uploaded for this project.")

    # Load file from GridFS
    try:
        stream    = await bucket.open_download_stream(ObjectId(project["fileId"]))
        file_data = await stream.read()
    except Exception:
        raise HTTPException(status_code=404, detail="Data file not found in storage.")

    # Load and preprocess
    df       = _load_csv(file_data)
    df_clean, _ = _preprocess(df)
    numeric_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()

    if len(numeric_cols) < 3:
        raise HTTPException(status_code=400, detail="PCA needs at least 3 numeric columns.")

    max_components = min(len(numeric_cols), len(df_clean))
    if n_components < 1 or n_components > max_components:
        raise HTTPException(
            status_code=400,
            detail=f"n_components must be between 1 and {max_components}."
        )

    X      = df_clean[numeric_cols].fillna(0)
    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X)

    pca         = SklearnPCA(n_components=n_components)
    X_reduced   = pca.fit_transform(X_sc)
    explained   = pca.explained_variance_ratio_
    total_var   = float(np.sum(explained) * 100)

    # Build output DataFrame
    col_names   = [f"PC{i+1}" for i in range(n_components)]
    reduced_df  = pd.DataFrame(X_reduced, columns=col_names)

    # Add back any non-numeric columns that survived (categorical identifiers)
    for col in df_clean.columns:
        if col not in numeric_cols:
            reduced_df.insert(0, col, df_clean[col].values)

    # Stream as CSV download
    csv_buffer = _io.StringIO()
    reduced_df.to_csv(csv_buffer, index=False)
    csv_bytes  = csv_buffer.getvalue().encode()

    filename = f"pca_{n_components}components_{project.get('name','project').replace(' ','_')}.csv"

    return StreamingResponse(
        _io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Total-Variance":    f"{total_var:.2f}",
            "X-N-Components":      str(n_components),
        }
    )


# ── VALIDATE TECHNIQUES ──────────────────────────────────────────────────────
@app.post("/validate-techniques/{role}/{project_id}")
async def validate_techniques_endpoint(
    role:              str,
    project_id:        str,
    problem_statement: str = Form(default=""),
):
    """
    Returns {technique: {applicable: bool, reason: str}} for all 8 techniques.
    """
    collection = _collection(role)
    bucket     = _bucket(role)
    oid        = _oid(project_id)

    project = await collection.find_one({"_id": oid})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    file_data = None
    if project.get("fileId"):
        try:
            stream    = await bucket.open_download_stream(ObjectId(project["fileId"]))
            file_data = await stream.read()
        except Exception:
            pass

    ps = problem_statement or project.get("problemStatement", "")
    return validate_techniques(file_data, ps)


# ── SUGGEST TECHNIQUES ───────────────────────────────────────────────────────
@app.post("/suggest/{role}/{project_id}")
async def suggest(
    role:              str,
    project_id:        str,
    problem_statement: str = Form(default=""),
):
    """
    Analyse the project's CSV + problem statement and return
    ranked technique suggestions with reasoning.
    """
    collection = _collection(role)
    bucket     = _bucket(role)
    oid        = _oid(project_id)

    project = await collection.find_one({"_id": oid})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Load file from GridFS if available
    file_data = None
    if project.get("fileId"):
        try:
            stream    = await bucket.open_download_stream(ObjectId(project["fileId"]))
            file_data = await stream.read()
        except Exception:
            pass

    ps = problem_statement or project.get("problemStatement", "")
    return suggest_techniques(ps, file_data)


# ── ANALYSIS ──────────────────────────────────────────────────────────────────
@app.post("/analyse/{role}/{project_id}")
async def analyse(
    role:              str,
    project_id:        str,
    problem_statement: str   = Form(...),
    technique:         str   = Form(...),
    # DBSCAN custom params (optional)
    dbscan_features:   str   = Form(default=""),
    dbscan_eps:        float = Form(default=0.5),
    dbscan_min_pts:    int   = Form(default=0),
    # K-Means custom params (optional)
    kmeans_features:   str   = Form(default=""),
    kmeans_k:          int   = Form(default=0),
    # Supervised custom params (optional)
    target_col:        str   = Form(default=""),   # user-chosen dependent variable
    tree_max_depth:    int   = Form(default=0),    # 0 = default (6)
    knn_k:             int   = Form(default=0),    # 0 = auto
):
    """
    Run ML analysis with full custom params for all techniques.
    """
    collection = _collection(role)
    bucket     = _bucket(role)
    oid        = _oid(project_id)

    project = await collection.find_one({"_id": oid})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    file_data = None
    if project.get("fileId"):
        try:
            stream    = await bucket.open_download_stream(ObjectId(project["fileId"]))
            file_data = await stream.read()
        except Exception:
            pass

    extra = {}
    if technique == "dbscan":
        if dbscan_features:
            extra["selected_features"] = [f.strip() for f in dbscan_features.split(",") if f.strip()]
        extra["eps"] = dbscan_eps
        if dbscan_min_pts > 0:
            extra["forced_min_pts"] = dbscan_min_pts
    elif technique == "kmeans":
        if kmeans_features:
            extra["selected_features"] = [f.strip() for f in kmeans_features.split(",") if f.strip()]
        if kmeans_k > 0:
            extra["forced_k"] = kmeans_k
    elif technique in ("classification", "regression", "decision_tree", "knn"):
        if target_col:
            extra["forced_target"] = target_col
        if technique == "decision_tree" and tree_max_depth > 0:
            extra["max_depth"] = tree_max_depth
        if technique == "knn" and knn_k > 0:
            extra["forced_k"] = knn_k

    results = run_analysis(technique, problem_statement, file_data, **extra)

    await collection.update_one(
        {"_id": oid},
        {"$set": {
            "problemStatement": problem_statement,
            "lastTechnique":    technique,
            "lastResults":      _sanitise(results),
            "lastAnalysedAt":   datetime.utcnow().isoformat(),
        }}
    )

    return _sanitise(results)


# ── PREDICT CLUSTER FOR CUSTOM INPUT ─────────────────────────────────────────
@app.post("/predict-cluster/{role}/{project_id}")
async def predict_cluster(
    role:           str,
    project_id:     str,
    technique:      str  = Form(...),          # "kmeans" or "dbscan"
    custom_input:   str  = Form(...),          # JSON string
    kmeans_features: str = Form(default=""),
    kmeans_k:        int = Form(default=0),
    dbscan_features: str = Form(default=""),
    dbscan_eps:     float = Form(default=0.5),
    dbscan_min_pts:  int = Form(default=0),
):
    import json as _json
    from ml_engine import predict_cluster_input

    collection = _collection(role)
    bucket     = _bucket(role)
    oid        = _oid(project_id)

    project = await collection.find_one({"_id": oid})
    if not project or not project.get("fileId"):
        raise HTTPException(status_code=400, detail="No data file for this project.")

    try:
        stream    = await bucket.open_download_stream(ObjectId(project["fileId"]))
        file_data = await stream.read()
    except Exception:
        raise HTTPException(status_code=404, detail="Data file not found.")

    try:
        input_data = _json.loads(custom_input)
    except Exception:
        raise HTTPException(status_code=400, detail="custom_input must be valid JSON.")

    extra = {}
    if technique == "kmeans":
        if kmeans_features:
            extra["selected_features"] = [f.strip() for f in kmeans_features.split(",") if f.strip()]
        if kmeans_k > 0:
            extra["forced_k"] = kmeans_k
    elif technique == "dbscan":
        if dbscan_features:
            extra["selected_features"] = [f.strip() for f in dbscan_features.split(",") if f.strip()]
        extra["eps"] = dbscan_eps
        if dbscan_min_pts > 0:
            extra["forced_min_pts"] = dbscan_min_pts

    result = predict_cluster_input(technique, file_data, input_data, **extra)
    return _sanitise(result)


# ── PREDICT ON CUSTOM INPUT ───────────────────────────────────────────────────
@app.post("/predict-custom/{role}/{project_id}")
async def predict_custom(
    role:          str,
    project_id:    str,
    technique:     str  = Form(...),
    target_col:    str  = Form(default=""),
    tree_max_depth: int = Form(default=0),
    knn_k:         int  = Form(default=0),
    custom_input:  str  = Form(...),   # JSON string: {"col1": val1, "col2": val2, ...}
):
    """
    Retrain the model on the stored CSV and predict for a single custom input row.
    Returns the predicted value/class and (for classification) probabilities.
    """
    import json as _json
    from ml_engine import predict_custom_input

    collection = _collection(role)
    bucket     = _bucket(role)
    oid        = _oid(project_id)

    project = await collection.find_one({"_id": oid})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.get("fileId"):
        raise HTTPException(status_code=400, detail="No data file uploaded for this project.")

    try:
        stream    = await bucket.open_download_stream(ObjectId(project["fileId"]))
        file_data = await stream.read()
    except Exception:
        raise HTTPException(status_code=404, detail="Data file not found.")

    try:
        input_data = _json.loads(custom_input)
    except Exception:
        raise HTTPException(status_code=400, detail="custom_input must be valid JSON.")

    extra = {}
    if target_col:
        extra["forced_target"] = target_col
    if technique == "decision_tree" and tree_max_depth > 0:
        extra["max_depth"] = tree_max_depth
    if technique == "knn" and knn_k > 0:
        extra["forced_k"] = knn_k

    result = predict_custom_input(technique, file_data, input_data, **extra)
    return _sanitise(result)



# ── ADMIN PROJECT CRUD ────────────────────────────────────────────────────────
@app.get("/projects")
async def get_projects(current_user: dict = Depends(get_current_user)):
    """
    Admin → all projects.
    Developer / guest_user → only starred projects.
    """
    projects = []
    query    = {} if current_user["role"] == "admin" else {"starred": True}
    async for p in projects_collection.find(query):
        projects.append(_clean(p))
    return {"projects": projects}

@app.post("/projects")
async def create_project(project: Project):
    d = project.dict()
    d["createdAt"] = datetime.utcnow().isoformat()
    result = await projects_collection.insert_one(d)
    d["id"] = str(result.inserted_id)
    d.pop("_id", None)
    return {"success": True, "project": d}

@app.get("/projects/{project_id}")
async def get_project(
    project_id:   str,
    current_user: dict = Depends(get_current_user),
):
    p = await projects_collection.find_one({"_id": _oid(project_id)})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    # Non-admins can only access starred projects
    if current_user["role"] != "admin" and not p.get("starred", False):
        raise HTTPException(status_code=403, detail="Access denied. This project has not been shared.")
    return {"project": _clean(p)}

@app.put("/projects/{project_id}")
async def update_project(project_id: str, body: ProjectUpdate):
    update_data = {k: v for k, v in body.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    result = await projects_collection.update_one(
        {"_id": _oid(project_id)}, {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True}

@app.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    oid = _oid(project_id)
    # Remove attached file if any
    p = await projects_collection.find_one({"_id": oid})
    if p and p.get("fileId"):
        try:
            await admin_fs.delete(ObjectId(p["fileId"]))
        except Exception:
            pass
    result = await projects_collection.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True}


# ── USER PROJECT CRUD ─────────────────────────────────────────────────────────
@app.get("/user-projects")
async def get_user_projects():
    projects = []
    async for p in user_projects_collection.find():
        projects.append(_clean(p))
    return {"projects": projects}

@app.post("/user-projects")
async def create_user_project(project: Project):
    d = project.dict()
    d["createdAt"] = datetime.utcnow().isoformat()
    result = await user_projects_collection.insert_one(d)
    d["id"] = str(result.inserted_id)
    d.pop("_id", None)
    return {"success": True, "project": d}

@app.get("/user-projects/{project_id}")
async def get_user_project(project_id: str):
    p = await user_projects_collection.find_one({"_id": _oid(project_id)})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": _clean(p)}

@app.put("/user-projects/{project_id}")
async def update_user_project(project_id: str, body: ProjectUpdate):
    update_data = {k: v for k, v in body.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    result = await user_projects_collection.update_one(
        {"_id": _oid(project_id)}, {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True}

@app.delete("/user-projects/{project_id}")
async def delete_user_project(project_id: str):
    oid = _oid(project_id)
    p = await user_projects_collection.find_one({"_id": oid})
    if p and p.get("fileId"):
        try:
            await user_fs.delete(ObjectId(p["fileId"]))
        except Exception:
            pass
    result = await user_projects_collection.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True}


# ── ROOT ──────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"message": "Notebook API is running"}
