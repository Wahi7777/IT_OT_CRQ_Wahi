import {ChevronRight} from "lucide-react";
import type {ReactNode} from "react";
import {Link} from "react-router-dom";

export function PageHeader({eyebrow, title, description, actions}: {eyebrow?: string; title: string; description?: string; actions?: ReactNode}) {
  return <header className="page-header">
    <div>
      {eyebrow && <div className="eyebrow"><Link to="/assessments">Assessments</Link><ChevronRight size={13} />{eyebrow}</div>}
      <h1>{title}</h1>
      {description && <p>{description}</p>}
    </div>
    {actions && <div className="page-actions">{actions}</div>}
  </header>;
}
