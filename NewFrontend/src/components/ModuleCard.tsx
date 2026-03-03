import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowRight, LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

interface ModuleCardProps {
  title: string;
  description: string;
  icon: LucideIcon;
  features: string[];
  link: string;
  gradient: string;
}

const ModuleCard = ({ title, description, icon: Icon, features, link, gradient }: ModuleCardProps) => {
  return (
    <Card className="group relative overflow-hidden glass-card hover:shadow-strong transition-all duration-300 hover:-translate-y-2">
      {/* Gradient Background */}
      <div className={`absolute inset-0 ${gradient} opacity-0 group-hover:opacity-10 transition-opacity duration-300`} />
      
      <div className="relative p-8 space-y-6">
        {/* Icon */}
        <div className={`w-16 h-16 rounded-2xl ${gradient} flex items-center justify-center shadow-medium group-hover:scale-110 transition-transform duration-300`}>
          <Icon className="w-8 h-8 text-white" />
        </div>

        {/* Content */}
        <div className="space-y-3">
          <h3 className="text-2xl font-bold text-foreground">{title}</h3>
          <p className="text-muted-foreground leading-relaxed">{description}</p>
        </div>

        {/* Features */}
        <ul className="space-y-2">
          {features.map((feature, index) => (
            <li key={index} className="flex items-start gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-primary mt-2 flex-shrink-0" />
              <span className="text-sm text-muted-foreground">{feature}</span>
            </li>
          ))}
        </ul>

        {/* CTA */}
        <Link to={link}>
          <Button variant="ghost" className="group/btn w-full justify-between mt-4">
            <span>Explore Module</span>
            <ArrowRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
          </Button>
        </Link>
      </div>
    </Card>
  );
};

export default ModuleCard;
