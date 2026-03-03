import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card, CardHeader, CardContent } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Spinner } from "../components/ui/Spinner";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { getSkillExplanation } from "../api/api";
import { ChevronLeft, ChevronDown, Info, Star, GraduationCap } from "lucide-react";

function n2(num, digits = 2) {
  const v = Number(num);
  if (!Number.isFinite(v)) return "N/A";
  return v.toFixed(digits);
}

function n4(num) {
  return n2(num, 4);
}

function pct(num, digits = 0) {
  const v = Number(num);
  if (!Number.isFinite(v)) return "N/A";
  return `${v.toFixed(digits)}%`;
}

function freshnessLabel(recency) {
  const r = Number(recency);
  if (!Number.isFinite(r)) return "N/A";
  if (r >= 0.85) return "Very recent";
  if (r >= 0.55) return "Recent";
  if (r >= 0.35) return "Older";
  return "Old";
}

function barWidth(value, max) {
  const v = Number(value);
  const m = Number(max);
  if (!Number.isFinite(v) || !Number.isFinite(m) || m <= 0) return 0;
  return Math.max(0, Math.min(100, (v / m) * 100));
}

export function SkillExplainPage() {
  const { studentId, skillName } = useParams();
  const navigate = useNavigate();

  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getSkillExplanation(studentId, skillName, "parent");
        setExplanation(data);
      } catch (err) {
        setError(err?.message || "Failed to load explanation");
      } finally {
        setLoading(false);
      }
    })();
  }, [studentId, skillName]);

  const rows = explanation?.course_breakdown || [];

  const totals = useMemo(() => {
    const tc = Number(explanation?.calculation?.total_contribution ?? 0);
    const tw = Number(explanation?.calculation?.total_weight ?? 0);
    const ratio = tw > 0 ? tc / tw : 0;
    return { tc, tw, ratio };
  }, [explanation]);

  const score = Number(explanation?.score ?? 0);
  const level = explanation?.level || "N/A";
  const confidencePct = explanation ? pct(explanation.confidence * 100, 0) : "N/A";

  // Pick the most impactful row (highest “points” / contribution)
  const topRow = useMemo(() => {
    if (!rows.length) return null;
    return [...rows].sort((a, b) => Number(b.contribution) - Number(a.contribution))[0];
  }, [rows]);

  const maxWeight = useMemo(() => {
    if (!rows.length) return 0;
    return Math.max(...rows.map(r => Number(r.weight) || 0));
  }, [rows]);

  const maxContribution = useMemo(() => {
    if (!rows.length) return 0;
    return Math.max(...rows.map(r => Number(r.contribution) || 0));
  }, [rows]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Spinner size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 p-6">
        <div className="max-w-4xl mx-auto">
          <ErrorAlert message={error} />
          <Button onClick={() => navigate(`/students/${studentId}/skills`)} className="mt-4">
            <ChevronLeft className="w-4 h-4 mr-2" />
            Back to Skills
          </Button>
        </div>
      </div>
    );
  }

  if (!explanation) return null;

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <Button variant="ghost" onClick={() => navigate(`/students/${studentId}/skills`)} className="mb-4">
              <ChevronLeft className="w-4 h-4 mr-2" />
              Back to Skills
            </Button>

            <div className="flex items-center gap-3">
              <Info className="w-7 h-7 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-slate-900">{explanation.skill_name}</h1>
                <p className="text-slate-600 mt-1">
                  We used your grades in related courses. Courses count more when they are more relevant, have more credits, and are more recent.
                </p>
              </div>
            </div>
          </div>

          <div className="text-right">
            <div className="text-4xl font-bold text-slate-900">{pct(score, 0)}</div>
            <div className="text-sm font-semibold text-slate-600 mt-1">{level}</div>
            <div className="mt-2 text-sm text-slate-600">
              Confidence: <span className="font-semibold text-slate-900">{confidencePct}</span>
            </div>
          </div>
        </div>

        {/* 1) What affects the score (no math) */}
        <Card className="shadow-md">
          <CardHeader className="bg-white">
            <h2 className="text-lg font-semibold text-slate-900">What affects your score</h2>
          </CardHeader>
          <CardContent className="grid sm:grid-cols-3 gap-3 pt-4">
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
              <div className="font-semibold text-slate-900">Grade</div>
              <div className="text-sm text-slate-600 mt-1">Better grades increase the score.</div>
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
              <div className="font-semibold text-slate-900">Credits</div>
              <div className="text-sm text-slate-600 mt-1">Higher credit courses count more.</div>
            </div>
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
              <div className="font-semibold text-slate-900">Freshness + Relevance</div>
              <div className="text-sm text-slate-600 mt-1">Recent and highly related courses count more.</div>
            </div>
          </CardContent>
        </Card>

        {/* 2) One worked example (THIS is what makes it clear) */}
        <Card className="shadow-md">
          <CardHeader className="bg-white">
            <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
              <Star className="w-5 h-5 text-amber-500" />
              Example: the course that affected your score the most
            </h2>
            <p className="text-sm text-slate-600 mt-1">
              We show one course as an example so you can understand the method quickly.
            </p>
          </CardHeader>

          <CardContent className="pt-4">
            {!topRow ? (
              <div className="text-sm text-slate-600">No course evidence available.</div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-start justify-between gap-3 bg-amber-50 border border-amber-200 rounded-lg p-4">
                  <div>
                    <div className="text-sm text-slate-600">Course</div>
                    <div className="text-lg font-bold text-slate-900">{topRow.course_code}</div>
                    <div className="mt-2 flex gap-2 flex-wrap text-sm">
                      <span className="px-2 py-1 rounded bg-white border border-slate-200">
                        Grade: <span className="font-semibold">{topRow.grade}</span>
                      </span>
                      <span className="px-2 py-1 rounded bg-white border border-slate-200">
                        Credits: <span className="font-semibold">{topRow.credits}</span>
                      </span>
                      <span className="px-2 py-1 rounded bg-white border border-slate-200">
                        Freshness: <span className="font-semibold">{freshnessLabel(topRow.recency)} ({n2(topRow.recency)})</span>
                      </span>
                      <span className="px-2 py-1 rounded bg-white border border-slate-200">
                        Relevance: <span className="font-semibold">{n2(topRow.map_weight)}</span>
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-slate-600">Points added</div>
                    <div className="text-2xl font-bold text-blue-700">{n4(topRow.contribution)}</div>
                  </div>
                </div>

                <div className="grid sm:grid-cols-2 gap-3">
                  <div className="bg-white border border-slate-200 rounded-lg p-4">
                    <div className="text-sm font-semibold text-slate-900">How much this course counts</div>
                    <div className="text-sm text-slate-600 mt-1">
                      “Counts” becomes higher when credits, freshness, and relevance are higher.
                    </div>

                    <div className="mt-3">
                      <div className="flex items-center justify-between text-xs text-slate-600">
                        <span>Counts (importance)</span>
                        <span className="font-semibold text-slate-900">{n4(topRow.weight)}</span>
                      </div>
                      <div className="w-full bg-slate-200 rounded-full h-2 mt-2 overflow-hidden">
                        <div
                          className="h-2 bg-indigo-600 rounded-full"
                          style={{ width: `${barWidth(topRow.weight, maxWeight)}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="bg-white border border-slate-200 rounded-lg p-4">
                    <div className="text-sm font-semibold text-slate-900">How many points it added</div>
                    <div className="text-sm text-slate-600 mt-1">
                      Points depend on your grade and how much the course counts.
                    </div>

                    <div className="mt-3">
                      <div className="flex items-center justify-between text-xs text-slate-600">
                        <span>Points added</span>
                        <span className="font-semibold text-slate-900">{n4(topRow.contribution)}</span>
                      </div>
                      <div className="w-full bg-slate-200 rounded-full h-2 mt-2 overflow-hidden">
                        <div
                          className="h-2 bg-blue-600 rounded-full"
                          style={{ width: `${barWidth(topRow.contribution, maxContribution)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <details className="bg-white border border-slate-200 rounded-lg p-4">
                  <summary className="cursor-pointer font-semibold text-slate-900 flex items-center justify-between">
                    Show the math for this example (optional)
                    <ChevronDown className="w-4 h-4" />
                  </summary>
                  <div className="mt-3 text-sm text-slate-700 space-y-2">
                    <div className="font-mono bg-slate-50 p-3 rounded border border-slate-200">
                      counts = relevance × credits × freshness
                    </div>
                    <div className="font-mono bg-slate-50 p-3 rounded border border-slate-200">
                      points = grade_norm × counts
                    </div>
                    <div className="text-xs text-slate-500">
                      You do not need this part to understand the result. It is here for transparency.
                    </div>
                  </div>
                </details>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 3) Evidence list (simple labels) */}
        <Card className="shadow-md">
          <CardHeader className="bg-white">
            <h2 className="text-lg font-semibold text-slate-900">Courses used</h2>
            <p className="text-sm text-slate-600 mt-1">
              Each row shows how much a course counted and how many points it added.
            </p>
          </CardHeader>

          <CardContent className="pt-4">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-100 border-b border-slate-200">
                  <tr>
                    <th className="text-left py-3 px-3">Course</th>
                    <th className="text-center py-3 px-3">Grade</th>
                    <th className="text-center py-3 px-3">Credits</th>
                    <th className="text-center py-3 px-3">Freshness</th>
                    <th className="text-center py-3 px-3">Relevance</th>
                    <th className="text-right py-3 px-3">Counts</th>
                    <th className="text-right py-3 px-3">Points</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {rows.map((r, idx) => (
                    <tr key={idx} className="bg-white">
                      <td className="py-3 px-3 font-semibold text-slate-900">{r.course_code}</td>
                      <td className="py-3 px-3 text-center">{r.grade}</td>
                      <td className="py-3 px-3 text-center">{r.credits}</td>
                      <td className="py-3 px-3 text-center">
                        <div className="font-semibold">{n2(r.recency)}</div>
                        <div className="text-xs text-slate-500">{freshnessLabel(r.recency)}</div>
                      </td>
                      <td className="py-3 px-3 text-center">{n2(r.map_weight)}</td>
                      <td className="py-3 px-3 text-right">{n4(r.weight)}</td>
                      <td className="py-3 px-3 text-right font-semibold text-blue-700">{n4(r.contribution)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-slate-50 border-t border-slate-200">
                  <tr>
                    <td colSpan={5} className="py-3 px-3 text-right font-semibold text-slate-700">Totals</td>
                    <td className="py-3 px-3 text-right font-semibold">{n4(totals.tw)}</td>
                    <td className="py-3 px-3 text-right font-semibold text-blue-700">{n4(totals.tc)}</td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* 4) Final score: one line */}
        <Card className="shadow-md">
          <CardHeader className="bg-white">
            <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
              <GraduationCap className="w-5 h-5 text-slate-700" />
              Final score
            </h2>
          </CardHeader>
          <CardContent className="pt-4 space-y-3">
            <div className="grid sm:grid-cols-3 gap-3">
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                <div className="text-xs text-slate-600">Total points</div>
                <div className="text-2xl font-bold text-slate-900">{n4(totals.tc)}</div>
              </div>
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                <div className="text-xs text-slate-600">Total counts</div>
                <div className="text-2xl font-bold text-slate-900">{n4(totals.tw)}</div>
              </div>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="text-xs text-slate-600">Final score</div>
                <div className="text-2xl font-bold text-blue-700">{pct(score, 0)}</div>
              </div>
            </div>

            <div className="bg-slate-900 text-white rounded-lg p-4 font-mono text-sm">
              Score = total points ÷ total counts = {n4(totals.tc)} ÷ {n4(totals.tw)} = {n2(totals.ratio)} → {pct(totals.ratio * 100, 1)}
            </div>

            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <div className="text-sm font-semibold text-slate-900">Confidence</div>
              <div className="mt-1 text-slate-700 text-sm">
                Confidence shows how much evidence supports this score. If more related courses contribute in the future, confidence will increase.
              </div>
              <div className="mt-2 text-lg font-bold text-slate-900">{confidencePct}</div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
