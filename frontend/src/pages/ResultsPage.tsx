import {
  Boxes,
  FileSearch,
  Filter,
  Gauge,
  Info,
  Network,
  ShieldCheck,
  Target,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { getRunApi } from "../api/RunApi";
import { Badge, GlassPanel } from "../components/ui";
import { outputMappings, resultScreens } from "../contracts/governedData";
import type { CRQResult } from "../contracts/types";
import {
  FinancialBars,
  LossCategoryDonut,
  LossExceedanceCurve,
  MetricCard,
  NoCanonicalData,
  RankedList,
  RiskFunnel,
  money,
  number,
  percent,
} from "../features/results/ResultComponents";
import { ResultsShell } from "../features/results/ResultsShell";
import { useAssessment } from "../features/assessment/AssessmentContext";

export function ResultsPage() {
  const { domain, dataMode, request } = useAssessment();
  const { runId = "demo" } = useParams();
  const [result, setResult] = useState<CRQResult | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedResultEntity, setSelectedResultEntity] = useState<{
    entity_type: string;
    entity_id: string;
  } | null>(null);
  const page = useLocation().pathname.split("/").at(-1) ?? "overview";
  useEffect(() => {
    let active = true;
    getRunApi(dataMode)
      .getResult(runId)
      .then((next) => {
        if (active) {
          setResult(next);
          setLoadError(null);
        }
      })
      .catch((reason) => {
        if (active)
          setLoadError(
            reason instanceof Error
              ? reason.message
              : "The result could not be loaded.",
          );
      });
    return () => {
      active = false;
    };
  }, [dataMode, domain, runId]);
  if (!result)
    return (
      <GlassPanel>
        <span className="spinner" /> Loading canonical result…
        {loadError && (
          <div className="error-banner" role="alert">
            {loadError}
          </div>
        )}
      </GlassPanel>
    );
  const resultDomain =
    result.compatibility?.native_domain === "OT" ||
    result.provenance?.sector_pack_id?.startsWith("OT-")
      ? "OT"
      : domain;
  const currency = request.assessment.assessment.currency ?? (resultDomain === "OT" ? "USD" : null);
  return (
    <ResultsShell
      result={result}
      domain={resultDomain}
      currency={currency}
      selectedEntity={page === "attack-paths" ? selectedResultEntity : null}
    >
      {loadError && (
        <div className="error-banner" role="alert">
          {loadError}
        </div>
      )}
      {renderPage(page, result, resultDomain, currency, setSelectedResultEntity)}
    </ResultsShell>
  );
}

function renderPage(
  page: string,
  result: CRQResult,
  domain: "IT" | "OT",
  currency?: string | null,
  onSelectedEntityChange?: (
    entity: { entity_type: string; entity_id: string } | null,
  ) => void,
) {
  switch (page) {
    case "overview":
      return <Overview result={result} currency={currency} />;
    case "risk-drivers":
      return <RiskDrivers result={result} currency={currency} />;
    case "scenarios":
      return <Scenarios result={result} currency={currency} />;
    case "attack-paths":
      return (
        <AttackPaths
          result={result}
          domain={domain}
          onSelectedEntityChange={onSelectedEntityChange}
        />
      );
    case "business-impact":
      return (
        <BusinessImpact result={result} domain={domain} currency={currency} />
      );
    case "treatment":
      return <Treatment result={result} currency={currency} />;
    case "insurance":
      return <Insurance result={result} currency={currency} />;
    case "uncertainty":
      return <Overview result={result} currency={currency} />;
    case "evidence":
      return <Evidence result={result} />;
    default:
      return <Overview result={result} currency={currency} />;
  }
}

function Overview({
  result,
  currency,
}: {
  result: CRQResult;
  currency?: string | null;
}) {
  const prudent = result.summary.prudent;
  const best = result.summary.best_estimate;
  return (
    <>
      <div className="metric-grid">
        <MetricCard
          label="Prudent AAL"
          value={money(prudent.aal, currency)}
          comparison={`Best estimate ${money(best.aal, currency)}`}
        />
        <MetricCard
          label="VaR 95"
          value={money(prudent.var95, currency)}
          comparison="95th percentile annual loss"
        />
        <MetricCard
          label="VaR 99"
          value={money(prudent.var99, currency)}
          comparison="99th percentile annual loss"
          tone="amber"
        />
        <MetricCard
          label="TVaR 95"
          value={money(prudent.tvar95, currency)}
          comparison="Mean loss beyond VaR95"
        />
        <MetricCard
          label="TVaR 99"
          value={money(prudent.tvar99, currency)}
          comparison="Mean loss beyond VaR99"
          tone="red"
        />
        <MetricCard
          label="P(material event)"
          value={percent(prudent.p_any_event)}
          comparison={`${number(prudent.event_frequency, 4)} events / year`}
        />
        <MetricCard
          label="Risk appetite"
          value={result.summary.appetite.status ?? "Not returned"}
          tone={
            result.summary.appetite.status === "Tolerance not set"
              ? "amber"
              : "green"
          }
        />
        <MetricCard
          label="Evidence confidence"
          value="Not scored"
          comparison={`${result.architecture.evidence_status?.length ?? 0} evidence records`}
        />
      </div>
      <div className="overview-grid">
        <GlassPanel className="chart-panel">
          <div className="panel-title-row">
            <div>
              <span className="overline">Prudent basis</span>
              <h2>Annual loss exceedance</h2>
              <p>
                How likely is annual loss to exceed a given financial threshold?
              </p>
            </div>
            <Badge tone="indigo">{currency ?? "Currency unspecified"}</Badge>
          </div>
          <LossExceedanceCurve
            aep={result.loss.aep ?? []}
            prudent={prudent}
            currency={currency}
          />
        </GlassPanel>
        <GlassPanel className="driver-spotlight">
          <LossCategoryDonut
            categories={result.loss.categories ?? []}
            currency={currency}
          />
        </GlassPanel>
      </div>
    </>
  );
}

function RiskDrivers({
  result,
  currency,
}: {
  result: CRQResult;
  currency?: string | null;
}) {
  return (
    <>
      <GlassPanel className="funnel-panel">
        <div className="panel-title-row">
          <div>
            <span className="overline">Risk formation</span>
            <h2>From campaign to financial impact</h2>
          </div>
          <Badge tone="neutral">Interactive chain</Badge>
        </div>
        <p className="panel-intro">
          Explore each governed stage without merging architecture feasibility
          and control effectiveness.
        </p>
        <RiskFunnel formation={result.formation} currency={currency} />
      </GlassPanel>
      <div className="two-column">
        <GlassPanel>
          <div className="panel-title-row">
            <h2>Dominant actors</h2>
            <Target />
          </div>
          <RankedList
            items={result.decomposition.actors ?? []}
            currency={currency}
          />
        </GlassPanel>
        <GlassPanel>
          <div className="panel-title-row">
            <h2>Frequency funnel</h2>
            <Gauge />
          </div>
          <dl className="fact-list">
            {Object.entries(result.formation).map(([key, value]) => (
              <div key={key}>
                <dt>{human(key)}</dt>
                <dd>
                  {key.includes("probability")
                    ? percent(value)
                    : key === "aal"
                      ? money(value, currency)
                      : number(value, 4)}
                </dd>
              </div>
            ))}
          </dl>
        </GlassPanel>
      </div>
    </>
  );
}

function Scenarios({
  result,
  currency,
}: {
  result: CRQResult;
  currency?: string | null;
}) {
  const scenarios = result.decomposition.scenarios ?? [];
  return (
    <GlassPanel className="data-table-panel scenario-table-panel">
      <div className="panel-title-row">
        <div>
          <span className="overline">Modelled scenarios</span>
          <h2>Scenarios ranked by financial exposure</h2>
          <p>
            Compare the annual expected loss and tail-loss contribution returned
            for each scenario.
          </p>
        </div>
        <Badge tone="indigo">{scenarios.length} scenarios</Badge>
      </div>
      <div className="scenario-result-table">
        <div className="scenario-result-row scenario-result-head">
          <span>Rank</span>
          <span>Scenario</span>
          <span>Prudent AAL</span>
          <span>TVaR95 contribution</span>
          <span>TVaR99 contribution</span>
        </div>
        {scenarios.map((scenario: any, index: number) => (
          <div className="scenario-result-row" key={scenario.id ?? index}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <div>
              <strong>{scenario.name}</strong>
              {index === 0 && <Badge tone="red">Dominant</Badge>}
            </div>
            <strong>{money(scenario.metrics?.prudent_aal, currency)}</strong>
            <strong>{money(scenario.contribution?.tvar95, currency)}</strong>
            <strong>{money(scenario.contribution?.tvar99, currency)}</strong>
          </div>
        ))}
      </div>
    </GlassPanel>
  );
}

function AttackPaths({
  result,
  domain,
  onSelectedEntityChange,
}: {
  result: CRQResult;
  domain: "IT" | "OT";
  onSelectedEntityChange?: (
    entity: { entity_type: string; entity_id: string } | null,
  ) => void;
}) {
  const paths = result.architecture.route_path_states ?? [];
  const [actorFilter, setActorFilter] = useState("ALL");
  const [scenarioFilter, setScenarioFilter] = useState("ALL");
  const [routeFilter, setRouteFilter] = useState("ALL");
  const routeName = (path: any) =>
    String(path.route ?? (domain === "OT" ? "S1 → S5" : "Canonical path"));
  const actors = unique(paths.map((path: any) => String(path.actor)));
  const scenarios = unique(paths.map((path: any) => String(path.scenario)));
  const routes = unique(paths.map(routeName));
  useEffect(() => {
    onSelectedEntityChange?.(
      routeFilter === "ALL"
        ? null
        : { entity_type: "route", entity_id: routeFilter },
    );
  }, [onSelectedEntityChange, routeFilter]);
  const filtered = paths.filter(
    (path: any) =>
      (actorFilter === "ALL" || String(path.actor) === actorFilter) &&
      (scenarioFilter === "ALL" || String(path.scenario) === scenarioFilter) &&
      (routeFilter === "ALL" || routeName(path) === routeFilter),
  );
  const visible = filtered.slice(0, 50);
  const clearFilters = () => {
    setActorFilter("ALL");
    setScenarioFilter("ALL");
    setRouteFilter("ALL");
  };
  return (
    <>
      <GlassPanel className="path-explainer">
        <Network />
        <div>
          <span className="overline">
            {domain === "IT" ? "Threat-route analysis" : "S1–S5 progression"}
          </span>
          <h2>
            {domain === "IT"
              ? "How threats could reach critical services"
              : "How threats could progress through operations"}
          </h2>
          <p>
            Architecture feasibility is shown separately from control
            effectiveness. Filter the paths to focus on a particular actor,
            scenario or route.
          </p>
          {domain === "IT" && (
            <p className="path-meaning-note">
              <strong>How to read this:</strong> a route describes the access
              mechanism, not the actor’s identity. “Insider or trusted access”
              can include an external actor compromising or co-opting a trusted
              user or connection.
            </p>
          )}
        </div>
      </GlassPanel>
      <GlassPanel className="data-table-panel">
        <div className="panel-title-row">
          <h2>
            {domain === "IT" ? "Threat paths" : "Operational threat paths"}
          </h2>
          <Badge tone="neutral">
            Showing {visible.length} of {filtered.length}
          </Badge>
        </div>
        <div className="path-filters" aria-label="Attack path filters">
          <Filter />
          <label>
            Actor
            <select
              value={actorFilter}
              onChange={(event) => setActorFilter(event.target.value)}
            >
              <option value="ALL">All actors</option>
              {actors.map((value) => (
                <option value={value} key={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label>
            Scenario
            <select
              value={scenarioFilter}
              onChange={(event) => setScenarioFilter(event.target.value)}
            >
              <option value="ALL">All scenarios</option>
              {scenarios.map((value) => (
                <option value={value} key={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label>
            {domain === "IT" ? "Route" : "Path"}
            <select
              value={routeFilter}
              onChange={(event) => setRouteFilter(event.target.value)}
            >
              <option value="ALL">
                All {domain === "IT" ? "routes" : "paths"}
              </option>
              {routes.map((value) => (
                <option value={value} key={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={clearFilters}>
            Clear filters
          </button>
        </div>
        <div className="data-table">
          <div className="data-row data-head">
            <span>Actor</span>
            <span>Scenario</span>
            <span>{domain === "IT" ? "Route" : "Stage path"}</span>
            <span>Event probability</span>
            <span>Path success</span>
          </div>
          {visible.map((path: any, index: number) => (
            <div className="data-row" key={index}>
              <strong>{path.actor}</strong>
              <span>{path.scenario}</span>
              <span>{routeName(path)}</span>
              <span>{percent(path.annual_event_probability)}</span>
              <span>{percent(path.success_probability)}</span>
            </div>
          ))}
        </div>
        {filtered.length === 0 && (
          <div className="table-empty">
            No paths match the selected filters.
          </div>
        )}
        {filtered.length > visible.length && (
          <p className="table-limit-note">
            Showing the first 50 matching paths. Narrow the filters to review a
            smaller group.
          </p>
        )}
      </GlassPanel>
      <div className="canonical-grid">
        <CanonicalFamily
          title="Relevant TTPs"
          value={result.architecture.relevant_ttps}
        />
        <CanonicalFamily
          title="Barriers"
          value={result.architecture.barriers}
        />
        <CanonicalFamily
          title="Stage-through probabilities"
          value={result.architecture.stage_through_probabilities}
        />
        <CanonicalFamily
          title="Applicability"
          value={result.architecture.applicability}
        />
        <CanonicalFamily
          title="Feasibility"
          value={result.architecture.feasibility}
        />
      </div>
    </>
  );
}

function BusinessImpact({
  result,
  domain,
  currency,
}: {
  result: CRQResult;
  domain: "IT" | "OT";
  currency?: string | null;
}) {
  const categories = result.loss.categories ?? [];
  const [lossView, setLossView] = useState<
    "aal" | "contrib_tvar95" | "contrib_tvar99"
  >("aal");
  const lossViews = {
    aal: "AAL",
    contrib_tvar95: "TVaR95",
    contrib_tvar99: "TVaR99",
  } as const;
  const chart = categories
    .slice(0, 8)
    .map((item: any) => ({ name: item.name, value: item[lossView] }));
  const impacts =
    domain === "OT"
      ? (result.impact.ot_downtime ?? result.impact.ot_capacity)
      : {
          ...result.impact.it_affected_records,
          ...result.impact.it_affected_endpoints,
          ...result.impact.it_affected_services,
        };
  const drivers = Array.isArray(result.loss.drivers) ? result.loss.drivers : [];
  return (
    <>
      <div className="two-column wide-left">
        <GlassPanel className="chart-panel">
          <div className="panel-title-row">
            <div>
              <span className="overline">Loss decomposition</span>
              <h2>Business interruption and non-BI drivers</h2>
            </div>
            <div
              className="loss-view-switch"
              role="group"
              aria-label="Loss decomposition measure"
            >
              {Object.entries(lossViews).map(([key, label]) => (
                <button
                  type="button"
                  className={lossView === key ? "active" : ""}
                  aria-pressed={lossView === key}
                  onClick={() => setLossView(key as keyof typeof lossViews)}
                  key={key}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <FinancialBars
            data={chart}
            valueLabel={
              lossView === "aal"
                ? "Annual expected loss"
                : `${lossViews[lossView]} contribution`
            }
            currency={currency}
          />
        </GlassPanel>
        <GlassPanel>
          <h2>
            {domain === "OT"
              ? "Downtime & capacity"
              : "Affected digital estate"}
          </h2>
          <dl className="fact-list">
            {Object.entries(impacts ?? {})
              .slice(0, 12)
              .map(([key, value]) => (
                <div key={key}>
                  <dt>{human(key)}</dt>
                  <dd>
                    {key.includes("capacity") || key.startsWith("p_")
                      ? percent(value)
                      : number(value)}
                  </dd>
                </div>
              ))}
          </dl>
        </GlassPanel>
      </div>
      <div className="two-column">
        <GlassPanel>
          <div className="panel-title-row">
            <h2>Loss categories</h2>
            <Badge tone="neutral">{categories.length}</Badge>
          </div>
          <RankedList items={categories} valuePath="aal" currency={currency} />
        </GlassPanel>
        {drivers.length > 0 && (
          <GlassPanel>
            <div className="panel-title-row">
              <h2>Individual loss drivers</h2>
              <Badge tone="neutral">{drivers.length}</Badge>
            </div>
            <RankedList
              items={drivers}
              valuePath="aal"
              currency={currency}
              showCategory
            />
          </GlassPanel>
        )}
      </div>
      <div className="canonical-grid">
        <CanonicalFamily title="AEP curve" value={result.loss.aep} />
        <CanonicalFamily title="OEP curve" value={result.loss.oep} />
        <CanonicalFamily
          title="Return periods"
          value={result.loss.return_periods}
        />
        <CanonicalFamily
          title="Business interruption"
          value={result.loss.business_interruption}
        />
        <CanonicalFamily title="Non-BI" value={result.loss.non_bi} />
      </div>
    </>
  );
}

function Treatment({
  result,
  currency,
}: {
  result: CRQResult;
  currency?: string | null;
}) {
  const controls = result.treatments.individual_controls ?? [];
  const [treatmentView, setTreatmentView] = useState<
    "aal" | "tvar95" | "tvar99"
  >("aal");
  const treatmentViews = {
    aal: "AAL",
    tvar95: "TVaR95",
    tvar99: "TVaR99",
  } as const;
  const treatmentMetric = (control: any) => {
    if (treatmentView === "aal") {
      return {
        current: control.current_aal ?? control.prudent?.baseline,
        post: control.whatif_aal ?? control.prudent?.aal,
        change: control.reduction ?? control.prudent?.reduction,
      };
    }
    return {
      current: control.prudent?.[`${treatmentView}_base`],
      post: control.prudent?.[treatmentView],
      change: control.prudent?.[`${treatmentView}_change`],
    };
  };
  const modelled = controls.filter(
    (control: any) =>
      Number(control.reduction ?? control.prudent?.reduction ?? 0) > 0,
  );
  const largest = Math.max(
    0,
    ...controls.map((control: any) =>
      Number(control.reduction ?? control.prudent?.reduction ?? 0),
    ),
  );
  return controls.length ? (
    <>
      <div className="treatment-summary">
        <MetricCard
          label="Capabilities assessed"
          value={String(controls.length)}
        />
        <MetricCard
          label="Modelled reductions"
          value={String(modelled.length)}
        />
        <MetricCard
          label="Largest AAL reduction"
          value={money(largest, currency)}
        />
      </div>
      {modelled.length === 0 && (
        <GlassPanel className="treatment-notice">
          <Info />
          <div>
            <h2>No control-uplift benefit is present in this result</h2>
            <p>
              The approved engine output reports the same AAL before and after
              each proposed maturity uplift. The frontend will not invent a
              benefit. A governed engine run must return a non-zero treatment
              reduction before one is shown here.
            </p>
          </div>
        </GlassPanel>
      )}
      <GlassPanel className="data-table-panel">
        <div className="panel-title-row">
          <div>
            <span className="overline">Treatment analysis</span>
            <h2>Protective capability uplifts</h2>
            <p>
              Values below are displayed exactly as returned by the governed
              quantitative result.
            </p>
          </div>
          <div className="treatment-panel-actions">
            <div
              className="loss-view-switch"
              role="group"
              aria-label="Treatment measure"
            >
              {Object.entries(treatmentViews).map(([key, label]) => (
                <button
                  type="button"
                  className={treatmentView === key ? "active" : ""}
                  aria-pressed={treatmentView === key}
                  onClick={() =>
                    setTreatmentView(key as keyof typeof treatmentViews)
                  }
                  key={key}
                >
                  {label}
                </button>
              ))}
            </div>
            <Badge tone={modelled.length ? "green" : "amber"}>
              {modelled.length ? "Benefits modelled" : "No benefit returned"}
            </Badge>
          </div>
        </div>
        <div className="data-table treatment-table">
          <div className="data-row data-head">
            <span>Capability</span>
            <span>Current</span>
            <span>Modelled uplift</span>
            <span>Current {treatmentViews[treatmentView]}</span>
            <span>Post-treatment {treatmentViews[treatmentView]}</span>
            <span>Reduction</span>
          </div>
          {controls.slice(0, 16).map((control: any, index: number) => {
            const metric = treatmentMetric(control);
            const reduction = Number(metric.change ?? 0);
            return (
              <div className="data-row" key={control.cid ?? index}>
                <strong>
                  {control.name ?? control.channel ?? "Protective capability"}
                </strong>
                <span>{control.current ?? "Not returned"}</span>
                <span>
                  {control.target ??
                    control.next ??
                    control.whatif ??
                    "Not returned"}
                </span>
                <span>{money(metric.current, currency)}</span>
                <span>{money(metric.post, currency)}</span>
                <strong className={reduction > 0 ? "positive-value" : "muted"}>
                  {reduction > 0
                    ? money(reduction, currency)
                    : "No modelled change"}
                </strong>
              </div>
            );
          })}
        </div>
      </GlassPanel>
      {modelled.length > 0 && (
        <div className="canonical-grid">
          <CanonicalFamily
            title="Treatment packages"
            value={result.treatments.packages}
          />
          <CanonicalFamily
            title="Post-treatment metrics"
            value={result.treatments.post_treatment_metrics}
          />
          <CanonicalFamily
            title="Treatment priorities"
            value={result.treatments.rankings}
          />
        </div>
      )}
    </>
  ) : (
    <NoCanonicalData family="treatment" />
  );
}

function Insurance({
  result,
  currency,
}: {
  result: CRQResult;
  currency?: string | null;
}) {
  const insurance = result.insurance;
  if (
    !insurance ||
    Array.isArray(insurance) ||
    Object.keys(insurance).length === 0
  )
    return <NoCanonicalData family="insurance outputs" />;
  return (
    <div className="insurance-flow">
      {Object.entries(insurance).map(([key, value]) => (
        <GlassPanel key={key}>
          <span>{human(key)}</span>
          <strong>
            {typeof value === "number"
              ? money(value, currency)
              : JSON.stringify(value)}
          </strong>
        </GlassPanel>
      ))}
    </div>
  );
}

function Evidence({ result }: { result: CRQResult }) {
  const evidence = result.architecture.evidence_status ?? [];
  const placement = resultScreens.map((screen) => ({
    screen: screen.screen_id,
    count: outputMappings.filter((mapping: any) =>
      screen.prefixes.some((prefix: string) =>
        mapping.canonical_path.startsWith(prefix),
      ),
    ).length,
  }));
  const visibleRecord = Object.entries(result.provenance).filter(
    ([key]) =>
      !["hash", "engine", "methodology", "bundle", "pack", "version", "workbook", "spreadsheet", "source_path"].some(
        (term) => key.includes(term),
      ),
  );
  return (
    <>
      <div className="two-column">
        <GlassPanel>
          <div className="panel-title-row">
            <h2>Assessment record</h2>
            <ShieldCheck />
          </div>
          <dl className="fact-list">
            {visibleRecord.map(([key, value]) => (
              <div key={key}>
                <dt>{human(key)}</dt>
                <dd>{userFacingText(value)}</dd>
              </div>
            ))}
          </dl>
        </GlassPanel>
        <GlassPanel>
          <div className="panel-title-row">
            <h2>Result coverage</h2>
            <Boxes />
          </div>
          <div className="coverage-list">
            {placement.map((item) => (
              <div key={item.screen}>
                <span>{human(item.screen)}</span>
                <strong>{item.count} result families</strong>
              </div>
            ))}
          </div>
        </GlassPanel>
      </div>
      <GlassPanel>
        <div className="panel-title-row">
          <h2>Evidence records</h2>
          <Badge tone="indigo">{evidence.length}</Badge>
        </div>
        <div className="evidence-list">
          {evidence.slice(0, 18).map((item: any, index: number) => (
            <article key={item.evidence_id ?? index}>
              <FileSearch />
              <div>
                <strong>{userFacingText(item.description || "Supporting evidence")}</strong>
                <p>
                  {item.source
                    ? `Source: ${userFacingEvidenceSource(item.source)}`
                    : "Source not specified"}
                </p>
              </div>
              <Badge tone={item.source ? "green" : "amber"}>
                {item.source ? "Available" : "Review"}
              </Badge>
            </article>
          ))}
        </div>
      </GlassPanel>
    </>
  );
}

function CanonicalFamily({ title, value }: { title: string; value: unknown }) {
  const empty =
    value == null ||
    (Array.isArray(value) && value.length === 0) ||
    (typeof value === "object" &&
      !Array.isArray(value) &&
      Object.keys(value as object).length === 0);
  if (empty) return null;
  const entries = Array.isArray(value)
    ? value.slice(0, 4).map((item, index) => [String(index + 1), item] as const)
    : value && typeof value === "object"
      ? Object.entries(value as Record<string, unknown>).slice(0, 8)
      : [["value", value] as const];
  return (
    <GlassPanel className="canonical-family">
      <div className="panel-title-row">
        <h2>{title}</h2>
        <Badge tone={empty ? "neutral" : "indigo"}>
          {Array.isArray(value)
            ? `${value.length} records`
            : empty
              ? "Not returned"
              : "Canonical"}
        </Badge>
      </div>
      {empty ? (
        <p className="muted">
          No values returned for this optional canonical family.
        </p>
      ) : (
        <dl>
          {entries.map(([key, item]) => (
            <div key={key}>
              <dt>{human(key)}</dt>
              <dd>{digest(item)}</dd>
            </div>
          ))}
        </dl>
      )}
    </GlassPanel>
  );
}

function digest(value: unknown) {
  if (value == null) return "Not returned";
  if (typeof value !== "object") return userFacingText(value);
  if (Array.isArray(value)) return `${value.length} values`;
  const record = value as Record<string, unknown>;
  return userFacingText(
    record.name ??
      record.id ??
      record.route_id ??
      record.ttp_id ??
      `${Object.keys(record).length} details`,
  );
}

function human(value: string) {
  if (/workbook|spreadsheet|xlsx/i.test(value)) return "Assessment source";
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
function userFacingEvidenceSource(value: unknown) {
  const source = String(value);
  return /workbook|spreadsheet|xlsx/i.test(source) ? "Assessment evidence" : source;
}
function userFacingText(value: unknown) {
  const text = String(value);
  return /workbook|spreadsheet|\.xlsx\b/i.test(text) ? "Assessment evidence" : text;
}
function unique(values: string[]) {
  return [...new Set(values.filter(Boolean))].sort((a, b) =>
    a.localeCompare(b),
  );
}
