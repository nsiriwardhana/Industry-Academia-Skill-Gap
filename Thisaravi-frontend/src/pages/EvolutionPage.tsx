import { useState, useEffect } from 'react';
import type { LLMProvider } from '@/services/evolutionService';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Separator } from '@/components/ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ChevronDown } from 'lucide-react';
import PageHeader from '@/components/layout/PageHeader';
import {
  fetchFeedbackStatus,
} from '@/services/feedbackService';
import {
  runAnalysis,
  fetchPatternReports,
  previewEvolution,
  applyEvolution,
  fetchEvolutions,
  fetchCurrentPrompt,
  runRegeneration,
  listDatasets,
  uploadToHF,
  type DatasetFile,
} from '@/services/evolutionService';

export default function EvolutionPage() {
  const queryClient = useQueryClient();
  const [provider, setProvider] = useState<LLMProvider>('ollama');
  const [selectedReportIdx, setSelectedReportIdx] = useState<string>('');
  const [selectedEvoIdx, setSelectedEvoIdx] = useState<string>('');
  const [targetCount, setTargetCount] = useState(200);
  const [diffPreview, setDiffPreview] = useState<string | null>(null);
  const [generationMode, setGenerationMode] = useState<'v1' | 'v2'>('v2');
  const [hfDataset, setHfDataset] = useState<string>('');

  // Queries
  const { data: status } = useQuery({
    queryKey: ['feedback-status'],
    queryFn: fetchFeedbackStatus,
  });

  const { data: reports = [] } = useQuery({
    queryKey: ['pattern-reports'],
    queryFn: fetchPatternReports,
  });

  const { data: evolutions = [] } = useQuery({
    queryKey: ['prompt-evolutions'],
    queryFn: fetchEvolutions,
  });

  const { data: currentPrompt } = useQuery({
    queryKey: ['current-prompt'],
    queryFn: fetchCurrentPrompt,
  });

  // Mutations
  const analysisMutation = useMutation({
    mutationFn: () => runAnalysis(provider),
    onSuccess: (report) => {
      toast.success(`Analysis complete! Report ID: ${report.report_id}`);
      queryClient.invalidateQueries({ queryKey: ['pattern-reports'] });
      queryClient.invalidateQueries({ queryKey: ['feedback-status'] });
    },
    onError: (err) => toast.error(`Analysis failed: ${err.message}`),
  });

  const previewMutation = useMutation({
    mutationFn: (reportId: string) => previewEvolution(reportId, provider),
    onSuccess: (data) => {
      setDiffPreview(data.diff);
      toast.success('Preview generated');
    },
    onError: (err) => toast.error(`Preview failed: ${err.message}`),
  });

  const applyMutation = useMutation({
    mutationFn: (reportId: string) => applyEvolution(reportId, provider),
    onSuccess: (evo) => {
      toast.success(`Prompt evolved! ${evo.parent_prompt_version} -> ${evo.new_prompt_version}`);
      queryClient.invalidateQueries({ queryKey: ['prompt-evolutions'] });
      queryClient.invalidateQueries({ queryKey: ['feedback-status'] });
      queryClient.invalidateQueries({ queryKey: ['current-prompt'] });
      setDiffPreview(null);
    },
    onError: (err) => toast.error(`Evolution failed: ${err.message}`),
  });

  const regenMutation = useMutation({
    mutationFn: ({ evoId, mode }: { evoId: string; mode: 'v1' | 'v2' }) =>
      runRegeneration(evoId, provider, targetCount, mode),
    onSuccess: (data) => {
      toast.success(`Dataset generated: ${data.output_path}`);
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
    onError: (err) => toast.error(`Regeneration failed: ${err.message}`),
  });

  const hfUploadMutation = useMutation({
    mutationFn: () => uploadToHF(hfDataset, undefined),
    onSuccess: (data) => toast.success(`✓ '${data.filename}' uploaded to HuggingFace!`),
    onError: (err) => toast.error(`Upload failed: ${err.message}`),
  });

  const feedbackCount = status?.total_feedback || 0;
  const latestReport = reports.length > 0 ? reports[reports.length - 1] : null;
  const selectedReport = selectedReportIdx ? reports[parseInt(selectedReportIdx)] : null;
  const selectedEvo = selectedEvoIdx ? evolutions[parseInt(selectedEvoIdx)] : null;
  const latestEvo = evolutions.length > 0 ? evolutions[evolutions.length - 1] : null;

  const { data: datasetsData, isLoading: datasetsLoading, error: datasetsError } = useQuery({
    queryKey: ['datasets'],
    queryFn: listDatasets,
    retry: 1,
  });
  const availableDatasets: DatasetFile[] = datasetsData?.datasets ?? [];

  // Auto-select the latest dataset when the list loads
  useEffect(() => {
    if (availableDatasets.length > 0 && !hfDataset) {
      setHfDataset(availableDatasets[availableDatasets.length - 1].filename);
    }
  }, [availableDatasets.length]);

  const selectedDatasetInfo = availableDatasets.find((d) => d.filename === hfDataset);
  const insufficientData = selectedDatasetInfo !== undefined && selectedDatasetInfo.entry_count < 200;

  return (
    <div>
      <PageHeader
        title="Self-Evolution Dashboard"
        subtitle="Manually trigger each phase of the prompt evolution cycle"
      />

      {/* Status Header */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card>
          <CardContent className="pt-4">
            <p className="text-xs text-muted-foreground">Prompt Version</p>
            <p className="text-xl font-bold font-mono">{status?.current_prompt_version || 'v2_base'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-xs text-muted-foreground">Total Feedback</p>
            <p className="text-xl font-bold">{feedbackCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-xs text-muted-foreground">Evolutions</p>
            <p className="text-xl font-bold">{status?.total_evolutions || 0}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar config */}
        <div className="lg:col-span-1 space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                <Label className="text-xs">LLM Provider</Label>
                <RadioGroup value={provider} onValueChange={(v) => setProvider(v as LLMProvider)}>
                  <div className="flex items-center gap-2">
                    <RadioGroupItem value="ollama" id="evo-ollama" />
                    <Label htmlFor="evo-ollama" className="text-sm font-normal cursor-pointer">Ollama</Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <RadioGroupItem value="gemini" id="evo-gemini" />
                    <Label htmlFor="evo-gemini" className="text-sm font-normal cursor-pointer">Gemini</Label>
                  </div>
                </RadioGroup>
              </div>
              <Separator />
              <div className="space-y-1">
                <p className="text-xs font-medium">Current System Prompt</p>
                <pre className="text-xs font-mono bg-muted/50 p-2 rounded-md overflow-auto max-h-48 whitespace-pre-wrap">
                  {currentPrompt?.prompt
                    ? (currentPrompt.prompt.length > 500
                        ? currentPrompt.prompt.slice(0, 500) + '...'
                        : currentPrompt.prompt)
                    : 'Loading...'}
                </pre>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main phases */}
        <div className="lg:col-span-3 space-y-6">
          {/* Phase 1: Pattern Analysis */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Phase 1: Pattern Analysis</CardTitle>
              <p className="text-xs text-muted-foreground">
                Analyze accumulated expert feedback to identify systematic patterns.
              </p>
              <p className="text-xs text-muted-foreground">Provider: <span className="font-mono">{provider}</span></p>
            </CardHeader>
            <CardContent className="space-y-4">
              {feedbackCount < 3 && (
                <div className="rounded-md bg-yellow-50 border border-yellow-200 p-3 text-sm text-yellow-800">
                  Only {feedbackCount} feedback entries collected. Recommend at least 10 for meaningful analysis.
                </div>
              )}

              <Button
                onClick={() => analysisMutation.mutate()}
                disabled={feedbackCount === 0 || analysisMutation.isPending}
              >
                {analysisMutation.isPending ? 'Analyzing...' : 'Run Analysis'}
              </Button>

              {latestReport && (
                <Collapsible defaultOpen>
                  <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium hover:underline">
                    <ChevronDown className="h-4 w-4" />
                    Latest Report: {latestReport.report_id}
                  </CollapsibleTrigger>
                  <CollapsibleContent className="mt-3 space-y-3">
                    <p className="text-sm"><span className="text-muted-foreground">Feedback Analyzed:</span> {latestReport.total_feedback_analyzed}</p>

                    {/* Rating averages */}
                    <div className="space-y-2">
                      <p className="text-sm font-medium">Average Ratings</p>
                      {Object.entries(latestReport.avg_ratings).map(([dim, avg]) => (
                        <div key={dim} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span>{dim.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</span>
                            <span>{typeof avg === 'number' ? avg.toFixed(1) : avg}/5</span>
                          </div>
                          <Progress value={((typeof avg === 'number' ? avg : 0) / 5) * 100} className="h-2" />
                        </div>
                      ))}
                    </div>

                    {/* Weak dimensions */}
                    {latestReport.low_scoring_dimensions.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        <span className="text-xs text-muted-foreground">Weak:</span>
                        {latestReport.low_scoring_dimensions.map((d) => (
                          <Badge key={d} variant="destructive" className="text-xs">
                            {d.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                          </Badge>
                        ))}
                      </div>
                    )}
                    {latestReport.strong_dimensions.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        <span className="text-xs text-muted-foreground">Strong:</span>
                        {latestReport.strong_dimensions.map((d) => (
                          <Badge key={d} variant="secondary" className="text-xs bg-green-100 text-green-800">
                            {d.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                          </Badge>
                        ))}
                      </div>
                    )}

                    {/* Themes */}
                    {latestReport.recurring_themes.length > 0 && (
                      <div>
                        <p className="text-sm font-medium mb-1">Recurring Themes</p>
                        <ul className="list-disc list-inside text-sm space-y-1">
                          {latestReport.recurring_themes.map((t, i) => <li key={i}>{t}</li>)}
                        </ul>
                      </div>
                    )}

                    {latestReport.actionable_insights.length > 0 && (
                      <div>
                        <p className="text-sm font-medium mb-1">Actionable Insights</p>
                        <ul className="list-disc list-inside text-sm space-y-1">
                          {latestReport.actionable_insights.map((r, i) => <li key={i}>{r}</li>)}
                        </ul>
                      </div>
                    )}
                  </CollapsibleContent>
                </Collapsible>
              )}
            </CardContent>
          </Card>

          {/* Phase 2: Prompt Evolution */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Phase 2: Prompt Evolution</CardTitle>
              <p className="text-xs text-muted-foreground">
                Evolve the system prompt based on the pattern analysis.
              </p>
              <p className="text-xs text-muted-foreground">Provider: <span className="font-mono">{provider}</span></p>
            </CardHeader>
            <CardContent className="space-y-4">
              {reports.length > 0 ? (
                <>
                  <div className="space-y-2">
                    <Label className="text-xs">Select Pattern Report</Label>
                    <Select
                      value={selectedReportIdx || String(reports.length - 1)}
                      onValueChange={setSelectedReportIdx}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {reports.map((r, i) => (
                          <SelectItem key={r.report_id} value={String(i)}>
                            {r.report_id} ({r.timestamp.slice(0, 10)})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={() => {
                        const report = selectedReport || reports[reports.length - 1];
                        previewMutation.mutate(report.report_id);
                      }}
                      disabled={previewMutation.isPending}
                    >
                      {previewMutation.isPending ? 'Generating...' : 'Preview Evolution'}
                    </Button>
                    <Button
                      onClick={() => {
                        const report = selectedReport || reports[reports.length - 1];
                        applyMutation.mutate(report.report_id);
                      }}
                      disabled={applyMutation.isPending}
                    >
                      {applyMutation.isPending ? 'Evolving...' : 'Apply Evolution'}
                    </Button>
                  </div>

                  {diffPreview && (
                    <div className="space-y-1">
                      <p className="text-sm font-medium">Preview Diff</p>
                      <pre className="text-xs font-mono bg-muted/50 p-3 rounded-md overflow-auto max-h-64 whitespace-pre-wrap">
                        {diffPreview}
                      </pre>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Run pattern analysis first (Phase 1) before evolving the prompt.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Phase 3: Dataset Regeneration */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Phase 3: Dataset Regeneration</CardTitle>
              <p className="text-xs text-muted-foreground">
                Regenerate training data using the evolved system prompt.
              </p>
              <p className="text-xs text-muted-foreground">Provider: <span className="font-mono">{provider}</span></p>
            </CardHeader>
            <CardContent className="space-y-4">
              {evolutions.length > 0 ? (
                <>
                  <div className="space-y-2">
                    <Label className="text-xs">Select Evolution</Label>
                    <Select
                      value={selectedEvoIdx || String(evolutions.length - 1)}
                      onValueChange={setSelectedEvoIdx}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {evolutions.map((e, i) => (
                          <SelectItem key={e.evolution_id} value={String(i)}>
                            {e.evolution_id}: {e.parent_prompt_version} -&gt; {e.new_prompt_version} ({e.timestamp.slice(0, 10)})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-xs">Target Entry Count</Label>
                    <Input
                      type="number"
                      min={1}
                      max={500}
                      value={targetCount}
                      onChange={(e) => setTargetCount(parseInt(e.target.value) || 200)}
                      className="w-32 h-8"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label className="text-xs">Generation Mode</Label>
                    <RadioGroup
                      value={generationMode}
                      onValueChange={(v) => setGenerationMode(v as 'v1' | 'v2')}
                      className="flex gap-4"
                    >
                      <div className="flex items-center gap-2">
                        <RadioGroupItem value="v2" id="regen-v2" />
                        <Label htmlFor="regen-v2" className="text-sm font-normal cursor-pointer">
                          v2 – JSON <span className="text-xs text-muted-foreground">(student-advisor:v2-json)</span>
                        </Label>
                      </div>
                      <div className="flex items-center gap-2">
                        <RadioGroupItem value="v1" id="regen-v1" />
                        <Label htmlFor="regen-v1" className="text-sm font-normal cursor-pointer">
                          v1 – Text <span className="text-xs text-muted-foreground">(student-advisor:v1-text)</span>
                        </Label>
                      </div>
                    </RadioGroup>
                    <p className="text-xs text-muted-foreground">
                      Output file: <code className="bg-muted px-1 rounded">
                        {(() => {
                          const ver = selectedEvo?.new_prompt_version ?? evolutions[evolutions.length - 1]?.new_prompt_version ?? '';
                          const evoNum = ver.split('_').pop() || '1';
                          return generationMode === 'v1'
                            ? `student_advisor_dataset_v1_evolved_${evoNum}.jsonl`
                            : `student_advisor_dataset_v2_evolved_${evoNum}.jsonl`;
                        })()}
                      </code>
                    </p>
                  </div>

                  <div>
                    <Button
                      onClick={() => {
                    const evo = selectedEvo || evolutions[evolutions.length - 1];
                        regenMutation.mutate({ evoId: evo.evolution_id, mode: generationMode });
                      }}
                      disabled={regenMutation.isPending}
                    >
                      {regenMutation.isPending ? 'Regenerating...' : 'Start Regeneration'}
                    </Button>
                    {regenMutation.isPending && (
                      <p className="text-xs text-muted-foreground mt-2">
                        This may take several minutes depending on target count...
                      </p>
                    )}
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Apply a prompt evolution first (Phase 2) before regenerating data.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Phase 4: Re-Fine-Tuning Instructions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Phase 4: Re-Fine-Tuning</CardTitle>
              <p className="text-xs text-muted-foreground">
                Upload the new dataset and re-fine-tune the model.
              </p>
              <p className="text-xs text-muted-foreground">Provider: <span className="font-mono">{provider}</span></p>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* HuggingFace Upload */}
                <div className="space-y-3 rounded-md border p-4">
                  <p className="text-sm font-medium">Upload Dataset to HuggingFace</p>

                  <div className="space-y-1">
                    <Label className="text-xs">Dataset file</Label>
                    <Select
                      value={hfDataset}
                      onValueChange={setHfDataset}
                      disabled={availableDatasets.length === 0}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={
                          datasetsLoading ? 'Loading datasets…' :
                          datasetsError ? 'Error loading datasets' :
                          availableDatasets.length === 0 ? 'No datasets found — run Phase 3 first' :
                          'Select a dataset…'
                        } />
                      </SelectTrigger>
                      <SelectContent>
                        {availableDatasets.map((d) => (
                          <SelectItem key={d.filename} value={d.filename}>
                            {d.filename}
                            <span className={`ml-2 text-xs font-mono ${
                              d.entry_count < 200 ? 'text-amber-500' : 'text-muted-foreground'
                            }`}>
                              ({d.entry_count} entries{d.entry_count < 200 ? ' ⚠' : ''})
                            </span>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {datasetsError && (
                      <p className="text-xs text-red-500">
                        Could not reach backend: {(datasetsError as Error).message}. Is the server running on port 8010?
                      </p>
                    )}
                    {!datasetsLoading && !datasetsError && availableDatasets.length === 0 && (
                      <p className="text-xs text-muted-foreground">No generated datasets found. Complete Phase 3 (Dataset Regeneration) first.</p>
                    )}
                    {insufficientData && (
                      <div className="rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-800">
                        ⚠️ Insufficient data: this dataset has only {selectedDatasetInfo!.entry_count} entries.
                        At least 200 entries are recommended for effective fine-tuning.
                        Consider running Phase 3 again with a higher target count.
                      </div>
                    )}
                  </div>

                  <Button
                    onClick={() => hfUploadMutation.mutate()}
                    disabled={!hfDataset || hfUploadMutation.isPending}
                  >
                    {hfUploadMutation.isPending ? 'Uploading…' : 'Upload to HuggingFace'}
                  </Button>
                </div>

                {/* Next steps */}
                {latestEvo && (
                  <div className="space-y-2 text-sm">
                    <p className="font-medium">Next steps after upload:</p>
                    <ol className="list-decimal list-inside space-y-1">
                      <li>Open the Colab notebook <code className="bg-muted px-1 rounded text-xs">notebooks/gemma_3_4b_student_advisor_v2.ipynb</code></li>
                      <li>Change <code className="bg-muted px-1 rounded text-xs">my_dataset</code> to point to the uploaded HuggingFace dataset</li>
                      <li>Run all cells (same LoRA fine-tuning pipeline)</li>
                      <li>Download the GGUF and register with Ollama:
                        <code className="block bg-muted px-2 py-1 rounded text-xs mt-1">
                          ollama create student-advisor:{latestEvo.new_prompt_version} -f Modelfile
                        </code>
                      </li>
                      <li>Update <code className="bg-muted px-1 rounded text-xs">.env</code> to point to the new model tag</li>
                    </ol>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Evolution History */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Evolution History</CardTitle>
            </CardHeader>
            <CardContent>
              {evolutions.length > 0 ? (
                <div className="space-y-2">
                  {[...evolutions].reverse().map((evo) => (
                    <Collapsible key={evo.evolution_id}>
                      <CollapsibleTrigger className="flex items-center gap-2 text-sm hover:underline w-full text-left">
                        <ChevronDown className="h-4 w-4 shrink-0" />
                        <span className="font-mono text-xs">
                          {evo.parent_prompt_version} -&gt; {evo.new_prompt_version}
                        </span>
                        <span className="text-muted-foreground text-xs">({evo.timestamp.slice(0, 10)})</span>
                      </CollapsibleTrigger>
                      <CollapsibleContent className="mt-2 pl-6 space-y-2">
                        <p className="text-sm"><span className="text-muted-foreground">Change Summary:</span> {evo.change_summary}</p>
                        <p className="text-xs text-muted-foreground">Report ID: {evo.pattern_report_id}</p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <div>
                            <p className="text-xs font-medium mb-1">Original Prompt</p>
                            <pre className="text-xs font-mono bg-muted/50 p-2 rounded-md overflow-auto max-h-32 whitespace-pre-wrap">
                              {evo.original_prompt.slice(0, 600)}
                            </pre>
                          </div>
                          <div>
                            <p className="text-xs font-medium mb-1">Evolved Prompt</p>
                            <pre className="text-xs font-mono bg-muted/50 p-2 rounded-md overflow-auto max-h-32 whitespace-pre-wrap">
                              {evo.evolved_prompt.slice(0, 600)}
                            </pre>
                          </div>
                        </div>
                      </CollapsibleContent>
                    </Collapsible>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No evolutions have been applied yet.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
