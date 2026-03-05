/**
 * XAI Explanation Component
 * Displays Explainable AI insights from SHAP analysis
 * Matches the comprehensive display from old frontend
 */

import { useState } from "react";
import { Brain, TrendingUp, TrendingDown, Lightbulb, AlertCircle, CheckCircle2, BarChart3 } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface XAIFactor {
  feature: string;
  value?: any;
  impact: number;
  message?: string;
  interpretation?: string;
}

interface SkillContributor {
  skill_name: string;
  deficit: number;
  importance: number;
  match_strength: number;
  contribution_percent: number;
}

interface SkillLevelXAI {
  candidate_id: string;
  role_key: string;
  top_contributors: SkillContributor[];
  total_deficit: number;
}

interface ShapLevelXAI {
  enabled: boolean;
  predicted_skill_gap_index?: number;
  predicted_readiness?: number;
  skill_gap_prediction?: number;
  readiness_prediction?: number;
  top_increasing_factors?: XAIFactor[];
  top_reducing_factors?: XAIFactor[];
  top_positive_contributors?: XAIFactor[];
  top_negative_contributors?: XAIFactor[];
  summary_text?: string;
  base_value?: number;
  notes?: string[];
  reason?: string;
}

interface XAIData {
  skill_level?: SkillLevelXAI;
  shap_level?: ShapLevelXAI;
}

interface ColabExplanation {
  explanation?: string;
  text?: string;
  explanation_text?: string;
  confidence_score?: number;
  generation_time?: number;
  model?: string;
}

interface Props {
  xai: XAIData | null | undefined;
  explanation?: ColabExplanation | null;
  className?: string;
}

export function XAIExplanation({ xai, explanation, className = "" }: Props) {
  // Default to "colab" if only explanation exists, otherwise "shap"
  const [activeXaiTab, setActiveXaiTab] = useState<"colab" | "shap">(!xai && explanation ? "colab" : "shap");

  // Show "not available" only if BOTH xai and explanation are missing
  if (!xai && !explanation) {
    return (
      <div className={`bg-gradient-card rounded-2xl border border-border p-6 ${className}`}>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-muted flex items-center justify-center">
            <Brain className="w-5 h-5 text-muted-foreground" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">AI Insights</h3>
            <p className="text-sm text-muted-foreground">Explainability analysis</p>
          </div>
        </div>
        
        <div className="flex items-center gap-2 text-muted-foreground">
          <AlertCircle className="w-4 h-4" />
          <p className="text-sm">AI explanations are not available for this analysis.</p>
        </div>
      </div>
    );
  }

  const shapLevel = xai?.shap_level;
  const skillLevel = xai?.skill_level;

  // Get the factors arrays (handle both old and new field names)
  const rawIncreasingFactors = shapLevel?.top_increasing_factors || shapLevel?.top_positive_contributors || [];
  const rawReducingFactors = shapLevel?.top_reducing_factors || shapLevel?.top_negative_contributors || [];
  
  // Filter duplicate features from one-hot encoding (e.g., Experience Level appears multiple times)
  const filterDuplicateFeatures = (factors: XAIFactor[]): XAIFactor[] => {
    const featureGroups: { [key: string]: XAIFactor[] } = {};
    
    // Group features by their base name (e.g., "Experience Level: Fresher" -> "Experience Level")
    factors.forEach(factor => {
      const baseName = factor.feature.includes(':') 
        ? factor.feature.split(':')[0].trim() 
        : factor.feature;
      
      if (!featureGroups[baseName]) {
        featureGroups[baseName] = [];
      }
      featureGroups[baseName].push(factor);
    });
    
    // For each group, keep only the one with highest absolute impact
    const filtered: XAIFactor[] = [];
    Object.values(featureGroups).forEach(group => {
      if (group.length === 1) {
        filtered.push(group[0]);
      } else {
        // Multiple features with same base name - keep the one with highest absolute impact
        const best = group.reduce((prev, curr) => 
          Math.abs(curr.impact) > Math.abs(prev.impact) ? curr : prev
        );
        filtered.push(best);
      }
    });
    
    return filtered;
  };
  
  const increasingFactors = filterDuplicateFeatures(rawIncreasingFactors);
  const reducingFactors = filterDuplicateFeatures(rawReducingFactors);
  const predictedGap = shapLevel?.predicted_skill_gap_index || shapLevel?.skill_gap_prediction;
  const predictedReadiness = shapLevel?.predicted_readiness || shapLevel?.readiness_prediction;

  return (
    <div className={`bg-gradient-card rounded-2xl border border-border shadow-elevated ${className}`}>
      {/* Header */}
      <div className="p-6 pb-0">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-semibold text-foreground">🔍 Explainability (XAI)</h3>
            <p className="text-sm text-muted-foreground">
              AI-powered insights using SHAP analysis
            </p>
          </div>
        </div>
      </div>

      {/* Render explanation content - with or without tabs */}
      {xai && explanation ? (
        // Case 1: Both exist - show tabs
        <Tabs value={activeXaiTab} onValueChange={(v) => setActiveXaiTab(v as "colab" | "shap")} className="w-full">
          <div className="px-6 pt-4">
            <TabsList className="grid w-full grid-cols-2 bg-muted/50">
              <TabsTrigger value="colab" className="gap-2">
                <Lightbulb className="w-4 h-4" />
                AI Explanation
              </TabsTrigger>
              <TabsTrigger value="shap" className="gap-2">
                <Brain className="w-4 h-4" />
                SHAP Analysis
              </TabsTrigger>
            </TabsList>
          </div>

          <div className="p-6">
            {/* Colab AI Explanation Tab */}
            <TabsContent value="colab" className="mt-0 space-y-4">
            {explanation && (explanation.explanation || explanation.text || explanation.explanation_text) ? (
              <>
                <div className="p-6 bg-gradient-to-br from-primary/10 to-accent/10 rounded-xl border border-primary/20">
                  <div className="flex items-center gap-2 mb-4">
                    <Lightbulb className="w-5 h-5 text-primary" />
                    <h4 className="font-semibold text-foreground">AI-Generated Insights</h4>
                  </div>
                  <div className="prose prose-sm max-w-none">
                    <p className="text-foreground leading-relaxed whitespace-pre-wrap">
                      {explanation.explanation || explanation.text || explanation.explanation_text}
                    </p>
                  </div>
                  
                  {/* Metadata */}
                  {(explanation.confidence_score || explanation.generation_time || explanation.model) && (
                    <div className="mt-4 pt-4 border-t border-border flex flex-wrap gap-4 text-sm text-muted-foreground">
                      {explanation.confidence_score && (
                        <div className="flex items-center gap-2">
                          <span>Confidence:</span>
                          <span className="font-medium text-primary">
                            {Math.round(explanation.confidence_score * 100)}%
                          </span>
                        </div>
                      )}
                      {explanation.generation_time && (
                        <div className="flex items-center gap-2">
                          <span>Generated in:</span>
                          <span className="font-medium text-foreground">
                            {explanation.generation_time.toFixed(2)}s
                          </span>
                        </div>
                      )}
                      {explanation.model && (
                        <div className="flex items-center gap-2">
                          <span>Model:</span>
                          <span className="font-medium text-foreground">
                            {explanation.model}
                          </span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="p-6 bg-muted/30 rounded-lg text-center">
                <AlertCircle className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">No AI explanation available</p>
                <p className="text-xs text-muted-foreground mt-2">The Colab explainer service may not be running</p>
              </div>
            )}
          </TabsContent>

          {/* SHAP Level Tab */}
          <TabsContent value="shap" className="mt-0 space-y-6">
            {shapLevel && shapLevel.enabled ? (
              <>
                {/* Summary Banner */}
                {shapLevel.summary_text && (
                  <div className="p-6 bg-gradient-to-br from-primary to-accent rounded-xl text-white shadow-lg">
                    <div className="text-xs uppercase tracking-wider opacity-90 mb-2">
                      📊 Analysis Summary
                    </div>
                    <div className="text-base leading-relaxed">
                      {shapLevel.summary_text}
                    </div>
                  </div>
                )}

                {/* Predictions */}
                <div className="grid grid-cols-2 gap-4">
                  {predictedGap !== undefined && (
                    <div className="p-6 bg-gradient-to-br from-destructive to-destructive/80 rounded-xl text-white text-center shadow-lg">
                      <div className="text-sm opacity-90 mb-2">Predicted Skill Gap</div>
                      <div className="text-4xl font-bold">
                        {(predictedGap * 100).toFixed(1)}%
                      </div>
                    </div>
                  )}
                  {predictedReadiness !== undefined && (
                    <div className="p-6 bg-gradient-to-br from-green-500 to-green-600 rounded-xl text-white text-center shadow-lg">
                      <div className="text-sm opacity-90 mb-2">Predicted Readiness</div>
                      <div className="text-4xl font-bold">
                        {(predictedReadiness * 100).toFixed(1)}%
                      </div>
                    </div>
                  )}
                </div>

                {/* Strengths (Reducing Factors) */}
                {reducingFactors.length > 0 && (
                  <div>
                    <h4 className="flex items-center gap-2 text-lg font-semibold text-green-600 dark:text-green-400 mb-4">
                      <CheckCircle2 className="w-5 h-5" />
                      Your Strengths
                      <span className="text-sm font-normal text-muted-foreground">
                        (Factors reducing your skill gap)
                      </span>
                    </h4>
                    
                    <div className="space-y-4">
                      {reducingFactors.map((feat, idx) => (
                        <div
                          key={idx}
                          className="p-5 bg-green-50 dark:bg-green-950/20 rounded-xl border-2 border-green-200 dark:border-green-800 shadow-sm hover:shadow-md transition-shadow"
                        >
                          <div className="flex items-center gap-4 mb-3">
                            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-green-600 text-white flex items-center justify-center text-lg font-bold">
                              {idx + 1}
                            </div>
                            <div className="flex-1">
                              <div className="font-semibold text-green-800 dark:text-green-200 text-base mb-1">
                                {feat.feature}
                              </div>
                              {feat.value !== null && feat.value !== undefined && (
                                <div className="text-sm text-muted-foreground">
                                  Current value: <strong>{typeof feat.value === 'number' ? feat.value.toFixed(2) : feat.value}</strong>
                                </div>
                              )}
                            </div>
                            <div className="px-4 py-2 bg-gradient-to-br from-green-500 to-green-600 rounded-full text-white font-bold text-sm shadow-md">
                              {feat.impact.toFixed(3)}
                            </div>
                          </div>
                          
                          {(feat.message || feat.interpretation) && (
                            <div className="p-3 bg-white dark:bg-green-950/30 rounded-lg border border-green-200 dark:border-green-800">
                              <div className="flex items-start gap-2 text-sm text-green-800 dark:text-green-200 leading-relaxed">
                                <Lightbulb className="w-4 h-4 flex-shrink-0 mt-0.5" />
                                <span>{feat.message || feat.interpretation}</span>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Weaknesses (Increasing Factors) */}
                {increasingFactors.length > 0 && (
                  <div>
                    <h4 className="flex items-center gap-2 text-lg font-semibold text-destructive mb-4">
                      <AlertCircle className="w-5 h-5" />
                      Areas to Improve
                      <span className="text-sm font-normal text-muted-foreground">
                        (Factors increasing your skill gap)
                      </span>
                    </h4>
                    
                    <div className="space-y-4">
                      {increasingFactors.map((feat, idx) => (
                        <div
                          key={idx}
                          className="p-5 bg-red-50 dark:bg-red-950/20 rounded-xl border-2 border-red-200 dark:border-red-800 shadow-sm hover:shadow-md transition-shadow"
                        >
                          <div className="flex items-center gap-4 mb-3">
                            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-destructive to-destructive/80 text-white flex items-center justify-center text-lg font-bold">
                              {idx + 1}
                            </div>
                            <div className="flex-1">
                              <div className="font-semibold text-red-800 dark:text-red-200 text-base mb-1">
                                {feat.feature}
                              </div>
                              {feat.value !== null && feat.value !== undefined && (
                                <div className="text-sm text-muted-foreground">
                                  Current value: <strong>{typeof feat.value === 'number' ? feat.value.toFixed(2) : feat.value}</strong>
                                </div>
                              )}
                            </div>
                            <div className="px-4 py-2 bg-gradient-to-br from-destructive to-destructive/80 rounded-full text-white font-bold text-sm shadow-md">
                              +{feat.impact.toFixed(3)}
                            </div>
                          </div>
                          
                          {(feat.message || feat.interpretation) && (
                            <div className="p-3 bg-white dark:bg-red-950/30 rounded-lg border border-red-200 dark:border-red-800">
                              <div className="flex items-start gap-2 text-sm text-red-800 dark:text-red-200 leading-relaxed">
                                <Lightbulb className="w-4 h-4 flex-shrink-0 mt-0.5" />
                                <span>{feat.message || feat.interpretation}</span>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* No factors message */}
                {increasingFactors.length === 0 && reducingFactors.length === 0 && (
                  <div className="p-6 bg-muted/30 rounded-lg text-center">
                    <AlertCircle className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">
                      No SHAP factors identified. This may indicate missing data.
                    </p>
                  </div>
                )}

                {/* Notes */}
                {shapLevel.notes && shapLevel.notes.length > 0 && (
                  <div className="p-4 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-800">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                      <div className="space-y-1">
                        {shapLevel.notes.map((note, index) => (
                          <p key={index} className="text-sm text-blue-800 dark:text-blue-200">
                            {note}
                          </p>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Footer */}
                <div className="pt-4 border-t border-border">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <CheckCircle2 className="w-3 h-3" />
                    <span>
                      Powered by SHAP (SHapley Additive exPlanations) - Industry-standard explainable AI
                    </span>
                  </div>
                </div>
              </>
            ) : (
              <div className="p-6 bg-muted/30 rounded-lg text-center">
                <AlertCircle className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                <p className="text-sm text-muted-foreground mb-2">
                  {shapLevel?.reason || "SHAP explanation is not available for this analysis."}
                </p>
              </div>
            )}
          </TabsContent>
        </div>
      </Tabs>
      ) : explanation ? (
        // Case 2: Only explanation exists - show directly without tabs
        <div className="p-6">
          {(explanation.explanation || explanation.text || explanation.explanation_text) ? (
            <div className="p-6 bg-gradient-to-br from-primary/10 to-accent/10 rounded-xl border border-primary/20">
              <div className="flex items-center gap-2 mb-4">
                <Lightbulb className="w-5 h-5 text-primary" />
                <h4 className="font-semibold text-foreground">AI-Generated Insights</h4>
              </div>
              <div className="prose prose-sm max-w-none">
                <p className="text-foreground leading-relaxed whitespace-pre-wrap">
                  {explanation.explanation || explanation.text || explanation.explanation_text}
                </p>
              </div>
              
              {/* Metadata */}
              {(explanation.confidence_score || explanation.generation_time || explanation.model) && (
                <div className="mt-4 pt-4 border-t border-border flex flex-wrap gap-4 text-sm text-muted-foreground">
                  {explanation.confidence_score && (
                    <div className="flex items-center gap-2">
                      <span>Confidence:</span>
                      <span className="font-medium text-primary">
                        {Math.round(explanation.confidence_score * 100)}%
                      </span>
                    </div>
                  )}
                  {explanation.generation_time && (
                    <div className="flex items-center gap-2">
                      <span>Generated in:</span>
                      <span className="font-medium text-foreground">
                        {explanation.generation_time.toFixed(2)}s
                      </span>
                    </div>
                  )}
                  {explanation.model && (
                    <div className="flex items-center gap-2">
                      <span>Model:</span>
                      <span className="font-medium text-foreground">
                        {explanation.model}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="p-6 bg-muted/30 rounded-lg text-center">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">No AI explanation available</p>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

