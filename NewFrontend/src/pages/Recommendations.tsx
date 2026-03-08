import { useNavigate, useLocation } from "react-router-dom";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import QuickActions from "@/components/QuickActions";
import { ArrowLeft, ExternalLink, Star, BookOpen, CheckCircle2, AlertCircle, Sparkles } from "lucide-react";
import { getCourseRecommendations, type CourseRecommendation } from "@/services/courseService";

const Recommendations = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { results, type } = location.state || {};

  const [courses, setCourses] = useState<CourseRecommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCourses = async () => {
      if (!results?.candidate_id || !results?.role_key) {
        setError("Missing candidate or role information");
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const courseData = await getCourseRecommendations(
          results.candidate_id,
          results.role_key,
          25, // top_k deficits
          20  // top_n courses - get more for recommendations page
        );
        setCourses(courseData.recommendations || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load recommendations");
      } finally {
        setLoading(false);
      }
    };

    fetchCourses();
  }, [results?.candidate_id, results?.role_key]);

  const getDifficultyColor = (difficulty?: string) => {
    switch (difficulty?.toLowerCase()) {
      case "beginner":
      case "intermediate":
        return "bg-primary/20 text-primary border-primary/30";
      case "advanced":
        return "bg-destructive/20 text-destructive border-destructive/30";
      default:
        return "bg-accent/20 text-accent border-accent/30";
    }
  };

  // Group courses by their top skill (first covered skill)
  const groupedCourses = courses.reduce((acc, course) => {
    const topSkill = course.covered_deficit_skills[0] || "Other";
    if (!acc[topSkill]) acc[topSkill] = [];
    acc[topSkill].push(course);
    return acc;
  }, {} as Record<string, CourseRecommendation[]>);

  return (
    <div className="min-h-screen bg-gradient-hero">
      {/* Background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-accent/5 rounded-full blur-3xl animate-float" style={{ animationDelay: "2s" }} />
      </div>

      {/* Header */}
      <header className="relative z-10 container mx-auto px-6 py-6">
        <nav className="flex items-center justify-between">
          <Button variant="ghost" onClick={() => navigate("/skill-gap", { state: { results, type } })}>
            <ArrowLeft className="w-4 h-4" />
            Back to Analysis
          </Button>
          <h1 className="text-xl font-bold text-foreground">Course Recommendations</h1>
          <Button variant="hero" onClick={() => navigate("/analysis")}>
            New Analysis
          </Button>
        </nav>
      </header>

      {/* Main Content */}
      <main className="relative z-10 container mx-auto px-6 py-8 max-w-7xl">
        {/* Header Section */}
        <div className="text-center mb-12 animate-slide-up">
          <div className="flex items-center justify-center gap-2 mb-3">
            <Sparkles className="w-8 h-8 text-primary" />
            <h2 className="text-3xl font-bold text-foreground">Your Learning Roadmap</h2>
          </div>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Personalized course recommendations to help you bridge your skill gaps for{" "}
            <span className="text-primary font-medium">{results?.roleLabel || results?.role_key || "your target role"}</span>
          </p>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="text-center py-16">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Finding the best courses for you...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-destructive/10 rounded-2xl border border-destructive/30 p-8 text-center">
            <AlertCircle className="w-12 h-12 text-destructive mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">Unable to Load Recommendations</h3>
            <p className="text-sm text-muted-foreground mb-4">{error}</p>
            <Button variant="outline" onClick={() => window.location.reload()}>
              Try Again
            </Button>
          </div>
        )}

        {/* Courses Grid */}
        {!loading && !error && courses.length > 0 && (
          <div className="space-y-8">
            {Object.entries(groupedCourses).map(([skill, skillCourses], groupIndex) => (
              <div key={skill} className="animate-fade-in" style={{ animationDelay: `${groupIndex * 0.1}s` }}>
                {/* Skill Category Header */}
                <div className="flex items-center gap-3 mb-4">
                  <div className="flex-1 h-px bg-gradient-to-r from-transparent via-border to-transparent" />
                  <h3 className="text-lg font-semibold text-foreground px-4 py-2 bg-primary/10 rounded-full border border-primary/20">
                    {skill}
                  </h3>
                  <div className="flex-1 h-px bg-gradient-to-r from-border via-transparent to-transparent" />
                </div>

                {/* Course Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {skillCourses.map((course, idx) => (
                    <div
                      key={course.course_id}
                      className="bg-gradient-card rounded-2xl border border-border overflow-hidden shadow-card hover:shadow-elevated transition-all duration-300 group flex flex-col"
                    >
                      {/* Course Image */}
                      {course.imageUrl ? (
                        <div className="relative h-48 overflow-hidden bg-muted">
                          <img
                            src={course.imageUrl}
                            alt={course.title}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            onError={(e) => {
                              e.currentTarget.style.display = "none";
                              e.currentTarget.parentElement!.classList.add("flex", "items-center", "justify-center");
                              e.currentTarget.parentElement!.innerHTML = '<div class="text-muted-foreground"><BookOpen class="w-12 h-12" /></div>';
                            }}
                          />
                          {/* Overlay gradient */}
                          <div className="absolute inset-0 bg-gradient-to-t from-background/80 to-transparent" />
                          
                          {/* Rating badge */}
                          {course.avg_rating && (
                            <div className="absolute top-3 right-3 flex items-center gap-1 bg-black/60 backdrop-blur-sm px-2 py-1 rounded-md">
                              <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                              <span className="text-xs font-medium text-white">{course.avg_rating.toFixed(1)}</span>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="h-48 bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center">
                          <BookOpen className="w-16 h-16 text-primary/40" />
                        </div>
                      )}

                      {/* Course Content */}
                      <div className="p-5 flex-1 flex flex-col">
                        {/* Provider */}
                        {course.provider && (
                          <p className="text-xs text-primary font-medium mb-2 uppercase tracking-wide">{course.provider}</p>
                        )}

                        {/* Title */}
                        <h4 className="font-semibold text-foreground mb-3 line-clamp-2 min-h-[3rem] group-hover:text-primary transition-colors">
                          {course.title || "Course"}
                        </h4>

                        {/* Skills Covered */}
                        <div className="mb-4 flex-1">
                          <p className="text-xs text-muted-foreground mb-2">Skills you'll gain:</p>
                          <div className="flex flex-wrap gap-1">
                            {course.covered_deficit_skills.slice(0, 3).map((skill, skillIdx) => (
                              <Badge key={skillIdx} variant="secondary" className="text-xs">
                                {skill}
                              </Badge>
                            ))}
                            {course.covered_deficit_skills.length > 3 && (
                              <Badge variant="outline" className="text-xs">
                                +{course.covered_deficit_skills.length - 3}
                              </Badge>
                            )}
                          </div>
                        </div>

                        {/* Footer */}
                        <div className="flex items-center justify-between pt-4 border-t border-border">
                          {/* Difficulty */}
                          {course.difficulty && (
                            <span className={`text-xs px-2 py-1 rounded-md border font-medium capitalize ${getDifficultyColor(course.difficulty)}`}>
                              {course.difficulty}
                            </span>
                          )}

                          {/* Impact Score */}
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">Impact:</span>
                            <span className="text-sm font-bold text-accent">{Math.round(course.gain_score)}</span>
                          </div>
                        </div>

                        {/* CTA Button */}
                        {course.url && (
                          <a
                            href={course.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-4 w-full"
                          >
                            <Button variant="hero" size="sm" className="w-full group-hover:shadow-glow transition-shadow">
                              View Course
                              <ExternalLink className="w-4 h-4" />
                            </Button>
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Summary Stats */}
        {!loading && !error && courses.length > 0 && (
          <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-4 animate-fade-in" style={{ animationDelay: "0.6s" }}>
            <div className="bg-gradient-card rounded-xl border border-border p-4 text-center shadow-card">
              <BookOpen className="w-6 h-6 text-primary mx-auto mb-2" />
              <p className="text-2xl font-bold text-foreground">{courses.length}</p>
              <p className="text-sm text-muted-foreground">Courses</p>
            </div>
            <div className="bg-gradient-card rounded-xl border border-border p-4 text-center shadow-card">
              <CheckCircle2 className="w-6 h-6 text-primary mx-auto mb-2" />
              <p className="text-2xl font-bold text-foreground">{Object.keys(groupedCourses).length}</p>
              <p className="text-sm text-muted-foreground">Skills Covered</p>
            </div>
            <div className="bg-gradient-card rounded-xl border border-border p-4 text-center shadow-card">
              <Star className="w-6 h-6 text-accent mx-auto mb-2" />
              <p className="text-2xl font-bold text-foreground">
                {courses.filter((c) => c.avg_rating && c.avg_rating >= 4.5).length}
              </p>
              <p className="text-sm text-muted-foreground">Top Rated</p>
            </div>
            <div className="bg-gradient-card rounded-xl border border-border p-4 text-center shadow-card">
              <Sparkles className="w-6 h-6 text-primary mx-auto mb-2" />
              <p className="text-2xl font-bold text-foreground">{Math.round(courses.reduce((sum, c) => sum + c.gain_score, 0))}</p>
              <p className="text-sm text-muted-foreground">Total Impact</p>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && courses.length === 0 && (
          <div className="text-center py-16">
            <BookOpen className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">No Recommendations Available</h3>
            <p className="text-sm text-muted-foreground mb-6">
              We couldn't find specific courses for your skill gaps. Try running a new analysis.
            </p>
            <Button variant="hero" onClick={() => navigate("/analysis")}>
              New Analysis
            </Button>
          </div>
        )}

        {/* Quick Actions */}
        <QuickActions />
      </main>
    </div>
  );
};

export default Recommendations;
