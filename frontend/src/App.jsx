import React, { useState, useEffect } from "react";
import { UploadCloud, Search, ShieldCheck, FileText, CheckCircle2, Loader2, AlertTriangle } from "lucide-react";

export default function App() {
  const [stats, setStats] = useState({ indexed_chunks: 0 });
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);

  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamLogs, setStreamLogs] = useState([]);
  const [auditResult, setAuditResult] = useState(null);

  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch(() => {});
  }, []);

  const handleUpload = async (e) => {
    const selectedFile = e.target.files?.[0] || file;
    if (!selectedFile) return;

    setUploading(true);
    setUploadStatus(null);
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch("http://localhost:8000/api/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.status === "success") {
        setUploadStatus(`Indexed ${data.new_chunks} chunks from ${data.filename}!`);
        setStats((prev) => ({ ...prev, indexed_chunks: data.total_chunks }));
      } else {
        setUploadStatus(`Error: ${data.message}`);
      }
    } catch {
      setUploadStatus("Failed to upload file to backend.");
    } finally {
      setUploading(false);
      setFile(null);
    }
  };

  const handleAudit = async (e) => {
    e.preventDefault();
    const cleanQuery = query.trim();
    if (cleanQuery.length < 3 || loading) return;

    setLoading(true);
    setAuditResult(null);
    setStreamLogs([]);

    try {
      // 1. Start SSE stream for real-time progress
      const response = await fetch("http://localhost:8000/api/search/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: cleanQuery, top_k: 2 }),
      });

      if (response.ok) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split("\n\n");
          buffer = events.pop() || "";

          for (const evt of events) {
            if (!evt.trim()) continue;
            const lines = evt.split("\n");
            const eventLine = lines[0] || "";
            const dataLine = lines[1] || "";
            if (dataLine.startsWith("data: ")) {
              try {
                const payload = JSON.parse(dataLine.replace("data: ", ""));
                if (eventLine.includes("status")) {
                  setStreamLogs((prev) => [...prev, `[${payload.stage}] Running step...`]);
                }
              } catch (_) {}
            }
          }
        }
      }

      // 2. Query the LangGraph Agentic Audit endpoint
      const auditRes = await fetch("http://localhost:8000/api/audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: cleanQuery }),
      });
      if (auditRes.ok) {
        const finalData = await auditRes.json();
        setAuditResult(finalData);
      }
    } catch (err) {
      setStreamLogs((prev) => [...prev, "Network error during audit process."]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <header className="header">
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, letterSpacing: "-0.02em" }}>AxiomRAG</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "0.2rem" }}>
            Enterprise Hybrid Search & Document Audit Engine
          </p>
        </div>
        <div className="logo-badge">
          <ShieldCheck size={14} />
          {stats.indexed_chunks} Chunks In Memory
        </div>
      </header>

      <div className="grid">
        {/* Left Column: PDF / TXT Ingestion */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          <div className="card">
            <h2 style={{ fontSize: "1.1rem", marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <FileText size={18} color="var(--accent-cyan)" /> Document Ingestion
            </h2>
            <label className="dropzone">
              <UploadCloud size={32} color="var(--accent-cyan)" style={{ margin: "0 auto 0.75rem" }} />
              <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>Drop compliance PDF / TXT here</div>
              <div style={{ color: "var(--text-muted)", fontSize: "0.8rem", marginTop: "0.3rem" }}>or click to browse from disk</div>
              <input
                type="file"
                accept=".pdf,.txt"
                style={{ display: "none" }}
                onChange={(e) => {
                  setFile(e.target.files?.[0]);
                  handleUpload(e);
                }}
              />
            </label>

            {uploading && (
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "1rem", fontSize: "0.85rem", color: "var(--accent-cyan)" }}>
                <Loader2 size={16} className="animate-spin" /> Chunking and vectorizing document...
              </div>
            )}

            {uploadStatus && (
              <div style={{ marginTop: "1rem", padding: "0.75rem", borderRadius: "0.5rem", background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.2)", fontSize: "0.85rem", color: "var(--success)" }}>
                {uploadStatus}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Interactive Audit Query Console */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          <div className="card">
            <h2 style={{ fontSize: "1.1rem", marginBottom: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Search size={18} color="var(--accent-cyan)" /> Compliance Audit Console
            </h2>

            <form onSubmit={handleAudit} style={{ display: "flex", gap: "0.75rem", marginBottom: "1.5rem" }}>
              <input
                type="text"
                className="input-box"
                placeholder="e.g. What is the maximum permitted workweek, including overtime?"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <button type="submit" className="btn" disabled={loading || query.trim().length < 3}>
                {loading ? <Loader2 size={16} className="animate-spin" /> : "Audit"}
              </button>
            </form>

            {/* Stream Logs */}
            {streamLogs.length > 0 && (
              <div style={{ background: "rgba(0,0,0,0.3)", borderRadius: "0.5rem", padding: "0.75rem", marginBottom: "1.5rem" }}>
                {streamLogs.map((log, i) => (
                  <div key={i} className="stream-event">
                    <CheckCircle2 size={12} color="var(--accent-cyan)" /> {log}
                  </div>
                ))}
              </div>
            )}

            {/* Audit Decision Result */}
            {auditResult && (
              <div style={{ borderTop: "1px solid var(--bg-card-border)", paddingTop: "1.25rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                  <span className={`badge ${auditResult.is_sufficient ? "badge-success" : "badge-warning"}`}>
                    {auditResult.is_sufficient ? "Verified Audit Policy" : "Low Confidence Excerpt"}
                  </span>
                  <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    Confidence: {(auditResult.confidence_score * 100).toFixed(1)}% ({auditResult.latency_ms}ms)
                  </span>
                </div>
                <div style={{ background: "rgba(15, 23, 42, 0.6)", borderRadius: "0.5rem", padding: "1rem", fontSize: "0.9rem", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
                  {auditResult.final_answer}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
