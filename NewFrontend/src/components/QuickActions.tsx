import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { Home, UserCircle, Briefcase, Users } from "lucide-react";

const QuickActions = () => {
  const navigate = useNavigate();

  return (
    <div className="bg-gradient-card rounded-2xl border border-border p-6 shadow-card animate-fade-in mt-12">
      <div className="mb-6">
        <h3 className="text-xl font-bold text-foreground mb-2">Quick Actions</h3>
        <p className="text-sm text-muted-foreground">Navigate to different sections</p>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Button
          variant="outline"
          className="flex flex-col items-center justify-center h-24 gap-2 hover:bg-primary/10 hover:border-primary transition-all"
          onClick={() => navigate('/profile')}
        >
          <UserCircle className="w-6 h-6" />
          <span className="text-sm font-medium">Edit Profile</span>
        </Button>
        
        <Button
          variant="outline"
          className="flex flex-col items-center justify-center h-24 gap-2 hover:bg-primary/10 hover:border-primary transition-all"
          onClick={() => navigate('/modules')}
        >
          <Briefcase className="w-6 h-6" />
          <span className="text-sm font-medium">Modules</span>
        </Button>
        
        <Button
          variant="outline"
          className="flex flex-col items-center justify-center h-24 gap-2 hover:bg-primary/10 hover:border-primary transition-all"
          onClick={() => navigate('/industry-connect')}
        >
          <Users className="w-6 h-6" />
          <span className="text-sm font-medium">Industry Connect</span>
        </Button>
        
        <Button
          variant="outline"
          className="flex flex-col items-center justify-center h-24 gap-2 hover:bg-primary/10 hover:border-primary transition-all"
          onClick={() => navigate('/')}
        >
          <Home className="w-6 h-6" />
          <span className="text-sm font-medium">Home</span>
        </Button>
      </div>
    </div>
  );
};

export default QuickActions;
