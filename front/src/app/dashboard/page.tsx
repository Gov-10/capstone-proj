"use client";

import { useState } from "react";
import { fetchAuthSession, signOut } from "aws-amplify/auth";
import { useRouter } from "next/navigation";

/* ---------------------------------------------
   Reusable Loader Overlay Component
---------------------------------------------- */
function LoaderOverlay({ message }: { message: string }) {
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="flex flex-col items-center gap-4 p-6 md:p-8 bg-gray-900/95 rounded-2xl border border-gray-700 shadow-2xl">
        <div className="w-10 h-10 border-4 border-purple-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-base md:text-lg text-gray-200 text-center">
          {message}
        </p>
      </div>
    </div>
  );
}

/* ---------------------------------------------
   Main Component
---------------------------------------------- */
export default function ChatPage() {
  const router = useRouter();

  const [file, setFile] = useState<File | null>(null);
  const [loadingUpload, setLoadingUpload] = useState(false);
  const [loadingAgent, setLoadingAgent] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const [result, setResult] = useState<string | null>(null);
  const [history, setHistory] = useState<Array<{timestamp: string; file_key: string; response: string}>>([]);
  const [showHistory, setShowHistory] = useState(false);

  /* -------------------- Sign Out -------------------- */
  const handleLogout = async () => {
    await signOut();
    router.push("/");
  };

  /* -------------------- Upload File -------------------- */
  const uploadVideo = async () => {
    if (!file) {
      alert("Please choose a file first.");
      return;
    }

    try {
      setLoadingUpload(true);
      setResult(null);

      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();

      const res = await fetch(
        "https://capstone-django-777268942678.asia-south1.run.app/api/get-upload-url",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            file_name: file.name,
            content_type: file.type,
          }),
        }
      );

      const { upload_url } = await res.json();

      await fetch(upload_url, {
        method: "PUT",
        headers: {
          "Content-Type": file.type,
        },
        body: file,
      });

      alert("Uploaded successfully!");
    } catch (err) {
      alert("Error: " + err);
    } finally {
      setLoadingUpload(false);
    }
  };

  /* -------------------- Fetch AI Agent Result -------------------- */
  const agentResult = async () => {
    try {
      setLoadingAgent(true);
      setResult(null);

      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();

      const res = await fetch(
        "https://capstone-proj-777268942678.asia-south1.run.app/status",
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await res.json();
      setResult(data.response);
    } catch (err) {
      console.log("Error fetching agent result:", err);
    } finally {
      setLoadingAgent(false);
    }
  };

  /* -------------------- Fetch Chat History -------------------- */
  const chatHistory = async () => {
    try {
      setLoadingHistory(true);

      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();

      const res = await fetch(
        "https://capstone-django-777268942678.asia-south1.run.app/api/chat-history",
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const data = await res.json();
      setHistory(data);
      setShowHistory(true);
    } catch (err) {
      console.log(err);
    } finally {
      setLoadingHistory(false);
    }
  };

  /* -------------------- UI -------------------- */
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#050014] via-black to-black text-white">
      {/* Global Loaders */}
      {loadingUpload && <LoaderOverlay message="Uploading document…" />}
      {loadingAgent && <LoaderOverlay message="Analyzing with AI…" />}
      {loadingHistory && <LoaderOverlay message="Loading past analyses…" />}

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 mt-6 md:mt-10 py-6 md:py-10">
        <div className="grid lg:grid-cols-[minmax(0,2fr)_minmax(260px,1fr)] gap-6 md:gap-8 items-start">
          {/* Left: Upload + Result */}
          <section className="space-y-6">
            {/* Upload Card */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl p-5 md:p-6">
              <h2 className="text-base md:text-lg font-semibold mb-1">
                Upload document
              </h2>
              <p className="text-xs md:text-sm text-slate-400 mb-4">
                Supported formats: PDF, DOCX and similar legal document files.
              </p>

              <div className="space-y-3">
                <label className="flex flex-col items-center justify-center w-full h-32 md:h-36 border-2 border-dashed border-slate-700 rounded-xl cursor-pointer bg-slate-900/80 hover:border-purple-500/70 hover:bg-slate-900 transition-colors">
                  <input
                    type="file"
                    className="hidden"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                  />
                  <span className="text-3xl mb-2">📄</span>
                  <span className="text-xs md:text-sm text-slate-300">
                    {file ? file.name : "Click to choose a file"}
                  </span>
                  <span className="text-[11px] text-slate-500 mt-1">
                    Max 25 MB
                  </span>
                </label>

                <button
                  type="button"
                  onClick={uploadVideo}
                  disabled={loadingUpload}
                  className={`w-full py-2.5 md:py-3 rounded-xl text-sm font-medium transition-colors ${
                    loadingUpload
                      ? "bg-cyan-600/60 cursor-not-allowed"
                      : "bg-cyan-500 hover:bg-cyan-400 text-slate-950"
                  }`}
                >
                  {loadingUpload ? "Uploading..." : "Upload Document"}
                </button>
              </div>
            </div>

            {/* Actions Card */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl p-5 md:p-6">
              <h2 className="text-base md:text-lg font-semibold mb-1">
                Run analysis
              </h2>
              <p className="text-xs md:text-sm text-slate-400 mb-4">
                Use the latest uploaded document to generate AI insights or
                review your history.
              </p>

              <div className="flex flex-col md:flex-row gap-3">
                <button
                  type="button"
                  onClick={agentResult}
                  disabled={loadingAgent}
                  className={`flex-1 py-2.5 md:py-3 rounded-xl text-sm font-medium transition-colors ${
                    loadingAgent
                      ? "bg-purple-600/60 cursor-not-allowed"
                      : "bg-purple-600 hover:bg-purple-500"
                  }`}
                >
                  {loadingAgent ? "Processing…" : "Get AI Analysis"}
                </button>

                <button
                  type="button"
                  onClick={chatHistory}
                  disabled={loadingHistory}
                  className={`flex-1 py-2.5 md:py-3 rounded-xl text-sm font-medium border transition-colors ${
                    loadingHistory
                      ? "border-slate-700 bg-slate-800/60 text-slate-400 cursor-not-allowed"
                      : "border-slate-700 bg-slate-900 hover:bg-slate-800 text-slate-200"
                  }`}
                >
                  {loadingHistory ? "Loading…" : "View Past Analyses"}
                </button>
              </div>
            </div>

            {/* AI Result */}
            <div className="bg-slate-950/80 border border-slate-800 rounded-2xl shadow-xl p-5 md:p-6 min-h-[160px]">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-base md:text-lg font-semibold">
                  AI Analysis Result
                </h2>
                <span className="text-[11px] md:text-xs text-slate-500">
                  Latest response
                </span>
              </div>

              {result ? (
                <div className="text-xs md:text-sm text-slate-200 whitespace-pre-wrap leading-relaxed max-h-[320px] overflow-y-auto pr-1">
                  {result}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center text-center py-10 text-slate-500 text-sm">
                  <span className="text-3xl mb-2">🧾</span>
                  <p>No analysis yet.</p>
                  <p className="text-xs mt-1">
                    Upload a document and click “Get AI Analysis” to see
                    results.
                  </p>
                </div>
              )}
            </div>
          </section>

          {/* Right: Summary / Tips */}
          <aside className="bg-slate-950/80 border border-slate-800 rounded-2xl shadow-xl p-5 md:p-6 space-y-4 md:space-y-5">
            <h2 className="text-base md:text-lg font-semibold mb-1">
              How it works
            </h2>
            <ol className="space-y-3 text-xs md:text-sm text-slate-300 list-decimal list-inside">
              <li>Upload a legal document using the card on the left.</li>
              <li>
                Click “Get AI Analysis” to generate a structured summary.
              </li>
              <li>Open “View Past Analyses” to revisit previous uploads.</li>
            </ol>

            <div className="pt-2 border-t border-slate-800">
              <h3 className="text-xs font-semibold text-slate-400 mb-2">
                Tips for best results
              </h3>
              <ul className="space-y-2 text-xs md:text-sm text-slate-300">
                <li>Use clear, readable documents (avoid low‑quality scans).</li>
                <li>
                  Limit very large multi‑document bundles into smaller files.
                </li>
                <li>
                  Check history to ensure the correct version was analyzed.
                </li>
              </ul>
            </div>
          </aside>
        </div>
      </main>

      {/* History Modal */}
      {showHistory && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 md:p-6 z-50">
          <div className="bg-slate-950/95 border border-slate-800 rounded-2xl shadow-2xl max-w-3xl w-full max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between px-5 md:px-6 py-4 border-b border-slate-800">
              <h2 className="text-base md:text-lg font-semibold">
                Analysis history
              </h2>
              <button
                type="button"
                onClick={() => setShowHistory(false)}
                className="text-slate-400 hover:text-slate-200 text-xl leading-none px-1"
              >
                ×
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-5 md:px-6 py-4 space-y-3">
              {history.length === 0 ? (
                <div className="flex flex-col items-center justify-center text-center py-10 text-slate-500 text-sm">
                  <span className="text-4xl mb-2">📭</span>
                  <p>No previous analyses found.</p>
                </div>
              ) : (
                history.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-4 md:p-5 rounded-xl bg-slate-900/80 border border-slate-800"
                  >
                    <div className="text-[11px] md:text-xs text-slate-400 mb-1">
                      📅 {item.timestamp || "N/A"}
                    </div>
                    <div className="text-xs md:text-sm font-semibold text-indigo-300 mb-2">
                      📄 {item.file_key || "Unknown file"}
                    </div>
                    <div className="text-xs md:text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
                      {item.response || "No response"}
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="px-5 md:px-6 py-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowHistory(false)}
                className="w-full py-2.5 rounded-xl text-sm font-medium bg-slate-800 hover:bg-slate-700 text-slate-100 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


