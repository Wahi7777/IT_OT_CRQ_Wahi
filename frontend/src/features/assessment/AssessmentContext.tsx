import {createContext, useContext, useMemo, useState, type ReactNode} from "react";
import {approvedRequests, sectorPacks} from "../../contracts/governedData";
import type {AssessmentRunRequest, Domain} from "../../contracts/types";

type DataMode = "demo" | "api";

interface AssessmentState {
  domain: Domain;
  request: AssessmentRunRequest;
  setDomain: (domain: Domain) => void;
  setValue: (path: (string | number)[], value: unknown) => void;
  reset: () => void;
  dataMode: DataMode;
  setDataMode: (mode: DataMode) => void;
  preferences: {tvar_selection: "TVaR95" | "TVaR99"};
}

const Context = createContext<AssessmentState | null>(null);

export function AssessmentProvider({children}: {children: ReactNode}) {
  const [domain, setDomainState] = useState<Domain>("IT");
  const [requests, setRequests] = useState<Record<Domain, AssessmentRunRequest>>(() => ({
    IT: structuredClone(approvedRequests.IT),
    OT: structuredClone(approvedRequests.OT)
  }));
  const [dataMode, setDataMode] = useState<DataMode>(() =>
    import.meta.env.VITE_CRQ_DATA_MODE === "api" ? "api" : "demo"
  );
  const [preferences, setPreferences] = useState<{tvar_selection: "TVaR95" | "TVaR99"}>({tvar_selection: "TVaR99"});

  const value = useMemo<AssessmentState>(() => ({
    domain,
    request: requests[domain],
    dataMode,
    preferences,
    setDataMode,
    setDomain(next) {
      setDomainState(next);
    },
    setValue(path, nextValue) {
      if (path[0] === "__ui" && path[1] === "tvar_selection") {
        setPreferences({tvar_selection: nextValue as "TVaR95" | "TVaR99"});
        return;
      }
      if (path.join(".") === "assessment.assessment.domain" && (nextValue === "IT" || nextValue === "OT")) {
        setDomainState(nextValue);
        return;
      }
      setRequests((current) => {
        const next = structuredClone(current);
        let target: any = next[domain];
        for (let index = 0; index < path.length - 1; index += 1) target = target[path[index]];
        target[path.at(-1)!] = nextValue;
        if (path.join(".") === "assessment.assessment.sector") {
          const pack = sectorPacks.find((candidate) => candidate.domain === domain && candidate.sector === nextValue);
          if (pack) next[domain].model_bundle_reference.bundle_id = pack.pack_id;
        }
        return next;
      });
    },
    reset() {
      setRequests((current) => ({...current, [domain]: structuredClone(approvedRequests[domain])}));
    }
  }), [dataMode, domain, preferences, requests]);

  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useAssessment() {
  const value = useContext(Context);
  if (!value) throw new Error("useAssessment must be used inside AssessmentProvider");
  return value;
}
