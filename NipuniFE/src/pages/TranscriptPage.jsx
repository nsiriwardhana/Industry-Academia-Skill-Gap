import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { FileText, ArrowRight } from "lucide-react";
import { getTranscript } from "@/api/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Spinner } from "@/components/ui/Spinner";

export default function TranscriptPage() {
  const navigate = useNavigate();
  const { studentId } = useParams();
  const [transcript, setTranscript] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchTranscript = async () => {
      setLoading(true);
      setError(null);

      try {
        const data = await getTranscript(studentId);
        setTranscript(data);
      } catch (err) {
        setError(err.response?.data || { message: err.message });
      } finally {
        setLoading(false);
      }
    };

    fetchTranscript();
  }, [studentId]);

  if (loading) return <Spinner />;
  if (error) return <div className="container mx-auto max-w-4xl p-6"><ErrorAlert error={error} /></div>;

  return (
    <div className="container mx-auto max-w-6xl p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-6 w-6" />
            Transcript Details
          </CardTitle>
          <CardDescription>
            Extracted information from your academic transcript
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Student ID</p>
              <p className="text-lg font-semibold">{transcript?.student_id || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Name</p>
              <p className="text-lg font-semibold">{transcript?.name || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Program</p>
              <p className="text-lg font-semibold">{transcript?.program || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Intake</p>
              <p className="text-lg font-semibold">{transcript?.intake || 'N/A'}</p>
            </div>
            <div className="col-span-2">
              <p className="text-sm font-medium text-muted-foreground">Field of Specialization</p>
              <p className="text-lg font-semibold">{transcript?.specialization || 'N/A'}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Courses</CardTitle>
          <CardDescription>
            List of courses extracted from your transcript
          </CardDescription>
        </CardHeader>
        <CardContent>
          {transcript?.courses && transcript.courses.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Course Code</TableHead>
                  <TableHead>Course Name</TableHead>
                  <TableHead>Grade</TableHead>
                  <TableHead>Credits</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transcript.courses.map((course, index) => (
                  <TableRow key={index}>
                    <TableCell className="font-medium">{course.course_code || 'N/A'}</TableCell>
                    <TableCell>{course.course_name || 'N/A'}</TableCell>
                    <TableCell>{course.grade || 'N/A'}</TableCell>
                    <TableCell>{course.credits || 'N/A'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-sm text-muted-foreground">No courses found</p>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button
          onClick={() => navigate(`/students/${studentId}/skills`)}
          size="lg"
        >
          View Skills
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
