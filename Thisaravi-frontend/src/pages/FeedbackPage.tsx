import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Clock, CheckCircle2, ChevronDown, Star } from 'lucide-react';
import { cn } from '@/lib/utils';
import PageHeader from '@/components/layout/PageHeader';
import { fetchUnreviewedOutputs, fetchAllFeedback, fetchFeedbackStatus, submitFeedback } from '@/services/feedbackService';
import { parseResponse } from '@/lib/parsers';
import type { FeedbackEntry, ModelOutputLog } from '@/types/api';

function getOutputLabel(out: ModelOutputLog, i: number): string {
  const inp = out.model_input || {};
  const student = (inp.student_data || {}) as Record<string, unknown>;
  const job = (inp.job_data || {}) as Record<string, unknown>;
  const demo = (student.demographics as string) || 'Unknown';
  const role = (job.target_job_role as string) || 'Unknown';
  return `${demo} → ${role}`;
}

function getFeedbackLabel(fb: FeedbackEntry): string {
  const inp = fb.model_input || {};
  const student = (inp.student_data || {}) as Record<string, unknown>;
  const job = (inp.job_data || {}) as Record<string, unknown>;
  const demo = (student.demographics as string) || 'Unknown';
  const role = (job.target_job_role as string) || 'Unknown';
  return `${demo} → ${role}`;
}

function formatTimestamp(ts?: string): string {
  if (!ts) return '';
  try {
    return new Date(ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch { return ts; }
}

/* ── Renders parsed model output ── */
function ModelOutputDisplay({ rawOutput }: { rawOutput: string }) {
  const parsed = rawOutput ? parseResponse(rawOutput) : null;

  if (parsed && !parsed.error) {
    return (
      <div className="space-y-3 text-sm">
        <div className="flex items-center gap-4">
          <span className="text-muted-foreground">Match Score: </span>
          <span className="font-bold text-lg">{parsed.gap_analysis.match_percentage}%</span>
        </div>
        <p className="text-muted-foreground">{parsed.gap_analysis.analysis_summary}</p>
        {parsed.gap_analysis.missing_skills.length > 0 && (
          <div className="flex flex-wrap gap-1">
            <span className="text-muted-foreground mr-1">Missing Skills:</span>
            {parsed.gap_analysis.missing_skills.map((s, i) => (
              <Badge key={i} variant="outline" className="text-xs">{s}</Badge>
            ))}
          </div>
        )}
        <Separator />
        <p><span className="font-semibold">Project:</span> {parsed.project_recommendation.project_title}</p>
        <p className="italic text-muted-foreground">{parsed.project_recommendation.objective}</p>
        <p><span className="text-muted-foreground">Tech Stack:</span> {parsed.project_recommendation.tech_stack.join(', ')}</p>
        <ol className="list-decimal list-inside space-y-1 mt-2">
          {parsed.project_recommendation.implementation_steps.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ol>
      </div>
    );
  }

  return (
    <pre className="text-xs font-mono bg-muted/50 p-3 rounded-md overflow-auto max-h-48">
      {rawOutput.slice(0, 2000)}
    </pre>
  );
}

/* ── Renders student + job input ── */
function InputDisplay({ input }: { input: Record<string, unknown> }) {
  const studentData = (input.student_data || {}) as Record<string, unknown>;
  const jobData = (input.job_data || {}) as Record<string, unknown>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="space-y-1 text-sm">
        <p className="font-semibold">Student Profile</p>
        <p><span className="text-muted-foreground">Demographics:</span> {studentData.demographics as string || 'N/A'}</p>
        <p><span className="text-muted-foreground">Major:</span> {studentData.major as string || 'N/A'}</p>
        <p><span className="text-muted-foreground">Interests:</span> {Array.isArray(studentData.interests) ? (studentData.interests as string[]).join(', ') : 'N/A'}</p>
        <p><span className="text-muted-foreground">Skills:</span> {Array.isArray(studentData.current_skills) ? (studentData.current_skills as string[]).join(', ') : 'N/A'}</p>
        <p><span className="text-muted-foreground">Personality:</span> {studentData.personality as string || 'N/A'}</p>
      </div>
      <div className="space-y-1 text-sm">
        <p className="font-semibold">Target Job</p>
        <p><span className="text-muted-foreground">Role:</span> {jobData.target_job_role as string || 'N/A'}</p>
        <p><span className="text-muted-foreground">Required Skills:</span> {Array.isArray(jobData.required_skills) ? (jobData.required_skills as string[]).join(', ') : 'N/A'}</p>
        <p><span className="text-muted-foreground">Description:</span> {jobData.description as string || 'N/A'}</p>
      </div>
    </div>
  );
}

export default function FeedbackPage() {
  const queryClient = useQueryClient();
  const [selectedOutput, setSelectedOutput] = useState<ModelOutputLog | null>(null);
  const [reviewerId, setReviewerId] = useState('expert_01');
  const [ratings, setRatings] = useState({
    skill_gap_accuracy: 3,
    project_relevance: 3,
    tech_stack_appropriateness: 3,
    implementation_step_quality: 3,
    overall_quality: 3,
  });
  const [comments, setComments] = useState('');

  const { data: unreviewed = [], isLoading: loadingOutputs } = useQuery({
    queryKey: ['unreviewed-outputs'],
    queryFn: fetchUnreviewedOutputs,
  });

  const { data: allFeedback = [] } = useQuery({
    queryKey: ['all-feedback'],
    queryFn: fetchAllFeedback,
  });

  const { data: status } = useQuery({
    queryKey: ['feedback-status'],
    queryFn: fetchFeedbackStatus,
  });

  const mutation = useMutation({
    mutationFn: submitFeedback,
    onSuccess: (data) => {
      toast.success(`Feedback submitted! (ID: ${data.feedback_id})`);
      queryClient.invalidateQueries({ queryKey: ['unreviewed-outputs'] });
      queryClient.invalidateQueries({ queryKey: ['all-feedback'] });
      queryClient.invalidateQueries({ queryKey: ['feedback-status'] });
      setComments('');
      setRatings({
        skill_gap_accuracy: 3,
        project_relevance: 3,
        tech_stack_appropriateness: 3,
        implementation_step_quality: 3,
        overall_quality: 3,
      });
      setSelectedOutput(null);
    },
    onError: (err) => {
      toast.error(`Failed to submit: ${err.message}`);
    },
  });

  const avgOverall = allFeedback.length > 0
    ? (allFeedback.reduce((sum, f) => sum + (f.ratings?.overall_quality || 0), 0) / allFeedback.length).toFixed(1)
    : 'N/A';

  const handleSubmit = () => {
    if (!comments.trim()) {
      toast.warning('Please provide comments explaining your ratings.');
      return;
    }
    if (!selectedOutput) return;

    const entry: FeedbackEntry = {
      model_input: selectedOutput.model_input,
      model_output: selectedOutput.model_output,
      model_provider: selectedOutput.model_provider || 'unknown',
      ratings,
      free_text_comments: comments,
      reviewer_id: reviewerId,
      prompt_version: selectedOutput.prompt_version || status?.current_prompt_version || 'v2_base',
    };
    mutation.mutate(entry);
  };

  const ratingFields = [
    { key: 'skill_gap_accuracy' as const, label: 'Skill Gap Accuracy' },
    { key: 'project_relevance' as const, label: 'Project Relevance' },
    { key: 'tech_stack_appropriateness' as const, label: 'Tech Stack Appropriateness' },
    { key: 'implementation_step_quality' as const, label: 'Implementation Step Quality' },
    { key: 'overall_quality' as const, label: 'Overall Quality' },
  ];

  return (
    <div>
      <PageHeader
        title="Expert Feedback Portal"
        subtitle="Review model outputs and provide structured ratings + comments"
      />

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar stats */}
        <div className="lg:col-span-1 space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-xs text-muted-foreground">Pending Review</p>
                <p className="text-2xl font-bold">{unreviewed.length}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Total Reviews</p>
                <p className="text-2xl font-bold">{allFeedback.length}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Avg Overall Quality</p>
                <p className="text-2xl font-bold">{avgOverall}/5</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Prompt Version</p>
                <p className="text-sm font-mono">{status?.current_prompt_version || 'v2_base'}</p>
              </div>
              <Separator />
              <div className="space-y-1">
                <Label className="text-xs">Your Reviewer ID</Label>
                <Input
                  value={reviewerId}
                  onChange={(e) => setReviewerId(e.target.value)}
                  className="h-8 text-sm"
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main content */}
        <div className="lg:col-span-3 space-y-6">
          <Tabs defaultValue="pending" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="pending" className="gap-2">
                <Clock className="h-4 w-4" />
                Pending Review
                {unreviewed.length > 0 && (
                  <Badge variant="secondary" className="ml-1 text-xs">{unreviewed.length}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="reviewed" className="gap-2">
                <CheckCircle2 className="h-4 w-4" />
                Reviewed
                {allFeedback.length > 0 && (
                  <Badge variant="secondary" className="ml-1 text-xs">{allFeedback.length}</Badge>
                )}
              </TabsTrigger>
            </TabsList>

            {/* ── PENDING OUTPUTS ────────────────────────── */}
            <TabsContent value="pending" className="space-y-4 mt-4">
              {loadingOutputs ? (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">Loading outputs...</CardContent>
                </Card>
              ) : unreviewed.length === 0 ? (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    No pending outputs to review. All caught up!
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-3">
                  {unreviewed.map((out, i) => {
                    const isSelected = selectedOutput?.output_id === out.output_id;
                    return (
                      <Card
                        key={out.output_id || i}
                        className={cn(
                          'cursor-pointer transition-all',
                          isSelected ? 'ring-2 ring-primary' : 'hover:border-muted-foreground/40',
                        )}
                        onClick={() => setSelectedOutput(isSelected ? null : out)}
                      >
                        <CardContent className="py-4">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-100 text-amber-700 text-xs font-bold">
                                {i + 1}
                              </div>
                              <div>
                                <p className="text-sm font-medium">{getOutputLabel(out, i)}</p>
                                <p className="text-xs text-muted-foreground">
                                  {formatTimestamp(out.timestamp)} · {out.model_provider}
                                  {out.prompt_version && ` · ${out.prompt_version}`}
                                </p>
                              </div>
                            </div>
                            <Badge variant="outline" className="text-amber-600 border-amber-300">Pending</Badge>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              )}

              {/* Review form — shows when an output is selected */}
              {selectedOutput && (
                <div className="space-y-4 border-t pt-6">
                  <h3 className="text-lg font-semibold">Reviewing: {getOutputLabel(selectedOutput, unreviewed.indexOf(selectedOutput))}</h3>

                  {/* Original Input */}
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">Original Input</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <InputDisplay input={selectedOutput.model_input || {}} />
                    </CardContent>
                  </Card>

                  {/* Model Output */}
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">Model Output</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ModelOutputDisplay rawOutput={selectedOutput.model_output || ''} />
                    </CardContent>
                  </Card>

                  {/* Ratings */}
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">Your Ratings (1–5)</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {ratingFields.map(({ key, label }) => (
                          <div key={key} className="space-y-2">
                            <div className="flex justify-between">
                              <Label className="text-xs">{label}</Label>
                              <span className="text-xs font-mono">{ratings[key]}</span>
                            </div>
                            <Slider
                              min={1}
                              max={5}
                              step={1}
                              value={[ratings[key]]}
                              onValueChange={([v]) => setRatings((prev) => ({ ...prev, [key]: v }))}
                            />
                          </div>
                        ))}
                      </div>

                      <Separator />

                      <div className="space-y-2">
                        <Label className="text-sm font-medium">Comments</Label>
                        <Textarea
                          value={comments}
                          onChange={(e) => setComments(e.target.value)}
                          placeholder="Explain your reasoning (what could be improved?)"
                          rows={4}
                        />
                      </div>

                      <Button
                        className="w-full"
                        onClick={handleSubmit}
                        disabled={mutation.isPending}
                      >
                        {mutation.isPending ? 'Submitting...' : 'Submit Feedback'}
                      </Button>
                    </CardContent>
                  </Card>
                </div>
              )}
            </TabsContent>

            {/* ── REVIEWED OUTPUTS ───────────────────────── */}
            <TabsContent value="reviewed" className="space-y-4 mt-4">
              {allFeedback.length === 0 ? (
                <Card>
                  <CardContent className="py-8 text-center text-muted-foreground">
                    No feedback submitted yet.
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-3">
                  {[...allFeedback].reverse().map((fb, i) => (
                    <Collapsible key={fb.feedback_id || i}>
                      <Card>
                        <CollapsibleTrigger asChild>
                          <CardContent className="py-4 cursor-pointer hover:bg-muted/30 transition-colors">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-100 text-green-700 text-xs font-bold">
                                  <CheckCircle2 className="h-4 w-4" />
                                </div>
                                <div>
                                  <p className="text-sm font-medium">{getFeedbackLabel(fb)}</p>
                                  <p className="text-xs text-muted-foreground">
                                    {formatTimestamp(fb.timestamp)}
                                    {fb.reviewer_id && ` · by ${fb.reviewer_id}`}
                                    {` · ${fb.prompt_version}`}
                                  </p>
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                <div className="flex items-center gap-1 text-sm">
                                  <Star className="h-3.5 w-3.5 text-amber-500 fill-amber-500" />
                                  <span className="font-medium">{fb.ratings?.overall_quality || '–'}/5</span>
                                </div>
                                <ChevronDown className="h-4 w-4 text-muted-foreground transition-transform [[data-state=open]_&]:rotate-180" />
                              </div>
                            </div>
                          </CardContent>
                        </CollapsibleTrigger>
                        <CollapsibleContent>
                          <div className="px-6 pb-4 space-y-4 border-t pt-4">
                            {/* Ratings summary */}
                            <div>
                              <p className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wider">Ratings</p>
                              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                {Object.entries(fb.ratings || {}).map(([key, value]) => (
                                  <div key={key} className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-1.5">
                                    <span className="text-xs text-muted-foreground capitalize">{key.replace(/_/g, ' ')}</span>
                                    <span className="text-xs font-bold">{value as number}/5</span>
                                  </div>
                                ))}
                              </div>
                            </div>

                            {/* Comments */}
                            {fb.free_text_comments && (
                              <div>
                                <p className="text-xs font-semibold text-muted-foreground mb-1 uppercase tracking-wider">Comments</p>
                                <p className="text-sm bg-muted/30 rounded-md p-3 italic">{fb.free_text_comments}</p>
                              </div>
                            )}

                            {/* Expandable model output */}
                            <Collapsible>
                              <CollapsibleTrigger asChild>
                                <Button variant="ghost" size="sm" className="text-xs gap-1 px-0 text-muted-foreground">
                                  <ChevronDown className="h-3 w-3" />
                                  View model output
                                </Button>
                              </CollapsibleTrigger>
                              <CollapsibleContent className="mt-2">
                                <div className="space-y-3">
                                  <InputDisplay input={fb.model_input || {}} />
                                  <Separator />
                                  <ModelOutputDisplay rawOutput={fb.model_output || ''} />
                                </div>
                              </CollapsibleContent>
                            </Collapsible>
                          </div>
                        </CollapsibleContent>
                      </Card>
                    </Collapsible>
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
