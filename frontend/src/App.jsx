import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { UploadCloud, ArrowUp, ShieldCheck, FileCheck, Loader2, Sparkles } from "lucide-react";

export default function App() {
  const [stats, setStats] = useState({ indexed_chunks: 0 });
  const [activeDoc, setActiveDoc] = useState(null);
  const [uploading, setUploading] = useState(false);

  const [inputQuery, setInputQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const chatEndRef = useRef(null);

  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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
        setActiveDoc({ name: data.filename, chunks: data.new_chunks });
        setStats((prev) => ({ ...prev, indexed_chunks: data.total_chunks }));
      }
    } catch (err) {
      console.error("Upload failed", err);
    } finally {
      setUploading(false);
    }
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
          text: "**Please upload a compliance policy first.**\n\nDrop a PDF or TXT document into the box above so I can audit your question against official rules.",
          status: "done",
        },
      ]);
      setInputQuery("");
      return;
    }

    setInputQuery("");
    setIsStreaming(true);

    // Add user message and empty AI container
    setMessages((prev) => [
      ...prev,
      { role: "user", text: query },
      { role: "ai", text: "", status: "thinking" },
    ]);

    try {
      const response = await fetch("http://localhost:8000/api/audit/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
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
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const payload = JSON.parse(line.slice(6));
                if (payload.token) {
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
    <div className="app-wrapper">
      {/* Top Header */}
      <header className="top-header">
        <div>
          <h1 style={{ fontSize: "1.35rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Sparkles size={20} color="var(--accent-cyan)" /> AxiomRAG
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "0.15rem" }}>
            Enterprise Compliance Auditor
          </p>
        </div>
        <div className="badge-cyan">
          <ShieldCheck size={14} />
          {stats.indexed_chunks} Clauses In Memory
        </div>
      </header>

      {/* Big Hero Center Dropbox */}
      {!activeDoc ? (
        <label className="hero-dropzone">
          <UploadCloud size={44} color="var(--accent-cyan)" style={{ margin: "0 auto 0.75rem" }} />
          <h2 style={{ fontSize: "1.1rem", fontWeight: 600 }}>Drop your Compliance Policy PDF / TXT here</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: "0.35rem" }}>
            Upload document to activate compliance chat
          </p>
          <input type="file" accept=".pdf,.txt" style={{ display: "none" }} onChange={handleFileUpload} />
        </label>
      ) : (
        <div style={{ display: "flex", justifyContent: "center", marginBottom: "1.75rem" }}>
          <div className="doc-pill">
            <FileCheck size={16} />
            <span>Active Policy: <strong>{activeDoc.name}</strong></span>
          </div>
        </div>
      )}

      {uploading && (
        <div style={{ textAlign: "center", marginBottom: "1.5rem", color: "var(--accent-cyan)", fontSize: "0.9rem" }}>
          <Loader2 size={18} className="animate-spin" style={{ display: "inline", marginRight: "0.5rem" }} />
          Indexing compliance policy...
        </div>
      )}

      {/* Chat Messages */}
      <div className="chat-container">
        {messages.length === 0 && !uploading && (
          <div style={{ textAlign: "center", color: "var(--text-muted)", marginTop: "3rem" }}>
            <p style={{ fontSize: "1.05rem", fontWeight: 500 }}>
              {!activeDoc ? "Upload a document above to get started." : "Ask any compliance or audit question below."}
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={msg.role === "user" ? "message-user" : "message-ai"}>
            {msg.role === "ai" && msg.status === "thinking" && !msg.text ? (
              <div className="dot-flashing">
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
              </div>
            ) : (
              <div className="markdown-content">
                <ReactMarkdown>{msg.text}</ReactMarkdown>
                {msg.status === "streaming" && <span className="typing-cursor" />}
              </div>
            )}
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>

      {/* Fixed Bottom Input Bar */}
      <div className="bottom-bar">
        <form onSubmit={handleSend} className="input-container">
          <input
            type="text"
            className="chat-input"
            placeholder={!activeDoc ? "Please upload a compliance document above first..." : "Ask an audit question..."}
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            disabled={isStreaming}
          />
          <button type="submit" className="btn-send" disabled={isStreaming || !inputQuery.trim()}>
            {isStreaming ? (
              <div className="dot-flashing" style={{ gap: "3px" }}>
                <span className="dot" style={{ width: "4px", height: "4px", backgroundColor: "#fff" }} />
                <span className="dot" style={{ width: "4px", height: "4px", backgroundColor: "#fff" }} />
                <span className="dot" style={{ width: "4px", height: "4px", backgroundColor: "#fff" }} />
              </div>
            ) : (
              <ArrowUp size={18} />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
