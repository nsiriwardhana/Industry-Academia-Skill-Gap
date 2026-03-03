import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChevronLeft, ChevronDown, ChevronUp, Award, TrendingUp, Info } from 'lucide-react';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Spinner } from '../components/ui/Spinner';
import { ErrorAlert } from '../components/ui/ErrorAlert';

const API_BASE = 'http://localhost:8000';

/**
 * ExplainParentSkillPage
 * Shows detailed explanation of how a parent skill score is calculated
 * Parent skills aggregate multiple child skills
 */
export function ExplainParentSkillPage() {
  const { studentId, parentSkill, skillName } = useParams();
  const navigate = useNavigate();
  
  // Support both route patterns: /skills/:skillName/explain and /explain/parent/:parentSkill
  const actualParentSkill = parentSkill || skillName;
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [skillData, setSkillData] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [showMathDetails, setShowMathDetails] = useState(false);

  useEffect(() => {
    fetchData();
  }, [studentId, actualParentSkill]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch parent skill explanation (includes summary and evidence)
      const response = await fetch(`${API_BASE}/students/${studentId}/explain/parent-skill/${encodeURIComponent(actualParentSkill)}`);

      if (!response.ok) {
        throw new Error('Failed to fetch parent skill explanation');
      }

      const data = await response.json();

      if (!data.parent_summary) {
        throw new Error('Parent skill not found');
      }

      setSkillData(data.parent_summary);
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

  // Calculate totals
  const totalContribution = evidence.reduce((sum, e) => sum + (e.contribution || 0), 0);
  const totalWeight = evidence.reduce((sum, e) => sum + (e.evidence_weight || 0), 0);
  const calculatedScore = totalWeight > 0 ? (totalContribution / totalWeight) * 100 : 0;

  // Group by child skill
  const childSkillGroups = evidence.reduce((acc, row) => {
    if (!acc[row.child_skill]) {
      acc[row.child_skill] = [];
    }
    acc[row.child_skill].push(row);
    return acc;
  }, {});

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
            <Award className="w-10 h-10 text-purple-600" />
            <div>
              <h1 className="text-3xl font-bold text-slate-900">How your score is calculated</h1>
              <p className="text-lg text-slate-600 mt-1">{actualParentSkill}</p>
            </div>
          </div>
        </div>

        {/* Score Display */}
        <Card className="border-purple-200 shadow-lg">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm text-slate-600 mb-1">Your Score</div>
                <div className="text-5xl font-bold text-purple-600">{skillData.parent_score}%</div>
                <div className="text-sm text-slate-600 mt-2">
                  Level: <span className="font-semibold">{skillData.parent_level}</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-slate-600 mb-1">Confidence</div>
                <div className="text-3xl font-bold text-green-600">
                  {(skillData.confidence * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  {Object.keys(childSkillGroups).length} related skills
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Section 1: In Simple Words */}
        <Card>
          <CardHeader>
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Info className="w-5 h-5 text-purple-600" />
              In Simple Words
            </h2>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-slate-700">
              <li className="flex gap-2">
                <span className="text-purple-600 font-bold">•</span>
                <span>This is a <strong>parent skill</strong> that combines {Object.keys(childSkillGroups).length} related sub-skills.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-purple-600 font-bold">•</span>
                <span>Your score comes from <strong>all courses</strong> that teach any of these sub-skills.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-purple-600 font-bold">•</span>
                <span>Better grades in recent, relevant courses contribute more points.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-purple-600 font-bold">•</span>
                <span>Final score: <strong>(Total Grade Points × Weights) ÷ (Total Weights) × 100</strong></span>
              </li>
            </ul>
          </CardContent>
        </Card>

        {/* Child Skills Breakdown */}
        <Card>
          <CardHeader>
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-600" />
              Sub-skills Included ({Object.keys(childSkillGroups).length})
            </h2>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {Object.entries(childSkillGroups).map(([childSkill, courses]) => {
                const childContribution = courses.reduce((sum, c) => sum + (c.contribution || 0), 0);
                const childWeight = courses.reduce((sum, c) => sum + (c.evidence_weight || 0), 0);
                
                return (
                  <details key={childSkill} className="border border-slate-200 rounded-lg">
                    <summary className="cursor-pointer p-4 hover:bg-slate-50 font-semibold text-slate-900 flex items-center justify-between">
                      <span>{childSkill}</span>
                      <span className="text-sm text-blue-600 font-normal">
                        {courses.length} course{courses.length !== 1 ? 's' : ''}
                      </span>
                    </summary>
                    <div className="p-4 bg-slate-50 border-t border-slate-200">
                      <table className="w-full text-sm">
                        <thead className="border-b border-slate-300">
                          <tr>
                            <th className="text-left py-2 px-2">Course</th>
                            <th className="text-center py-2 px-2">Grade</th>
                            <th className="text-right py-2 px-2">Credits</th>
                            <th className="text-right py-2 px-2">Weight</th>
                            <th className="text-right py-2 px-2">Points</th>
                          </tr>
                        </thead>
                        <tbody>
                          {courses.map((course, idx) => (
                            <tr key={idx} className="border-b border-slate-200">
                              <td className="py-2 px-2">{course.course_code}</td>
                              <td className="py-2 px-2 text-center">
                                <span className="inline-block px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-semibold">
                                  {course.grade}
                                </span>
                              </td>
                              <td className="py-2 px-2 text-right">{course.credits}</td>
                              <td className="py-2 px-2 text-right font-medium text-purple-600">
                                {course.evidence_weight.toFixed(2)}
                              </td>
                              <td className="py-2 px-2 text-right font-bold text-blue-600">
                                {course.contribution.toFixed(2)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                        <tfoot className="bg-slate-100 border-t-2 border-slate-300">
                          <tr>
                            <td colSpan="3" className="py-2 px-2 text-right font-semibold">Subtotal:</td>
                            <td className="py-2 px-2 text-right font-bold text-purple-700">
                              {childWeight.toFixed(2)}
                            </td>
                            <td className="py-2 px-2 text-right font-bold text-blue-700">
                              {childContribution.toFixed(2)}
                            </td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  </details>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Section 3: Totals and Final Score */}
        <Card className="border-purple-200">
          <CardHeader className="bg-gradient-to-r from-purple-50 to-indigo-50">
            <h2 className="text-xl font-semibold text-purple-900">Final Score Calculation</h2>
          </CardHeader>
          <CardContent className="p-6">
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                  <div className="text-sm text-blue-700">Total Contribution</div>
                  <div className="text-3xl font-bold text-blue-900">{totalContribution.toFixed(2)}</div>
                  <div className="text-xs text-blue-600 mt-1">From all {evidence.length} courses</div>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                  <div className="text-sm text-purple-700">Total Weight</div>
                  <div className="text-3xl font-bold text-purple-900">{totalWeight.toFixed(2)}</div>
                  <div className="text-xs text-purple-600 mt-1">Combined importance</div>
                </div>
              </div>

              <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-5 rounded-xl">
                <div className="text-sm opacity-90 mb-2">Formula:</div>
                <div className="font-mono text-base mb-3">
                  Score = (Total Contribution ÷ Total Weight) × 100
                </div>
                <div className="font-mono text-base mb-3">
                  Score = ({totalContribution.toFixed(2)} ÷ {totalWeight.toFixed(2)}) × 100
                </div>
                <div className="font-mono text-base mb-3">
                  Score = {(totalContribution / totalWeight).toFixed(4)} × 100
                </div>
                <div className="pt-3 border-t border-white/30">
                  <div className="text-sm opacity-90">Your Final Score:</div>
                  <div className="text-4xl font-bold">{calculatedScore.toFixed(1)}%</div>
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
                  Shows how <strong>reliable</strong> this score is based on the breadth and depth of evidence across {Object.keys(childSkillGroups).length} sub-skills.
                </p>
                <p className="text-sm text-slate-600">
                  More courses across more sub-skills = higher confidence.
                  {skillData.confidence >= 0.8 ? ' Your confidence is excellent! ✓' : 
                   skillData.confidence >= 0.5 ? ' Your confidence is good.' : 
                   ' More related courses would increase confidence.'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Section 5: Math Details */}
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
                  <div className="text-xs text-slate-600 mb-1">Evidence Weight (per course):</div>
                  <div className="text-slate-900">evidence_weight = map_weight × credits × recency</div>
                </div>
                <div>
                  <div className="text-xs text-slate-600 mb-1">Contribution (per course):</div>
                  <div className="text-slate-900">contribution = grade_norm × evidence_weight</div>
                </div>
                <div>
                  <div className="text-xs text-slate-600 mb-1">Parent Score:</div>
                  <div className="text-slate-900">parent_score = (sum(all_contributions) / sum(all_weights)) × 100</div>
                </div>
                <div>
                  <div className="text-xs text-slate-600 mb-1">Confidence:</div>
                  <div className="text-slate-900">confidence = 1 − exp(−0.25 × sum(all_weights))</div>
                </div>
                <div className="mt-3 pt-3 border-t border-slate-300">
                  <div className="text-xs text-slate-600 mb-2">Notes:</div>
                  <div className="text-xs text-slate-700 space-y-1">
                    <p>• Grade normalization converts letter grades to numerical values (A=4.0, B=3.0, etc.)</p>
                    <p>• Recency factor: more recent courses have values closer to 1.0</p>
                    <p>• Map weight: how strongly each course teaches the specific sub-skill (0.0-1.0)</p>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
