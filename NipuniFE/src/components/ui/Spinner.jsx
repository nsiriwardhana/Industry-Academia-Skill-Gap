import { Loader2 } from "lucide-react";

export function Spinner({ className = "h-8 w-8" }) {
  return (
    <div className="flex justify-center items-center p-8">
      <Loader2 className={`${className} animate-spin text-primary`} />
    </div>
  );
}
