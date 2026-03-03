import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Briefcase,
  Target,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Award,
  BookOpen
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Spinner } from "@/components/ui/Spinner";
import api from "@/api/api";

export default function MLJobRecommendationsPage() {
  const { studentId } = useParams();
  const navigate = useNavigate();
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [metadata, setMetadata] = useState(null);

  useEffect(() => {
    const fetchRecommendations = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await api.get(
          `/students/${studentId}/jobs/recommend/ml?use_verified=true&threshold=70&top_k=10`
        );
        setRecommendations(response.data.recommendations);
        setMetadata({
          total: response.data.total_recommendations,
          threshold: response.data.threshold_used,
          usingVerified: response.data.using_verified_skills,
          mlEnabled: response.data.ml_enabled
        });
      } catch (err) {
        console.error("Error fetching ML job recommendations:", err);
        setError(err.response?.data || { message: err.message });
      } finally {
        setLoading(false);
      }
    };

    fetchRecommendations();
  }, [studentId]);

  const getReadinessColor = (level) => {
    const colors = {
      "Ready to Apply": "text-green-700 bg-green-50 border-green-200",
      "Almost Ready": "text-yellow-700 bg-yellow-50 border-yellow-200",
      "Developing": "text-orange-700 bg-orange-50 border-orange-200",
      "Early Stage": "text-red-700 bg-red-50 border-red-200"
    };
    return colors[level] || "text-gray-700 bg-gray-50 border-gray-200";
  };

  const getLevelBadgeColor = (level) => {
    const colors = {
      "Advanced": "bg-green-100 text-green-700",
      "Intermediate": "bg-blue-100 text-blue-700",
      "Beginner": "bg-yellow-100 text-yellow-700",
      "Not Assessed": "bg-gray-100 text-gray-700"
    };
    return colors[level] || "bg-gray-100 text-gray-700";
  };

  if (loading) return <Spinner />;

  return (
    <div className="container mx-auto max-w-7xl p-6 space-y-6">
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-foreground mb-2 flex items-center justify-center gap-2">
          <Target className="h-8 w-8 text-primary" />
          AI-Powered Job Recommendations
        </h2>
        <p className="text-muted-foreground">
          Intelligent job matching based on your verified skills and proficiency levels
        </p>
        {metadata && (
          <div className="mt-4 flex items-center justify-center gap-4 text-sm">
            <span className="inline-flex items-center gap-2 px-3 py-1 bg-primary/10 rounded-full">
              {metadata.mlEnabled && <Award className="h-4 w-4 text-primary" />}
              <span className="font-medium">
                {metadata.mlEnabled ? "ML-Enhanced" : "Standard Matching"}
              </span>
            </span>
            <span className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 rounded-full">
              {metadata.usingVerified && <CheckCircle2 className="h-4 w-4 text-blue-600" />}
              <span className="font-medium">
                {metadata.usingVerified ? "Verified Skills" : "Claimed Skills"}
              </span>
            </span>
          </div>
        )}
      </div>

      {error && <ErrorAlert error={error} />}

      {/* Recommendations */}
      <div className="space-y-6">
        {recommendations.length === 0 && !loading ? (
          <Card>
            <CardContent className="py-12 text-center">
              <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-lg font-medium">No recommendations found</p>
              <p className="text-sm text-muted-foreground mt-2">
                Complete your profile and take skill quizzes to get personalized recommendations
              </p>
            </CardContent>
          </Card>
        ) : (
          recommendations.map((job, index) => (
            <Card key={index} className="overflow-hidden hover:shadow-lg transition-shadow">
              {/* Job Header */}
              <CardHeader className="bg-gradient-to-r from-primary/5 to-primary/10 pb-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="px-2 py-1 bg-white rounded text-xs font-bold text-primary border">
                        #{index + 1}
                      </span>
                      <span className="px-2 py-1 bg-primary/20 rounded text-xs font-semibold">
                        {job.role_key}
                      </span>
                    </div>
                    <CardTitle className="text-xl">{job.title}</CardTitle>
                    <CardDescription className="text-sm mt-1">
                      {job.company}
                    </CardDescription>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-bold text-primary">
                      {job.match_score}%
                    </div>
                    <div className="text-xs text-muted-foreground">Match Score</div>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-4 pt-6">
                {/* Readiness Assessment */}
                <div className={`p-4 rounded-lg border-2 ${getReadinessColor(job.readiness.level)}`}>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold flex items-center gap-2">
                      <Target className="h-5 w-5" />
                      {job.readiness.level}
                    </h4>
                    <div className="text-sm font-medium">{job.skill_match_percentage}% Skills Match</div>
                  </div>
                  <p className="text-sm">{job.readiness.message}</p>
                </div>

                {/* Skill Breakdown */}
                <div className="grid md:grid-cols-3 gap-4 pt-2">
                  {/* Proficient Skills */}
                  <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                    <div className="flex items-center gap-2 mb-3">
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                      <h4 className="font-semibold text-green-900">
                        Proficient ({job.proficient_skills_count})
                      </h4>
                    </div>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {job.proficient_skills.slice(0, 5).map((skill, i) => (
                        <div key={i} className="flex items-center justify-between text-sm">
                          <span className="font-medium">{skill.skill}</span>
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 rounded text-xs ${getLevelBadgeColor(skill.level)}`}>
                              {skill.level}
                            </span>
                            <span className="text-green-700 font-semibold">{skill.score}</span>
                          </div>
                        </div>
                      ))}
                      {job.proficient_skills.length > 5 && (
                        <p className="text-xs text-green-700 font-medium">
                          +{job.proficient_skills.length - 5} more
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Needs Improvement */}
                  <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                    <div className="flex items-center gap-2 mb-3">
                      <TrendingUp className="h-5 w-5 text-yellow-600" />
                      <h4 className="font-semibold text-yellow-900">
                        Improve ({job.needs_improvement_count})
                      </h4>
                    </div>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {job.needs_improvement.slice(0, 5).map((skill, i) => (
                        <div key={i} className="text-sm">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium">{skill.skill}</span>
                            <span className="text-yellow-700 font-semibold">{skill.score}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="flex-1 bg-yellow-200 rounded-full h-1.5">
                              <div
                                className="bg-yellow-600 h-1.5 rounded-full"
                                style={{ width: `${skill.score}%` }}
                              />
                            </div>
                            <span className="text-xs text-yellow-700">-{skill.gap}</span>
                          </div>
                          <p className="text-xs text-yellow-700 mt-1">{skill.recommendation}</p>
                        </div>
                      ))}
                      {job.needs_improvement.length > 5 && (
                        <p className="text-xs text-yellow-700 font-medium">
                          +{job.needs_improvement.length - 5} more
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Missing Skills */}
                  <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                    <div className="flex items-center gap-2 mb-3">
                      <XCircle className="h-5 w-5 text-red-600" />
                      <h4 className="font-semibold text-red-900">
                        Missing ({job.missing_skills_count})
                      </h4>
                    </div>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {job.missing_skills.slice(0, 5).map((skill, i) => (
                        <div key={i} className="text-sm">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium">{skill.skill}</span>
                            <BookOpen className="h-4 w-4 text-red-600" />
                          </div>
                          <p className="text-xs text-red-700">{skill.recommendation}</p>
                        </div>
                      ))}
                      {job.missing_skills.length > 5 && (
                        <p className="text-xs text-red-700 font-medium">
                          +{job.missing_skills.length - 5} more
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Next Steps */}
                {job.next_steps && job.next_steps.length > 0 && (
                  <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                    <h4 className="font-semibold text-blue-900 mb- flex items-center gap-2">
                      <ArrowRight className="h-5 w-5" />
                      Recommended Next Steps
                    </h4>
                    <ul className="space-y-2 mt-3">
                      {job.next_steps.map((step, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm">
                          <span className="text-blue-600 font-bold">{i + 1}.</span>
                          <span>{step}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-3 pt-2">
                  <Button 
                    className="flex-1"
                    onClick={() => navigate(`/jobs/${job.job_id}`)}
                  >
                    <Briefcase className="h-4 w-4 mr-2" />
                    View Job Details
                  </Button>
                  <Button 
                    variant="outline"
                    onClick={() => navigate(`/students/${studentId}/skills`)}
                  >
                    Improve Skills
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Back Button */}
      <div className="text-center pt-6">
        <Button variant="outline" onClick={() => navigate(`/students/${studentId}/skills`)}>
          Back to Skills
        </Button>
      </div>
    </div>
  );
}
