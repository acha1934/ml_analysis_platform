"""
ml_engine.py
Handles all ML analysis for the project.
Supports Supervised and Unsupervised techniques on CSV data.
"""

import io
import json
import numpy  as np
import pandas as pd

from sklearn.preprocessing    import LabelEncoder, StandardScaler
from sklearn.model_selection  import train_test_split, cross_val_score
from sklearn.ensemble         import RandomForestClassifier, RandomForestRegressor, IsolationForest
from sklearn.linear_model     import Ridge
from sklearn.tree             import DecisionTreeClassifier
from sklearn.neighbors        import KNeighborsClassifier
from sklearn.cluster          import KMeans, DBSCAN
from sklearn.decomposition    import PCA
from sklearn.metrics          import (
    accuracy_score, classification_report,
    mean_squared_error, r2_score, mean_absolute_error,
    silhouette_score
)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def run_analysis(technique: str, problem_statement: str, file_data: bytes | None, **kwargs) -> dict:
    if file_data is None:
        return _no_data_response(technique, problem_statement)

    try:
        df = _load_csv(file_data)
    except Exception as e:
        return {"error": f"Could not parse CSV file: {str(e)}"}

    try:
        dispatch = {
            "classification": run_classification,
            "regression":     run_regression,
            "decision_tree":  run_decision_tree,
            "knn":            run_knn,
            "kmeans":         run_kmeans,
            "dbscan":         run_dbscan,
            "pca":            run_pca,
            "anomaly":        run_anomaly,
        }
        fn = dispatch.get(technique)
        if fn is None:
            return {"error": f"Unknown technique: {technique}"}
        # Pass extra kwargs to techniques that support them
        if technique in ("kmeans", "dbscan", "classification", "regression", "decision_tree", "knn"):
            return fn(df, problem_statement, **kwargs)
        return fn(df, problem_statement)
    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}


# ─────────────────────────────────────────────────────────────────────────────
# DATA HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _load_csv(file_data: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(file_data))
    df.columns = df.columns.str.strip()
    return df


def _preprocess(df: pd.DataFrame):
    """
    Auto-preprocess: encode categoricals, drop high-cardinality text columns,
    fill missing values. Returns cleaned df + encoders dict.
    """
    df = df.copy()

    # Drop columns where >80% values are missing
    thresh = max(1, int(0.8 * len(df)))
    df = df.dropna(thresh=thresh, axis=1)

    # Fill missing values safely
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].fillna(df[col].mode().iloc[0] if not df[col].mode().empty else "unknown")
        else:
            df[col] = df[col].fillna(df[col].median())

    encoders = {}
    for col in df.select_dtypes(include="object").columns:
        n_unique = df[col].nunique()
        if n_unique > 50:
            df = df.drop(columns=[col])
        else:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoders[col] = le

    return df, encoders


def _pick_target(df: pd.DataFrame, problem_statement: str, prefer_categorical=False):
    """
    Pick target column by matching problem statement keywords,
    then fall back to heuristics.
    """
    ps_lower = problem_statement.lower()

    # Match any column name mentioned in problem statement
    for col in df.columns:
        if col.lower() in ps_lower:
            return col

    if prefer_categorical:
        # Pick last column with < 20 unique values
        for col in reversed(df.columns.tolist()):
            if df[col].nunique() < 20:
                return col

    # Final fallback: last column
    return df.columns[-1]


def _safe(val):
    """Make a value JSON-serialisable."""
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return round(float(val), 4)
    if isinstance(val, np.ndarray):
        return val.tolist()
    return val


def _no_data_response(technique, problem_statement):
    return {
        "summary":  f"No data file attached. Please upload a CSV to run {technique} analysis.",
        "metrics":  {},
        "insights": ["Upload a CSV file and re-run the analysis."],
        "raw":      {"technique": technique, "problem_statement": problem_statement},
    }


# ─────────────────────────────────────────────────────────────────────────────
# SUPERVISED — CLASSIFICATION (Random Forest)
# ─────────────────────────────────────────────────────────────────────────────
def run_classification(df: pd.DataFrame, ps: str, forced_target: str = "") -> dict:
    df_clean, _ = _preprocess(df)
    if df_clean.empty or len(df_clean.columns) < 2:
        return {"error": "Not enough usable columns after preprocessing."}

    target = forced_target if forced_target and forced_target in df_clean.columns \
             else _pick_target(df_clean, ps, prefer_categorical=True)
    X = df_clean.drop(columns=[target])
    y = df_clean[target]

    if X.empty:
        return {"error": "No feature columns remaining after preprocessing."}
    if y.nunique() < 2:
        return {"error": f"Target column '{target}' has only 1 unique value — cannot classify."}
    if len(df_clean) < 10:
        return {"error": "Need at least 10 rows for classification."}

    # Ensure minimum test size
    test_size = 0.2 if len(df_clean) >= 25 else 0.1
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y if y.nunique() <= 10 else None
    )

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    cv_folds = min(5, len(X_train), y.value_counts().min())
    cv_folds = max(2, cv_folds)
    cv_scores = cross_val_score(model, X, y, cv=cv_folds, scoring="accuracy")

    fi = sorted(
        zip(X.columns.tolist(), model.feature_importances_.tolist()),
        key=lambda x: x[1], reverse=True
    )[:5]

    return {
        "summary": (
            f"Random Forest Classification on '{target}'. "
            f"Trained on {len(X_train)} samples, tested on {len(X_test)}. "
            f"Accuracy: {acc:.1%}."
        ),
        "metrics": {
            "Accuracy":      f"{acc:.1%}",
            "CV Accuracy":   f"{cv_scores.mean():.1%} ± {cv_scores.std():.1%}",
            "Classes":       str(y.nunique()),
            "Train samples": str(len(X_train)),
            "Test samples":  str(len(X_test)),
            "Features used": str(len(X.columns)),
        },
        "insights": [
            f"Target column detected: '{target}'",
            f"Top feature: '{fi[0][0]}' (importance {fi[0][1]:.3f})",
            *[f"  • {name}: {imp:.3f}" for name, imp in fi],
            f"Cross-validation accuracy: {cv_scores.mean():.1%} ({cv_folds}-fold)",
        ],
        "feature_importance": [{"feature": n, "importance": round(i, 4)} for n, i in fi],
        "class_labels": [str(c) for c in sorted(y.unique().tolist())],
        "raw": {
            "technique":  "classification",
            "target_col": target,
            "n_features": len(X.columns),
            "n_classes":  int(y.nunique()),
            "accuracy":   round(acc, 4),
            "cv_mean":    round(float(cv_scores.mean()), 4),
        },
        "supervised_config": {"target": target},
    }


# ─────────────────────────────────────────────────────────────────────────────
# SUPERVISED — REGRESSION (Ridge)
# ─────────────────────────────────────────────────────────────────────────────
def run_regression(df: pd.DataFrame, ps: str, forced_target: str = "") -> dict:
    df_clean, _ = _preprocess(df)
    if df_clean.empty or len(df_clean.columns) < 2:
        return {"error": "Not enough usable columns after preprocessing."}
    if len(df_clean) < 10:
        return {"error": "Need at least 10 rows for regression."}

    target = forced_target if forced_target and forced_target in df_clean.columns \
             else _pick_target(df_clean, ps, prefer_categorical=False)

    if not pd.api.types.is_numeric_dtype(df_clean[target]):
        # Try to find a numeric target instead
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            return {"error": "No numeric target column found. Regression requires a numeric target."}
        target = numeric_cols[-1]

    X = df_clean.drop(columns=[target])
    y = df_clean[target]

    if X.empty:
        return {"error": "No feature columns remaining after removing target."}

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2 if len(df_clean) >= 25 else 0.1, random_state=42
    )

    model  = Ridge(alpha=1.0)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    r2   = r2_score(y_test, y_pred)
    mae  = mean_absolute_error(y_test, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))

    coef = sorted(
        zip(X.columns.tolist(), model.coef_.tolist()),
        key=lambda x: abs(x[1]), reverse=True
    )[:5]

    return {
        "summary": (
            f"Ridge Regression predicting '{target}'. "
            f"R² = {r2:.3f}, MAE = {mae:.3f}, RMSE = {rmse:.3f}."
        ),
        "metrics": {
            "R² Score":      f"{r2:.4f}",
            "MAE":           f"{mae:.4f}",
            "RMSE":          f"{rmse:.4f}",
            "Train samples": str(len(X_train)),
            "Test samples":  str(len(X_test)),
        },
        "insights": [
            f"Target column: '{target}'",
            f"R² of {r2:.3f} means the model explains {max(0,r2)*100:.1f}% of variance.",
            f"Mean absolute error: {mae:.3f} units",
            f"Most influential feature: '{coef[0][0]}'" if coef else "No significant features found.",
            *[f"  • {n}: coef {c:.4f}" for n, c in coef],
        ],
        "scatter_data": {
            "actual":    [round(float(v), 3) for v in y_test.values[:20]],
            "predicted": [round(float(v), 3) for v in y_pred[:20]],
        },
        "raw": {
            "technique":  "regression",
            "target_col": target,
            "r2":         round(r2, 4),
            "mae":        round(float(mae), 4),
            "rmse":       round(float(rmse), 4),
        },
        "supervised_config": {"target": target},
    }


# ─────────────────────────────────────────────────────────────────────────────
# SUPERVISED — DECISION TREE
# ─────────────────────────────────────────────────────────────────────────────
def run_decision_tree(df: pd.DataFrame, ps: str,
                      forced_target: str = "",
                      max_depth: int = 0) -> dict:
    df_clean, _ = _preprocess(df)
    if df_clean.empty or len(df_clean.columns) < 2:
        return {"error": "Not enough usable columns after preprocessing."}
    if len(df_clean) < 10:
        return {"error": "Need at least 10 rows for Decision Tree."}

    target = forced_target if forced_target and forced_target in df_clean.columns \
             else _pick_target(df_clean, ps, prefer_categorical=True)
    X = df_clean.drop(columns=[target])
    y = df_clean[target]

    if X.empty:
        return {"error": "No feature columns left after removing target."}
    if y.nunique() < 2:
        return {"error": f"Target '{target}' has only 1 class — need at least 2."}

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2 if len(df_clean) >= 25 else 0.1, random_state=42
    )

    depth_used = max_depth if max_depth > 0 else 6
    model = DecisionTreeClassifier(max_depth=depth_used, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    acc    = accuracy_score(y_test, y_pred)
    depth  = model.get_depth()
    leaves = model.get_n_leaves()

    fi = sorted(
        zip(X.columns.tolist(), model.feature_importances_.tolist()),
        key=lambda x: x[1], reverse=True
    )[:5]

    return {
        "summary": (
            f"Decision Tree on '{target}'. "
            f"Depth: {depth}, Leaves: {leaves}. Accuracy: {acc:.1%}."
        ),
        "metrics": {
            "Accuracy":      f"{acc:.1%}",
            "Tree depth":    str(depth),
            "Max depth set": str(depth_used),
            "Leaf nodes":    str(leaves),
            "Classes":       str(y.nunique()),
            "Train size":    str(len(X_train)),
            "Test size":     str(len(X_test)),
        },
        "insights": [
            f"Target column: '{target}'",
            f"Tree reached depth {depth} with {leaves} leaf nodes.",
            f"Top splitting feature: '{fi[0][0]}' ({fi[0][1]:.3f})" if fi else "",
            *[f"  • {n}: {i:.3f}" for n, i in fi],
            "Tip: Reduce max_depth to avoid overfitting on small datasets.",
        ],
        "feature_importance": [{"feature": n, "importance": round(i, 4)} for n, i in fi],
        "raw": {
            "technique":  "decision_tree",
            "target_col": target,
            "depth":      depth,
            "leaves":     leaves,
            "accuracy":   round(acc, 4),
        },
        "supervised_config": {"target": target, "max_depth": depth_used},
    }


# ─────────────────────────────────────────────────────────────────────────────
# SUPERVISED — K-NEAREST NEIGHBOURS
# ─────────────────────────────────────────────────────────────────────────────
def run_knn(df: pd.DataFrame, ps: str,
            forced_target: str = "",
            forced_k: int = 0) -> dict:
    df_clean, _ = _preprocess(df)
    if df_clean.empty or len(df_clean.columns) < 2:
        return {"error": "Not enough usable columns after preprocessing."}
    if len(df_clean) < 10:
        return {"error": "Need at least 10 rows for KNN."}

    target = forced_target if forced_target and forced_target in df_clean.columns \
             else _pick_target(df_clean, ps, prefer_categorical=True)
    X = df_clean.drop(columns=[target])
    y = df_clean[target]

    if X.empty:
        return {"error": "No feature columns left after removing target."}
    if y.nunique() < 2:
        return {"error": f"Target '{target}' has only 1 class."}

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2 if len(df_clean) >= 25 else 0.1, random_state=42
    )

    if forced_k > 0:
        best_k  = min(forced_k, len(X_train) - 1)
        best_k  = max(1, best_k)
        k_source = f"user-set (k={best_k})"
    else:
        best_k, best_acc = 3, 0.0
        for k in [3, 5, 7, 9]:
            if k >= len(X_train):
                continue
            cv_folds = min(5, len(X_train), y.value_counts().min())
            if cv_folds < 2:
                continue
            try:
                cv = cross_val_score(
                    KNeighborsClassifier(n_neighbors=k), X_scaled, y,
                    cv=cv_folds, scoring="accuracy"
                )
                if cv.mean() > best_acc:
                    best_acc, best_k = cv.mean(), k
            except Exception:
                continue
        best_k   = min(best_k, len(X_train) - 1)
        best_k   = max(1, best_k)
        k_source = f"auto (k={best_k})"

    model  = KNeighborsClassifier(n_neighbors=best_k)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    acc    = accuracy_score(y_test, y_pred)

    return {
        "summary": f"KNN Classification on '{target}' (k={best_k}, {k_source}). Accuracy: {acc:.1%}.",
        "metrics": {
            "Accuracy":   f"{acc:.1%}",
            "k value":    str(best_k),
            "k source":   k_source,
            "Classes":    str(y.nunique()),
            "Train size": str(len(X_train)),
            "Test size":  str(len(X_test)),
        },
        "insights": [
            f"Target column: '{target}'",
            f"k={best_k} ({k_source})",
            f"KNN classifies each record by its {best_k} nearest neighbours.",
            "StandardScaler applied — features are normalised before distance calculation.",
        ],
        "raw": {
            "technique":  "knn",
            "target_col": target,
            "best_k":     best_k,
            "k_source":   k_source,
            "accuracy":   round(acc, 4),
        },
        "supervised_config": {"target": target, "k": best_k},
    }


# ─────────────────────────────────────────────────────────────────────────────
# UNSUPERVISED — K-MEANS CLUSTERING
# ─────────────────────────────────────────────────────────────────────────────
def run_kmeans(df: pd.DataFrame, ps: str,
               selected_features: list = None,
               forced_k: int = 0) -> dict:
    df_clean, _ = _preprocess(df)

    all_numeric = df_clean.select_dtypes(include=[np.number]).columns.tolist()
    if selected_features:
        numeric_cols = [f for f in selected_features if f in all_numeric]
        if len(numeric_cols) < 2:
            return {"error": f"Selected features must include ≥2 numeric columns. Valid: {', '.join(all_numeric)}"}
    else:
        numeric_cols = all_numeric

    if len(numeric_cols) < 2:
        return {"error": "K-Means requires at least 2 numeric columns."}
    if len(df_clean) < 4:
        return {"error": "Need at least 4 rows for K-Means."}

    X      = df_clean[numeric_cols].fillna(0)
    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X)

    max_k = min(8, len(X) - 1)
    if max_k < 2:
        return {"error": "Not enough rows to form multiple clusters."}

    inertias = []
    for k in range(2, max_k + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_sc)
        inertias.append(km.inertia_)

    if forced_k >= 2 and forced_k <= max_k:
        best_k = forced_k
    else:
        diffs  = [inertias[i] - inertias[i+1] for i in range(len(inertias)-1)]
        best_k = diffs.index(max(diffs)) + 2 if diffs else 3
        best_k = min(best_k, max_k)

    km     = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    labels = km.fit_predict(X_sc)

    sil = silhouette_score(X_sc, labels) if len(set(labels)) > 1 else 0.0

    cluster_counts = pd.Series(labels).value_counts().sort_index()
    cluster_info   = [{"cluster": int(i), "size": int(cluster_counts.get(i, 0))} for i in range(best_k)]

    # ── Per-cluster average values for all features ───────────────────────────
    X_with_labels       = X.copy()
    X_with_labels["_cluster"] = labels
    cluster_averages = []
    for cid in range(best_k):
        subset = X_with_labels[X_with_labels["_cluster"] == cid].drop(columns=["_cluster"])
        avg    = subset.mean().round(3).to_dict()
        cluster_averages.append({
            "cluster": cid,
            "size":    int(cluster_counts.get(cid, 0)),
            "averages": {k: round(float(v), 3) for k, v in avg.items()},
        })

    k_source = "user-selected" if forced_k >= 2 else "auto (elbow method)"

    return {
        "summary": (
            f"K-Means found {best_k} clusters ({k_source}) across {len(X)} records "
            f"using {len(numeric_cols)} features. Silhouette: {sil:.3f}."
        ),
        "metrics": {
            "Clusters":         str(best_k),
            "K source":         k_source,
            "Silhouette score": f"{sil:.3f}",
            "Records":          str(len(X)),
            "Features used":    str(len(numeric_cols)),
            "Largest cluster":  str(int(cluster_counts.max())),
            "Smallest cluster": str(int(cluster_counts.min())),
        },
        "insights": [
            f"K={best_k} ({k_source}).",
            f"Features: {', '.join(numeric_cols)}",
            *[f"Cluster {c['cluster']}: {c['size']} records" for c in cluster_info],
            f"Silhouette {sil:.3f}: {'good' if sil>0.5 else 'moderate' if sil>0.25 else 'weak'} separation.",
        ],
        "cluster_info":     cluster_info,
        "cluster_averages": cluster_averages,
        "cluster_features": numeric_cols,
        "elbow_data": {
            "k_values": list(range(2, max_k + 1)),
            "inertias": [round(float(v), 2) for v in inertias],
        },
        "kmeans_config": {"features": numeric_cols, "k": best_k},
        "raw": {
            "technique":        "kmeans",
            "best_k":           best_k,
            "silhouette":       round(float(sil), 4),
            "numeric_features": numeric_cols,
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# UNSUPERVISED — DBSCAN
# ─────────────────────────────────────────────────────────────────────────────
def run_dbscan(df: pd.DataFrame, ps: str,
               selected_features: list = None,
               eps: float = 0.5,
               forced_min_pts: int = 0) -> dict:
    df_clean, _ = _preprocess(df)
    all_numeric  = df_clean.select_dtypes(include=[np.number]).columns.tolist()

    if selected_features:
        numeric_cols = [f for f in selected_features if f in all_numeric]
        if len(numeric_cols) < 2:
            return {"error": f"Selected features must include ≥2 numeric columns. Available: {', '.join(all_numeric)}"}
    else:
        numeric_cols = all_numeric

    if len(numeric_cols) < 2:
        return {"error": "DBSCAN requires at least 2 numeric columns."}
    if len(df_clean) < 10:
        return {"error": "Need at least 10 rows for DBSCAN."}

    X      = df_clean[numeric_cols].fillna(0)
    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X)

    if forced_min_pts > 0:
        min_samples = forced_min_pts
        ms_source   = f"user-set ({forced_min_pts})"
    else:
        min_samples = max(2, min(5, len(X) // 10))
        ms_source   = f"auto ({min_samples})"

    db     = DBSCAN(eps=eps, min_samples=min_samples)
    labels = db.fit_predict(X_sc)

    unique_labels = set(labels)
    n_clusters    = len(unique_labels) - (1 if -1 in unique_labels else 0)
    n_noise       = int((labels == -1).sum())

    valid_mask = labels != -1
    sil = 0.0
    if n_clusters > 1 and valid_mask.sum() > n_clusters:
        try:
            sil = float(silhouette_score(X_sc[valid_mask], labels[valid_mask]))
        except Exception:
            sil = 0.0

    cluster_counts = pd.Series(labels[labels >= 0]).value_counts().sort_index() if n_clusters > 0 else pd.Series(dtype=int)
    cluster_info   = [{"cluster": int(i), "size": int(cluster_counts.get(i, 0))} for i in range(n_clusters)]

    # ── Per-cluster average values ────────────────────────────────────────────
    X_with_labels = X.copy()
    X_with_labels["_cluster"] = labels
    cluster_averages = []
    for cid in range(n_clusters):
        subset = X_with_labels[X_with_labels["_cluster"] == cid].drop(columns=["_cluster"])
        avg    = subset.mean().round(3).to_dict()
        cluster_averages.append({
            "cluster":  cid,
            "size":     int(cluster_counts.get(cid, 0)),
            "averages": {k: round(float(v), 3) for k, v in avg.items()},
        })

    # ── Outlier table (original df rows where label == -1) ────────────────────
    orig = df.copy().iloc[:len(X)].reset_index(drop=True)
    orig["_cluster"] = labels
    outlier_df  = orig[orig["_cluster"] == -1].drop(columns=["_cluster"])
    outlier_rows = json.loads(outlier_df.head(20).to_json(orient="records"))

    return {
        "summary": (
            f"DBSCAN found {n_clusters} clusters and {n_noise} noise/outlier points "
            f"out of {len(X)} records. ε={eps}, minPts={min_samples} ({ms_source}). "
            f"Silhouette: {sil:.3f}."
        ),
        "metrics": {
            "Clusters found": str(n_clusters),
            "Noise points":   str(n_noise),
            "Records":        str(len(X)),
            "Noise %":        f"{n_noise/len(X)*100:.1f}%",
            "Silhouette":     f"{sil:.3f}",
            "ε (epsilon)":    str(eps),
            "minPts":         f"{min_samples} ({ms_source})",
            "Features used":  str(len(numeric_cols)),
        },
        "insights": [
            f"DBSCAN found {n_clusters} clusters without specifying k.",
            f"ε={eps}, minPts={min_samples} ({ms_source}).",
            f"Features used: {', '.join(numeric_cols)}",
            f"{n_noise} records ({n_noise/len(X)*100:.1f}%) are noise/outliers.",
            *[f"Cluster {c['cluster']}: {c['size']} records" for c in cluster_info[:5]],
            "High noise % — try increasing ε or reducing minPts." if n_noise/len(X) > 0.3 else "Noise level looks reasonable.",
        ],
        "cluster_info":     cluster_info,
        "cluster_averages": cluster_averages,
        "cluster_features": numeric_cols,
        "outlier_rows":     outlier_rows,
        "dbscan_config": {
            "features":    numeric_cols,
            "eps":         eps,
            "min_samples": min_samples,
        },
        "raw": {
            "technique":  "dbscan",
            "n_clusters": n_clusters,
            "n_noise":    n_noise,
            "silhouette": round(sil, 4),
            "eps":        eps,
            "min_pts":    min_samples,
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# UNSUPERVISED — PCA (Dimensionality Reduction)
# ─────────────────────────────────────────────────────────────────────────────
def run_pca(df: pd.DataFrame, ps: str) -> dict:
    df_clean, _ = _preprocess(df)
    numeric_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()

    if len(numeric_cols) < 3:
        return {"error": f"PCA requires at least 3 numeric columns. Found: {len(numeric_cols)}."}
    if len(df_clean) < 5:
        return {"error": "Need at least 5 rows for PCA."}

    X      = df_clean[numeric_cols].fillna(0)
    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X)

    n_comp = min(len(numeric_cols), len(X), 10)
    pca    = PCA(n_components=n_comp)
    pca.fit(X_sc)

    explained  = pca.explained_variance_ratio_
    cumulative = np.cumsum(explained)

    # Find components needed for 90% / 95% variance
    n_for_90 = int(np.argmax(cumulative >= 0.90)) + 1 if cumulative[-1] >= 0.90 else n_comp
    n_for_95 = int(np.argmax(cumulative >= 0.95)) + 1 if cumulative[-1] >= 0.95 else n_comp

    pc1_loading = sorted(zip(numeric_cols, np.abs(pca.components_[0])), key=lambda x: x[1], reverse=True)[:5]
    pc2_loading = sorted(zip(numeric_cols, np.abs(pca.components_[1])), key=lambda x: x[1], reverse=True)[:5] if n_comp >= 2 else []

    return {
        "summary": (
            f"PCA on {len(numeric_cols)} features. "
            f"{n_for_90} components explain 90% variance. "
            f"PC1 explains {explained[0]*100:.1f}%."
        ),
        "metrics": {
            "Original features": str(len(numeric_cols)),
            "Components (90%)":  str(n_for_90),
            "Components (95%)":  str(n_for_95),
            "PC1 variance":      f"{explained[0]*100:.1f}%",
            "PC2 variance":      f"{explained[1]*100:.1f}%" if n_comp >= 2 else "N/A",
            "Total components":  str(n_comp),
        },
        "insights": [
            f"PC1 explains {explained[0]*100:.1f}% — top feature: '{pc1_loading[0][0]}'",
            f"Top PC1 features: {', '.join(n for n, _ in pc1_loading[:3])}",
            *([ f"Top PC2 features: {', '.join(n for n, _ in pc2_loading[:3])}"] if pc2_loading else []),
            f"Reduce to {n_for_90} features to retain 90% of information.",
        ],
        "scree_data": {
            "components": list(range(1, n_comp + 1)),
            "explained":  [round(float(v)*100, 2) for v in explained],
            "cumulative": [round(float(v)*100, 2) for v in cumulative],
        },
        "loadings": {
            "PC1": [{"feature": n, "loading": round(float(l), 4)} for n, l in pc1_loading],
            "PC2": [{"feature": n, "loading": round(float(l), 4)} for n, l in pc2_loading],
        },
        "raw": {
            "technique":   "pca",
            "n_features":  len(numeric_cols),
            "n_for_90pct": n_for_90,
            "n_for_95pct": n_for_95,
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# UNSUPERVISED — ANOMALY DETECTION (Isolation Forest)
# ─────────────────────────────────────────────────────────────────────────────
def run_anomaly(df: pd.DataFrame, ps: str) -> dict:
    df_clean, _ = _preprocess(df)
    numeric_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()

    if len(numeric_cols) < 1:
        return {"error": "Anomaly detection requires at least 1 numeric column."}
    if len(df_clean) < 10:
        return {"error": "Need at least 10 rows for anomaly detection."}

    X = df_clean[numeric_cols].fillna(0)

    # Contamination: assume 5%, but cap it sensibly
    contamination = min(0.5, max(0.01, 5 / len(X)))

    iso    = IsolationForest(contamination=contamination, random_state=42)
    labels = iso.fit_predict(X)
    scores = iso.score_samples(X)

    anomaly_mask = labels == -1
    n_anomalies  = int(anomaly_mask.sum())
    anomaly_pct  = n_anomalies / len(X) * 100

    # Build anomaly rows from original df (not preprocessed, more readable)
    orig = df.copy().iloc[:len(X)].reset_index(drop=True)
    orig["_anomaly_score"] = scores
    orig["_is_anomaly"]    = anomaly_mask

    top_anomalies = (
        orig[orig["_is_anomaly"]]
        .nsmallest(10, "_anomaly_score")
        .drop(columns=["_is_anomaly"])
    )

    # Convert to JSON-safe records
    try:
        anomaly_rows = json.loads(top_anomalies.to_json(orient="records"))
    except Exception:
        anomaly_rows = []

    return {
        "summary": (
            f"Isolation Forest detected {n_anomalies} anomalies ({anomaly_pct:.1f}%) "
            f"out of {len(X)} records across {len(numeric_cols)} features."
        ),
        "metrics": {
            "Total records":  str(len(X)),
            "Anomalies":      str(n_anomalies),
            "Anomaly %":      f"{anomaly_pct:.1f}%",
            "Normal records": str(len(X) - n_anomalies),
            "Features used":  str(len(numeric_cols)),
        },
        "insights": [
            f"{n_anomalies} records flagged as anomalies.",
            f"Anomaly rate: {anomaly_pct:.1f}%.",
            f"Features analysed: {', '.join(numeric_cols[:5])}{'...' if len(numeric_cols) > 5 else ''}",
            "Lower _anomaly_score = more anomalous.",
            "Anomalies are rows that behave differently from the majority.",
        ],
        "anomaly_rows": anomaly_rows,
        "raw": {
            "technique":   "anomaly",
            "n_records":   len(X),
            "n_anomalies": n_anomalies,
            "anomaly_pct": round(anomaly_pct, 2),
        }
    }

# ─────────────────────────────────────────────────────────────────────────────
# SPACY NLP — loaded once at module level
# ─────────────────────────────────────────────────────────────────────────────
try:
    import spacy as _spacy
    _nlp = _spacy.load("en_core_web_md")
except Exception:
    _nlp = None   # graceful fallback — system works without it


def _nlp_score(ps: str, reference_phrases: list[str]) -> float:
    """
    Compute average cosine similarity between the problem statement and
    a list of reference phrases using spaCy word vectors.
    Returns 0.0 if spaCy is unavailable or vectors are empty.
    """
    if _nlp is None:
        return 0.0
    doc_ps = _nlp(ps.lower())
    if not doc_ps.has_vector:
        return 0.0
    scores = []
    for phrase in reference_phrases:
        doc_ref = _nlp(phrase.lower())
        if doc_ref.has_vector:
            scores.append(doc_ps.similarity(doc_ref))
    return float(sum(scores) / len(scores)) if scores else 0.0
# -----------------------------------------------------------------------------
# TECHNIQUE SUGGESTER  (spaCy NLP + data profiling)
# -----------------------------------------------------------------------------
_TECHNIQUE_PHRASES = {
    "classification": [
        "classify predict category label class",
        "detect fraud spam churn binary outcome",
        "identify type group yes no true false",
    ],
    "regression": [
        "predict estimate forecast numeric value",
        "price cost salary revenue sales amount",
        "continuous output score rate quantity",
    ],
    "decision_tree": [
        "explain rules interpretable decision why reason",
        "classify with transparent logic conditions",
        "understand which features drive outcome",
    ],
    "knn": [
        "similar records nearest neighbour compare",
        "classify based on similarity closest examples",
        "find most similar data points",
    ],
    "kmeans": [
        "segment group cluster profile customers",
        "find natural groups without labels",
        "partition data into similar clusters",
    ],
    "dbscan": [
        "density cluster irregular shape outlier noise",
        "find clusters of arbitrary shape",
        "group dense regions detect sparse outliers",
    ],
    "pca": [
        "reduce dimensions key features correlation",
        "compress variables find principal components",
        "identify most important features variance",
    ],
    "anomaly": [
        "detect anomaly outlier fraud unusual suspicious",
        "find abnormal rare defective records",
        "flag irregularities in data",
    ],
}

def suggest_techniques(problem_statement: str, file_data: bytes | None) -> dict:
    """
    Uses spaCy NLP cosine similarity to score each ML technique against the
    problem statement, combined with CSV data profiling for structural signals.
    """
    ps = problem_statement.strip()

    data_profile = {}
    if file_data:
        try:
            df           = _load_csv(file_data)
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            cat_cols     = df.select_dtypes(include="object").columns.tolist()
            high_card    = [c for c in cat_cols if df[c].nunique() > 50]
            low_card     = [c for c in cat_cols if df[c].nunique() <= 20]
            target       = df.columns[-1]
            target_num   = target in numeric_cols
            target_uniq  = int(df[target].nunique())
            data_profile = {
                "n_rows":           len(df),
                "n_cols":           len(df.columns),
                "numeric_cols":     numeric_cols,
                "cat_cols":         low_card,
                "high_card_cols":   high_card,
                "candidate_target": target,
                "target_is_numeric":target_num,
                "target_n_unique":  target_uniq,
                "target_is_binary": target_uniq == 2,
                "target_multiclass":2 < target_uniq <= 20,
                "has_enough_rows":  len(df) >= 30,
            }
        except Exception:
            data_profile = {}

    n_numeric     = len(data_profile.get("numeric_cols", []))
    target_num    = data_profile.get("target_is_numeric", False)
    target_binary = data_profile.get("target_is_binary", False)
    target_multi  = data_profile.get("target_multiclass", False)
    high_card     = data_profile.get("high_card_cols", [])

    nlp_scores = {
        tech: _nlp_score(ps, phrases)
        for tech, phrases in _TECHNIQUE_PHRASES.items()
    }

    def _build(tech, label, category, icon, use_when):
        nlp     = nlp_scores.get(tech, 0.0)
        nlp_pts = round(nlp * 6)
        data_pts = 0
        reasons  = []

        if tech in ("classification", "decision_tree", "knn"):
            if target_binary or target_multi:
                data_pts += 3
                reasons.append(f"Target column '{data_profile.get('candidate_target','')}' has {data_profile.get('target_n_unique','?')} classes.")
            if target_num and data_profile.get("target_n_unique", 0) > 20:
                data_pts -= 2
            if n_numeric >= 2:
                data_pts += 1
        elif tech == "regression":
            if target_num and data_profile.get("target_n_unique", 0) > 10:
                data_pts += 3
                reasons.append("Target appears numeric and continuous.")
            if target_binary:
                data_pts -= 2
            if n_numeric >= 2:
                data_pts += 1
        elif tech in ("kmeans", "dbscan"):
            if n_numeric >= 2:
                data_pts += 2
                reasons.append(f"{n_numeric} numeric features available.")
        elif tech == "pca":
            if n_numeric >= 3:
                data_pts += 2
                reasons.append(f"{n_numeric} numeric columns � PCA can find key components.")
            if len(high_card) > 0:
                data_pts += 1
        elif tech == "anomaly":
            if n_numeric >= 1:
                data_pts += 2

        total = nlp_pts + max(0, data_pts)
        if nlp >= 0.6:
            reasons.insert(0, f"Problem statement closely matches '{label}' intent (NLP similarity: {nlp:.2f}).")
        elif nlp >= 0.4:
            reasons.insert(0, f"Moderate NLP match with '{label}' (similarity: {nlp:.2f}).")
        elif nlp > 0:
            reasons.append(f"Weak NLP match (similarity: {nlp:.2f}).")
        if not reasons:
            reasons.append("Low match with current problem statement and data.")

        return {
            "technique":  tech,
            "label":      label,
            "category":   category,
            "icon":       icon,
            "score":      total,
            "nlp_sim":    round(nlp, 3),
            "confidence": _score_to_confidence(total),
            "reasons":    reasons[:4],
            "use_when":   use_when,
        }

    suggestions = [
        _build("classification", "Classification (Random Forest)",       "supervised",   "??", "Target column has discrete categories (Yes/No, labels)."),
        _build("regression",     "Regression (Ridge)",                    "supervised",   "??", "Target column is a continuous number (price, score, salary)."),
        _build("decision_tree",  "Decision Tree",                         "supervised",   "??", "You need interpretable if/else rules explaining predictions."),
        _build("knn",            "KNN Classifier",                        "supervised",   "??", "Classify records by finding the most similar labelled examples."),
        _build("kmeans",         "K-Means Clustering",                    "unsupervised", "??", "Discover natural segments in unlabelled data."),
        _build("dbscan",         "DBSCAN Clustering",                     "unsupervised", "??", "Find clusters of irregular shape and flag noise/outliers."),
        _build("pca",            "PCA (Dimensionality Reduction)",        "unsupervised", "??", "Identify the most informative features and reduce redundancy."),
        _build("anomaly",        "Anomaly Detection (Isolation Forest)",  "unsupervised", "??", "Flag suspicious, rare, or abnormal records."),
    ]
    suggestions.sort(key=lambda x: x["score"], reverse=True)

    summary = {}
    if data_profile:
        summary = {
            "rows":             data_profile.get("n_rows"),
            "columns":          data_profile.get("n_cols"),
            "numeric_cols":     data_profile.get("numeric_cols", []),
            "text_cols":        data_profile.get("cat_cols", []),
            "candidate_target": data_profile.get("candidate_target"),
        }

    return {
        "suggestions":  suggestions,
        "data_summary": summary,
        "nlp_scores":   {k: round(v, 3) for k, v in nlp_scores.items()},
    }
def _score_to_confidence(score: int) -> str:
    if score >= 5:  return "High"
    if score >= 3:  return "Medium"
    return "Low"


# ─────────────────────────────────────────────────────────────────────────────
# TECHNIQUE VALIDATOR
# Checks data structure + problem statement alignment only — no row limits.
# ─────────────────────────────────────────────────────────────────────────────
def validate_techniques(file_data: bytes | None, problem_statement: str = "") -> dict:
    """
    Returns {technique: {applicable: bool, reason: str}} for all 8 techniques.
    Applicability is based on:
      1. Whether the data has the right column types for the technique
      2. Whether the problem statement conflicts with the technique
    No minimum row counts are enforced.
    """
    all_techniques = ["classification", "regression", "decision_tree", "knn",
                      "kmeans", "dbscan", "pca", "anomaly"]
    out = {}

    # ── No file uploaded ──────────────────────────────────────────────────────
    if file_data is None:
        for t in all_techniques:
            out[t] = {"applicable": False, "reason": "Upload a CSV file to check applicability."}
        return out

    # ── Parse CSV ────────────────────────────────────────────────────────────
    try:
        df = _load_csv(file_data)
    except Exception as e:
        for t in all_techniques:
            out[t] = {"applicable": False, "reason": f"Could not read file: {e}"}
        return out

    # ── Profile raw data ──────────────────────────────────────────────────────
    n_cols        = len(df.columns)
    numeric_cols  = df.select_dtypes(include="number").columns.tolist()
    cat_cols      = df.select_dtypes(include="object").columns.tolist()
    n_numeric     = len(numeric_cols)

    # Preprocess to see what survives encoding
    try:
        df_clean, _ = _preprocess(df)
    except Exception:
        df_clean = df.copy()

    n_clean_cols    = len(df_clean.columns)
    n_clean_numeric = len(df_clean.select_dtypes(include="number").columns)

    # Infer candidate target: last column (or column mentioned in PS)
    ps = problem_statement.lower()
    target_col = df_clean.columns[-1]
    for col in df_clean.columns:
        if col.lower() in ps:
            target_col = col
            break

    target_is_numeric  = target_col in df_clean.select_dtypes(include="number").columns
    target_n_unique    = int(df_clean[target_col].nunique()) if target_col in df_clean.columns else 0
    target_is_cat      = not target_is_numeric or target_n_unique <= 20
    target_is_cont     = target_is_numeric and target_n_unique > 10

    # ── Problem statement signals ─────────────────────────────────────────────
    wants_predict   = any(k in ps for k in ["predict","forecast","classify","detect","determine","identify","estimate"])
    wants_numeric   = any(k in ps for k in ["price","cost","revenue","sales","score","salary","age","amount","value","count","rate","number","quantity"])
    wants_category  = any(k in ps for k in ["category","class","type","label","group","fraud","spam","churn","binary","yes","no"])
    wants_cluster   = any(k in ps for k in ["segment","group","cluster","pattern","profile","similar"])
    wants_anomaly   = any(k in ps for k in ["anomaly","outlier","fraud","unusual","abnormal","rare","fault","defect","suspicious"])
    wants_explain   = any(k in ps for k in ["explain","rule","why","reason","interpretable","decision"])
    wants_similar   = any(k in ps for k in ["similar","nearest","neighbour","neighbor","closest"])
    wants_reduce    = any(k in ps for k in ["reduce","dimension","compress","feature","key variable","important"])

    # PS conflicts: if user says "cluster" but also "predict" — not a hard block,
    # just note the mismatch. We only block when data structure makes it impossible.

    # ── CLASSIFICATION ────────────────────────────────────────────────────────
    if n_clean_cols < 2:
        out["classification"] = {"applicable": False, "reason": f"Need ≥2 columns — only {n_clean_cols} usable after preprocessing."}
    elif target_is_cont and not wants_category:
        out["classification"] = {"applicable": False, "reason": f"Target '{target_col}' appears continuous ({target_n_unique} unique values). Use Regression for continuous targets."}
    elif target_n_unique < 2:
        out["classification"] = {"applicable": False, "reason": f"Target '{target_col}' has only 1 unique value — nothing to classify."}
    elif wants_numeric and not wants_category:
        out["classification"] = {"applicable": False, "reason": f"Problem asks to predict a numeric value — Regression is more appropriate."}
    else:
        out["classification"] = {"applicable": True, "reason": f"✓ Target '{target_col}' has {target_n_unique} classes across {n_clean_cols-1} features."}

    # ── REGRESSION ────────────────────────────────────────────────────────────
    if n_clean_cols < 2:
        out["regression"] = {"applicable": False, "reason": f"Need ≥2 columns — only {n_clean_cols} usable."}
    elif not target_is_cont:
        if target_n_unique <= 5:
            out["regression"] = {"applicable": False, "reason": f"Target '{target_col}' has only {target_n_unique} unique values — looks categorical. Use Classification."}
        elif not target_is_numeric:
            out["regression"] = {"applicable": False, "reason": f"Target '{target_col}' is text/categorical. Regression needs a numeric target."}
        else:
            out["regression"] = {"applicable": True, "reason": f"✓ Numeric target '{target_col}' detected."}
    elif wants_category and not wants_numeric:
        out["regression"] = {"applicable": False, "reason": "Problem asks to predict a category — Classification is more appropriate."}
    else:
        out["regression"] = {"applicable": True, "reason": f"✓ Continuous numeric target '{target_col}' with {target_n_unique} distinct values."}

    # ── DECISION TREE ─────────────────────────────────────────────────────────
    if n_clean_cols < 2:
        out["decision_tree"] = {"applicable": False, "reason": f"Need ≥2 columns — only {n_clean_cols} usable."}
    elif target_is_cont and not wants_category:
        out["decision_tree"] = {"applicable": False, "reason": f"Target '{target_col}' looks continuous. Decision Tree classifies categories, not continuous values."}
    elif target_n_unique < 2:
        out["decision_tree"] = {"applicable": False, "reason": f"Target '{target_col}' has only 1 unique value."}
    elif wants_numeric and not wants_category and not wants_explain:
        out["decision_tree"] = {"applicable": False, "reason": "Problem asks for a numeric prediction — use Regression instead."}
    else:
        note = " Great for explaining decision rules." if wants_explain else ""
        out["decision_tree"] = {"applicable": True, "reason": f"✓ Target '{target_col}' has {target_n_unique} classes.{note}"}

    # ── KNN ───────────────────────────────────────────────────────────────────
    if n_clean_cols < 2:
        out["knn"] = {"applicable": False, "reason": f"Need ≥2 columns — only {n_clean_cols} usable."}
    elif target_n_unique < 2:
        out["knn"] = {"applicable": False, "reason": f"Target '{target_col}' has only 1 unique value."}
    elif target_is_cont and not wants_category:
        out["knn"] = {"applicable": False, "reason": f"Target '{target_col}' looks continuous. KNN classifies categories; use Regression for numeric targets."}
    elif n_clean_numeric < 1:
        out["knn"] = {"applicable": False, "reason": "KNN works on distances — needs at least 1 numeric feature."}
    else:
        note = " Ideal for similarity-based tasks." if wants_similar else ""
        out["knn"] = {"applicable": True, "reason": f"✓ {n_clean_numeric} numeric features for distance calculation.{note}"}

    # ── K-MEANS ───────────────────────────────────────────────────────────────
    if n_clean_numeric < 2:
        out["kmeans"] = {"applicable": False, "reason": f"K-Means needs ≥2 numeric columns — found {n_clean_numeric}."}
    elif wants_predict and not wants_cluster:
        out["kmeans"] = {"applicable": False, "reason": "Problem asks to predict a value — K-Means groups data without a target. Use a supervised technique."}
    else:
        note = " Matches your goal of segmentation." if wants_cluster else ""
        out["kmeans"] = {"applicable": True, "reason": f"✓ {n_clean_numeric} numeric features available for clustering.{note}"}

    # ── DBSCAN ────────────────────────────────────────────────────────────────
    if n_clean_numeric < 2:
        out["dbscan"] = {"applicable": False, "reason": f"DBSCAN needs ≥2 numeric columns — found {n_clean_numeric}."}
    elif wants_predict and not wants_cluster and not wants_anomaly:
        out["dbscan"] = {"applicable": False, "reason": "Problem asks to predict — DBSCAN is for clustering/outlier detection without a target."}
    else:
        note = " Especially useful for finding outliers." if wants_anomaly else ""
        out["dbscan"] = {"applicable": True, "reason": f"✓ {n_clean_numeric} numeric features available.{note}"}

    # ── PCA ───────────────────────────────────────────────────────────────────
    if n_clean_numeric < 3:
        out["pca"] = {"applicable": False, "reason": f"PCA needs ≥3 numeric columns to reduce — found {n_clean_numeric}."}
    elif wants_predict and not wants_reduce:
        out["pca"] = {"applicable": False, "reason": "PCA reduces dimensions — it doesn't predict. Consider using it before a supervised technique."}
    else:
        note = " Matches your goal of reducing features." if wants_reduce else ""
        out["pca"] = {"applicable": True, "reason": f"✓ {n_clean_numeric} numeric features — PCA can reduce to key components.{note}"}

    # ── ANOMALY DETECTION ─────────────────────────────────────────────────────
    if n_clean_numeric < 1:
        out["anomaly"] = {"applicable": False, "reason": "Anomaly detection needs ≥1 numeric column."}
    elif wants_cluster and not wants_anomaly and not wants_predict:
        out["anomaly"] = {"applicable": False, "reason": "Problem focuses on clustering groups — use K-Means or DBSCAN instead."}
    else:
        note = " Directly matches your problem statement." if wants_anomaly else ""
        out["anomaly"] = {"applicable": True, "reason": f"✓ {n_clean_numeric} numeric features for anomaly scoring.{note}"}

    return out



# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM INPUT PREDICTOR
# Retrains on stored CSV and predicts for a single user-supplied row.
# ─────────────────────────────────────────────────────────────────────────────
def predict_custom_input(
    technique:     str,
    file_data:     bytes,
    input_data:    dict,
    forced_target: str = "",
    max_depth:     int = 0,
    forced_k:      int = 0,
) -> dict:
    """
    Re-trains the chosen model on the full dataset, then predicts for input_data.
    Returns prediction, confidence/probability, and feature values used.
    """
    SUPPORTED = ("classification", "regression", "decision_tree", "knn")
    if technique not in SUPPORTED:
        return {"error": f"Custom prediction is only supported for: {', '.join(SUPPORTED)}"}

    try:
        df = _load_csv(file_data)
    except Exception as e:
        return {"error": f"Could not parse CSV: {e}"}

    df_clean, encoders = _preprocess(df)
    if df_clean.empty or len(df_clean.columns) < 2:
        return {"error": "Not enough usable columns after preprocessing."}

    # ── Determine target ──────────────────────────────────────────────────────
    if forced_target and forced_target in df_clean.columns:
        target = forced_target
    else:
        target = df_clean.columns[-1]

    X_train      = df_clean.drop(columns=[target])
    y_train      = df_clean[target]
    feature_cols = X_train.columns.tolist()

    # ── Build the input row ───────────────────────────────────────────────────
    row = {}
    missing_cols = []
    for col in feature_cols:
        raw_val = input_data.get(col, None)
        user_provided = raw_val is not None and str(raw_val).strip() != ""

        if user_provided:
            val = raw_val
            # Categorical column — label-encode the raw string value
            if col in encoders:
                le = encoders[col]
                val_str = str(val).strip()
                if val_str in le.classes_:
                    val = int(le.transform([val_str])[0])
                else:
                    # Closest match (case-insensitive) or fallback to most common
                    lower_classes = [c.lower() for c in le.classes_]
                    if val_str.lower() in lower_classes:
                        idx = lower_classes.index(val_str.lower())
                        val = int(le.transform([le.classes_[idx]])[0])
                    else:
                        val = int(le.transform([le.classes_[0]])[0])
            try:
                row[col] = float(val)
            except (ValueError, TypeError):
                row[col] = float(X_train[col].median())
                missing_cols.append(col)
        else:
            # User left this blank — fill with median
            row[col] = float(X_train[col].median())
            missing_cols.append(col)

    input_df = pd.DataFrame([row])[feature_cols]

    # ── Train model and predict ───────────────────────────────────────────────
    if technique in ("classification", "decision_tree", "knn"):
        if y_train.nunique() < 2:
            return {"error": f"Target '{target}' has only 1 class — cannot train classifier."}

        if technique == "classification":
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            pred_encoded  = model.predict(input_df)[0]
            probabilities = model.predict_proba(input_df)[0]
            classes       = model.classes_

        elif technique == "decision_tree":
            depth = max_depth if max_depth > 0 else 6
            model = DecisionTreeClassifier(max_depth=depth, random_state=42)
            model.fit(X_train, y_train)
            pred_encoded  = model.predict(input_df)[0]
            probabilities = model.predict_proba(input_df)[0]
            classes       = model.classes_

        elif technique == "knn":
            scaler   = StandardScaler()
            X_sc     = scaler.fit_transform(X_train)
            input_sc = scaler.transform(input_df)

            k = forced_k if forced_k > 0 else min(5, len(X_train) - 1)
            k = max(1, k)
            model = KNeighborsClassifier(n_neighbors=k)
            model.fit(X_sc, y_train)
            pred_encoded  = model.predict(input_sc)[0]
            probabilities = model.predict_proba(input_sc)[0]
            classes       = model.classes_

        # Decode prediction back to original label if it was encoded
        if target in encoders:
            le         = encoders[target]
            prediction = str(le.inverse_transform([int(pred_encoded)])[0])
            class_labels = [str(c) for c in le.inverse_transform(
                [int(c) for c in classes]
            )]
        else:
            prediction   = str(pred_encoded)
            class_labels = [str(c) for c in classes]

        # Build probability breakdown
        prob_breakdown = [
            {"class": lbl, "probability": round(float(p) * 100, 1)}
            for lbl, p in zip(class_labels, probabilities)
        ]
        prob_breakdown.sort(key=lambda x: x["probability"], reverse=True)
        confidence = round(float(max(probabilities)) * 100, 1)

        return {
            "prediction":    prediction,
            "confidence":    f"{confidence}%",
            "type":          "classification",
            "probabilities": prob_breakdown,
            "target_col":    target,
            "features_used": {col: row[col] for col in feature_cols},
            "missing_filled": missing_cols,
        }

    elif technique == "regression":
        scaler   = StandardScaler()
        X_sc     = scaler.fit_transform(X_train)
        input_sc = scaler.transform(input_df)

        model = Ridge(alpha=1.0)
        model.fit(X_sc, y_train)
        prediction = float(model.predict(input_sc)[0])

        # Feature contributions (coefficient × scaled value)
        contributions = sorted(
            [
                {
                    "feature":      col,
                    "coefficient":  round(float(model.coef_[i]), 4),
                    "contribution": round(float(model.coef_[i] * input_sc[0][i]), 4),
                }
                for i, col in enumerate(feature_cols)
            ],
            key=lambda x: abs(x["contribution"]),
            reverse=True
        )[:6]

        return {
            "prediction":    round(prediction, 4),
            "type":          "regression",
            "target_col":    target,
            "contributions": contributions,
            "features_used": {col: row[col] for col in feature_cols},
            "missing_filled": missing_cols,
        }


# ─────────────────────────────────────────────────────────────────────────────
# CLUSTER PREDICTOR — assigns custom input to a cluster
# ─────────────────────────────────────────────────────────────────────────────
def predict_cluster_input(
    technique:       str,
    file_data:       bytes,
    input_data:      dict,
    selected_features: list = None,
    forced_k:        int   = 0,
    eps:             float = 0.5,
    forced_min_pts:  int   = 0,
) -> dict:
    """
    Retrains K-Means or DBSCAN on the full dataset, then assigns
    a single custom input row to its nearest cluster.
    """
    if technique not in ("kmeans", "dbscan"):
        return {"error": "Cluster prediction is only available for K-Means and DBSCAN."}

    try:
        df = _load_csv(file_data)
    except Exception as e:
        return {"error": f"Could not parse CSV: {e}"}

    df_clean, _ = _preprocess(df)
    all_numeric  = df_clean.select_dtypes(include=[np.number]).columns.tolist()

    if selected_features:
        numeric_cols = [f for f in selected_features if f in all_numeric]
        if len(numeric_cols) < 2:
            return {"error": f"Need ≥2 valid numeric features. Available: {', '.join(all_numeric)}"}
    else:
        numeric_cols = all_numeric

    if len(numeric_cols) < 2:
        return {"error": "Need at least 2 numeric columns for clustering."}

    X      = df_clean[numeric_cols].fillna(0)
    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X)

    # ── Build input row ───────────────────────────────────────────────────────
    row = {}
    missing = []
    for col in numeric_cols:
        val = input_data.get(col, "")
        if val != "" and val is not None:
            try:
                row[col] = float(val)
            except (ValueError, TypeError):
                row[col] = float(X[col].median())
                missing.append(col)
        else:
            row[col] = float(X[col].median())
            missing.append(col)

    input_arr = scaler.transform([[row[c] for c in numeric_cols]])

    if technique == "kmeans":
        # ── K-Means ───────────────────────────────────────────────────────────
        max_k = min(8, len(X) - 1)
        inertias = []
        for k in range(2, max_k + 1):
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            km.fit(X_sc)
            inertias.append(km.inertia_)

        if forced_k >= 2 and forced_k <= max_k:
            best_k = forced_k
        else:
            diffs  = [inertias[i] - inertias[i+1] for i in range(len(inertias)-1)]
            best_k = diffs.index(max(diffs)) + 2 if diffs else 3
            best_k = min(best_k, max_k)

        km     = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        labels = km.fit_predict(X_sc)
        pred_cluster = int(km.predict(input_arr)[0])

        # Distance to each cluster centre
        centres     = km.cluster_centers_
        distances   = [
            {"cluster": int(i), "distance": round(float(np.linalg.norm(input_arr[0] - centres[i])), 4)}
            for i in range(best_k)
        ]
        distances.sort(key=lambda x: x["distance"])

        # Cluster averages for context
        X_with_labels = X.copy()
        X_with_labels["_cluster"] = labels
        cluster_avg = X_with_labels[X_with_labels["_cluster"] == pred_cluster].drop(columns=["_cluster"]).mean().round(3).to_dict()

        return {
            "predicted_cluster": pred_cluster,
            "technique":         "kmeans",
            "distances":         distances,
            "cluster_averages":  {k: round(float(v), 3) for k, v in cluster_avg.items()},
            "input_used":        {c: row[c] for c in numeric_cols},
            "missing_filled":    missing,
            "note": f"Assigned to Cluster {pred_cluster} — closest cluster centre.",
        }

    else:
        # ── DBSCAN — find nearest cluster using training labels ────────────────
        min_samples = forced_min_pts if forced_min_pts > 0 else max(2, min(5, len(X) // 10))
        db          = DBSCAN(eps=eps, min_samples=min_samples)
        labels      = db.fit_predict(X_sc)

        n_clusters = len(set(labels)) - (1 if -1 in set(labels) else 0)

        if n_clusters == 0:
            return {
                "predicted_cluster": -1,
                "technique":         "dbscan",
                "note":              "No clusters were formed with current ε and minPts. The point would be noise.",
                "input_used":        {c: row[c] for c in numeric_cols},
                "missing_filled":    missing,
            }

        # Calculate mean distance to each cluster's members
        cluster_dists = []
        for cid in range(n_clusters):
            cluster_pts = X_sc[labels == cid]
            if len(cluster_pts) == 0:
                continue
            dists  = np.linalg.norm(cluster_pts - input_arr, axis=1)
            avg_d  = float(dists.mean())
            min_d  = float(dists.min())
            cluster_dists.append({"cluster": cid, "avg_distance": round(avg_d, 4), "min_distance": round(min_d, 4)})

        cluster_dists.sort(key=lambda x: x["min_distance"])
        nearest = cluster_dists[0]
        pred_cluster = nearest["cluster"]

        # Is it within eps of a core point? (noise check)
        nearest_pt_dist = nearest["min_distance"]
        is_noise = nearest_pt_dist > eps

        X_with_labels = X.copy()
        X_with_labels["_cluster"] = labels
        cluster_avg = X_with_labels[X_with_labels["_cluster"] == pred_cluster].drop(columns=["_cluster"]).mean().round(3).to_dict()

        return {
            "predicted_cluster": -1 if is_noise else pred_cluster,
            "technique":         "dbscan",
            "is_noise":          is_noise,
            "cluster_distances": cluster_dists[:5],
            "cluster_averages":  {k: round(float(v), 3) for k, v in cluster_avg.items()},
            "input_used":        {c: row[c] for c in numeric_cols},
            "missing_filled":    missing,
            "note": (
                "This point would be classified as noise/outlier — it's too far from any cluster core."
                if is_noise else
                f"Assigned to Cluster {pred_cluster} — nearest cluster (min distance: {nearest_pt_dist:.3f})."
            ),
        }
