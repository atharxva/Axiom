import React, { useState, useEffect } from "react";
import { FileText, Eye, Download, CheckCircle2, ChevronRight, X, Loader2 } from "lucide-react";

export default function DocumentDrawer({ isOpen, onClose, onSelectDoc, activeDocId }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchDocuments();
    }
  }, [isOpen]);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/documents");
      const data = await res.json();
      setDocuments(data);
    } catch (err) {
      console.error("Failed to fetch documents", err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="drawer-overlay" onClick={onClose} style={{
      position: "fixed",
      inset: 0,
      background: "rgba(15, 23, 42, 0.4)",
      backdropFilter: "blur(4px)",
      zIndex: 100,
      display: "flex",
      justifyContent: "flex-end"
    }}>
      <div 
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: "460px",
          background: "#ffffff",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          boxShadow: "-10px 0 25px rgba(0, 0, 0, 0.08)",
          borderLeft: "1px solid var(--border-light)"
        }}
      >
        <div style={{
          padding: "1.25rem 1.5rem",
          borderBottom: "1px solid var(--border-light)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center"
        }}>
          <div>
            <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text-main)" }}>Policy Repository</h2>
            <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: "2px" }}>
              Uploaded compliance policies & statute documents
            </p>
          </div>
          <button 
            onClick={onClose}
            style={{
              background: "transparent",
              border: "1px solid var(--border-light)",
              borderRadius: "8px",
              padding: "4px",
              cursor: "pointer",
              color: "var(--text-muted)"
            }}
          >
            <X size={18} />
          </button>
        </div>

        <div style={{ padding: "1.25rem 1.5rem", overflowY: "auto", flex: 1 }}>
          {loading ? (
            <div style={{ textAlign: "center", padding: "3rem 1rem", color: "var(--text-muted)" }}>
              <Loader2 className="animate-spin" size={24} style={{ margin: "0 auto 0.5rem" }} />
              <p style={{ fontSize: "0.85rem" }}>Loading repository...</p>
            </div>
          ) : documents.length === 0 ? (
            <div style={{ textAlign: "center", padding: "3rem 1rem", color: "var(--text-muted)" }}>
              <FileText size={36} style={{ margin: "0 auto 0.75rem", opacity: 0.4 }} />
              <p style={{ fontWeight: 600 }}>No documents uploaded yet</p>
              <p style={{ fontSize: "0.8rem", marginTop: "4px" }}>Upload a policy on the audit desk to start.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {documents.map((doc) => {
                const isSelected = activeDocId === doc.id;
                return (
                  <div 
                    key={doc.id} 
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      background: isSelected ? "var(--primary-light)" : "var(--bg-app)",
                      border: `1px solid ${isSelected ? "var(--primary)" : "var(--border-light)"}`,
                      borderRadius: "10px",
                      padding: "0.85rem 1rem",
                      transition: "all 0.15s"
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem", flex: 1, minWidth: 0 }}>
                      <div style={{
                        background: isSelected ? "#fff" : "var(--bg-surface)",
                        padding: "0.45rem",
                        borderRadius: "8px",
                        border: "1px solid var(--border-light)"
                      }}>
                        <FileText size={18} color={isSelected ? "var(--primary)" : "var(--text-secondary)"} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <h4 style={{ 
                          fontSize: "0.85rem", 
                          fontWeight: 600, 
                          color: "var(--text-main)", 
                          whiteSpace: "nowrap", 
                          overflow: "hidden", 
                          textOverflow: "ellipsis" 
                        }}>
                          {doc.filename}
                        </h4>
                        <div style={{ display: "flex", gap: "0.4rem", fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "2px" }}>
                          <span>{(doc.file_size_bytes / 1024).toFixed(0)} KB</span>
                          <span>•</span>
                          <span>{doc.chunk_count} clauses</span>
                        </div>
                      </div>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                      <a 
                        href={`http://localhost:8000/api/documents/${doc.id}/download`} 
                        download={doc.filename}
                        title="Download Original"
                        style={{
                          background: "#fff",
                          border: "1px solid var(--border-light)",
                          color: "var(--text-muted)",
                          padding: "6px",
                          borderRadius: "6px",
                          display: "flex"
                        }}
                      >
                        <Download size={14} />
                      </a>
                      <button 
                        onClick={() => onSelectDoc(doc)}
                        title={isSelected ? "Active for audit" : "Set as active"}
                        style={{
                          background: isSelected ? "var(--primary)" : "#fff",
                          border: `1px solid ${isSelected ? "var(--primary)" : "var(--border-light)"}`,
                          color: isSelected ? "#fff" : "var(--text-muted)",
                          padding: "6px",
                          borderRadius: "6px",
                          cursor: "pointer",
                          display: "flex"
                        }}
                      >
                        {isSelected ? <CheckCircle2 size={14} /> : <ChevronRight size={14} />}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
