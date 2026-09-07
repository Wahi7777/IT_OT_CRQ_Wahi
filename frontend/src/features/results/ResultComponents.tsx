import {ArrowDown, ArrowRight, CheckCircle2, CircleDot, LockKeyhole, ShieldAlert, TrendingDown, TrendingUp} from "lucide-react";
import {Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis} from "recharts";
import {Badge, EmptyState, GlassPanel} from "../../components/ui";

export const money = (value: unknown, currency?: string | null) => typeof value === "number" ? currency ? new Intl.NumberFormat("en-AE", {style: "currency", currency, notation: "compact", maximumFractionDigits: 2}).format(value) : `${new Intl.NumberFormat("en-AE", {notation: "compact", maximumFractionDigits: 2}).format(value)} currency units` : "Not returned";
export const number = (value: unknown, digits = 2) => typeof value === "number" ? new Intl.NumberFormat("en-AE", {maximumFractionDigits: digits}).format(value) : "Not returned";
export const percent = (value: unknown) => typeof value === "number" ? new Intl.NumberFormat("en-AE", {style: "percent", maximumFractionDigits: 2}).format(value) : "Not returned";

export function MetricCard({label, value, comparison, tone = "neutral"}: {label: string; value: string; comparison?: string; tone?: string}) {
  return <GlassPanel className={`metric-card metric-card--${tone}`}><div className="metric-label"><span>{label}</span>{tone === "red" ? <ShieldAlert /> : tone === "green" ? <CheckCircle2 /> : <CircleDot />}</div><strong>{value}</strong>{comparison && <small>{comparison}</small>}</GlassPanel>;
}

export function FinancialBars({data, valueKey = "value", currency}: {data: {name: string; [key: string]: any}[]; valueKey?: string; currency?: string | null}) {
  return <div className="chart" role="img" aria-label="Financial values bar chart"><ResponsiveContainer width="100%" height={280}><BarChart data={data} margin={{top: 12, right: 10, left: 0, bottom: 20}}><CartesianGrid vertical={false} stroke="rgba(255,255,255,.07)" /><XAxis dataKey="name" tick={{fill: "#98a2b3", fontSize: 12}} axisLine={false} tickLine={false} /><YAxis tickFormatter={(value) => new Intl.NumberFormat("en-AE", {notation: "compact", maximumFractionDigits: 1}).format(Number(value))} tick={{fill: "#98a2b3", fontSize: 12}} axisLine={false} tickLine={false} width={52} /><Tooltip contentStyle={{background: "#141923", border: "1px solid rgba(255,255,255,.12)", borderRadius: 12}} formatter={(v) => money(Number(v), currency)} /><Bar dataKey={valueKey} radius={[7, 7, 0, 0]}>{data.map((_, index) => <Cell key={index} fill={index === data.length - 1 ? "#8b83ff" : "#4d5566"} />)}</Bar></BarChart></ResponsiveContainer></div>;
}

export function RiskFunnel({formation, currency}: {formation: Record<string, any>; currency?: string | null}) {
  const stages = [
    ["Campaigns", number(formation.campaigns_per_year, 3)], ["Threat actor", "Actor mix"], ["Scenario", "Scenario mix"],
    ["Route / path", percent(formation.conditional_success_probability)], ["Architecture", "Feasibility"], ["Controls", "Effectiveness"],
    ["Successful event", number(formation.successful_events_per_year, 4)], ["Financial impact", money(formation.aal, currency)]
  ];
  return <div className="risk-funnel">{stages.map(([label, value], index) => <div className="funnel-stage" tabIndex={0} key={label}><small>0{index + 1}</small><span>{label}</span><strong>{value}</strong>{index < stages.length - 1 && <ArrowRight className="funnel-arrow" />}</div>)}</div>;
}

export function RankedList({items, valuePath = "metrics.prudent_aal", currency}: {items: any[]; valuePath?: string; currency?: string | null}) {
  const value = (item: any) => valuePath.split(".").reduce((target, key) => target?.[key], item);
  const ranked = [...items].sort((left, right) => (value(right) ?? 0) - (value(left) ?? 0));
  return <div className="ranked-list">{ranked.map((item, index) => <article key={item.id ?? item.name ?? index}><span className="rank">{String(index + 1).padStart(2, "0")}</span><div><strong>{item.name ?? item.id}</strong><small>{item.metadata?.description ?? item.category ?? "Canonical decomposition"}</small></div><span className="rank-value">{money(value(item) ?? item.aal, currency)}</span></article>)}</div>;
}

export function Direction({value}: {value: number}) {
  return value < 0 ? <span className="green-text"><TrendingDown />{percent(Math.abs(value))}</span> : <span><TrendingUp />{percent(value)}</span>;
}

export function StateBadge({value}: {value: string}) {
  const normalized = value.toUpperCase();
  const tone = normalized === "CLOSED" ? "green" : normalized === "UNKNOWN" ? "amber" : normalized === "OPEN" ? "red" : "neutral";
  return <Badge tone={tone}>{normalized}</Badge>;
}

export function NoCanonicalData({family}: {family: string}) {
  return <GlassPanel><EmptyState title={`No ${family} returned`} body="The approved canonical result does not contain this optional output family. The interface does not substitute or calculate a value." /></GlassPanel>;
}

export function FlowArrow() { return <ArrowDown className="flow-down" aria-hidden="true" />; }
export function LockNote({children}: {children: string}) { return <span className="lock-note"><LockKeyhole />{children}</span>; }
