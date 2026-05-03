import React, { useState } from "react";
import { Download } from "lucide-react";
import { NILMANI_API_BASE } from "@/services/nilmaniService";

const ExportValidation: React.FC = () => {
  const [status, setStatus] = useState<string | null>(null);
  const files = ["question_ratings.csv", "answer_ratings.csv"];

  const download = async (file: string) => {
    setStatus("downloading");
    try {
      const url = `${NILMANI_API_BASE}/validation/export?file=${encodeURIComponent(file)}`;
      const res = await fetch(url);
      if (!res.ok) {
        let errMsg = `HTTP ${res.status}`;
        try {
          const j = await res.json();
          errMsg = j.detail || j.message || JSON.stringify(j);
        } catch (e) {
          const txt = await res.text().catch(() => "");
          if (txt) errMsg = txt.slice(0, 200);
        }
        setStatus(errMsg);
        return;
      }

      const blob = await res.blob();
      const urlBlob = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = urlBlob;
      a.download = file;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(urlBlob);
      setStatus("done");
      setTimeout(() => setStatus(null), 2000);
    } catch (e: any) {
      setStatus(e?.message || "error");
    }
  };

  return (
    <div className="export-validation inline-flex flex-col gap-1 rounded-xl border border-slate-700 bg-slate-950/80 px-2 py-1 shadow-lg backdrop-blur-sm">
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
        <Download className="h-3.5 w-3.5 text-cyan-400" />
        Validation Export
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {files.map((file, index) => (
          <button
            key={file}
            type="button"
            onClick={() => download(file)}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[12px] font-medium transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-cyan-400/70 ${
              index === 0
                ? "border-cyan-500/50 bg-cyan-500/15 text-cyan-50 hover:bg-cyan-500/25"
                : "border-emerald-500/50 bg-emerald-500/15 text-emerald-50 hover:bg-emerald-500/25"
            }`}
          >
            <span>{file === "question_ratings.csv" ? "Questions CSV" : "Answers CSV"}</span>
          </button>
        ))}
      </div>

      <div className="min-h-[14px] text-[11px] leading-none text-slate-400">
        {status === "downloading" && <span>Downloading…</span>}
        {status === "done" && <span className="text-emerald-300">Export ready</span>}
        {status && status !== "downloading" && status !== "done" && (
          <span className="text-rose-300">{status}</span>
        )}
      </div>
    </div>
  );
};

export default ExportValidation;
