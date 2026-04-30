import { useNavigate, useLocation } from "react-router-dom";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { XAIExplanation } from "@/components/XAIExplanation";
import { ArrowLeft, ArrowRight, AlertTriangle, CheckCircle2, TrendingUp, Target, BookOpen, Award, Briefcase, Code, ExternalLink, Star } from "lucide-react";
import { getCourseRecommendations, type CourseRecommendation } from "@/services/courseService";

interface SkillGapItem {
  skill: string;
  currentLevel: number;
  requiredLevel: number;
  gap: number;
  priority: "high" | "medium" | "low";
  deficit?: number;
  importance?: number;
  // GNN fields
  P_gnn?: number;  // Learning potential from GNN (0-1)
  final_score?: number;  // Hybrid ranking score
  reason?: string;  // Human-readable explanation
  category?: string;  // Skill category
  ranking_method?: string;  // "hybrid", "symbolic", etc.
}

const SkillGap = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { results, type } = location.state || {};
  
  const [courses, setCourses] = useState<CourseRecommendation[]>([]);
  const [loadingCourses, setLoadingCourses] = useState(false);
  const [coursesError, setCoursesError] = useState<string | null>(null);

  if (!results) {
    return (
      <div className="min-h-screen bg-gradient-hero flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-foreground mb-4">No Results Found</h2>
          <Button onClick={() => navigate('/analysis')}>
            <ArrowLeft className="w-4 h-4" />
            Back to Analysis
          </Button>
        </div>
      </div>
    );
  }

  // Fetch course recommendations
  useEffect(() => {
    const fetchCourses = async () => {
      if (type === 'job-based' || results.role_key === 'custom_job') {
        console.log('ℹ️ Skipping course recommendations for custom job-based analysis');
        return;
      }

      if (!results.candidate_id || !results.role_key) {
        console.log('⚠️ Missing candidate_id or role_key, skipping course recommendations');
        return;
      }

      setLoadingCourses(true);
      setCoursesError(null);

      try {
        console.log('📚 Fetching courses for:', results.candidate_id, results.role_key);
        const courseData = await getCourseRecommendations(
          results.candidate_id,
          results.role_key,
          25, // top_k deficits
          10  // top_n courses
        );
        setCourses(courseData.recommendations || []);
        console.log('✅ Courses loaded:', courseData.recommendations.length);
      } catch (error) {
        console.error('❌ Failed to fetch courses:', error);
        setCoursesError(error instanceof Error ? error.message : 'Failed to load course recommendations');
      } finally {
        setLoadingCourses(false);
      }
    };

    fetchCourses();
  }, [results.candidate_id, results.role_key]);

  // Process skill gaps
  const skillGaps: SkillGapItem[] = (results.skill_gap_top || []).map((gap: any) => {
    const currentLevel = Math.max(0, (1 - (gap.deficit || 0)) * 100);
    const requiredLevel = (gap.importance || 0.5) * 100;
    const gapValue = requiredLevel - currentLevel;
    
    let priority: "high" | "medium" | "low" = "medium";
    if (gapValue > 50 || gap.deficit > 0.5) priority = "high";
    else if (gapValue < 25 || gap.deficit < 0.3) priority = "low";

    return {
      skill: gap.skill_name || gap.skill,
      currentLevel: Math.round(currentLevel),
      requiredLevel: Math.round(requiredLevel),
      gap: Math.round(gapValue),
      priority,
      deficit: gap.deficit,
      importance: gap.importance,
      // GNN fields
      P_gnn: gap.P_gnn,
      final_score: gap.final_score,
      reason: gap.reason,
      category: gap.category,
      ranking_method: gap.ranking_method,
    };
  });

  // Debug: Log GNN status
  useEffect(() => {
    const hasGNN = skillGaps.some(gap => gap.P_gnn !== undefined);
    const rankingMethod = skillGaps[0]?.ranking_method || 'unknown';
    
    console.log('🔍 Skill Gap Analysis:');
    console.log(`  Ranking Method: ${rankingMethod}`);
    console.log(`  GNN Active: ${hasGNN ? '✅ YES' : '❌ NO'}`);
    
    if (hasGNN) {
      console.log('  📊 Sample GNN Data:');
      console.log(`    Skill: ${skillGaps[0]?.skill}`);
      console.log(`    P_gnn: ${skillGaps[0]?.P_gnn}`);
      console.log(`    Reason: ${skillGaps[0]?.reason}`);
    }
  }, [skillGaps]);

  // Process matched skills
  const matchedSkills = (results.skill_confidence_top || []).slice(0, 5).map((skill: any) => ({
    name: skill.skill_name || skill.skill,
    confidence: Math.round((skill.confidence || 0) * 100),
  }));

  // Calculate overall readiness
  const overallReadiness = results.readiness_score 
    ? Math.round(results.readiness_score * 100)
    : Math.round((matchedSkills.reduce((acc: number, s: any) => acc + s.confidence, 0) / (matchedSkills.length || 1)));

  // Calculate max importance for normalization
  const maxImportance = Math.max(...skillGaps.map(sg => sg.importance || 0), 1);

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "high": return "text-destructive border-destructive/30 bg-destructive/10";
      case "medium": return "text-accent border-accent/30 bg-accent/10";
      case "low": return "text-primary border-primary/30 bg-primary/10";
      default: return "text-muted-foreground border-border bg-muted";
    }
  };

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case "high": return AlertTriangle;
      case "medium": return TrendingUp;
      case "low": return CheckCircle2;
      default: return Target;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-hero">
      {/* Background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-accent/5 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }} />
      </div>

      {/* Header */}
      <header className="relative z-10 container mx-auto px-6 py-6">
        <nav className="flex items-center justify-between">
          <Button variant="ghost" onClick={() => navigate('/analysis')}>
            <ArrowLeft className="w-4 h-4" />
            New Analysis
          </Button>
          <h1 className="text-xl font-bold text-foreground">Skill Gap Analysis & Insights</h1>
          <Button variant="hero" onClick={() => navigate('/recommendations', { state: { results, type } })}>
            View Recommendations
            <ArrowRight className="w-4 h-4" />
          </Button>
        </nav>
      </header>

      {/* Main Content */}
      <main className="relative z-10 container mx-auto px-6 py-8 max-w-6xl">
        
        {/* Summary Card with Readiness Score */}
        <div className="bg-gradient-card rounded-2xl border border-border p-8 mb-8 shadow-elevated animate-slide-up">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-foreground mb-2">
                Analysis for: {results.roleLabel || "Target Role"}
              </h2>
              
              {/* GNN Ranking Indicator */}
              {skillGaps[0]?.ranking_method === 'hybrid' && (
                <div className="inline-flex items-center gap-2 mb-3 px-3 py-1.5 rounded-full bg-accent/10 border border-accent/30">
                  <svg className="w-4 h-4 text-accent" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM5 10a1 1 0 01-1 1H3a1 1 0 110-2h1a1 1 0 011 1zM8 16v-1h4v1a2 2 0 11-4 0zM12 14c.015-.34.208-.646.477-.859a4 4 0 10-4.954 0c.27.213.462.519.476.859h4.002z" />
                  </svg>
                  <span className="text-sm font-medium text-accent">GNN-Powered Recommendations</span>
                  <span className="text-xs text-accent/70">(AI Learning Potential)</span>
                </div>
              )}
              
              <p className="text-muted-foreground mb-4">
                {type === 'role-based' ? 'Role-based' : 'Job description-based'} analysis completed
              </p>
              
              {/* Key Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-4">
                <div className="bg-primary/10 rounded-lg p-3 border border-primary/20">
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle2 className="w-4 h-4 text-primary" />
                    <span className="text-sm font-medium text-foreground">Matched Skills</span>
                  </div>
                  <p className="text-2xl font-bold text-primary">{matchedSkills.length}</p>
                </div>
                <div className="bg-destructive/10 rounded-lg p-3 border border-destructive/20">
                  <div className="flex items-center gap-2 mb-1">
                    <AlertTriangle className="w-4 h-4 text-destructive" />
                    <span className="text-sm font-medium text-foreground">Skill Gaps</span>
                  </div>
                  <p className="text-2xl font-bold text-destructive">{skillGaps.length}</p>
                </div>
                {results.project_relevance_score !== undefined && (
                  <div className="bg-accent/10 rounded-lg p-3 border border-accent/20">
                    <div className="flex items-center gap-2 mb-1">
                      <Briefcase className="w-4 h-4 text-accent" />
                      <span className="text-sm font-medium text-foreground">Project Score</span>
                    </div>
                    <p className="text-2xl font-bold text-accent">
                      {Math.round(results.project_relevance_score * 100)}%
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Readiness Circle */}
            <div className="flex-shrink-0 text-center">
              <div className="relative w-32 h-32">
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="64"
                    cy="64"
                    r="56"
                    stroke="hsl(var(--muted))"
                    strokeWidth="8"
                    fill="none"
                  />
                  <circle
                    cx="64"
                    cy="64"
                    r="56"
                    stroke="url(#progressGradient)"
                    strokeWidth="8"
                    fill="none"
                    strokeDasharray={`${(overallReadiness / 100) * 352} 352`}
                    strokeLinecap="round"
                  />
                  <defs>
                    <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="hsl(174, 72%, 46%)" />
                      <stop offset="100%" stopColor="hsl(199, 89%, 48%)" />
                    </linearGradient>
                  </defs>
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-3xl font-bold text-foreground">{overallReadiness}%</span>
                  <span className="text-xs text-muted-foreground">Readiness</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Matched Skills Section */}
        {matchedSkills.length > 0 && (
          <div className="bg-gradient-card rounded-2xl border border-border p-6 mb-8 shadow-card animate-fade-in" style={{ animationDelay: '0.05s' }}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
                <Award className="w-5 h-5 text-primary" />
              </div>
              <h3 className="text-lg font-semibold text-foreground">Your Strengths</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {matchedSkills.map((skill: any, idx: number) => (
                <div key={idx} className="bg-muted/30 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-foreground">{skill.name}</span>
                    <span className="text-sm font-bold text-primary">{skill.confidence}%</span>
                  </div>
                  <Progress value={skill.confidence} className="h-2" />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Skills to Develop Section - Moved Above XAI */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-destructive/20 flex items-center justify-center">
              <Code className="w-5 h-5 text-destructive" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-foreground">Skills to Develop</h3>
              <p className="text-sm text-muted-foreground">Top 12 priority skills for your target role</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {skillGaps.slice(0, 12).map((skillGap, index) => {
            const PriorityIcon = getPriorityIcon(skillGap.priority);
            const normalizedImportance = Math.round((skillGap.importance || 0) / maxImportance * 100);
            
            return (
              <div
                key={index}
                className="bg-gradient-card rounded-xl border border-border p-4 shadow-card hover:shadow-elevated transition-all duration-300 animate-scale-in"
                style={{ animationDelay: `${0.03 * index}s` }}
              >
                <div className="flex items-start justify-between mb-3">
                  <h4 className="font-semibold text-foreground text-base">{skillGap.skill}</h4>
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${getPriorityColor(skillGap.priority)}`}>
                    <PriorityIcon className="w-3 h-3" />
                    {skillGap.priority.charAt(0).toUpperCase() + skillGap.priority.slice(1)}
                  </span>
                </div>

                <div className="space-y-3">
                  <div>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Current Level</span>
                      <span className="text-foreground font-medium">{skillGap.currentLevel}%</span>
                    </div>
                    <Progress value={skillGap.currentLevel} className="h-2" />
                  </div>
                  
                  <div>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Required for Role</span>
                      <span className="text-primary font-medium">{normalizedImportance}%</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-primary rounded-full"
                        style={{ width: `${normalizedImportance}%` }}
                      />
                    </div>
                  </div>
                  
                  {/* GNN Learning Potential */}
                  {skillGap.P_gnn !== undefined && (
                    <div>
                      <div className="flex items-center justify-between text-sm mb-1">
                        <span className="text-muted-foreground flex items-center gap-1">
                          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
                          </svg>
                          Learning Potential
                        </span>
                        <span className="text-accent font-bold">{Math.round((skillGap.P_gnn || 0) * 100)}%</span>
                      </div>
                      <div className="h-2 bg-muted rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-accent rounded-full transition-all"
                          style={{ width: `${(skillGap.P_gnn || 0) * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                  
                  {/* GNN Reason/Explanation */}
                  {skillGap.reason && (
                    <p className="text-xs text-muted-foreground italic border-l-2 border-accent/30 pl-2">
                      {skillGap.reason}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* XAI Explanation Section (Colab + SHAP insights) */}
        {(results.xai || results.explanation) && (
          <XAIExplanation 
            xai={results.xai}
            explanation={results.explanation}
            className="mb-8 animate-fade-in"
          />
        )}

        {/* Course Recommendations Section */}
        {loadingCourses && (
          <div className="bg-gradient-card rounded-2xl border border-border p-6 mb-8 shadow-card animate-fade-in">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-accent/20 flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-accent" />
              </div>
              <h3 className="text-lg font-semibold text-foreground">Recommended Courses</h3>
            </div>
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
              <p className="text-sm text-muted-foreground mt-4">Finding best courses for your skill gaps...</p>
            </div>
          </div>
        )}

        {coursesError && (
          <div className="bg-destructive/10 rounded-2xl border border-destructive/30 p-6 mb-8">
            <p className="text-sm text-destructive">{coursesError}</p>
          </div>
        )}

        {!loadingCourses && !coursesError && courses.length > 0 && (
          <div className="bg-gradient-card rounded-2xl border border-border p-6 mb-8 shadow-card animate-fade-in">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-accent/20 flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-accent" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-foreground">Recommended Courses</h3>
                <p className="text-sm text-muted-foreground">Top courses to bridge your skill gaps</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {courses.map((course, idx) => (
                <div 
                  key={course.course_id}
                  className="bg-muted/30 rounded-xl p-5 border border-border hover:border-accent/50 hover:bg-muted/50 transition-all duration-300 group"
                >
                  {/* Course Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h4 className="font-semibold text-foreground mb-1 group-hover:text-accent transition-colors">
                        {course.title || 'Course'}
                      </h4>
                      {course.provider && (
                        <p className="text-xs text-muted-foreground">{course.provider}</p>
                      )}
                    </div>
                    {course.avg_rating && (
                      <div className="flex items-center gap-1 bg-amber-500/10 px-2 py-1 rounded-md border border-amber-500/20">
                        <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
                        <span className="text-xs font-medium text-amber-500">{course.avg_rating.toFixed(1)}</span>
                      </div>
                    )}
                  </div>

                  {/* Skills Covered */}
                  <div className="mb-3">
                    <p className="text-xs text-muted-foreground mb-2">Skills you'll learn:</p>
                    <div className="flex flex-wrap gap-1">
                      {course.covered_deficit_skills.slice(0, 4).map((skill, skillIdx) => (
                        <span 
                          key={skillIdx}
                          className="text-xs px-2 py-0.5 bg-primary/10 text-primary rounded-md border border-primary/20"
                        >
                          {skill}
                        </span>
                      ))}
                      {course.covered_deficit_skills.length > 4 && (
                        <span className="text-xs px-2 py-0.5 bg-muted text-muted-foreground rounded-md">
                          +{course.covered_deficit_skills.length - 4} more
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="flex items-center justify-between pt-3 border-t border-border">
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      {course.difficulty && (
                        <span className="capitalize">{course.difficulty}</span>
                      )}
                      <span className="font-medium text-accent">
                        Impact: {Math.round(course.gain_score)}
                      </span>
                    </div>
                    {course.url && (
                      <a 
                        href={course.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs font-medium text-accent hover:text-accent/80 transition-colors"
                      >
                        View Course
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Project Relevance Section */}
        {results.relevant_projects && results.relevant_projects.length > 0 && (
          <div className="mt-8 bg-gradient-card rounded-2xl border border-border p-6 shadow-card animate-fade-in" style={{ animationDelay: '0.15s' }}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-accent/20 flex items-center justify-center">
                <Briefcase className="w-5 h-5 text-accent" />
              </div>
              <h3 className="text-lg font-semibold text-foreground">Relevant Projects</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {results.relevant_projects.slice(0, 4).map((project: any, idx: number) => (
                <div key={idx} className="bg-muted/30 rounded-lg p-4">
                  <h4 className="font-medium text-foreground mb-2">
                    {project.project_name || project.name || `Project ${idx + 1}`}
                  </h4>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Relevance Score</span>
                    <span className="text-sm font-bold text-accent">
                      {Math.round((project.relevance_score || project.relevance || 0) * 100)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* CTA */}
        <div className="mt-12 text-center animate-fade-in" style={{ animationDelay: '0.2s' }}>
          <Button variant="hero" size="xl" onClick={() => navigate('/recommendations', { state: { results, type } })}>
            Get Personalized Learning Path
            <ArrowRight className="w-5 h-5" />
          </Button>
        </div>
      </main>
    </div>
  );
};

export default SkillGap;
