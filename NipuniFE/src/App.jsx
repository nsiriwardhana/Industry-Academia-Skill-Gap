import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import UploadPage from './pages/UploadPage';
import TranscriptPage from './pages/TranscriptPage';
import SkillsPage from './pages/SkillsPage';
import { SkillExplainPage } from './pages/SkillExplainPage';
import { ExplainChildSkillPage } from './pages/ExplainChildSkillPage';
import { ExplainParentSkillPage } from './pages/ExplainParentSkillPage';
// import JobRecommendationsPage from './pages/JobRecommendationsPage'; // DEPRECATED: Legacy rule-based recommendations
import MLJobRecommendationsPage from './pages/MLJobRecommendationsPage';
import JobDetailPage from './pages/JobDetailPage';
import PortfolioPage from './pages/PortfolioPage';
import QuizPage from './pages/QuizPage';
import ResultsPage from './pages/ResultsPage';

function App() {
  // Default student ID for demo purposes
  const defaultStudentId = 'IT21013928';

  return (
    <BrowserRouter>
      <div className="min-h-screen">
        {/* Header */}
        <header className="bg-gradient-to-r from-primary via-primary-dark to-primary border-b shadow-lg sticky top-0 z-10 backdrop-blur-sm">
          <div className="container mx-auto px-6 py-5">
            <h1 className="text-2xl font-bold text-white tracking-tight">
              SkillBridge
            </h1>
            <p className="text-sm text-primary-foreground/80 mt-1">Transcript-Based Skill Validation</p>
          </div>
        </header>

        {/* Main Content */}
        <main className="py-8">
          <Routes>
            <Route path="/" element={<Navigate to={`/students/${defaultStudentId}/upload`} replace />} />
            <Route path="/students/:studentId/upload" element={<UploadPage />} />
            <Route path="/students/:studentId/transcript" element={<TranscriptPage />} />
            <Route path="/students/:studentId/skills" element={<SkillsPage />} />
            <Route path="/students/:studentId/skills/:skillName/explain" element={<ExplainParentSkillPage />} />
            {/* Alternative routes for direct access */}
            <Route path="/students/:studentId/explain/child/:skillName" element={<ExplainChildSkillPage />} />
            <Route path="/students/:studentId/explain/parent/:parentSkill" element={<ExplainParentSkillPage />} />
            {/* Default job recommendations route - now uses ML-powered system */}
            <Route path="/students/:studentId/jobs" element={<MLJobRecommendationsPage />} />
            {/* Alias route for backward compatibility */}
            <Route path="/students/:studentId/jobs/ml" element={<MLJobRecommendationsPage />} />
            <Route path="/jobs/:jobId" element={<JobDetailPage />} />
            <Route path="/students/:studentId/portfolio" element={<PortfolioPage />} />
            <Route path="/students/:studentId/quiz" element={<QuizPage />} />
            <Route path="/students/:studentId/results/:attemptId" element={<ResultsPage />} />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="border-t mt-12 bg-card/50 backdrop-blur-sm">
          <div className="container mx-auto px-6 py-6 text-center text-sm text-muted-foreground">
            <p>&copy; 2026 SkillBridge Research Team. All rights reserved.</p>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;
