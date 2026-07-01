import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  FaArrowLeft,
  FaUpload,
  FaPlay,
  FaSpinner,
  FaChartBar,
  FaFileAlt,
  FaBrain,
  FaCheckCircle,
  FaFileCsv,
  FaDownload,
  FaTrash,
  FaSync,
  FaRedo,
  FaLightbulb,
  FaChevronDown,
  FaChevronUp,
  FaMagic,
} from "react-icons/fa";
import "../styles/ProjectPage.css";

const API_URL = "http://localhost:8000";

// ── Auth helpers ──────────────────────────────────────────────────────────────
function authHeaders() {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// Role permission helpers
const CAN = {
  uploadData:  ["admin", "developer"],
  runAnalysis: ["admin", "developer", "guest_user"],
  saveData:    ["admin", "developer"],
};
function canDo(action, role) {
  return CAN[action]?.includes(role) ?? false;
}

const TECHNIQUES = {
  supervised: [
    { value: "classification", label: "Classification",   desc: "Predict categories — Random Forest", icon: "🎯" },
    { value: "regression",     label: "Regression",       desc: "Predict numeric values — Ridge",     icon: "📈" },
    { value: "decision_tree",  label: "Decision Tree",    desc: "Rule-based classification tree",      icon: "🌳" },
    { value: "knn",            label: "KNN",              desc: "K-Nearest Neighbours classifier",     icon: "📍" },
  ],
  unsupervised: [
    { value: "kmeans",  label: "K-Means Clustering", desc: "Group similar records automatically",     icon: "🔵" },
    { value: "dbscan",  label: "DBSCAN",             desc: "Density-based clustering + outliers",    icon: "🟣" },
    { value: "pca",     label: "PCA",                desc: "Reduce dimensions, find key patterns",   icon: "🔺" },
    { value: "anomaly", label: "Anomaly Detection",  desc: "Find unusual records — Isolation Forest", icon: "⚠️" },
  ],
};

function formatBytes(bytes) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function SmartInput({ col, colInfo, value, onChange }) {
  const info = colInfo?.[col];
  if (!info) {
    return (
      <input
        type="text"
        className="custom-input-box"
        placeholder="value"
        value={value ?? ""}
        onChange={e => onChange(e.target.value)}
      />
    );
  }
  if (info.type === "categorical" && info.values?.length > 0) {
    return (
      <select
        className="custom-input-box supervised-select"
        value={value ?? ""}
        onChange={e => onChange(e.target.value)}
      >
        <option value="">— select —</option>
        {info.values.map(v => (
          <option key={v} value={v}>{v}</option>
        ))}
      </select>
    );
  }
  if (info.type === "numeric") {
    return (
      <input
        type="number"
        className="custom-input-box"
        placeholder={`${info.min} – ${info.max} (avg ${info.mean})`}
        value={value ?? ""}
        onChange={e => onChange(e.target.value)}
        step="any"
      />
    );
  }
  // free text
  return (
    <input
      type="text"
      className="custom-input-box"
      placeholder="value"
      value={value ?? ""}
      onChange={e => onChange(e.target.value)}
    />
  );
}

function ProjectPage() {
  const { id }       = useParams();
  const navigate     = useNavigate();
  const role         = localStorage.getItem("role") || "guest_user";
  const fileInputRef = useRef();

  // ── State ─────────────────────────────────────────────────────────────────
  const [project,            setProject]            = useState(null);
  const [loading,            setLoading]            = useState(true);
  const [problemStatement,   setProblemStatement]   = useState("");
  const [selectedTechnique,  setSelectedTechnique]  = useState("");
  const [mlTab,              setMlTab]              = useState("supervised"); // "supervised" | "unsupervised"
  const [uploadedFile,       setUploadedFile]       = useState(null);
  const [savedFileName,      setSavedFileName]      = useState("");
  const [savedFileSize,      setSavedFileSize]      = useState(null);
  const [savedFileId,        setSavedFileId]        = useState(null);
  const [uploading,          setUploading]          = useState(false);
  const [uploadDone,         setUploadDone]         = useState(false);
  const [analysing,          setAnalysing]          = useState(false);
  const [results,            setResults]            = useState(null);
  const [savingPS,           setSavingPS]           = useState(false);
  const [psSaved,            setPsSaved]            = useState(false);
  const [lastAnalysedAt,     setLastAnalysedAt]     = useState(null);
  const [showRestartDialog,  setShowRestartDialog]  = useState(false);
  const [restarting,         setRestarting]         = useState(false);

  // Suggestion panel
  const [suggestions,        setSuggestions]        = useState([]);
  const [dataSummary,        setDataSummary]        = useState(null);
  const [suggesting,         setSuggesting]         = useState(false);
  const [expandedSug,        setExpandedSug]        = useState(null);

  // PCA dimension reducer
  const [pcaDimensions,      setPcaDimensions]      = useState(2);
  const [pcaGenerating,      setPcaGenerating]      = useState(false);

  // Technique validity
  const [validity,           setValidity]           = useState({});
  const [validating,         setValidating]         = useState(false);

  // Supervised technique custom config
  const [supervisedTarget,   setSupervisedTarget]   = useState("");   // chosen dependent variable
  const [treeMaxDepth,       setTreeMaxDepth]       = useState(0);    // 0 = default (6)
  const [knnK,               setKnnK]               = useState(0);    // 0 = auto

  // Custom prediction
  const [customInputs,       setCustomInputs]       = useState({});   // {colName: value}
  const [predicting,         setPredicting]         = useState(false);
  const [predictionResult,   setPredictionResult]   = useState(null);

  // Cluster custom prediction (kmeans / dbscan)
  const [clusterInputs,      setClusterInputs]      = useState({});
  const [clusterPredicting,  setClusterPredicting]  = useState(false);
  const [clusterPredResult,  setClusterPredResult]  = useState(null);
  const [kmeansFeatures,     setKmeansFeatures]     = useState([]);
  const [kmeansK,            setKmeansK]            = useState(0);    // 0 = auto

  // DBSCAN custom config
  const [dbscanFeatures,     setDbscanFeatures]     = useState([]);
  const [dbscanEps,          setDbscanEps]          = useState(0.5);
  const [dbscanMinPts,       setDbscanMinPts]       = useState(0);   // 0 = auto

  // Available numeric columns from uploaded CSV
  const [csvNumericCols,     setCsvNumericCols]     = useState([]);
  const [csvAllCols,         setCsvAllCols]         = useState([]);
  const [csvColInfo,         setCsvColInfo]         = useState({});  // {col: {type, values/min/max/mean}}

  // ── Load project ──────────────────────────────────────────────────────────
  useEffect(() => { fetchProject(); }, [id]);

  const fetchProject = async () => {
    try {
      const res  = await fetch(`${API_URL}/projects/${id}`, {
        headers: authHeaders(),
      });
      if (res.status === 401) { navigate("/"); return; }
      const data = await res.json();
      if (data.project) {
        const p = data.project;
        setProject(p);
        setProblemStatement(p.problemStatement || "");
        setSelectedTechnique(p.lastTechnique   || "");
        setResults(p.lastResults               || null);
        setLastAnalysedAt(p.lastAnalysedAt     || null);
        setSavedFileName(p.fileName            || "");
        setSavedFileSize(p.fileSize            || null);
        setSavedFileId(p.fileId                || null);
        // Restore DBSCAN config from last run if available
        if (p.lastResults?.dbscan_config) {
          setDbscanFeatures(p.lastResults.dbscan_config.features || []);
          setDbscanEps(p.lastResults.dbscan_config.eps ?? 0.5);
          setDbscanMinPts(p.lastResults.dbscan_config.min_samples ?? 0);
        }
        // Restore K-Means config from last run if available
        if (p.lastResults?.kmeans_config) {
          setKmeansFeatures(p.lastResults.kmeans_config.features || []);
          setKmeansK(p.lastResults.kmeans_config.k || 0);
        }
        // Restore supervised config
        if (p.lastResults?.supervised_config) {
          setSupervisedTarget(p.lastResults.supervised_config.target || "");
          setTreeMaxDepth(p.lastResults.supervised_config.max_depth || 0);
          setKnnK(p.lastResults.supervised_config.k || 0);
        }
      }
    } catch (err) {
      console.error("Error fetching project:", err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch columns after project loads if file exists
  useEffect(() => {
    if (savedFileId) fetchCsvProfile();
  }, [savedFileId]);

  // ── Save problem statement ────────────────────────────────────────────────
  const handleSaveProblemStatement = async () => {
    setSavingPS(true);
    try {
      const form = new FormData();
      form.append("problemStatement", problemStatement);
      if (selectedTechnique) form.append("technique", selectedTechnique);
      await fetch(`${API_URL}/save-problem/admin/${id}`, {
        method: "PUT",
        headers: { ...authHeaders() },
        body: form,
      });
      setPsSaved(true);
      setTimeout(() => setPsSaved(false), 2500);
    } catch (err) {
      console.error("Error saving:", err);
    } finally {
      setSavingPS(false);
    }
  };

  // ── Upload file ───────────────────────────────────────────────────────────
  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploadedFile(file);
    setUploading(true);
    setUploadDone(false);
    try {
      const form = new FormData();
      form.append("file", file);
      const res  = await fetch(`${API_URL}/upload/admin/${id}`, {
        method: "POST",
        headers: { ...authHeaders() },
        body: form,
      });
      const data = await res.json();
      if (data.success) {
        setSavedFileName(data.fileName);
        setSavedFileSize(data.fileSize);
        setSavedFileId(data.fileId);
        setUploadDone(true);
        setTimeout(() => setUploadDone(false), 2500);
        // Re-validate techniques now that file has changed
        await validateTechniques();
        // Refresh column list for K-Means
        await fetchCsvProfile();
      }
    } catch (err) {
      console.error("Upload error:", err);
      alert("File upload failed.");
    } finally {
      setUploading(false);
    }
  };

  // ── Download / Remove file ────────────────────────────────────────────────
  const handleDownload = () => {
    if (savedFileId) window.open(`${API_URL}/download/${role}/${savedFileId}`, "_blank");
  };

  const handleRemoveFile = async () => {
    await fetch(`${API_URL}/projects/${id}`, {
      method:  "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ fileName: "", fileId: "", fileSize: 0 }),
    });
    setSavedFileName("");
    setSavedFileId(null);
    setSavedFileSize(null);
    setUploadedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // ── Predict cluster for custom input ─────────────────────────────────────
  const handlePredictCluster = async () => {
    setClusterPredicting(true);
    setClusterPredResult(null);
    try {
      const form = new FormData();
      form.append("technique",    selectedTechnique);
      form.append("custom_input", JSON.stringify(clusterInputs));
      if (selectedTechnique === "kmeans") {
        if (kmeansFeatures.length > 0) form.append("kmeans_features", kmeansFeatures.join(","));
        if (kmeansK > 0) form.append("kmeans_k", kmeansK);
      } else if (selectedTechnique === "dbscan") {
        if (dbscanFeatures.length > 0) form.append("dbscan_features", dbscanFeatures.join(","));
        form.append("dbscan_eps", dbscanEps);
        if (dbscanMinPts > 0) form.append("dbscan_min_pts", dbscanMinPts);
      }
      const res  = await fetch(`${API_URL}/predict-cluster/admin/${id}`, {
        method: "POST",
        headers: { ...authHeaders() },
        body: form,
      });
      const data = await res.json();
      setClusterPredResult(data);
    } catch (err) {
      setClusterPredResult({ error: "Cluster prediction failed." });
    } finally {
      setClusterPredicting(false);
    }
  };

  // ── Predict on custom input ───────────────────────────────────────────────
  const handlePredict = async () => {
    setPredicting(true);
    setPredictionResult(null);
    try {
      const form = new FormData();
      form.append("technique",    selectedTechnique);
      form.append("custom_input", JSON.stringify(customInputs));
      if (supervisedTarget)  form.append("target_col",     supervisedTarget);
      if (treeMaxDepth > 0)  form.append("tree_max_depth", treeMaxDepth);
      if (knnK > 0)          form.append("knn_k",          knnK);

      const res  = await fetch(`${API_URL}/predict-custom/admin/${id}`, {
        method: "POST",
        headers: { ...authHeaders() },
        body: form,
      });
      const data = await res.json();
      setPredictionResult(data);
    } catch (err) {
      console.error("Prediction error:", err);
      setPredictionResult({ error: "Prediction failed. Make sure the backend is running." });
    } finally {
      setPredicting(false);
    }
  };

  // ── Fetch CSV column profile (for DBSCAN feature selector) ─────────────
  const fetchCsvProfile = async () => {
    try {
      const res  = await fetch(`${API_URL}/csv-profile/admin/${id}`, {
        headers: authHeaders(),
      });
      const data = await res.json();
      if (data.numeric_cols?.length) {
        setCsvNumericCols(data.numeric_cols);
        setDbscanFeatures(data.numeric_cols);  // default: all selected
        setKmeansFeatures(data.numeric_cols);  // default: all selected
      }
      if (data.all_cols?.length) {
        setCsvAllCols(data.all_cols);
      }
      if (data.col_info) {
        setCsvColInfo(data.col_info);
      }
    } catch (err) {
      console.error("CSV profile error:", err);
    }
  };

  // ── PCA — generate and download reduced CSV ──────────────────────────────
  const handlePcaGenerate = async () => {
    setPcaGenerating(true);
    try {
      const form = new FormData();
      form.append("n_components", pcaDimensions);

      const res = await fetch(`${API_URL}/pca-reduce/admin/${id}`, {
        method: "POST",
        headers: { ...authHeaders() },
        body: form,
      });

      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Failed to generate reduced data.");
        return;
      }

      // Trigger browser download
      const blob     = await res.blob();
      const url      = window.URL.createObjectURL(blob);
      const a        = document.createElement("a");
      const filename = res.headers.get("Content-Disposition")
        ?.split("filename=")[1] || `pca_${pcaDimensions}components.csv`;
      a.href     = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PCA generate error:", err);
      alert("Failed to generate reduced data.");
    } finally {
      setPcaGenerating(false);
    }
  };

  // ── Validate which techniques are applicable ─────────────────────────────
  const validateTechniques = async () => {
    setValidating(true);
    try {
      const form = new FormData();
      form.append("problem_statement", problemStatement);
      const res  = await fetch(`${API_URL}/validate-techniques/admin/${id}`, {
        method: "POST",
        headers: { ...authHeaders() },
        body: form,
      });
      const data = await res.json();
      setValidity(data);
    } catch (err) {
      console.error("Validation error:", err);
    } finally {
      setValidating(false);
    }
  };

  // ── Get suggestions ───────────────────────────────────────────────────────
  const handleSuggest = async () => {
    setSuggesting(true);
    setSuggestions([]);
    try {
      const form = new FormData();
      form.append("problem_statement", problemStatement);
      const res  = await fetch(`${API_URL}/suggest/admin/${id}`, {
        method: "POST",
        headers: { ...authHeaders() },
        body: form,
      });
      const data = await res.json();
      setSuggestions(data.suggestions || []);
      setDataSummary(data.data_summary || null);
    } catch (err) {
      console.error("Suggest error:", err);
    } finally {
      setSuggesting(false);
    }
  };

  // ── Run analysis ──────────────────────────────────────────────────────────
  const handleRunAnalysis = async () => {
    if (!problemStatement.trim()) { alert("Please enter a problem statement first."); return; }
    if (!selectedTechnique)       { alert("Please select an ML technique.");          return; }
    setAnalysing(true);
    setResults(null);
    try {
      const form = new FormData();
      form.append("problem_statement", problemStatement);
      form.append("technique", selectedTechnique);
      // DBSCAN custom params
      if (selectedTechnique === "dbscan") {
        if (dbscanFeatures.length > 0) form.append("dbscan_features", dbscanFeatures.join(","));
        form.append("dbscan_eps", dbscanEps);
        if (dbscanMinPts > 0) form.append("dbscan_min_pts", dbscanMinPts);
      }
      // K-Means custom params
      if (selectedTechnique === "kmeans") {
        if (kmeansFeatures.length > 0) form.append("kmeans_features", kmeansFeatures.join(","));
        if (kmeansK > 0) form.append("kmeans_k", kmeansK);
      }
      // Supervised custom params
      if (["classification","regression","decision_tree","knn"].includes(selectedTechnique)) {
        if (supervisedTarget) form.append("target_col", supervisedTarget);
        if (selectedTechnique === "decision_tree" && treeMaxDepth > 0)
          form.append("tree_max_depth", treeMaxDepth);
        if (selectedTechnique === "knn" && knnK > 0)
          form.append("knn_k", knnK);
      }
      const res  = await fetch(`${API_URL}/analyse/admin/${id}`, {
        method: "POST",
        headers: { ...authHeaders() },
        body: form,
      });
      const data = await res.json();
      setResults(data);
      setLastAnalysedAt(new Date().toISOString());
    } catch (err) {
      console.error("Analysis error:", err);
      setResults({ error: "Analysis failed. Make sure the backend is running." });
    } finally {
      setAnalysing(false);
    }
  };

  // ── Refresh — clears only results, keeps everything else ─────────────────
  const handleRefresh = async () => {
    await fetch(`${API_URL}/projects/${id}`, {
      method:  "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ lastResults: {}, lastAnalysedAt: "" }),
    });
    setResults(null);
    setLastAnalysedAt(null);
    setPredictionResult(null);
    setClusterPredResult(null);
  };

  const handleRestart = async () => {
    setRestarting(true);
    try {
      if (savedFileId) await handleRemoveFile();

      await fetch(`${API_URL}/projects/${id}`, {
        method:  "PUT",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          problemStatement: "",
          lastTechnique:    "",
          lastResults:      {},
          lastAnalysedAt:   "",
          fileName:         "",
          fileId:           "",
          fileSize:         0,
        }),
      });

      setProblemStatement("");
      setSelectedTechnique("");
      setResults(null);
      setLastAnalysedAt(null);
      setSavedFileName("");
      setSavedFileId(null);
      setSavedFileSize(null);
      setUploadedFile(null);
      setPredictionResult(null);
      setClusterPredResult(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      console.error("Restart error:", err);
    } finally {
      setRestarting(false);
      setShowRestartDialog(false);
    }
  };

  const backPath = "/dashboard";

  // ── Loading ───────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="project-page-loading">
        <FaSpinner className="spin" />
        <p>Loading project...</p>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="project-page">

      {/* ── Restart Confirmation Dialog ────────────────────────────────────── */}
      {showRestartDialog && (
        <div className="dialog-overlay" onClick={() => setShowRestartDialog(false)}>
          <div className="dialog-box" onClick={(e) => e.stopPropagation()}>
            <div className="dialog-header">
              <h3>Restart project?</h3>
            </div>
            <div className="dialog-body">
              <p>This will clear the <strong>problem statement</strong>, <strong>uploaded file</strong>, and all <strong>analysis results</strong> for this project.</p>
              <p className="dialog-warning">This action cannot be undone.</p>
            </div>
            <div className="dialog-actions">
              <button className="dialog-btn cancel-btn" onClick={() => setShowRestartDialog(false)}>
                Cancel
              </button>
              <button className="dialog-btn restart-confirm-btn" onClick={handleRestart} disabled={restarting}>
                {restarting ? <><FaSpinner className="spin" /> Restarting...</> : <><FaRedo /> Yes, Restart</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Header ────────────────────────────────────────────────────────── */}
      <header className="project-header">
        <button className="back-btn" onClick={() => navigate(backPath)}>
          <FaArrowLeft /> Back
        </button>
        <div className="project-header-title">
          <FaBrain className="header-brain-icon" />
          <span>{project?.name || "Project"}</span>
        </div>
        <div className="header-right-actions">
          {lastAnalysedAt && (
            <span className="last-analysed">
              Last analysed: {new Date(lastAnalysedAt).toLocaleString()}
            </span>
          )}
          <button
            className="restart-btn"
            onClick={() => setShowRestartDialog(true)}
            title="Reset project to default state"
          >
            <FaRedo /> Restart
          </button>
        </div>
      </header>

      <div className="project-layout">

        {/* ── SIDEBAR ───────────────────────────────────────────────────── */}
        <aside className="project-sidebar">
          {/* Problem Statement */}
          <div className="sidebar-card">
            <div className="sidebar-card-title"><FaFileAlt /> Problem Statement</div>
            <textarea
              className="problem-textarea"
              placeholder={"Describe the problem you want to analyse...\n\ne.g. 'Predict customer churn based on usage patterns'"}
              value={problemStatement}
              onChange={(e) => setProblemStatement(e.target.value)}
              rows={7}
            />
            <button
              className={`save-btn ${psSaved ? "saved" : ""}`}
              onClick={handleSaveProblemStatement}
              disabled={savingPS || !canDo("saveData", role)}
              title={!canDo("saveData", role) ? "Guest users cannot save changes" : ""}
            >
              {psSaved
                ? <><FaCheckCircle /> Saved!</>
                : savingPS
                  ? <><FaSpinner className="spin" /> Saving...</>
                  : "Save"}
            </button>
          </div>

          {/* Data File */}
          <div className="sidebar-card">
            <div className="sidebar-card-title"><FaUpload /> Data File</div>
            {savedFileName ? (              <div className="saved-file-info">
                <FaFileCsv className="file-type-icon" />
                <div className="file-details">
                  <span className="file-name">{savedFileName}</span>
                  {savedFileSize && <span className="file-size">{formatBytes(savedFileSize)}</span>}
                  <span className="file-status">✅ Saved to database</span>
                </div>
                <div className="file-actions">
                  <button className="file-action-btn download-btn" onClick={handleDownload} title="Download"><FaDownload /></button>
                  {canDo("uploadData", role) && (
                    <button className="file-action-btn remove-btn" onClick={handleRemoveFile} title="Remove"><FaTrash /></button>
                  )}
                </div>
              </div>
            ) : canDo("uploadData", role) ? (
              <label className="upload-area">
                <input type="file" accept=".csv,.xlsx,.json,.txt" onChange={handleFileChange} ref={fileInputRef} hidden />
                <div className={`upload-inner ${uploading ? "uploading" : ""}`}>
                  {uploading   ? <FaSpinner className="upload-icon spin" />
                   : uploadDone ? <FaCheckCircle className="upload-icon done" />
                   :              <FaUpload className="upload-icon" />}
                  <span className="upload-label">
                    {uploading ? "Uploading..." : uploadDone ? "Uploaded!" : "Click to upload CSV / Excel / JSON"}
                  </span>
                  <span className="upload-hint">Max 10 MB · Stored in database</span>
                </div>
              </label>
            ) : (
              <div className="upload-inner" style={{cursor:"default",opacity:0.6}}>
                <FaUpload className="upload-icon" />
                <span className="upload-label">No file uploaded</span>
                <span className="upload-hint">Guest users cannot upload files</span>
              </div>
            )}
            {savedFileName && canDo("uploadData", role) && (
              <label className="replace-file-label">
                <input type="file" accept=".csv,.xlsx,.json,.txt" onChange={handleFileChange} ref={fileInputRef} hidden />
                <span className="replace-file-btn">
                  {uploading ? <FaSpinner className="spin" /> : <FaUpload />}
                  {uploading ? " Uploading..." : " Replace file"}
                </span>
              </label>
            )}
          </div>

          {/* ML Technique */}
          <div className="sidebar-card">
            <div className="sidebar-card-title"><FaBrain /> ML Technique</div>

            {/* Tabs */}
            <div className="ml-tabs">
              <button
                className={`ml-tab ${mlTab === "supervised" ? "active" : ""}`}
                onClick={() => setMlTab("supervised")}
              >
                Supervised
              </button>
              <button
                className={`ml-tab ${mlTab === "unsupervised" ? "active" : ""}`}
                onClick={() => setMlTab("unsupervised")}
              >
                Unsupervised
              </button>
            </div>

            <div className="technique-list">
              {TECHNIQUES[mlTab].map((t) => (
                <button
                  key={t.value}
                  className={`technique-btn ${selectedTechnique === t.value ? "active" : ""}`}
                  onClick={() => setSelectedTechnique(t.value)}
                >
                  <span className="technique-icon">{t.icon}</span>
                  <span className="technique-text">
                    <span className="technique-label">{t.label}</span>
                    <span className="technique-desc">{t.desc}</span>
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Supervised config panel */}
          {["classification","regression","decision_tree","knn"].includes(selectedTechnique)
           && csvNumericCols.length > 0 && (
            <div className="sidebar-card supervised-config-card">
              <div className="sidebar-card-title">⚙️ Model Settings</div>

              {/* Target / Dependent Variable */}
              <div className="kmeans-section">
                <p className="kmeans-section-label">Dependent variable (target):</p>
                <select
                  className="supervised-select"
                  value={supervisedTarget}
                  onChange={(e) => setSupervisedTarget(e.target.value)}
                >
                  <option value="">Auto-detect</option>
                  {/* Show all columns from the CSV as options */}
                  {[...csvNumericCols,
                    ...csvAllCols.filter(c => !csvNumericCols.includes(c))
                  ].map(col => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
                <p className="kmeans-k-hint">
                  {supervisedTarget
                    ? `Predicting: "${supervisedTarget}"`
                    : "Auto: last column or keyword match from problem statement"}
                </p>
              </div>

              {/* Max Depth — Decision Tree only */}
              {selectedTechnique === "decision_tree" && (
                <div className="kmeans-section">
                  <p className="kmeans-section-label">Max tree depth:</p>
                  <div className="kmeans-k-row">
                    <button className="pca-dim-btn"
                      onClick={() => setTreeMaxDepth(d => Math.max(0, d - 1))}
                      disabled={treeMaxDepth <= 0}>−</button>
                    <span className="kmeans-k-value">
                      {treeMaxDepth === 0 ? "Auto" : treeMaxDepth}
                    </span>
                    <button className="pca-dim-btn"
                      onClick={() => setTreeMaxDepth(d => d === 0 ? 2 : Math.min(20, d + 1))}
                      disabled={treeMaxDepth >= 20}>+</button>
                  </div>
                  <p className="kmeans-k-hint">
                    {treeMaxDepth === 0
                      ? "Auto: default max depth of 6"
                      : `Max depth = ${treeMaxDepth} levels`}
                  </p>
                </div>
              )}

              {/* k — KNN only */}
              {selectedTechnique === "knn" && (
                <div className="kmeans-section">
                  <p className="kmeans-section-label">Number of neighbours (k):</p>
                  <div className="kmeans-k-row">
                    <button className="pca-dim-btn"
                      onClick={() => setKnnK(k => Math.max(0, k - 1))}
                      disabled={knnK <= 0}>−</button>
                    <span className="kmeans-k-value">
                      {knnK === 0 ? "Auto" : knnK}
                    </span>
                    <button className="pca-dim-btn"
                      onClick={() => setKnnK(k => k === 0 ? 3 : Math.min(20, k + 1))}
                      disabled={knnK >= 20}>+</button>
                  </div>
                  <p className="kmeans-k-hint">
                    {knnK === 0
                      ? "Auto: best k chosen by cross-validation"
                      : `Fixed at k=${knnK} neighbours`}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* K-Means config panel */}
          {selectedTechnique === "kmeans" && csvNumericCols.length > 0 && (
            <div className="sidebar-card kmeans-config-card">
              <div className="sidebar-card-title">🔵 K-Means Settings</div>

              {/* Feature selection */}
              <div className="kmeans-section">
                <p className="kmeans-section-label">Features to cluster on:</p>
                <div className="feature-checkbox-list">
                  {csvNumericCols.map((col) => (
                    <label key={col} className="feature-checkbox-item">
                      <input
                        type="checkbox"
                        checked={kmeansFeatures.includes(col)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setKmeansFeatures([...kmeansFeatures, col]);
                          } else {
                            setKmeansFeatures(kmeansFeatures.filter(f => f !== col));
                          }
                        }}
                      />
                      <span>{col}</span>
                    </label>
                  ))}
                </div>
                <div className="feature-select-all">
                  <button onClick={() => setKmeansFeatures([...csvNumericCols])}>Select all</button>
                  <button onClick={() => setKmeansFeatures([])}>Clear</button>
                </div>
              </div>

              {/* Number of clusters */}
              <div className="kmeans-section">
                <p className="kmeans-section-label">Number of clusters (k):</p>
                <div className="kmeans-k-row">
                  <button
                    className="pca-dim-btn"
                    onClick={() => setKmeansK(k => Math.max(0, k - 1))}
                    disabled={kmeansK <= 0}
                  >−</button>
                  <span className="kmeans-k-value">
                    {kmeansK === 0 ? "Auto" : kmeansK}
                  </span>
                  <button
                    className="pca-dim-btn"
                    onClick={() => setKmeansK(k => k === 0 ? 2 : Math.min(8, k + 1))}
                    disabled={kmeansK >= 8}
                  >+</button>
                </div>
                <p className="kmeans-k-hint">
                  {kmeansK === 0
                    ? "Auto: best k chosen by elbow method"
                    : `Fixed at k=${kmeansK} clusters`}
                </p>
              </div>
            </div>
          )}

          {/* DBSCAN config panel */}
          {selectedTechnique === "dbscan" && csvNumericCols.length > 0 && (            <div className="sidebar-card dbscan-config-card">
              <div className="sidebar-card-title">🟣 DBSCAN Settings</div>

              {/* Feature selection */}
              <div className="kmeans-section">
                <p className="kmeans-section-label">Features to cluster on:</p>
                <div className="feature-checkbox-list">
                  {csvNumericCols.map((col) => (
                    <label key={col} className="feature-checkbox-item">
                      <input
                        type="checkbox"
                        checked={dbscanFeatures.includes(col)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setDbscanFeatures([...dbscanFeatures, col]);
                          } else {
                            setDbscanFeatures(dbscanFeatures.filter(f => f !== col));
                          }
                        }}
                      />
                      <span>{col}</span>
                    </label>
                  ))}
                </div>
                <div className="feature-select-all">
                  <button onClick={() => setDbscanFeatures([...csvNumericCols])}>Select all</button>
                  <button onClick={() => setDbscanFeatures([])}>Clear</button>
                </div>
              </div>

              {/* Epsilon */}
              <div className="kmeans-section">
                <p className="kmeans-section-label">
                  Epsilon (ε) — neighbourhood radius:
                </p>
                <div className="dbscan-slider-row">
                  <input
                    type="range"
                    min="0.1" max="3.0" step="0.1"
                    value={dbscanEps}
                    onChange={(e) => setDbscanEps(parseFloat(e.target.value))}
                    className="dbscan-slider"
                  />
                  <span className="dbscan-slider-val">{dbscanEps.toFixed(1)}</span>
                </div>
                <p className="kmeans-k-hint">
                  Smaller ε = tighter clusters, more noise. Larger ε = bigger clusters.
                </p>
              </div>

              {/* MinPts */}
              <div className="kmeans-section">
                <p className="kmeans-section-label">
                  Min Points — min samples to form a cluster:
                </p>
                <div className="kmeans-k-row">
                  <button
                    className="pca-dim-btn"
                    onClick={() => setDbscanMinPts(p => Math.max(0, p - 1))}
                    disabled={dbscanMinPts <= 0}
                  >−</button>
                  <span className="kmeans-k-value">
                    {dbscanMinPts === 0 ? "Auto" : dbscanMinPts}
                  </span>
                  <button
                    className="pca-dim-btn"
                    onClick={() => setDbscanMinPts(p => p === 0 ? 2 : Math.min(20, p + 1))}
                    disabled={dbscanMinPts >= 20}
                  >+</button>
                </div>
                <p className="kmeans-k-hint">
                  {dbscanMinPts === 0
                    ? "Auto: set based on dataset size"
                    : `Minimum ${dbscanMinPts} points required to form a core point`}
                </p>
              </div>
            </div>
          )}

          {/* Run */}
          <button
            className="run-btn"
            onClick={handleRunAnalysis}
            disabled={analysing || !canDo("runAnalysis", role)}
            title={!canDo("runAnalysis", role) ? "You don't have permission to run analysis" : ""}
          >
            {analysing
              ? <><FaSpinner className="spin" /> Analysing...</>
              : <><FaPlay /> Run Analysis</>}
          </button>

        </aside>

        {/* ── SUGGESTION PANEL ──────────────────────────────────────── */}
        <aside className="suggestion-panel">
          <div className="suggestion-panel-header">
            <div className="suggestion-title">
              <FaLightbulb className="suggest-icon" />
              <span>Smart Suggestions</span>
            </div>
            <button
              className="suggest-btn"
              onClick={handleSuggest}
              disabled={suggesting}
              title="Analyse your data and problem statement"
            >
              {suggesting
                ? <FaSpinner className="spin" />
                : <FaLightbulb />}
              {suggesting ? "Analysing..." : "Suggest"}
            </button>
          </div>

          {/* Data summary */}
          {dataSummary && (
            <div className="data-summary-card">
              <p className="data-summary-title">📊 Data Profile</p>
              <div className="data-summary-grid">
                <div className="ds-item"><span className="ds-val">{dataSummary.rows}</span><span className="ds-key">Rows</span></div>
                <div className="ds-item"><span className="ds-val">{dataSummary.columns}</span><span className="ds-key">Columns</span></div>
                <div className="ds-item"><span className="ds-val">{dataSummary.numeric_cols?.length}</span><span className="ds-key">Numeric</span></div>
                <div className="ds-item"><span className="ds-val">{dataSummary.text_cols?.length}</span><span className="ds-key">Categorical</span></div>
              </div>
              {dataSummary.candidate_target && (
                <p className="ds-target">Likely target: <strong>{dataSummary.candidate_target}</strong></p>
              )}
            </div>
          )}

          {/* Empty state */}
          {!suggesting && suggestions.length === 0 && (
            <div className="suggest-empty">
              <FaLightbulb className="suggest-empty-icon" />
              <p>Click <strong>Suggest</strong> after uploading your data and entering a problem statement.</p>
            </div>
          )}

          {/* Suggestion cards */}
          {suggestions.length > 0 && (
            <div className="suggestion-list">
              {suggestions.map((s, i) => (
                <div
                  key={s.technique}
                  className={`suggestion-card ${selectedTechnique === s.technique ? "selected" : ""} conf-${s.confidence.toLowerCase()}`}
                >
                  <div
                    className="suggestion-card-top"
                    onClick={() => setExpandedSug(expandedSug === i ? null : i)}
                  >
                    <span className="sug-icon">{s.icon}</span>
                    <div className="sug-info">
                      <span className="sug-label">{s.label}</span>
                      <span className={`sug-confidence conf-badge-${s.confidence.toLowerCase()}`}>
                        {s.confidence} match
                      </span>
                    </div>
                    <button
                      className="sug-use-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedTechnique(s.technique);
                        // Switch to correct tab
                        setMlTab(s.category);
                      }}
                    >
                      Use
                    </button>
                    <span className="sug-chevron">
                      {expandedSug === i ? <FaChevronUp /> : <FaChevronDown />}
                    </span>
                  </div>

                  {expandedSug === i && (
                    <div className="suggestion-card-body">
                      <p className="sug-use-when"><strong>Use when:</strong> {s.use_when}</p>
                      <ul className="sug-reasons">
                        {s.reasons.map((r, j) => <li key={j}>{r}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </aside>

        {/* ── MAIN AREA ─────────────────────────────────────────────────── */}
        <main className="project-main">

          {!results && !analysing && (
            <div className="empty-state">
              <FaChartBar className="empty-icon" />
              <h2>Ready to analyse</h2>
              <p>Fill in the problem statement, upload your data file, choose an ML technique and hit <strong>Run Analysis</strong>. Everything will be saved automatically.</p>
            </div>
          )}

          {analysing && (
            <div className="empty-state">
              <FaSpinner className="empty-icon spin" />
              <h2>Running analysis...</h2>
              <p>This may take a few moments.</p>
            </div>
          )}

          {results && !analysing && (
            <div className="results-area">
              {results.error ? (
                <div className="result-error">
                  <h3>⚠️ Error</h3>
                  <p>{results.error}</p>
                </div>
              ) : (
                <>
                  <div className="results-header">
                    <h2>Analysis Results</h2>
                    <span className="results-badge">{selectedTechnique.replace("_", " ")}</span>
                    <button className="refresh-btn" onClick={handleRefresh} title="Clear results">
                      <FaSync /> Refresh
                    </button>
                  </div>

                  {/* Summary */}
                  {results.summary && (
                    <div className="result-card">
                      <h3>📋 Summary</h3>
                      <p>{results.summary}</p>
                    </div>
                  )}

                  {/* Metrics grid */}
                  {results.metrics && Object.keys(results.metrics).length > 0 && (
                    <div className="metrics-grid">
                      {Object.entries(results.metrics).map(([key, val]) => (
                        <div className="metric-tile" key={key}>
                          <span className="metric-val">{val}</span>
                          <span className="metric-key">{key}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Insights */}
                  {results.insights && results.insights.length > 0 && (
                    <div className="result-card">
                      <h3>💡 Key Insights</h3>
                      <ul className="insights-list">
                        {results.insights.map((ins, i) => <li key={i}>{ins}</li>)}
                      </ul>
                    </div>
                  )}

                  {/* Feature importance (classification / decision tree) */}
                  {results.feature_importance && (
                    <div className="result-card">
                      <h3>📊 Feature Importance</h3>
                      <div className="bar-chart">
                        {results.feature_importance.map((f) => (
                          <div className="bar-row" key={f.feature}>
                            <span className="bar-label">{f.feature}</span>
                            <div className="bar-track">
                              <div
                                className="bar-fill"
                                style={{ width: `${(f.importance * 100).toFixed(1)}%` }}
                              />
                            </div>
                            <span className="bar-value">{(f.importance * 100).toFixed(1)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Scatter plot for regression */}
                  {results.scatter_data && (
                    <div className="result-card">
                      <h3>📈 Actual vs Predicted (first 20 samples)</h3>
                      <div className="scatter-table">
                        <div className="scatter-header">
                          <span>Sample</span><span>Actual</span><span>Predicted</span><span>Δ Error</span>
                        </div>
                        {results.scatter_data.actual.map((act, i) => {
                          const pred  = results.scatter_data.predicted[i];
                          const error = Math.abs(act - pred).toFixed(3);
                          return (
                            <div className="scatter-row" key={i}>
                              <span>#{i + 1}</span>
                              <span>{act}</span>
                              <span>{pred}</span>
                              <span className="error-val">{error}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Cluster breakdown + averages (kmeans / dbscan) */}
                  {results.cluster_info && (
                    <div className="result-card">
                      <h3>🔵 Cluster Breakdown</h3>
                      <div className="cluster-grid">
                        {results.cluster_info.map((c) => (
                          <div className="cluster-tile" key={c.cluster}>
                            <span className="cluster-num">Cluster {c.cluster}</span>
                            <span className="cluster-size">{c.size} records</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Per-cluster average feature values */}
                  {results.cluster_averages?.length > 0 && (
                    <div className="result-card">
                      <h3>📊 Average Feature Values per Cluster</h3>
                      <div className="cluster-avg-table-wrap">
                        <table className="cluster-avg-table">
                          <thead>
                            <tr>
                              <th>Cluster</th>
                              <th>Size</th>
                              {results.cluster_features?.map(f => (
                                <th key={f}>{f}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {results.cluster_averages.map(c => (
                              <tr key={c.cluster}>
                                <td><span className="cluster-badge">Cluster {c.cluster}</span></td>
                                <td>{c.size}</td>
                                {results.cluster_features?.map(f => (
                                  <td key={f}>{c.averages?.[f] ?? "—"}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* DBSCAN outliers table */}
                  {results.outlier_rows?.length > 0 && (
                    <div className="result-card">
                      <h3>⚠️ Outlier Records (Noise Points)</h3>
                      <div className="anomaly-table-wrap">
                        <table className="anomaly-table">
                          <thead>
                            <tr>
                              {Object.keys(results.outlier_rows[0]).map(k => (
                                <th key={k}>{k}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {results.outlier_rows.map((row, i) => (
                              <tr key={i}>
                                {Object.values(row).map((v, j) => (
                                  <td key={j}>{typeof v === "number" ? Number(v.toFixed(3)) : String(v)}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Custom Cluster Prediction Input */}
                  {["kmeans","dbscan"].includes(selectedTechnique) && results.cluster_features?.length > 0 && (
                    <div className="result-card custom-predict-card">
                      <h3><FaMagic style={{marginRight:8,color:"#667eea"}}/>Predict Cluster for Custom Input</h3>
                      <p className="custom-predict-desc">
                        Enter values for each feature below and click <strong>Predict Cluster</strong> to
                        find which cluster this data point belongs to.
                      </p>
                      <div className="custom-input-grid">
                        {results.cluster_features.map(col => (
                          <div className="custom-input-field" key={col}>
                            <label className="custom-input-label">{col}</label>
                            <SmartInput
                              col={col}
                              colInfo={csvColInfo}
                              value={clusterInputs[col]}
                              onChange={v => setClusterInputs(prev => ({ ...prev, [col]: v }))}
                            />
                          </div>
                        ))}
                      </div>
                      <button
                        className="predict-btn"
                        onClick={handlePredictCluster}
                        disabled={clusterPredicting}
                      >
                        {clusterPredicting
                          ? <><FaSpinner className="spin" /> Predicting...</>
                          : <><FaMagic /> Predict Cluster</>}
                      </button>

                      {/* Cluster prediction result */}
                      {clusterPredResult && (
                        <div className="prediction-output">
                          {clusterPredResult.error ? (
                            <div className="predict-error">⚠️ {clusterPredResult.error}</div>
                          ) : (
                            <>
                              <div className="predict-result-main">
                                <span className="predict-label">Predicted Cluster</span>
                                <span className="predict-value">
                                  {clusterPredResult.predicted_cluster === -1
                                    ? "🔴 Noise / Outlier"
                                    : `Cluster ${clusterPredResult.predicted_cluster}`}
                                </span>
                              </div>
                              <p className="predict-missing" style={{color:"#5f6368",marginBottom:12}}>
                                {clusterPredResult.note}
                              </p>

                              {/* K-Means distances */}
                              {clusterPredResult.distances?.length > 0 && (
                                <div className="predict-probs">
                                  <p className="predict-probs-title">Distance to each cluster centre:</p>
                                  {clusterPredResult.distances.map(d => (
                                    <div className="predict-prob-row" key={d.cluster}>
                                      <span className="prob-class">
                                        {d.cluster === clusterPredResult.predicted_cluster ? "★ " : ""}
                                        Cluster {d.cluster}
                                      </span>
                                      <div className="prob-bar-track">
                                        <div className="prob-bar-fill" style={{
                                          width: `${Math.min(100, (1 / (d.distance + 0.01)) * 20)}%`,
                                          background: d.cluster === clusterPredResult.predicted_cluster
                                            ? "linear-gradient(90deg,#43e97b,#38f9d7)"
                                            : "linear-gradient(90deg,#667eea,#764ba2)"
                                        }} />
                                      </div>
                                      <span className="prob-pct">{d.distance}</span>
                                    </div>
                                  ))}
                                </div>
                              )}

                              {/* DBSCAN distances */}
                              {clusterPredResult.cluster_distances?.length > 0 && (
                                <div className="predict-probs">
                                  <p className="predict-probs-title">Distance to each cluster:</p>
                                  {clusterPredResult.cluster_distances.map(d => (
                                    <div className="predict-prob-row" key={d.cluster}>
                                      <span className="prob-class">Cluster {d.cluster}</span>
                                      <span className="prob-coeff">min: {d.min_distance} · avg: {d.avg_distance}</span>
                                    </div>
                                  ))}
                                </div>
                              )}

                              {/* Cluster averages for context */}
                              {clusterPredResult.cluster_averages && clusterPredResult.predicted_cluster >= 0 && (
                                <div style={{marginTop:14}}>
                                  <p className="predict-probs-title">
                                    Typical values in Cluster {clusterPredResult.predicted_cluster}:
                                  </p>
                                  <div className="custom-input-grid" style={{marginTop:8}}>
                                    {Object.entries(clusterPredResult.cluster_averages).map(([k,v]) => (
                                      <div key={k} className="cluster-avg-mini">
                                        <span className="cluster-avg-mini-key">{k}</span>
                                        <span className="cluster-avg-mini-val">{v}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {clusterPredResult.missing_filled?.length > 0 && (
                                <p className="predict-missing">
                                  ℹ️ Missing values filled with median:&nbsp;
                                  <strong>{clusterPredResult.missing_filled.join(", ")}</strong>
                                </p>
                              )}
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* PCA scree data */}
                  {results.scree_data && (
                    <div className="result-card">
                      <h3>🔺 Variance Explained per Component</h3>
                      <div className="bar-chart">
                        {results.scree_data.components.map((c, i) => (
                          <div className="bar-row" key={c}>
                            <span className="bar-label">PC{c}</span>
                            <div className="bar-track">
                              <div
                                className="bar-fill pca-fill"
                                style={{ width: `${results.scree_data.explained[i]}%` }}
                              />
                            </div>
                            <span className="bar-value">
                              {results.scree_data.explained[i]}% (cum: {results.scree_data.cumulative[i]}%)
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* PCA — dimension reducer */}
                  {results.scree_data && (
                    <div className="result-card pca-reducer-card">
                      <h3>⬇️ Generate Reduced Dataset</h3>
                      <p className="pca-reducer-desc">
                        Choose how many principal components to keep, then download
                        the reduced CSV. Each component captures a portion of the
                        total variance shown above.
                      </p>
                      <div className="pca-reducer-controls">
                        <div className="pca-dim-selector">
                          <label className="pca-dim-label">
                            Number of dimensions (components):
                          </label>
                          <div className="pca-dim-row">
                            <button
                              className="pca-dim-btn"
                              onClick={() => setPcaDimensions(d => Math.max(1, d - 1))}
                              disabled={pcaDimensions <= 1}
                            >−</button>
                            <span className="pca-dim-value">{pcaDimensions}</span>
                            <button
                              className="pca-dim-btn"
                              onClick={() => setPcaDimensions(d => Math.min(results.scree_data.components.length, d + 1))}
                              disabled={pcaDimensions >= results.scree_data.components.length}
                            >+</button>
                          </div>
                          {/* Show variance retained */}
                          <p className="pca-variance-note">
                            Variance retained:{" "}
                            <strong>
                              {results.scree_data.cumulative[pcaDimensions - 1] ?? "—"}%
                            </strong>
                          </p>
                        </div>
                        <button
                          className="pca-generate-btn"
                          onClick={handlePcaGenerate}
                          disabled={pcaGenerating}
                        >
                          {pcaGenerating
                            ? <><FaSpinner className="spin" /> Generating...</>
                            : <><FaDownload /> Generate & Download CSV</>}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Anomaly rows */}
                  {results.anomaly_rows && results.anomaly_rows.length > 0 && (
                    <div className="result-card">
                      <h3>⚠️ Top Anomalous Records</h3>
                      <div className="anomaly-table-wrap">
                        <table className="anomaly-table">
                          <thead>
                            <tr>
                              {Object.keys(results.anomaly_rows[0]).map((k) => (
                                <th key={k}>{k}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {results.anomaly_rows.map((row, i) => (
                              <tr key={i}>
                                {Object.values(row).map((v, j) => (
                                  <td key={j}>{typeof v === "number" ? v.toFixed(3) : String(v)}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                  {/* ── Custom Prediction Input ── */}
                  {["classification","regression","decision_tree","knn"].includes(selectedTechnique)
                   && csvAllCols.length > 0 && (
                    <div className="result-card custom-predict-card">
                      <h3><FaMagic style={{marginRight:8,color:"#667eea"}}/>Predict on Custom Input</h3>
                      <p className="custom-predict-desc">
                        Enter values for each feature below and click <strong>Predict</strong> to see
                        what the trained model outputs for your custom data point.
                      </p>

                      {/* Feature input grid */}
                      <div className="custom-input-grid">
                        {csvAllCols
                          .filter(col => col !== (supervisedTarget || results?.raw?.target_col))
                          .map(col => (
                            <div className="custom-input-field" key={col}>
                              <label className="custom-input-label">{col}</label>
                              <SmartInput
                                col={col}
                                colInfo={csvColInfo}
                                value={customInputs[col]}
                                onChange={v => setCustomInputs(prev => ({ ...prev, [col]: v }))}
                              />
                            </div>
                          ))}
                      </div>

                      <button
                        className="predict-btn"
                        onClick={handlePredict}
                        disabled={predicting}
                      >
                        {predicting
                          ? <><FaSpinner className="spin" /> Predicting...</>
                          : <><FaMagic /> Predict</>}
                      </button>

                      {/* Prediction result */}
                      {predictionResult && (
                        <div className="prediction-output">
                          {predictionResult.error ? (
                            <div className="predict-error">⚠️ {predictionResult.error}</div>
                          ) : (
                            <>
                              <div className="predict-result-main">
                                <span className="predict-label">
                                  {predictionResult.target_col
                                    ? `Predicted ${predictionResult.target_col}`
                                    : "Prediction"}
                                </span>
                                <span className="predict-value">{predictionResult.prediction}</span>
                                {predictionResult.confidence && (
                                  <span className="predict-confidence">
                                    {predictionResult.confidence} confidence
                                  </span>
                                )}
                              </div>

                              {/* Classification probabilities */}
                              {predictionResult.probabilities?.length > 0 && (
                                <div className="predict-probs">
                                  <p className="predict-probs-title">Class probabilities:</p>
                                  {predictionResult.probabilities.map(p => (
                                    <div className="predict-prob-row" key={p.class}>
                                      <span className="prob-class">{p.class}</span>
                                      <div className="prob-bar-track">
                                        <div
                                          className="prob-bar-fill"
                                          style={{ width: `${p.probability}%` }}
                                        />
                                      </div>
                                      <span className="prob-pct">{p.probability}%</span>
                                    </div>
                                  ))}
                                </div>
                              )}

                              {/* Regression contributions */}
                              {predictionResult.contributions?.length > 0 && (
                                <div className="predict-probs">
                                  <p className="predict-probs-title">Top feature contributions:</p>
                                  {predictionResult.contributions.map(c => (
                                    <div className="predict-prob-row" key={c.feature}>
                                      <span className="prob-class">{c.feature}</span>
                                      <span className="prob-coeff">
                                        {c.contribution >= 0 ? "+" : ""}{c.contribution}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              )}

                              {/* Filled missing columns notice */}
                              {predictionResult.missing_filled?.length > 0 && (
                                <p className="predict-missing">
                                  ℹ️ Missing values filled with median:&nbsp;
                                  <strong>{predictionResult.missing_filled.join(", ")}</strong>
                                </p>
                              )}
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

        </main>
      </div>
    </div>
  );
}

export default ProjectPage;
