import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { CheckCircle, ArrowLeft, AlertCircle, Loader2 } from "lucide-react";
import { getInterviewSummary, InterviewSummaryResponse } from "@/services/nilmaniService";
import "../styles/interview.css";

const FeedbackPage = () => {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<InterviewSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSummary = async () => {
      const sessionId = localStorage.getItem("nilmani_sessionId");

      if (!sessionId) {
        const cachedSummary = localStorage.getItem("nilmani_interviewSummary");
        if (cachedSummary) {
          try {
            setSummary(JSON.parse(cachedSummary));
          } catch (parseError) {
            setError("Summary data is unavailable. Please start a new interview.");
          }
        } else {
          setError("Session expired. Please start a new interview.");
        }

        setLoading(false);
        return;
      }

      try {
        const response = await getInterviewSummary(sessionId);
        setSummary(response);
        localStorage.setItem("nilmani_interviewSummary", JSON.stringify(response));
      } catch (fetchError) {
        console.error(fetchError);

        const cachedSummary = localStorage.getItem("nilmani_interviewSummary");
        if (cachedSummary) {
          try {
            setSummary(JSON.parse(cachedSummary));
          } catch (parseError) {
            setError(
              fetchError instanceof Error
                ? fetchError.message
                : "Unable to load interview summary"
            );
          }
        } else {
          setError(
            fetchError instanceof Error
              ? fetchError.message
              : "Unable to load interview summary"
          );
        }
      } finally {
        setLoading(false);
      }
    };

    void loadSummary();
  }, []);

  const handleStartNew = () => {
    localStorage.removeItem("nilmani_sessionId");
    localStorage.removeItem("nilmani_jdText");
    localStorage.removeItem("nilmani_chunksCount");
    localStorage.removeItem("nilmani_interviewSummary");
    navigate("/interview-prep");
  };

  const handleBackToModules = () => {
    navigate("/modules");
  };

  return (
    <div className="interview-page">
      <div className="interview-header">
        <div>
          <div className="interview-eyebrow">Completed</div>
          <h1 className="interview-title">Interview Summary</h1>
        </div>
      </div>

      <div className="interview-feedback-container">
        {loading ? (
          <Card className="interview-feedback-card success-card">
            <Loader2 className="w-16 h-16 text-primary mb-4 animate-spin" />
            <h2 className="interview-feedback-title">Loading your summary...</h2>
            <p className="interview-card-description">
              We are gathering the answer correctness and emotion analysis results.
            </p>
          </Card>
        ) : error && !summary ? (
          <Card className="interview-feedback-card success-card">
            <AlertCircle className="w-16 h-16 text-destructive mb-4" />
            <h2 className="interview-feedback-title">Summary unavailable</h2>
            <p className="interview-card-description">{error}</p>
          </Card>
        ) : (
          <>
            <Card className="interview-feedback-card success-card">
              <CheckCircle className="w-16 h-16 text-success mb-4" />
              <h2 className="interview-feedback-title">
                Interview Completed Successfully!
              </h2>
              <p className="interview-card-description">
                You've finished your AI-powered interview training session. Great work!
              </p>
            </Card>

            <div className="grid gap-4 md:grid-cols-2">
              <Card className="p-6">
                <div className="text-sm text-muted-foreground mb-2">Answer Correctness</div>
                <div className="text-4xl font-semibold text-foreground">
                  {summary?.answer_correctness_score?.toFixed(1) ?? "0.0"}%
                </div>
                <p className="text-sm text-muted-foreground mt-2">
                  Based on the evaluator's assessment of your answers against the job description.
                </p>
              </Card>

              <Card className="p-6">
                <div className="text-sm text-muted-foreground mb-2">Emotion Analysis</div>
                <div className="text-4xl font-semibold text-foreground">
                  {summary?.emotion_analysis_score?.toFixed(1) ?? "0.0"}%
                </div>
                <p className="text-sm text-muted-foreground mt-2">
                  Dominant emotion: {summary?.dominant_emotion ?? "Not available"}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  Latest emotion: {summary?.latest_emotion_label ?? "Not available"}
                  {summary?.latest_emotion_label ? ` (${summary.latest_emotion_confidence.toFixed(1)}%)` : ""}
                </p>
              </Card>
            </div>

            {(summary?.latest_feedback || summary?.latest_reasoning) && (
              <Card className="p-6">
                <div className="text-sm text-muted-foreground mb-2">Feedback</div>
                {summary?.latest_feedback && (
                  <p className="text-sm text-foreground leading-6">{summary.latest_feedback}</p>
                )}
                {summary?.latest_reasoning && (
                  <p className="text-sm text-muted-foreground mt-3">
                    Reasoning: {summary.latest_reasoning}
                  </p>
                )}
              </Card>
            )}
          </>
        )}

        <div className="interview-action-buttons">
          <Button onClick={handleStartNew} size="lg" className="w-full sm:w-auto">
            Start New Interview
          </Button>
          <Button
            onClick={handleBackToModules}
            variant="outline"
            size="lg"
            className="w-full sm:w-auto"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Modules
          </Button>
        </div>
      </div>
    </div>
  );
};

export default FeedbackPage;
