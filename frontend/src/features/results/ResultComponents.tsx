import {
  ArrowDown,
  ArrowRight,
  CheckCircle2,
  CircleDot,
  LockKeyhole,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge, EmptyState, GlassPanel } from "../../components/ui";

export const money = (value: unknown, currency?: string | null) =>
  typeof value === "number"
    ? currency
      ? new Intl.NumberFormat("en-AE", {
          style: "currency",
          currency,
          notation: "compact",
          maximumFractionDigits: 2,
        }).format(value)
      : `${new Intl.NumberFormat("en-AE", { notation: "compact", maximumFractionDigits: 2 }).format(value)} currency units`
    : "Not returned";
export const number = (value: unknown, digits = 2) =>
  typeof value === "number"
    ? new Intl.NumberFormat("en-AE", { maximumFractionDigits: digits }).format(
        value,
      )
    : "Not returned";
export const percent = (value: unknown, digits = 2) =>
  typeof value === "number"
    ? new Intl.NumberFormat("en-AE", {
        style: "percent",
        maximumFractionDigits: digits,
      }).format(value)
    : "Not returned";

export function MetricCard({
  label,
  value,
  comparison,
  tone = "neutral",
}: {
  label: string;
  value: string;
  comparison?: string;
  tone?: string;
}) {
  return (
    <GlassPanel className={`metric-card metric-card--${tone}`}>
      <div className="metric-label">
        <span>{label}</span>
        {tone === "red" ? (
          <ShieldAlert />
        ) : tone === "green" ? (
          <CheckCircle2 />
        ) : (
          <CircleDot />
        )}
      </div>
      <strong>{value}</strong>
      {comparison && <small>{comparison}</small>}
    </GlassPanel>
  );
}

export function FinancialBars({
  data,
  valueKey = "value",
  valueLabel = "Annual expected loss",
  currency,
}: {
  data: { name: string; [key: string]: any }[];
  valueKey?: string;
  valueLabel?: string;
  currency?: string | null;
}) {
  return (
    <div
      className="chart"
      role="img"
      aria-label={`${valueLabel} by loss category`}
    >
      <ResponsiveContainer width="100%" height={280}>
        <BarChart
          data={data}
          margin={{ top: 12, right: 10, left: 0, bottom: 20 }}
        >
          <CartesianGrid vertical={false} stroke="rgba(70,82,115,.08)" />
          <XAxis
            dataKey="name"
            tickFormatter={(value) =>
              String(value).length > 18
                ? `${String(value).slice(0, 16)}…`
                : String(value)
            }
            tick={{ fill: "#7b8599", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(value) =>
              new Intl.NumberFormat("en-AE", {
                notation: "compact",
                maximumFractionDigits: 1,
              }).format(Number(value))
            }
            tick={{ fill: "#7b8599", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={52}
          />
          <Tooltip
            cursor={false}
            content={({ active, label, payload }) =>
              active && payload?.length ? (
                <div className="chart-tooltip">
                  <strong>{String(label)}</strong>
                  <span>{valueLabel}</span>
                  <output>{money(Number(payload[0].value), currency)}</output>
                </div>
              ) : null
            }
          />
          <Bar dataKey={valueKey} radius={[7, 7, 0, 0]}>
            {data.map((item, index) => (
              <Cell
                key={item.name ?? index}
                fill={categoryColours[index % categoryColours.length]}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

type CurvePoint = {
  loss: number;
  exceedance_probability: number;
  basis?: string;
  label?: string;
};

export function LossExceedanceCurve({
  aep,
  prudent,
  currency,
}: {
  aep: CurvePoint[];
  prudent: Record<string, any>;
  currency?: string | null;
}) {
  const points = useMemo(() => {
    const governed = (aep ?? []).filter(
      (point) =>
        Number.isFinite(point.loss) &&
        Number.isFinite(point.exceedance_probability) &&
        (!point.basis || point.basis.toLowerCase().includes("prudent")),
    );
    if (governed.length >= 2)
      return [...governed]
        .sort((left, right) => left.loss - right.loss)
        .map((point) => ({
          ...point,
          label: point.label ?? "Annual exceedance point",
        }));
    return [
      {
        loss: 0,
        exceedance_probability: Number(prudent.p_any_event),
        label: "Probability of any event",
      },
      {
        loss: Number(prudent.var95),
        exceedance_probability: 0.05,
        label: "VaR95",
      },
      {
        loss: Number(prudent.var99),
        exceedance_probability: 0.01,
        label: "VaR99",
      },
    ].filter(
      (point) =>
        Number.isFinite(point.loss) &&
        Number.isFinite(point.exceedance_probability),
    );
  }, [aep, prudent]);
  const [active, setActive] = useState<CurvePoint & { label?: string }>(
    () => points[Math.min(1, points.length - 1)],
  );
  const canonicalSeries = (aep ?? []).length >= 2;
  return (
    <div className="exceedance-curve">
      <div className="curve-readout" aria-live="polite">
        <div>
          <span>Selected loss threshold</span>
          <strong>{money(active?.loss, currency)}</strong>
        </div>
        <div>
          <span>Annual exceedance probability</span>
          <strong>{percent(active?.exceedance_probability)}</strong>
        </div>
        <Badge tone={canonicalSeries ? "green" : "indigo"}>
          {canonicalSeries
            ? "Canonical AEP series"
            : "Governed headline anchors"}
        </Badge>
      </div>
      <div
        className="chart"
        role="img"
        aria-label="Interactive annual loss exceedance curve"
      >
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart
            data={points}
            margin={{ top: 14, right: 18, left: 6, bottom: 22 }}
            onMouseMove={(state: any) => {
              const point = state?.activePayload?.[0]?.payload;
              if (point) setActive(point);
            }}
          >
            <defs>
              <linearGradient id="aep-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#6f7fe2" stopOpacity=".28" />
                <stop offset="100%" stopColor="#9ea9ec" stopOpacity=".03" />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="rgba(70,82,115,.09)" strokeDasharray="3 5" />
            <XAxis
              type="number"
              dataKey="loss"
              domain={[0, "dataMax"]}
              tickFormatter={(value) => compactMoney(Number(value), currency)}
              tick={{ fill: "#7b8599", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
              label={{
                value: "Annual loss threshold",
                position: "insideBottom",
                offset: -14,
                fill: "#7b8599",
                fontSize: 11,
              }}
            />
            <YAxis
              type="number"
              dataKey="exceedance_probability"
              domain={[0, "dataMax"]}
              tickFormatter={(value) => percent(Number(value), 1)}
              tick={{ fill: "#7b8599", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
              width={58}
            />
            <Tooltip
              cursor={{
                stroke: "#7385e4",
                strokeWidth: 1,
                strokeDasharray: "4 4",
              }}
              content={({ active: shown, payload }) =>
                shown && payload?.length ? (
                  <div className="chart-tooltip">
                    <strong>{String(payload[0].payload.label)}</strong>
                    <span>Loss threshold</span>
                    <output>
                      {money(Number(payload[0].payload.loss), currency)}
                    </output>
                    <span>Annual exceedance probability</span>
                    <output>
                      {percent(
                        Number(payload[0].payload.exceedance_probability),
                      )}
                    </output>
                  </div>
                ) : null
              }
            />
            <Area
              type="monotone"
              dataKey="exceedance_probability"
              stroke="#6376da"
              strokeWidth={3}
              fill="url(#aep-fill)"
              activeDot={{
                r: 6,
                fill: "#fff",
                stroke: "#6376da",
                strokeWidth: 3,
              }}
              dot={{ r: 4, fill: "#6376da", stroke: "#fff", strokeWidth: 2 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <p className="curve-note">
        Move across the curve to inspect returned values.{" "}
        {canonicalSeries
          ? "Every point comes from the canonical AEP result."
          : "This demo result does not contain a full AEP series, so only exact returned headline anchors are shown."}
      </p>
    </div>
  );
}

function compactMoney(value: number, currency?: string | null) {
  return new Intl.NumberFormat("en-AE", {
    style: currency ? "currency" : "decimal",
    currency: currency ?? undefined,
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

const categoryColours = [
  "#6376da",
  "#8b83dc",
  "#5fa8bd",
  "#d88eaa",
  "#d5a65c",
  "#7e93b8",
  "#a18ac7",
  "#64a58e",
];

export function LossCategoryDonut({
  categories,
  currency,
}: {
  categories: Record<string, any>[];
  currency?: string | null;
}) {
  const data = categories.filter(
    (item) => typeof item.aal === "number" && item.aal >= 0,
  );
  const [activeIndex, setActiveIndex] = useState(0);
  const active = data[Math.min(activeIndex, Math.max(0, data.length - 1))];
  if (!data.length)
    return <NoCanonicalData family="loss-category decomposition" />;
  return (
    <div className="loss-donut">
      <div
        className="loss-donut-chart"
        role="img"
        aria-label="Interactive annual loss by category donut chart"
      >
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={data}
              dataKey="aal"
              nameKey="name"
              innerRadius={62}
              outerRadius={91}
              paddingAngle={2}
              onMouseEnter={(_, index) => setActiveIndex(index)}
            >
              {data.map((item, index) => (
                <Cell
                  key={item.id ?? item.name ?? index}
                  fill={categoryColours[index % categoryColours.length]}
                  stroke="#fff"
                  strokeWidth={2}
                />
              ))}
            </Pie>
            <Tooltip
              content={({ active: shown, payload }) =>
                shown && payload?.length ? (
                  <div className="chart-tooltip">
                    <strong>{String(payload[0].payload.name)}</strong>
                    <span>Annual expected loss</span>
                    <output>
                      {money(Number(payload[0].payload.aal), currency)}
                    </output>
                    <span>Share of AAL</span>
                    <output>{percent(payload[0].payload.pct_aal)}</output>
                  </div>
                ) : null
              }
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="loss-donut-centre">
          <span>Share of AAL</span>
          <strong>{percent(active?.pct_aal)}</strong>
        </div>
      </div>
      <div className="loss-donut-readout" aria-live="polite">
        <span className="overline">Selected loss category</span>
        <h2>{active?.name ?? "Not returned"}</h2>
        <strong>{money(active?.aal, currency)}</strong>
        <p>{percent(active?.pct_aal)} of annual expected loss</p>
        <div>
          <span>TVaR99 contribution</span>
          <strong>{money(active?.contrib_tvar99, currency)}</strong>
        </div>
      </div>
      <div className="loss-donut-legend">
        {data.slice(0, 8).map((item, index) => (
          <button
            type="button"
            className={index === activeIndex ? "active" : ""}
            onMouseEnter={() => setActiveIndex(index)}
            onFocus={() => setActiveIndex(index)}
            onClick={() => setActiveIndex(index)}
            key={item.id ?? item.name ?? index}
          >
            <i
              style={{
                background: categoryColours[index % categoryColours.length],
              }}
            />
            <span>{item.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function RiskFunnel({
  formation,
  currency,
}: {
  formation: Record<string, any>;
  currency?: string | null;
}) {
  const stages = [
    ["Campaigns", number(formation.campaigns_per_year, 3)],
    ["Threat actor", "Actor mix"],
    ["Scenario", "Scenario mix"],
    ["Route / path", percent(formation.conditional_success_probability)],
    ["Architecture", "Feasibility"],
    ["Controls", "Effectiveness"],
    ["Successful event", number(formation.successful_events_per_year, 4)],
    ["Financial impact", money(formation.aal, currency)],
  ];
  return (
    <div className="risk-funnel">
      {stages.map(([label, value], index) => (
        <div
          className={`funnel-stage funnel-stage--${index + 1}`}
          tabIndex={0}
          key={label}
        >
          <small>0{index + 1}</small>
          <span>{label}</span>
          <strong>{value}</strong>
          {index < stages.length - 1 && <ArrowRight className="funnel-arrow" />}
        </div>
      ))}
    </div>
  );
}

export function RankedList({
  items,
  valuePath = "metrics.prudent_aal",
  currency,
  showCategory = false,
}: {
  items: any[];
  valuePath?: string;
  currency?: string | null;
  showCategory?: boolean;
}) {
  const value = (item: any) =>
    valuePath.split(".").reduce((target, key) => target?.[key], item);
  const ranked = [...items].sort(
    (left, right) => (value(right) ?? 0) - (value(left) ?? 0),
  );
  return (
    <div className="ranked-list">
      {ranked.map((item, index) => (
        <article key={item.id ?? item.driver_id ?? item.name ?? index}>
          <span className="rank">{String(index + 1).padStart(2, "0")}</span>
          <div>
            <div className="ranked-title">
              <strong>{item.name ?? item.id}</strong>
              {showCategory && item.category && (
                <Badge tone="indigo">{item.category}</Badge>
              )}
            </div>
            <small>
              {showCategory && typeof item.pct_aal === "number"
                ? `${percent(item.pct_aal)} of annual expected loss`
                : (item.metadata?.description ??
                  item.category ??
                  "Canonical decomposition")}
            </small>
          </div>
          <span className="rank-value">
            {money(value(item) ?? item.aal, currency)}
          </span>
        </article>
      ))}
    </div>
  );
}

export function Direction({ value }: { value: number }) {
  return value < 0 ? (
    <span className="green-text">
      <TrendingDown />
      {percent(Math.abs(value))}
    </span>
  ) : (
    <span>
      <TrendingUp />
      {percent(value)}
    </span>
  );
}

export function StateBadge({ value }: { value: string }) {
  const normalized = value.toUpperCase();
  const tone =
    normalized === "CLOSED"
      ? "green"
      : normalized === "UNKNOWN"
        ? "amber"
        : normalized === "OPEN"
          ? "red"
          : "neutral";
  return <Badge tone={tone}>{normalized}</Badge>;
}

export function NoCanonicalData({ family }: { family: string }) {
  return (
    <GlassPanel>
      <EmptyState
        title={`No ${family} returned`}
        body="The approved canonical result does not contain this optional output family. The interface does not substitute or calculate a value."
      />
    </GlassPanel>
  );
}

export function FlowArrow() {
  return <ArrowDown className="flow-down" aria-hidden="true" />;
}
export function LockNote({ children }: { children: string }) {
  return (
    <span className="lock-note">
      <LockKeyhole />
      {children}
    </span>
  );
}
