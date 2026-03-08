import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { ArrowLeft, Upload, Play, CheckCircle2, Briefcase, FileText } from "lucide-react";
import { toast } from "@/hooks/use-toast";
import { ROLES } from "@/config/api";

const Analysis = () => {
  const navigate = useNavigate();
  const [targetRole, setTargetRole] = useState("");
  const [targetRoleLabel, setTargetRoleLabel] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [storeInGraph, setStoreInGraph] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleCvFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setCvFile(file);
    }
  };

  const handleRoleBasedAnalysis = () => {
    if (!cvFile) {
      toast({
        title: "Missing CV File",
        description: "Please upload a CV/Resume PDF file.",
        variant: "destructive",
      });
      return;
    }
    
    if (!targetRole) {
      toast({
        title: "Missing Target Role",
        description: "Please select a target role for analysis.",
        variant: "destructive",
      });
      return;
    }
    
    navigate('/pipeline', { 
      state: { 
        type: 'role-based',
        profile: null,
        cvFile: cvFile,
        roleKey: targetRole,
        roleLabel: targetRoleLabel
      } 
    });
  };

  const handleJobBasedAnalysis = () => {
    if (!cvFile) {
      toast({
        title: "Missing CV File",
        description: "Please upload a CV/Resume PDF file.",
        variant: "destructive",
      });
      return;
    }
    
    navigate('/pipeline', { 
      state: { 
        type: 'job-based',
        profile: null,
        cvFile: cvFile,
        jobFile: selectedFile,
        storeInGraph
      } 
    });
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
          <Button variant="ghost" onClick={() => navigate('/')}>
            <ArrowLeft className="w-4 h-4" />
            Back
          </Button>
          <h1 className="text-xl font-bold text-foreground">Analysis Setup</h1>
          <div className="w-20" />
        </nav>
      </header>

      {/* Main Content */}
      <main className="relative z-10 container mx-auto px-6 py-8 max-w-4xl">
        <div className="animate-slide-up">
          <h2 className="text-3xl font-bold text-center mb-8 text-foreground">
            Upload Your Resume for Analysis
          </h2>

          <Card className="mb-6 border-border/50 shadow-lg bg-card/30 backdrop-blur-sm">
            <CardHeader>
              <Label className="text-base font-semibold">Candidate Resume/CV</Label>
            </CardHeader>

            <CardContent className="pt-6">
              <div className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-primary/50 transition-colors cursor-pointer relative">
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleCvFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <Upload className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                {cvFile ? (
                  <div className="flex flex-col items-center gap-2">
                    <div className="flex items-center gap-2 text-primary">
                      <CheckCircle2 className="w-5 h-5" />
                      <span className="font-medium">{cvFile.name}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {(cvFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <>
                    <p className="text-foreground font-medium mb-1">Upload Resume/CV (PDF)</p>
                    <p className="text-sm text-muted-foreground">Drag & drop or click to upload</p>
                  </>
                )}
              </div>
              <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg">
                <p className="text-sm text-blue-800 dark:text-blue-200">
                  <strong>🤖 AI-Powered Parsing:</strong> Your CV will be automatically parsed using advanced LLMs to extract skills, projects, education, and experience.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Analysis Type Selection */}
          <Tabs defaultValue="role-based" className="w-full">
            <TabsList className="grid w-full grid-cols-2 bg-muted/50">
              <TabsTrigger value="role-based" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                <Briefcase className="w-4 h-4 mr-2" />
                Role-Based Analysis
              </TabsTrigger>
              <TabsTrigger value="job-based" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                <FileText className="w-4 h-4 mr-2" />
                Job Description Analysis
              </TabsTrigger>
            </TabsList>

            {/* Role-Based Tab Content */}
            <TabsContent value="role-based" className="mt-0">
            <div className="bg-gradient-card rounded-2xl border border-border p-6 shadow-card">
              <Label htmlFor="target-role" className="text-lg font-semibold text-foreground mb-4 block">
                Target Role
              </Label>
              <Select value={targetRole} onValueChange={(value) => {
                setTargetRole(value);
                const role = ROLES.find(r => r.key === value);
                setTargetRoleLabel(role?.label || value);
              }}>
                <SelectTrigger className="bg-muted/50 border-border">
                  <SelectValue placeholder="Select target role for analysis" />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map((role) => (
                    <SelectItem key={role.key} value={role.key}>
                      {role.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Button 
                variant="hero" 
                size="lg" 
                className="w-full mt-6"
                onClick={handleRoleBasedAnalysis}
              >
                <Play className="w-5 h-5" />
                Run Analysis
              </Button>
            </div>
          </TabsContent>

          {/* Job-Based Tab Content */}
          <TabsContent value="job-based" className="mt-0">
            <div className="bg-gradient-card rounded-2xl border border-border p-6 shadow-card">
              <Label className="text-lg font-semibold text-foreground mb-4 block">
                Job Description
              </Label>
              
              <div className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-primary/50 transition-colors cursor-pointer relative">
                <input
                  type="file"
                  accept="image/*,.pdf"
                  onChange={handleFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <Upload className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                {selectedFile ? (
                  <div className="flex items-center justify-center gap-2 text-primary">
                    <CheckCircle2 className="w-5 h-5" />
                    <span className="font-medium">{selectedFile.name}</span>
                  </div>
                ) : (
                  <>
                    <p className="text-foreground font-medium mb-1">Upload Job Description</p>
                    <p className="text-sm text-muted-foreground">Drag & drop or click to upload (Image/PDF)</p>
                  </>
                )}
              </div>

              <div className="flex items-center space-x-2 mt-4">
                <Checkbox 
                  id="store-graph" 
                  checked={storeInGraph}
                  onCheckedChange={(checked) => setStoreInGraph(checked as boolean)}
                />
                <Label 
                  htmlFor="store-graph" 
                  className="text-sm text-muted-foreground cursor-pointer"
                >
                  Store job in knowledge graph for future analysis
                </Label>
              </div>

              <Button 
                variant="hero" 
                size="lg" 
                className="w-full mt-6"
                onClick={handleJobBasedAnalysis}
              >
                <Play className="w-5 h-5" />
                Run Analysis
              </Button>
            </div>
          </TabsContent>
        </Tabs>
        </div>
      </main>
    </div>
  );
};

export default Analysis;
