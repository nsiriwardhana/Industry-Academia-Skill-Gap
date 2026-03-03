import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChevronLeft, ChevronDown, ChevronUp, BookOpen, TrendingUp, Info } from 'lucide-react';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Spinner } from '../components/ui/Spinner';
import { ErrorAlert } from '../components/ui/ErrorAlert';

const API_BASE = 'http://localhost:8000';

/**
 * ExplainChildSkillPage
 * Shows detailed explanation of how a child skill score is calculated
 */
export function ExplainChildSkillPage() {
  const { studentId, skillName } = useParams();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [skillData, setSkillData] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [showMathDetails, setShowMathDetails] = useState(false);

  useEffect(() => {
    fetchData();
  }, [studentId, skillName]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch skill explanation (includes summary and evidence)
      const response = await fetch(`${API_BASE}/students/${studentId}/explain/skill/${encodeURIComponent(skillName)}`);

      if (!response.ok) {
        throw new Error('Failed to fetch skill explanation');
      }

      const data = await response.json();

      if (!data.skill_summary) {
        throw new Error('Skill not found');
      }

      setSkillData(data.skill_summary);
      setEvidence(data.evidence || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

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

  if (!skillData) return null;

  // Calculate totals - backend doesn't return evidence_weight, so calculate from displayed score
  const totalContribution = evidence.reduce((sum, e) => sum + (e.contribution || 0), 0);
  // Derive totalWeight from the score formula: score = (contribution / weight) * 100
  // So: weight = (contribution / score) * 100
  const totalWeight = skillData.claimed_score > 0 ? (totalContribution / skillData.claimed_score) * 100 : totalContribution;
  const calculatedScore = skillData.claimed_score; // Use the score from backend

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <Button 
            variant="ghost" 
            onClick={() => navigate(`/students/${studentId}/skills`)}
            className="mb-4"
          >
            <ChevronLeft className="w-4 h-4 mr-2" />
            Back to Skills
          </Button>
          <div className="flex items-center gap-3">
            <BookOpen className="w-10 h-10 text-blue-600" />
            <div>
              <h1 className="text-3xl font-bold text-slate-900">How your score is calculated</h1>
              <p className="text-lg text-slate-600 mt-1">{skillName}</p>
            </div>
          </div>
        </div>

        {/* Score Display */}
        <Card className="border-blue-200 shadow-lg">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-slate-600 mb-1">Your Score</div>
                <div className="text-5xl font-bold text-blue-600">{skillData.claimed_score}%</div>
                <div className="text-sm text-slate-600 mt-2">
                  Level: <span className="font-semibold">{skillData.claimed_level}</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-slate-600 mb-1">Confidence</div>
                <div className="text-3xl font-bold text-green-600">
                  {(skillData.confidence * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Section 1: In Simple Words */}
        <Card>
          <CardHeader>
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Info className="w-5 h-5 text-blue-600" />
              In Simple Words
            </h2>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-slate-700">
              <li className="flex gap-2">
                <span className="text-blue-600 font-bold">•</span>
                <span>Your score is based on <strong>your grades</strong> in courses related to this skill.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-600 font-bold">•</span>
                <span>Better grades contribute more points. <strong>Recent courses count more</strong> than older ones.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-600 font-bold">•</span>
                <span>Each course has a "weight" based on <strong>credits, recency</strong>, and how strongly it teaches this skill.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-600 font-bold">•</span>
                <span>We calculate: <strong>(Total Grade Points × Weights) ÷ (Total Weights) × 100</strong></span>
              </li>
            </ul>
          </CardContent>
        </Card>

        {/* Section 2: Your Evidence */}
        <Card>
          <CardHeader>
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-600" />
              Your Evidence ({evidence.length} courses)
            </h2>
          </CardHeader>
          <CardContent>
            {evidence.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-100 border-b-2 border-slate-300">
                    <tr>
                      <th className="text-left py-3 px-3 font-semibold text-slate-700">Course</th>
                      <th className="text-center py-3 px-3 font-semibold text-slate-700">Grade</th>
                      <th className="text-right py-3 px-3 font-semibold text-slate-700">Credits</th>
                      <th className="text-right py-3 px-3 font-semibold text-slate-700">Recency</th>
                      <th className="text-right py-3 px-3 font-semibold text-slate-700">Relevance</th>
                      <th className="text-right py-3 px-3 font-semibold text-slate-700">Contribution</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {evidence.map((row, idx) => (
                      <tr key={idx} className="hover:bg-blue-50">
                        <td className="py-3 px-3 font-medium text-slate-900">{row.course_code}</td>
                        <td className="py-3 px-3 text-center">
                          <span className="inline-block px-2 py-1 bg-green-100 text-green-700 rounded font-semibold">
                            {row.grade}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-right text-slate-700">{row.credits}</td>
                        <td className="py-3 px-3 text-right text-slate-700">{row.recency?.toFixed(2) || 'N/A'}</td>
                        <td className="py-3 px-3 text-right text-slate-700">{row.map_weight?.toFixed(2) || 'N/A'}</td>
                        <td className="py-3 px-3 text-right font-bold text-blue-600">
                          {row.contribution?.toFixed(2) || 'N/A'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-slate-100 border-t-2 border-slate-300">
                    <tr>
                      <td colSpan="5" className="py-3 px-3 text-right font-bold text-slate-800">TOTALS:</td>
                      <td className="py-3 px-3 text-right font-bold text-blue-700 text-base">
                        {totalContribution.toFixed(2)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            ) : (
              <p className="text-slate-500 text-center py-8">No evidence courses found</p>
            )}

            <div className="mt-4 text-xs text-slate-600 space-y-1">
              <p><strong>Recency:</strong> 1.00 = most recent courses, lower values = older courses</p>
              <p><strong>Relevance:</strong> How strongly this course teaches this skill (0.0 - 1.0)</p>
              <p><strong>Contribution:</strong> How much this course adds to your overall score</p>
            </div>
          </CardContent>
        </Card>

        {/* Section 3: Totals and Final Score */}
        <Card className="border-blue-200">
          <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50">
            <h2 className="text-xl font-semibold text-blue-900">Final Score Calculation</h2>
          </CardHeader>
          <CardContent className="p-6">
            <div className="space-y-4">
              <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                <div className="text-sm text-blue-700">Total Contribution</div>
                <div className="text-3xl font-bold text-blue-900">{totalContribution.toFixed(2)}</div>
                <div className="text-xs text-blue-600 mt-1">Sum of all course contributions</div>
              </div>

              <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-5 rounded-xl">
                <div className="text-sm opacity-90 mb-2">Your Score:</div>
                <div className="text-4xl font-bold mb-3">{calculatedScore.toFixed(1)}%</div>
                <div className="text-xs opacity-80">
                  Calculated from {evidence.length} course{evidence.length !== 1 ? 's' : ''} with weighted contributions
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Section 4: Confidence */}
        <Card>
          <CardHeader>
            <h2 className="text-xl font-semibold">Confidence Score</h2>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-6">
              <div className="text-5xl font-bold text-green-600">
                {(skillData.confidence * 100).toFixed(0)}%
              </div>
              <div className="flex-1">
                <p className="text-slate-700 mb-2">
                  This shows how <strong>reliable</strong> your score is based on the amount of evidence we have.
                </p>
                <p className="text-sm text-slate-600">
                  More courses with higher weights = higher confidence. 
                  {skillData.confidence >= 0.8 ? ' Your confidence is high! ✓' : 
                   skillData.confidence >= 0.5 ? ' Your confidence is moderate.' : 
                   ' More courses would increase confidence.'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Section 5: Math Details (Collapsible) */}
        <Card>
          <CardContent className="p-4">
            <button
              onClick={() => setShowMathDetails(!showMathDetails)}
              className="w-full flex items-center justify-between text-left hover:bg-slate-50 p-2 rounded"
            >
              <span className="font-semibold text-slate-900">🔬 Math Details (for the curious)</span>
              {showMathDetails ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
            </button>
            
            {showMathDetails && (
              <div className="mt-4 p-4 bg-slate-50 rounded-lg space-y-3 text-sm font-mono">
                <div>
                  <div className="text-xs text-slate-600 mb-1">Evidence Weight:</div>
                  <div className="text-slate-900">evidence_weight = map_weight × credits × recency</div>
                </div>
                <div>
                  <div className="text-xs text-slate-600 mb-1">Contribution:</div>
                  <div className="text-slate-900">contribution = grade_norm × evidence_weight</div>
                </div>
                <div>
                  <div className="text-xs text-slate-600 mb-1">Claimed Score:</div>
                  <div className="text-slate-900">claimed_score = (sum(contribution) / sum(evidence_weight)) × 100</div>
                </div>
                <div>
                  <div className="text-xs text-slate-600 mb-1">Confidence:</div>
                  <div className="text-slate-900">confidence = 1 − exp(−0.25 × sum(evidence_weight))</div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
