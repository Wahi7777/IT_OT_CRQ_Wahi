import type {ButtonHTMLAttributes, ReactNode} from "react";
import {LockKeyhole, ShieldCheck} from "lucide-react";

export function GlassPanel({children, className = "", as: Tag = "section"}: {children: ReactNode; className?: string; as?: "section" | "article" | "aside" | "div"}) {
  return <Tag className={`glass-panel ${className}`}>{children}</Tag>;
}

export function Button({className = "", variant = "primary", ...props}: ButtonHTMLAttributes<HTMLButtonElement> & {variant?: "primary" | "secondary" | "ghost" | "danger"}) {
  return <button className={`button button--${variant} ${className}`} {...props} />;
}

export function Badge({children, tone = "neutral"}: {children: ReactNode; tone?: "neutral" | "green" | "amber" | "red" | "indigo"}) {
  return <span className={`badge badge--${tone}`}>{children}</span>;
}

export function LockedBanner({children = "Governed by the approved model bundle"}: {children?: ReactNode}) {
  return <div className="locked-banner"><LockKeyhole size={15} aria-hidden="true" />{children}</div>;
}

export function ProvenanceStamp({children}: {children: ReactNode}) {
  return <span className="provenance-stamp"><ShieldCheck size={14} aria-hidden="true" />{children}</span>;
}

export function EmptyState({title, body}: {title: string; body: string}) {
  return <div className="empty-state"><div className="empty-orbit" aria-hidden="true" /><h3>{title}</h3><p>{body}</p></div>;
}
