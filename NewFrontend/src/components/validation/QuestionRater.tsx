import React, { useState } from "react";
import { NILMANI_API_BASE } from "@/services/nilmaniService";

interface Props {
  jobId?: string | null;
  questionId: string;
  questionText: string;
}

const QuestionRater: React.FC<Props> = ({ jobId, questionId, questionText }) => {
  const [relevance, setRelevance] = useState(4);
  const [clarity, setClarity] = useState(4);
  const [realism, setRealism] = useState(4);
  const [comment, setComment] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  const submit = async () => {
    setStatus("saving");
    try {
      const payload = {
        job_id: jobId || "",
        question_id: questionId,
        question_text: questionText,
        rater_id: "frontend",
        relevance,
        clarity,
        realism,
        comment,
      };

      const url = `${NILMANI_API_BASE}/validation/question-rating`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        // try parse JSON error, else use status
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

      setStatus("saved");
      setTimeout(() => setStatus(null), 2000);
    } catch (e: any) {
      setStatus(e?.message || "failed");
    }
  };

  return (
    <div className="question-rater mt-2 w-full rounded-xl border border-slate-700 bg-slate-950/90 p-3 shadow-lg shadow-black/20 backdrop-blur-sm text-slate-100">
      <div className="flex items-center justify-between gap-3 mb-2">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-cyan-300">
            Validation rating
          </div>
          <div className="text-xs text-slate-300">Rate the question right here</div>
        </div>
        <div className="rounded-full border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-300">
          1 = low, 5 = high
        </div>
      </div>

      <div className="grid gap-2 sm:grid-cols-3 text-sm">
        <label className="flex flex-col gap-1 rounded-lg border border-slate-800 bg-slate-900/70 px-2 py-2">
          <span className="text-[11px] font-medium text-slate-300">Relevance</span>
          <select
            value={relevance}
            onChange={(e) => setRelevance(Number(e.target.value))}
            className="h-9 w-full rounded-md border border-slate-600 bg-slate-950 px-2 text-sm text-slate-50 outline-none focus:border-cyan-400"
          >
            {[1, 2, 3, 4, 5].map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 rounded-lg border border-slate-800 bg-slate-900/70 px-2 py-2">
          <span className="text-[11px] font-medium text-slate-300">Clarity</span>
          <select
            value={clarity}
            onChange={(e) => setClarity(Number(e.target.value))}
            className="h-9 w-full rounded-md border border-slate-600 bg-slate-950 px-2 text-sm text-slate-50 outline-none focus:border-cyan-400"
          >
            {[1, 2, 3, 4, 5].map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1 rounded-lg border border-slate-800 bg-slate-900/70 px-2 py-2">
          <span className="text-[11px] font-medium text-slate-300">Realism</span>
          <select
            value={realism}
            onChange={(e) => setRealism(Number(e.target.value))}
            className="h-9 w-full rounded-md border border-slate-600 bg-slate-950 px-2 text-sm text-slate-50 outline-none focus:border-cyan-400"
          >
            {[1, 2, 3, 4, 5].map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="mt-2">
        <textarea
          placeholder="Optional note for this question"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          className="min-h-[54px] w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-50 placeholder:text-slate-500 outline-none focus:border-cyan-400"
          rows={2}
        />
      </div>

      <div className="mt-2 flex items-center justify-between gap-3">
        <button
          onClick={submit}
          className="inline-flex items-center justify-center rounded-lg bg-cyan-400 px-3 py-2 text-xs font-semibold text-slate-950 transition hover:bg-cyan-300 active:bg-cyan-500"
        >
          Submit rating
        </button>

        <div className="min-h-[16px] text-xs">
          {status === "saving" && <span className="text-slate-300">Saving…</span>}
          {status === "saved" && <span className="text-emerald-300">Saved</span>}
          {status && status !== "saving" && status !== "saved" && (
            <span className="text-rose-300">{status}</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default QuestionRater;
