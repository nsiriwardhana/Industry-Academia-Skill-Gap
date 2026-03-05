import { useNavigate } from 'react-router-dom';
import { LogOut, User, Settings } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';

function AvatarButton({ name }: { name: string }) {
  const initials = name
    .split(' ')
    .map(n => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  return (
    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold select-none cursor-pointer hover:brightness-110 transition-all shadow-sm">
      {initials}
    </div>
  );
}

export default function TopBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    toast.success('You have been signed out.');
    navigate('/login', { replace: true });
  };

  if (!user) return null;

  const isExpert = user.userType === 'expert';

  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b bg-background/90 backdrop-blur-sm px-6 py-2.5 gap-3">
      <div className="flex items-center gap-2 md:hidden">
        <span className="text-sm font-semibold text-primary">UpSkill</span>
      </div>
      <div className="flex-1" />
      {/* User name — hidden on small screens */}
      <span className="hidden sm:block text-sm text-muted-foreground">
        {user.name}
      </span>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="rounded-full p-0 h-9 w-9">
            <AvatarButton name={user.name} />
          </Button>
        </DropdownMenuTrigger>

        <DropdownMenuContent align="end" className="w-52">
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col gap-0.5">
              <span className="font-semibold text-sm truncate">{user.name}</span>
              <span className="text-xs text-muted-foreground truncate">{user.email}</span>
            </div>
          </DropdownMenuLabel>

          <DropdownMenuSeparator />

          <DropdownMenuItem onClick={() => navigate('/profile')}>
            <User className="h-4 w-4" />
            Profile
          </DropdownMenuItem>

          {isExpert && (
            <DropdownMenuItem onClick={() => navigate('/settings')}>
              <Settings className="h-4 w-4" />
              Settings
            </DropdownMenuItem>
          )}

          <DropdownMenuSeparator />

          <DropdownMenuItem variant="destructive" onClick={handleLogout}>
            <LogOut className="h-4 w-4" />
            Sign Out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
