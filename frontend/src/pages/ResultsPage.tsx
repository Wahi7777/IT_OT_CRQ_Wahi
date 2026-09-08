import {AlertTriangle, BarChart3, Boxes, ChevronRight, FileSearch, Gauge, Info, Network, ShieldCheck, Target} from "lucide-react";
import {useEffect, useState} from "react";
import {useLocation, useParams} from "react-router-dom";
import {getRunApi} from "../api/RunApi";
import {AIPlaceholder} from "../components/AIPlaceholder";
import {Badge, EmptyState, GlassPanel} from "../components/ui";
import {outputMappings, resultScreens} from "../contracts/governedData";
import type {CRQResult} from "../contracts/types";
import {FinancialBars, MetricCard, NoCanonicalData, RankedList, RiskFunnel, StateBadge, money, number, percent} from "../features/results/ResultComponents";
import {ResultsShell} from "../features/results/ResultsShell";
import {useAssessment} from "../features/assessment/AssessmentContext";

export function ResultsPage() {
  const {domain, dataMode, request} = useAssessment();
  const {runId = "demo"} = useParams();
  const [result, setResult] = useState<CRQResult | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const page = useLocation().pathname.split("/").at(-1) ?? "overview";
  useEffect(() => {
    let active = true;
    getRunApi(dataMode).getResult(runId).then((next) => {if (active) {setResult(next); setLoadError(null);}}).catch((reason) => {if (active) setLoadError(reason instanceof Error ? reason.message : "The result could not be loaded.");});
    return () => {active = false;};
  }, [dataMode, domain, runId]);
  if (!result) return <GlassPanel><span className="spinner" /> Loading canonical result…{loadError && <div className="error-banner" role="alert">{loadError}</div>}</GlassPanel>;
  const resultDomain = result.compatibility?.native_domain === "OT" || result.provenance?.sector_pack_id?.startsWith("OT-") ? "OT" : domain;
  const currency = request.assessment.assessment.currency;
  return <ResultsShell result={result} domain={resultDomain} currency={currency}>{loadError && <div className="error-banner" role="alert">{loadError}</div>}{renderPage(page, result, resultDomain, currency)}</ResultsShell>;
}

function renderPage(page: string, result: CRQResult, domain: "IT" | "OT", currency?: string | null) {
  switch (page) {
    case "overview": return <Overview result={result} currency={currency} />;
    case "risk-drivers": return <RiskDrivers result={result} currency={currency} />;
    case "scenarios": return <Scenarios result={result} currency={currency} />;
    case "attack-paths": return <AttackPaths result={result} domain={domain} />;
    case "business-impact": return <BusinessImpact result={result} domain={domain} currency={currency} />;
    case "treatment": return <Treatment result={result} currency={currency} />;
    case "insurance": return <Insurance result={result} currency={currency} />;
    case "uncertainty": return <Uncertainty result={result} />;
    case "evidence": return <Evidence result={result} />;
    default: return <Overview result={result} currency={currency} />;
  }
}

function Overview({result, currency}: {result: CRQResult; currency?: string | null}) {
  const prudent = result.summary.prudent;
  const best = result.summary.best_estimate;
  const chartData = [
    {name: "AAL", value: prudent.aal}, {name: "VaR 95", value: prudent.var95}, {name: "VaR 99", value: prudent.var99},
    {name: "TVaR 95", value: prudent.tvar95}, {name: "TVaR 99", value: prudent.tvar99}
  ];
  const topDriver = [...(result.loss.categories ?? [])].sort((a, b) => (b.aal ?? 0) - (a.aal ?? 0))[0];
  return <>
    <div className="metric-grid"><MetricCard label="Prudent AAL" value={money(prudent.aal, currency)} comparison={`Best estimate ${money(best.aal, currency)}`} /><MetricCard label="VaR 99" value={money(prudent.var99, currency)} comparison="Prudent basis" tone="amber" /><MetricCard label="TVaR 99" value={money(prudent.tvar99, currency)} comparison="Prudent tail mean" tone="red" /><MetricCard label="P(material event)" value={percent(prudent.p_any_event)} comparison={`${number(prudent.event_frequency, 4)} events / year`} /><MetricCard label="Risk appetite" value={result.summary.appetite.status ?? "Not returned"} tone={result.summary.appetite.status === "Tolerance not set" ? "amber" : "green"} /><MetricCard label="Evidence confidence" value="Not scored" comparison={`${result.architecture.evidence_status?.length ?? 0} canonical evidence records`} /></div>
    <div className="overview-grid"><GlassPanel className="chart-panel"><div className="panel-title-row"><div><span className="overline">Prudent basis</span><h2>Annual loss profile</h2></div><Badge tone="indigo">{currency ?? "Currency unspecified"}</Badge></div><FinancialBars data={chartData} currency={currency} /></GlassPanel>
      <GlassPanel className="driver-spotlight"><span className="overline">Principal loss category</span><h2>{topDriver?.name ?? "Not returned"}</h2><strong>{money(topDriver?.aal, currency)}</strong><p>{topDriver ? `${percent(topDriver.pct_aal)} of annualized loss.` : "No category decomposition was returned."}</p><div className="spotlight-line"><span>TVaR99 contribution</span><strong>{money(topDriver?.contrib_tvar99, currency)}</strong></div></GlassPanel></div>
    <AIPlaceholder />
  </>;
}

function RiskDrivers({result, currency}: {result: CRQResult; currency?: string | null}) {
  return <><GlassPanel className="funnel-panel"><div className="panel-title-row"><div><span className="overline">Risk formation</span><h2>From campaign to financial impact</h2></div><Badge tone="neutral">Interactive chain</Badge></div><p className="panel-intro">Explore each governed stage without merging architecture feasibility and control effectiveness.</p><RiskFunnel formation={result.formation} currency={currency} /></GlassPanel><div className="two-column"><GlassPanel><div className="panel-title-row"><h2>Dominant actors</h2><Target /></div><RankedList items={result.decomposition.actors ?? []} currency={currency} /></GlassPanel><GlassPanel><div className="panel-title-row"><h2>Frequency funnel</h2><Gauge /></div><dl className="fact-list">{Object.entries(result.formation).map(([key, value]) => <div key={key}><dt>{human(key)}</dt><dd>{key.includes("probability") ? percent(value) : key === "aal" ? money(value, currency) : number(value, 4)}</dd></div>)}</dl></GlassPanel></div></>;
}

function Scenarios({result, currency}: {result: CRQResult; currency?: string | null}) {
  const scenarios = result.decomposition.scenarios ?? [];
  return <><div className="scenario-grid">{scenarios.map((scenario: any, index: number) => <GlassPanel className="scenario-card" key={scenario.id}><div className="scenario-head"><span>{String(index + 1).padStart(2, "0")}</span><Badge tone={index === 0 ? "red" : "neutral"}>{index === 0 ? "Dominant" : "Scenario"}</Badge></div><h2>{scenario.name}</h2><div className="scenario-metrics"><div><span>Prudent AAL</span><strong>{money(scenario.metrics?.prudent_aal, currency)}</strong></div><div><span>TVaR99 contribution</span><strong>{money(scenario.contribution?.tvar99, currency)}</strong></div></div><button className="text-link">Open decomposition <ChevronRight /></button></GlassPanel>)}</div><div className="canonical-grid"><CanonicalFamily title="Actor · scenario decomposition" value={result.decomposition.actor_scenario} /><CanonicalFamily title="IT route decomposition" value={result.decomposition.it_routes} /><CanonicalFamily title="OT path / TTP decomposition" value={result.decomposition.ot_paths_ttps} /></div></>;
}

function AttackPaths({result, domain}: {result: CRQResult; domain: "IT" | "OT"}) {
  const paths = result.architecture.route_path_states ?? [];
  const grouped = paths.slice(0, 16);
  return <><GlassPanel className="path-explainer"><Network /><div><span className="overline">{domain === "IT" ? "Route-state architecture" : "S1–S5 progression"}</span><h2>{domain === "IT" ? "Feasibility remains separate from control effectiveness" : "Operational paths retain applicability and stage semantics"}</h2><p>States and probabilities below are rendered directly from the canonical architecture result.</p></div></GlassPanel><GlassPanel className="data-table-panel"><div className="panel-title-row"><h2>{domain === "IT" ? "Actor · scenario · route states" : "Actor · scenario path states"}</h2><Badge tone="neutral">{paths.length} records</Badge></div><div className="data-table"><div className="data-row data-head"><span>Actor</span><span>Scenario</span><span>{domain === "IT" ? "Route" : "Stage path"}</span><span>Event probability</span><span>Path success</span></div>{grouped.map((path: any, index: number) => <div className="data-row" key={index}><strong>{path.actor}</strong><span>{path.scenario}</span><span>{path.route ?? (domain === "OT" ? "S1 → S5" : "Canonical path")}</span><span>{percent(path.annual_event_probability)}</span><span>{percent(path.success_probability)}</span></div>)}</div></GlassPanel><div className="canonical-grid"><CanonicalFamily title="Relevant TTPs" value={result.architecture.relevant_ttps} /><CanonicalFamily title="Barriers" value={result.architecture.barriers} /><CanonicalFamily title="Stage-through probabilities" value={result.architecture.stage_through_probabilities} /><CanonicalFamily title="Applicability" value={result.architecture.applicability} /><CanonicalFamily title="Feasibility" value={result.architecture.feasibility} /><CanonicalFamily title="Architecture input snapshot" value={result.architecture.input_snapshot} /></div>{domain === "IT" && <GlassPanel><div className="panel-title-row"><h2>Governed state legend</h2></div><div className="state-legend"><StateBadge value="OPEN" /><StateBadge value="CONDITIONAL" /><StateBadge value="CLOSED" /><StateBadge value="UNKNOWN" /><span>Unknown is never coerced to closed.</span></div></GlassPanel>}</>;
}

function BusinessImpact({result, domain, currency}: {result: CRQResult; domain: "IT" | "OT"; currency?: string | null}) {
  const categories = result.loss.categories ?? [];
  const chart = categories.slice(0, 8).map((item: any) => ({name: truncate(item.name), value: item.aal}));
  const impacts = domain === "OT" ? result.impact.ot_downtime ?? result.impact.ot_capacity : {...result.impact.it_affected_records, ...result.impact.it_affected_endpoints, ...result.impact.it_affected_services};
  return <><div className="two-column wide-left"><GlassPanel className="chart-panel"><div className="panel-title-row"><div><span className="overline">Loss decomposition</span><h2>Business interruption and non-BI drivers</h2></div><Badge tone="indigo">AAL · {currency ?? "currency unspecified"}</Badge></div><FinancialBars data={chart} currency={currency} /></GlassPanel><GlassPanel><h2>{domain === "OT" ? "Downtime & capacity" : "Affected digital estate"}</h2><dl className="fact-list">{Object.entries(impacts ?? {}).slice(0, 12).map(([key, value]) => <div key={key}><dt>{human(key)}</dt><dd>{key.includes("capacity") || key.startsWith("p_") ? percent(value) : number(value)}</dd></div>)}</dl></GlassPanel></div><GlassPanel><div className="panel-title-row"><h2>Loss categories</h2><Badge tone="neutral">{categories.length}</Badge></div><RankedList items={categories} valuePath="aal" currency={currency} /></GlassPanel><div className="canonical-grid"><CanonicalFamily title="AEP curve" value={result.loss.aep} /><CanonicalFamily title="OEP curve" value={result.loss.oep} /><CanonicalFamily title="Return periods" value={result.loss.return_periods} /><CanonicalFamily title="Business interruption" value={result.loss.business_interruption} /><CanonicalFamily title="Non-BI" value={result.loss.non_bi} /><CanonicalFamily title="Individual loss drivers" value={result.loss.drivers} /><CanonicalFamily title="Loss reconciliation" value={result.loss.reconciliation} /></div></>;
}

function Treatment({result, currency}: {result: CRQResult; currency?: string | null}) {
  const controls = result.treatments.individual_controls ?? [];
  return controls.length ? <><div className="treatment-summary"><MetricCard label="Controls modelled" value={String(controls.length)} /><MetricCard label="Treatment packages" value={String(result.treatments.packages?.length ?? 0)} /><MetricCard label="Sensitivity outputs" value={String(result.sensitivity?.length ?? 0)} /></div><GlassPanel className="data-table-panel"><div className="panel-title-row"><div><span className="overline">Engine-calculated</span><h2>Individual control treatments</h2></div><Badge tone="green">No UI arithmetic</Badge></div><div className="data-table treatment-table"><div className="data-row data-head"><span>Control</span><span>Current</span><span>Target</span><span>Current AAL</span><span>Post-treatment AAL</span></div>{controls.slice(0, 16).map((control: any, index: number) => <div className="data-row" key={control.cid ?? index}><strong>{control.cid ?? control.id} · {control.channel ?? control.name}</strong><span>{control.current ?? "Returned"}</span><span>{control.target ?? "Returned"}</span><span>{money(control.current_aal ?? control.prudent?.baseline ?? control.pr?.baseline, currency)}</span><span>{money(control.post_aal ?? control.prudent?.aal ?? control.pr?.aal, currency)}</span></div>)}</div></GlassPanel><div className="canonical-grid"><CanonicalFamily title="Treatment packages" value={result.treatments.packages} /><CanonicalFamily title="Post-treatment metrics" value={result.treatments.post_treatment_metrics} /><CanonicalFamily title="Engine reductions" value={result.treatments.reductions} /><CanonicalFamily title="Treatment rankings" value={result.treatments.rankings} /><CanonicalFamily title="Sensitivity outputs" value={result.sensitivity} /></div></> : <NoCanonicalData family="treatment" />;
}

function Insurance({result, currency}: {result: CRQResult; currency?: string | null}) {
  const insurance = result.insurance;
  if (!insurance || Array.isArray(insurance) || Object.keys(insurance).length === 0) return <NoCanonicalData family="insurance outputs" />;
  return <div className="insurance-flow">{Object.entries(insurance).map(([key, value]) => <GlassPanel key={key}><span>{human(key)}</span><strong>{typeof value === "number" ? money(value, currency) : JSON.stringify(value)}</strong></GlassPanel>)}</div>;
}

function Uncertainty({result}: {result: CRQResult}) {
  const mc = result.uncertainty.monte_carlo ?? {};
  const limitations = result.uncertainty.evidence_limitations ?? result.limitations ?? [];
  return <div className="two-column"><GlassPanel><div className="panel-title-row"><h2>Monte Carlo uncertainty</h2><BarChart3 /></div><dl className="fact-list">{Object.entries(mc).map(([key, value]) => <div key={key}><dt>{human(key)}</dt><dd>{key.includes("aal") ? money(value) : number(value, 6)}</dd></div>)}</dl></GlassPanel><GlassPanel><div className="panel-title-row"><h2>Evidence limitations</h2><AlertTriangle className="amber-text pulse-warning" /></div>{limitations.length ? <div className="limitation-list">{limitations.map((item: any, index: number) => <div key={item.id ?? index}><Badge tone="amber">{item.id ?? `L${index + 1}`}</Badge><p>{item.reason ?? item.description ?? String(item)}</p></div>)}</div> : <EmptyState title="No limitations returned" body="The approved result contains no evidence limitation records." />}</GlassPanel></div>;
}

function Evidence({result}: {result: CRQResult}) {
  const evidence = result.architecture.evidence_status ?? [];
  const placement = resultScreens.map((screen) => ({screen: screen.screen_id, count: outputMappings.filter((mapping: any) => screen.prefixes.some((prefix: string) => mapping.canonical_path.startsWith(prefix))).length}));
  return <><div className="two-column"><GlassPanel><div className="panel-title-row"><h2>Model provenance</h2><ShieldCheck /></div><dl className="fact-list">{Object.entries(result.provenance).filter(([key]) => !key.includes("hash")).map(([key, value]) => <div key={key}><dt>{human(key)}</dt><dd>{String(value)}</dd></div>)}</dl></GlassPanel><GlassPanel><div className="panel-title-row"><h2>Canonical coverage</h2><Boxes /></div><div className="coverage-list">{placement.map((item) => <div key={item.screen}><span>{human(item.screen)}</span><strong>{item.count} families</strong></div>)}</div></GlassPanel></div><GlassPanel><div className="panel-title-row"><h2>Evidence records</h2><Badge tone="indigo">{evidence.length}</Badge></div><div className="evidence-list">{evidence.slice(0, 18).map((item: any, index: number) => <article key={item.evidence_id ?? index}><FileSearch /><div><strong>{item.evidence_id}</strong><p>{item.description}</p></div><Badge tone={item.source ? "green" : "amber"}>{item.source ?? "Unspecified"}</Badge></article>)}</div></GlassPanel><div className="canonical-grid"><CanonicalFamily title="Compatibility metadata" value={{lossless: result.compatibility.lossless, native_domain: result.compatibility.native_domain, router_metadata: result.compatibility.router_metadata}} /><CanonicalFamily title="Hash provenance" value={Object.fromEntries(Object.entries(result.provenance).filter(([key]) => key.includes("hash")))} /></div></>;
}

function CanonicalFamily({title, value}: {title: string; value: unknown}) {
  const empty = value == null || (Array.isArray(value) && value.length === 0) || (typeof value === "object" && !Array.isArray(value) && Object.keys(value as object).length === 0);
  const entries = Array.isArray(value) ? value.slice(0, 4).map((item, index) => [String(index + 1), item] as const) : value && typeof value === "object" ? Object.entries(value as Record<string, unknown>).slice(0, 8) : [["value", value] as const];
  return <GlassPanel className="canonical-family"><div className="panel-title-row"><h2>{title}</h2><Badge tone={empty ? "neutral" : "indigo"}>{Array.isArray(value) ? `${value.length} records` : empty ? "Not returned" : "Canonical"}</Badge></div>{empty ? <p className="muted">No values returned for this optional canonical family.</p> : <dl>{entries.map(([key, item]) => <div key={key}><dt>{human(key)}</dt><dd>{digest(item)}</dd></div>)}</dl>}</GlassPanel>;
}

function digest(value: unknown) {
  if (value == null) return "Not returned";
  if (typeof value !== "object") return String(value);
  if (Array.isArray(value)) return `${value.length} values`;
  const record = value as Record<string, unknown>;
  return String(record.name ?? record.id ?? record.route_id ?? record.ttp_id ?? record.parameter_id ?? `${Object.keys(record).length} fields`);
}

function human(value: string) { return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); }
function truncate(value: string) { return value.length > 18 ? `${value.slice(0, 16)}…` : value; }
