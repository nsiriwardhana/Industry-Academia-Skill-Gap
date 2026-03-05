import { Navigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useAuth } from '@/context/AuthContext';
import type { UserType } from '@/context/AuthContext';
import { useEffect, useRef } from 'react';

interface RoleProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles: UserType[];
}

export default function RoleProtectedRoute({ children, allowedRoles }: RoleProtectedRouteProps) {
  const { user } = useAuth();
  const hasToasted = useRef(false);

  const userType = user?.userType ?? 'student';
  const isAllowed = allowedRoles.includes(userType);

  useEffect(() => {
    if (!isAllowed && !hasToasted.current) {
      hasToasted.current = true;
      toast.error('You do not have permission to access that page.');
    }
  }, [isAllowed]);

  if (!isAllowed) {
    // Redirect experts to /feedback, students to /
    const fallback = userType === 'expert' ? '/feedback' : '/';
    return <Navigate to={fallback} replace />;
  }

  return <>{children}</>;
}
