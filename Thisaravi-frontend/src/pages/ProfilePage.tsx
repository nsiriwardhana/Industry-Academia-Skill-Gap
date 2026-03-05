import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import {
  User, Mail, Briefcase, FileText, CalendarDays,
  GraduationCap, Lightbulb, Brain, Code2,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import PageHeader from '@/components/layout/PageHeader';

const schema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  bio: z.string().max(300).optional(),
  role: z.string().max(100).optional(),
  current_role: z.string().max(100).optional(),
  major: z.string().max(100).optional(),
  interests: z.string().max(300).optional(),
  personality: z.string().max(300).optional(),
  skills: z.string().max(500).optional(),
});

type FormValues = z.infer<typeof schema>;

function AvatarPlaceholder({ name }: { name: string }) {
  const initials = name
    .split(' ')
    .map(n => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
  return (
    <div className="flex h-20 w-20 items-center justify-center rounded-full bg-primary text-primary-foreground text-2xl font-bold select-none shrink-0">
      {initials}
    </div>
  );
}

function fromUser(user: ReturnType<typeof useAuth>['user']): FormValues {
  return {
    name: user?.name ?? '',
    bio: user?.bio ?? '',
    role: user?.role ?? '',
    current_role: user?.current_role ?? '',
    major: user?.major ?? '',
    interests: user?.interests ?? '',
    personality: user?.personality ?? '',
    skills: user?.skills ?? '',
  };
}

function Field({
  label,
  icon,
  error,
  children,
}: {
  label: string;
  icon: React.ReactNode;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {icon}
        {label}
      </Label>
      {children}
      {error && <p className="text-destructive text-xs">{error}</p>}
    </div>
  );
}

export default function ProfilePage() {
  const { user, updateProfile } = useAuth();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: fromUser(user),
  });

  // Sync form whenever the user object changes (e.g. after save)
  useEffect(() => {
    reset(fromUser(user));
  }, [user, reset]);

  if (!user) return null;

  const joinedDate = new Date(user.joinedAt).toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
  });

  const onSubmit = (data: FormValues) => {
    updateProfile({
      name: data.name,
      bio: data.bio || undefined,
      role: data.role || undefined,
      current_role: data.current_role || undefined,
      major: data.major || undefined,
      interests: data.interests || undefined,
      personality: data.personality || undefined,
      skills: data.skills || undefined,
    });
    toast.success('Profile updated!');
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <PageHeader
        title="Profile"
        subtitle="Your personal information — used automatically across the app"
      />

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* ── Identity ── */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-4">
              <AvatarPlaceholder name={user.name} />
              <div className="min-w-0">
                <CardTitle className="text-xl truncate">{user.name}</CardTitle>
                <CardDescription className="flex items-center gap-1 mt-1">
                  <Mail className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{user.email}</span>
                </CardDescription>
                <CardDescription className="flex items-center gap-1">
                  <CalendarDays className="h-3.5 w-3.5 shrink-0" />
                  Member since {joinedDate}
                </CardDescription>
              </div>
            </div>
          </CardHeader>

          <Separator />

          <CardContent className="pt-6 space-y-4">
            <Field label="Full Name" icon={<User className="h-3.5 w-3.5" />} error={errors.name?.message}>
              <Input id="name" {...register('name')} />
            </Field>

            <Field label="Title / Job Title" icon={<Briefcase className="h-3.5 w-3.5" />} error={errors.role?.message}>
              <Input id="role" placeholder="e.g. Software Engineer" {...register('role')} />
            </Field>

            <Field label="Bio" icon={<FileText className="h-3.5 w-3.5" />} error={errors.bio?.message}>
              <Textarea id="bio" rows={3} placeholder="Tell us a bit about yourself…" {...register('bio')} />
            </Field>
          </CardContent>
        </Card>

        {/* ── Academic & Skills Profile ── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Academic &amp; Skills Profile</CardTitle>
            <CardDescription>
              These details are pre-filled automatically in the Skill Gap Analyzer — update them here once and they'll always be current.
            </CardDescription>
          </CardHeader>

          <Separator />

          <CardContent className="pt-6 space-y-4">
            <Field label="Current Role" icon={<Briefcase className="h-3.5 w-3.5" />} error={errors.current_role?.message}>
              <Input id="current_role" placeholder="e.g. Undergraduate Student" {...register('current_role')} />
            </Field>

            <Field label="Major / Background" icon={<GraduationCap className="h-3.5 w-3.5" />} error={errors.major?.message}>
              <Input id="major" placeholder="e.g. Computer Science" {...register('major')} />
            </Field>

            <Field label="Interests (comma separated)" icon={<Lightbulb className="h-3.5 w-3.5" />} error={errors.interests?.message}>
              <Input id="interests" placeholder="e.g. AI, Web Development, NLP" {...register('interests')} />
            </Field>

            <Field label="Personality Traits" icon={<Brain className="h-3.5 w-3.5" />} error={errors.personality?.message}>
              <Input id="personality" placeholder="e.g. ambitious, analytical, team-player" {...register('personality')} />
            </Field>

            <Field label="Current Skills (comma separated)" icon={<Code2 className="h-3.5 w-3.5" />} error={errors.skills?.message}>
              <Textarea id="skills" rows={3} placeholder="e.g. Python, SQL, React, Git" {...register('skills')} />
            </Field>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button type="submit" disabled={!isDirty}>
            Save Changes
          </Button>
        </div>
      </form>
    </div>
  );
}
