import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { BookOpen, Send } from "lucide-react";
import { generateQuizFromBank, submitQuiz } from "@/api/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Spinner } from "@/components/ui/Spinner";

export default function QuizPage() {
  const navigate = useNavigate();
  const { studentId } = useParams();
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchQuiz = async () => {
      setLoading(true);
      setError(null);

      try {
        const data = await generateQuizFromBank(studentId);
        setQuiz(data);
        // Initialize answers object
        const initialAnswers = {};
        data.questions?.forEach(q => {
          initialAnswers[q.question_id] = null;
        });
        setAnswers(initialAnswers);
      } catch (err) {
        setError(err.response?.data || { message: err.message });
      } finally {
        setLoading(false);
      }
    };

    fetchQuiz();
  }, [studentId]);

  const handleAnswerChange = (questionId, option) => {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: option,
    }));
  };

  const handleSubmit = async () => {
    // Check if all questions are answered
    const unanswered = Object.values(answers).filter(a => a === null).length;
    if (unanswered > 0) {
      setError({ message: `Please answer all questions. ${unanswered} question(s) remaining.` });
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const formattedAnswers = Object.entries(answers).map(([question_id, selected_option]) => ({
        question_id: parseInt(question_id),
        selected_option,
      }));

      const result = await submitQuiz(studentId, quiz.attempt_id, formattedAnswers);
      
      // Save to localStorage as backup
      localStorage.setItem(`quiz_result_${quiz.attempt_id}`, JSON.stringify(result));
      
      // Navigate with attemptId in URL and state
      navigate(`/students/${studentId}/results/${quiz.attempt_id}`, { state: { result } });
    } catch (err) {
      setError(err.response?.data || { message: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <Spinner />;
  if (error && !quiz) return <div className="container mx-auto max-w-4xl p-6"><ErrorAlert error={error} /></div>;

  const answeredCount = Object.values(answers).filter(a => a !== null).length;
  const totalQuestions = quiz?.questions?.length || 0;

  return (
    <div className="container mx-auto max-w-4xl p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="h-6 w-6" />
            Skill Validation Quiz
          </CardTitle>
          <CardDescription>
            Answer all questions to validate your skills
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="bg-muted/50 p-4 rounded-md mb-6">
            <p className="text-sm font-medium">
              Progress: {answeredCount} / {totalQuestions} questions answered
            </p>
            <div className="mt-2 h-2 bg-background rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-300"
                style={{ width: `${(answeredCount / totalQuestions) * 100}%` }}
              />
            </div>
          </div>

          {error && <ErrorAlert error={error} />}
        </CardContent>
      </Card>

      <div className="space-y-4">
        {quiz?.questions?.map((question, index) => (
          <Card key={question.question_id}>
            <CardHeader>
              <CardTitle className="text-lg">
                Question {index + 1}
              </CardTitle>
              <div className="flex gap-2 text-xs text-muted-foreground">
                <span className="bg-secondary px-2 py-1 rounded">
                  {question.parent_skill}
                </span>
                <span className="bg-secondary px-2 py-1 rounded">
                  Difficulty: {question.difficulty_level}
                </span>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-base font-medium">{question.question_text}</p>
              
              <div className="space-y-2">
                {['A', 'B', 'C', 'D'].map((option) => (
                  <label
                    key={option}
                    className={`flex items-start gap-3 p-4 rounded-lg border-2 cursor-pointer transition-colors ${
                      answers[question.question_id] === option
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-primary/50'
                    }`}
                  >
                    <input
                      type="radio"
                      name={`question-${question.question_id}`}
                      value={option}
                      checked={answers[question.question_id] === option}
                      onChange={() => handleAnswerChange(question.question_id, option)}
                      className="mt-1 h-4 w-4 text-primary focus:ring-primary"
                    />
                    <span className="flex-1">
                      <span className="font-semibold mr-2">{option}.</span>
                      {question.options?.[option] || question[`option_${option.toLowerCase()}`]}
                    </span>
                  </label>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="flex justify-end">
        {submitting ? (
          <Spinner />
        ) : (
          <Button
            onClick={handleSubmit}
            disabled={answeredCount < totalQuestions}
            size="lg"
          >
            <Send className="mr-2 h-4 w-4" />
            Submit Quiz
          </Button>
        )}
      </div>
    </div>
  );
}
