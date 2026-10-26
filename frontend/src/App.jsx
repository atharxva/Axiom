import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { 
  ShieldCheck, 
  UploadCloud, 
  ArrowUp, 
  FileText, 
  FolderOpen, 
  Loader2, 
  CheckCircle2, 
  AlertTriangle,
  ExternalLink,
  BookOpen,
  Sparkles,
  Columns,
  Maximize2,
  X,
  MapPin
} from "lucide-react";
import DocumentDrawer from "./DocumentDrawer";

export default function App() {
  const [stats, setStats] = useState({ indexed_chunks: 0 });
  const [activeDoc, setActiveDoc] = useState(null);
  const [docContent, setDocContent] = useState("");
  const [docLoading, setDocLoading] = useState(false);
  
  // Default to full-screen chat; split view is toggled via button
  const [isSplitView, setIsSplitView] = useState(false);
  const [targetPage, setTargetPage] = useState(1);
  const [highlightSnippet, setHighlightSnippet] = useState("");

  const [uploading, setUploading] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const [inputQuery, setInputQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const chatEndRef = useRef(null);

  // Load server stats and initial active document
  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch(() => {});

    fetch("http://localhost:8000/api/documents")
      .then((res) => res.json())
      .then((docs) => {
        if (docs && docs.length > 0) {
          handleSelectDoc(docs[0]);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const [docRawText, setDocRawText] = useState("");
  const evidenceTextRef = useRef(null);

  // Load document content and raw text for the evidence viewer
  const loadDocumentContent = async (doc) => {
    if (!doc) return;
    setDocLoading(true);
    try {
      // 1. Set document source URL (/view serves inline preview, /download triggers file save)
      if (doc.filename.endsWith(".pdf")) {
        setDocContent(`http://localhost:8000/api/documents/${doc.id}/view`);
      } else {
        const res = await fetch(`http://localhost:8000/api/documents/${doc.id}/view`);
        const text = await res.text();
        setDocContent(text);
      }

      // 2. Load extracted text for pinpoint sentence highlighting
      const textRes = await fetch(`http://localhost:8000/api/documents/${doc.id}/text`);
      const textData = await textRes.json();
      setDocRawText(textData.text || "");
    } catch (err) {
      console.error("Failed to load document preview", err);
      setDocContent("");
      setDocRawText("");
    } finally {
      setDocLoading(false);
    }
  };

  const handleSelectDoc = (doc) => {
    setActiveDoc({ id: doc.id, name: doc.filename, chunks: doc.chunk_count });
    loadDocumentContent(doc);
    setIsDrawerOpen(false);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/api/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.status === "success") {
        const newDoc = { id: data.doc_id, filename: data.filename, chunk_count: data.new_chunks };
        setActiveDoc({ id: data.doc_id, name: data.filename, chunks: data.new_chunks });
        setStats((prev) => ({ ...prev, indexed_chunks: data.total_chunks }));
        loadDocumentContent(newDoc);
      }
    } catch (err) {
      console.error("Upload failed", err);
    } finally {
      setUploading(false);
    }
  };

  const [activeTab, setActiveTab] = useState("original"); // "original" (PDF) or "text"

  // Jump to specific cited sentence in split screen with native PDF search & highlighting
  const handleJumpToCitation = (pageNum, snippet) => {
    setTargetPage(pageNum || 1);
    setHighlightSnippet(snippet || "");
    setActiveTab("original");
    setIsSplitView(true);

    setTimeout(() => {
      const el = document.getElementById("highlighted-clause");
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 200);
  };

  const handleSend = async (e) => {
    e.preventDefault();
    const query = inputQuery.trim();
    if (!query || isStreaming) return;

    if (!activeDoc) {
      setMessages((prev) => [
        ...prev,
        { role: "user", text: query },
        {
          role: "ai",
          text: "**Please upload or select a compliance policy first.**\n\nUpload a document so I can verify your inquiry against official clauses.",
          confidence: null,
          status: "done",
        },
      ]);
      setInputQuery("");
      return;
    }

    setInputQuery("");
    setIsStreaming(true);

    setMessages((prev) => [
      ...prev,
      { role: "user", text: query },
      { role: "ai", text: "", confidence: null, citation: null, status: "thinking" },
    ]);

    try {
      const response = await fetch("http://localhost:8000/api/audit/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          query,
          doc_id: activeDoc?.id || null 
        }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let streamAccumulator = "";
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
          let eventType = "message";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              try {
                const payload = JSON.parse(line.slice(6));
                
                if (eventType === "metadata" && payload.confidence !== undefined) {
                  setMessages((prev) => {
                    const copy = [...prev];
                    const lastIdx = copy.length - 1;
                    if (copy[lastIdx] && copy[lastIdx].role === "ai") {
                      copy[lastIdx].confidence = payload.confidence;
                      copy[lastIdx].is_sufficient = payload.is_sufficient;
                      copy[lastIdx].citation = {
                        page_number: payload.page_number,
                        source: payload.source,
                        snippet: payload.snippet
                      };
                    }
                    return copy;
                  });
                } else if (eventType === "token" && payload.token) {
                  streamAccumulator += payload.token;
                  const currentText = streamAccumulator;
                  setMessages((prev) => {
                    const copy = [...prev];
                    const lastIdx = copy.length - 1;
                    if (copy[lastIdx] && copy[lastIdx].role === "ai") {
                      copy[lastIdx] = {
                        ...copy[lastIdx],
                        text: currentText,
                        status: "streaming",
                      };
                    }
                    return copy;
                  });
                }
              } catch (_) {}
            }
          }
        }
      }
    } catch (err) {
      setMessages((prev) => {
        const copy = [...prev];
        const lastIdx = copy.length - 1;
        copy[lastIdx] = { ...copy[lastIdx], text: "Error connecting to compliance audit engine.", status: "done" };
        return copy;
      });
    } finally {
      setIsStreaming(false);
      setMessages((prev) => {
        const copy = [...prev];
        const lastIdx = copy.length - 1;
        if (copy[lastIdx]) copy[lastIdx] = { ...copy[lastIdx], status: "done" };
        return copy;
      });
    }
  };

  return (
    <div className="app-container">
      <div style={{ display: "flex", flexDirection: "column", width: "100%", height: "100%" }}>
        {/* Top Executive Header */}
        <header className="app-header">
          <div className="brand-section">
            <div className="brand-icon">
              <ShieldCheck size={18} />
            </div>
            <div>
              <h1 className="brand-title">AxiomRAG</h1>
              <p className="brand-subtitle">Enterprise Compliance & Legal Audit Desk</p>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            {/* Toggle Split Screen Button */}
            <button 
              className={`btn-neutral ${isSplitView ? "btn-active" : ""}`}
              onClick={() => setIsSplitView(!isSplitView)}
              title={isSplitView ? "Close Split View (Full Screen Chat)" : "Open Document Split View"}
              style={{
                background: isSplitView ? "var(--primary-light)" : "var(--bg-surface)",
                borderColor: isSplitView ? "var(--primary)" : "var(--border-light)",
                color: isSplitView ? "var(--primary)" : "var(--text-secondary)"
              }}
            >
              <Columns size={15} />
              <span>{isSplitView ? "Full Screen Chat" : "Split View"}</span>
            </button>

            <button 
              className="btn-neutral"
              onClick={() => setIsDrawerOpen(true)}
              title="Open Policy Repository"
            >
              <FolderOpen size={15} color="var(--primary)" />
              <span>Repository</span>
            </button>

            <div className="header-status-badge">
              <span style={{ width: "7px", height: "7px", borderRadius: "50%", background: "var(--success)" }} />
              {stats.indexed_chunks} Clauses
            </div>
          </div>
        </header>

        {/* Split / Full Viewport */}
        <div className="split-viewport">
          {/* Main Audit Workspace (Full width by default, half width in split mode) */}
          <div 
            className="audit-workspace" 
            style={{ 
              borderRight: isSplitView ? "1px solid var(--border-light)" : "none",
              maxWidth: isSplitView ? "55%" : "880px",
              margin: isSplitView ? "0" : "0 auto",
              width: "100%"
            }}
          >
            {/* Active Policy Status Bar */}
            {activeDoc && (
              <div className="active-policy-bar">
                <div className="policy-card-meta">
                  <span className="policy-badge">Active Policy</span>
                  <span style={{ maxWidth: "260px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {activeDoc.name}
                  </span>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.78rem" }}>
                    ({activeDoc.chunks} clauses)
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  {!isSplitView && (
                    <button 
                      className="btn-neutral" 
                      style={{ padding: "0.25rem 0.6rem", fontSize: "0.75rem" }}
                      onClick={() => setIsSplitView(true)}
                    >
                      <Columns size={13} />
                      <span>Inspect PDF</span>
                    </button>
                  )}
                  <button 
                    className="btn-neutral" 
                    style={{ padding: "0.25rem 0.6rem", fontSize: "0.75rem" }}
                    onClick={() => setIsDrawerOpen(true)}
                  >
                    Switch
                  </button>
                </div>
              </div>
            )}

            {/* Audit Conversation Feed */}
            <div className="chat-scrollport">
              {messages.length === 0 && (
                <div className="empty-hero">
                  <div className="hero-icon-bubble">
                    <BookOpen size={28} />
                  </div>
                  <h2 style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--text-main)", letterSpacing: "-0.01em" }}>
                    Executive Audit Console
                  </h2>
                  <p style={{ color: "var(--text-muted)", fontSize: "0.88rem", marginTop: "0.35rem", lineHeight: 1.5 }}>
                    Drop a compliance policy, supplier code, or legal statute below to begin deterministic verification.
                  </p>

                  <label className="hero-dropzone-box">
                    <UploadCloud size={32} color="var(--primary)" style={{ margin: "0 auto 0.5rem" }} />
                    <p style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text-main)" }}>
                      Upload Policy Document
                    </p>
                    <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "2px" }}>
                      PDF or TXT compliance files supported
                    </p>
                    <input type="file" accept=".pdf,.txt" style={{ display: "none" }} onChange={handleFileUpload} />
                  </label>
                </div>
              )}

              {uploading && (
                <div style={{ textAlign: "center", padding: "1.5rem", color: "var(--primary)" }}>
                  <Loader2 size={20} className="animate-spin" style={{ display: "inline", marginRight: "0.5rem" }} />
                  <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>Extracting clauses & indexing vector space...</span>
                </div>
              )}

              {messages.map((msg, idx) => (
                <div key={idx} className={msg.role === "user" ? "message-row-user" : "message-row-ai"}>
                  {msg.role === "user" ? (
                    <div className="user-bubble">{msg.text}</div>
                  ) : (
                    <div className="ai-card">
                      <div className="ai-card-header">
                        <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
                          <Sparkles size={16} color="var(--primary)" />
                          <span style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--text-main)" }}>
                            Audit Finding
                          </span>
                        </div>
                        
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          {/* Citation Quick-Jump Pill */}
                          {msg.citation && msg.confidence >= 0.5 && (
                            <button
                              onClick={() => handleJumpToCitation(msg.citation.page_number, msg.citation.snippet)}
                              title="Inspect exact source sentence in split screen"
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "0.35rem",
                                background: "var(--primary-light)",
                                color: "var(--primary)",
                                border: "1px solid rgba(2, 132, 199, 0.25)",
                                padding: "0.22rem 0.65rem",
                                borderRadius: "9999px",
                                fontSize: "0.72rem",
                                fontWeight: 700,
                                cursor: "pointer",
                                transition: "all 0.15s"
                              }}
                            >
                              <MapPin size={12} />
                              <span>View Source Clause</span>
                            </button>
                          )}

                          {msg.confidence !== null && (
                            <div className={`confidence-indicator ${msg.confidence >= 0.5 ? "confidence-high" : "confidence-low"}`}>
                              {msg.confidence >= 0.5 ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}
                              <span>Confidence: {(msg.confidence * 100).toFixed(1)}%</span>
                            </div>
                          )}
                        </div>
                      </div>

                      {msg.status === "thinking" && !msg.text ? (
                        <div className="thinking-box">
                          <div className="dot-bounce" />
                          <div className="dot-bounce" />
                          <div className="dot-bounce" />
                          <span>Searching hybrid index & reranking verified clauses...</span>
                        </div>
                      ) : (
                        <div className="markdown-editorial">
                          <ReactMarkdown>{msg.text}</ReactMarkdown>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            {/* Input Dock */}
            <div className="audit-input-dock">
              <form onSubmit={handleSend} className="input-bar">
                <input
                  type="text"
                  className="audit-input"
                  placeholder={!activeDoc ? "Please upload a document to begin..." : "Inquire about a policy clause, restriction, or obligation..."}
                  value={inputQuery}
                  onChange={(e) => setInputQuery(e.target.value)}
                  disabled={isStreaming}
                />
                <button type="submit" className="btn-audit-send" disabled={isStreaming || !inputQuery.trim()}>
                  {isStreaming ? <Loader2 size={16} className="animate-spin" /> : <ArrowUp size={16} />}
                </button>
              </form>
            </div>
          </div>

          {/* Right Pane: Live Document Evidence Viewer (Rendered only in Split View) */}
          {isSplitView && (
            <div className="evidence-viewer">
              <div className="evidence-header">
                <div className="evidence-title">
                  <FileText size={16} color="var(--primary)" />
                  <span>Document Evidence {targetPage > 1 && `(Page ${targetPage})`}</span>
                </div>
                
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  {activeDoc && (
                    <a 
                      href={`http://localhost:8000/api/documents/${activeDoc.id}/download`} 
                      download={activeDoc.name}
                      className="btn-neutral"
                      style={{ padding: "0.2rem 0.55rem", fontSize: "0.72rem" }}
                      title="Download original file"
                    >
                      <ExternalLink size={12} />
                      <span>Download</span>
                    </a>
                  )}
                  <button 
                    onClick={() => setIsSplitView(false)}
                    style={{
                      background: "transparent",
                      border: "1px solid var(--border-light)",
                      borderRadius: "6px",
                      padding: "4px",
                      cursor: "pointer",
                      display: "flex",
                      color: "var(--text-muted)"
                    }}
                    title="Close split view"
                  >
                    <X size={15} />
                  </button>
                </div>
              </div>

              {/* Verified Clause Snippet Notification Banner */}
              {highlightSnippet && (
                <div className="highlighted-sentence-banner">
                  <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                    <MapPin size={14} color="#854d0e" />
                    <strong style={{ fontSize: "0.82rem" }}>Direct Source Clause Reference:</strong>
                  </div>
                  <span style={{ fontStyle: "italic", fontSize: "0.8rem", lineHeight: 1.4 }}>
                    "{highlightSnippet}"
                  </span>
                </div>
              )}

              <div className="evidence-body">
                {docLoading ? (
                  <div className="evidence-empty">
                    <Loader2 size={24} className="animate-spin" style={{ marginBottom: "0.5rem", color: "var(--primary)" }} />
                    <p style={{ fontSize: "0.85rem" }}>Loading document viewer...</p>
                  </div>
                ) : !activeDoc ? (
                  <div className="evidence-empty">
                    <BookOpen size={36} style={{ opacity: 0.3, marginBottom: "0.75rem" }} />
                    <p style={{ fontWeight: 600, fontSize: "0.9rem" }}>No Active Document</p>
                    <p style={{ fontSize: "0.78rem", maxWidth: "260px", marginTop: "4px" }}>
                      Upload or select a policy on the left to inspect its clauses.
                    </p>
                  </div>
                ) : activeDoc.name.endsWith(".pdf") ? (
                  <iframe 
                    key={`${activeDoc.id}-${targetPage}-${highlightSnippet}`}
                    src={(() => {
                      const params = [];
                      if (targetPage && targetPage >= 1) {
                        params.push(`page=${targetPage}`);
                      }
                      if (highlightSnippet) {
                        // Extract 2 to 3 distinctive words from the clause to highlight in the PDF
                        const searchWords = highlightSnippet
                          .replace(/[^\w\s]/gi, ' ')
                          .split(/\s+/)
                          .filter(w => w.length > 3)
                          .slice(0, 3)
                          .join(' ');
                        if (searchWords) {
                          params.push(`search="${encodeURIComponent(searchWords)}"`);
                        }
                      }
                      const fragment = params.length > 0 ? `#${params.join('&')}` : '';
                      return `${docContent}${fragment}`;
                    })()} 
                    title="Document Evidence Viewer" 
                    className="evidence-iframe" 
                  />
                ) : (
                  <pre className="evidence-raw-text">{docContent}</pre>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Slide-out Document Repository */}
        <DocumentDrawer 
          isOpen={isDrawerOpen} 
          onClose={() => setIsDrawerOpen(false)}
          onSelectDoc={handleSelectDoc}
          activeDocId={activeDoc?.id}
        />
      </div>
    </div>
  );
}
