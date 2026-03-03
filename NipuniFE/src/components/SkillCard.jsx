import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Info, Award } from 'lucide-react';
import { Card, CardContent } from './ui/Card';
import { Button } from './ui/Button';

/**
 * SkillCard Component
 * Displays a skill with score, level, and an "Explain" button
 * 
 * @param {Object} props
 * @param {string} props.skillName - Name of the skill
 * @param {number} props.score - Score percentage (0-100)
 * @param {string} props.level - Proficiency level (Beginner/Intermediate/Advanced)
 * @param {number} props.confidence - Confidence value (0-1)
 * @param {string} props.type - 'child' or 'parent'
 * @param {string} props.studentId - Student ID for navigation
 */
export function SkillCard({ skillName, score, level, confidence, type = 'parent', studentId }) {
  const navigate = useNavigate();

  const getLevelColor = (level) => {
    const colors = {
      'Beginner': 'bg-yellow-100 text-yellow-800 border-yellow-200',
      'Intermediate': 'bg-blue-100 text-blue-800 border-blue-200',
      'Advanced': 'bg-green-100 text-green-800 border-green-200'
    };
    return colors[level] || 'bg-gray-100 text-gray-800 border-gray-200';
  };

  const getScoreColor = (score) => {
    if (score >= 75) return 'text-green-600';
    if (score >= 50) return 'text-blue-600';
    return 'text-yellow-600';
  };

  const handleExplain = () => {
    navigate(`/students/${studentId}/explain/${type}/${encodeURIComponent(skillName)}`);
  };

  return (
    <Card className="hover:shadow-lg transition-shadow border-slate-200">
      <CardContent className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <h3 className="font-semibold text-slate-900 mb-2">{skillName}</h3>
            <div className="flex items-center gap-2">
              <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium border ${getLevelColor(level)}`}>
                {level}
              </span>
              <span className="text-xs text-slate-500">
                {(confidence * 100).toFixed(0)}% confidence
              </span>
            </div>
          </div>
          <div className="text-right">
            <div className={`text-3xl font-bold ${getScoreColor(score)}`}>
              {score}
            </div>
            <div className="text-xs text-slate-500">score</div>
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExplain}
            className="flex-1 gap-2"
          >
            <Info className="w-4 h-4" />
            Explain Score
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
