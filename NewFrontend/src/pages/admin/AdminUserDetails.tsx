import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Loader2, UserCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";

const AUTH_API_URL = import.meta.env.VITE_AUTH_API || "http://localhost:8182";

interface CandidateProfile {
  id: number;
  target_role?: string | null;
  status?: string | null;
  readiness_score?: number | null;
  latest_analysis_date?: string | null;
  created_at?: string | null;
}

interface UserDetails {
  id: number;
  name?: string;
  email: string;
  provider?: string;
  is_active: boolean;
  created_at?: string;
  last_login?: string;
  candidate?: CandidateProfile;
}

const formatDate = (value?: string | null) => {
  if (!value) return "N/A";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
};

export default function AdminUserDetails() {
  const navigate = useNavigate();
  const { userId } = useParams();
  const [user, setUser] = useState<UserDetails | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUserDetails = async () => {
      const token = localStorage.getItem("admin_token");
      if (!token) {
        navigate("/admin/login");
        return;
      }

      try {
        const response = await fetch(`${AUTH_API_URL}/admin/users/${userId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        });

        if (response.status === 401 || response.status === 403) {
          localStorage.removeItem("admin_token");
          localStorage.removeItem("admin_user");
          navigate("/admin/login");
          return;
        }

        if (!response.ok) {
          throw new Error("Failed to load user details");
        }

        const data = await response.json();
        setUser(data.user ?? null);
      } catch (error) {
        console.error("Failed to fetch user details:", error);
        toast.error("Unable to load user details");
      } finally {
        setLoading(false);
      }
    };

    fetchUserDetails();
  }, [navigate, userId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <Loader2 className="w-10 h-10 text-cyan-400 animate-spin" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
        <div className="max-w-4xl mx-auto">
          <Button variant="outline" onClick={() => navigate("/admin/dashboard")}> 
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Button>
          <Card className="bg-slate-900/50 border-slate-800 mt-6">
            <CardContent className="py-12 text-center text-slate-300">
              User not found.
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={() => navigate("/admin/dashboard")}
            className="border-slate-700 hover:bg-slate-800 text-slate-300"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Button>
        </div>

        <Card className="bg-slate-900/50 border-slate-800">
          <CardHeader className="flex flex-row items-center gap-3">
            <UserCircle2 className="w-7 h-7 text-cyan-400" />
            <CardTitle className="text-white">User #{user.id}</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-5 text-sm">
            <div>
              <p className="text-slate-400">Name</p>
              <p className="text-white font-medium">{user.name || "N/A"}</p>
            </div>
            <div>
              <p className="text-slate-400">Email</p>
              <p className="text-white font-medium">{user.email}</p>
            </div>
            <div>
              <p className="text-slate-400">Provider</p>
              <p className="text-white font-medium">{user.provider || "N/A"}</p>
            </div>
            <div>
              <p className="text-slate-400">Status</p>
              {user.is_active ? (
                <Badge className="bg-green-500/20 text-green-400 border-green-500/30">Active</Badge>
              ) : (
                <Badge variant="destructive">Inactive</Badge>
              )}
            </div>
            <div>
              <p className="text-slate-400">Created</p>
              <p className="text-white font-medium">{formatDate(user.created_at)}</p>
            </div>
            <div>
              <p className="text-slate-400">Last Login</p>
              <p className="text-white font-medium">{formatDate(user.last_login)}</p>
            </div>
          </CardContent>
        </Card>

        {user.candidate && (
          <Card className="bg-slate-900/50 border-slate-800">
            <CardHeader>
              <CardTitle className="text-white">Candidate Profile</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-5 text-sm">
              <div>
                <p className="text-slate-400">Candidate ID</p>
                <p className="text-white font-medium">{user.candidate.id}</p>
              </div>
              <div>
                <p className="text-slate-400">Target Role</p>
                <p className="text-white font-medium">{user.candidate.target_role || "N/A"}</p>
              </div>
              <div>
                <p className="text-slate-400">Status</p>
                <p className="text-white font-medium">{user.candidate.status || "N/A"}</p>
              </div>
              <div>
                <p className="text-slate-400">Readiness Score</p>
                <p className="text-white font-medium">{user.candidate.readiness_score ?? "N/A"}</p>
              </div>
              <div>
                <p className="text-slate-400">Latest Analysis</p>
                <p className="text-white font-medium">{formatDate(user.candidate.latest_analysis_date)}</p>
              </div>
              <div>
                <p className="text-slate-400">Profile Created</p>
                <p className="text-white font-medium">{formatDate(user.candidate.created_at)}</p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
