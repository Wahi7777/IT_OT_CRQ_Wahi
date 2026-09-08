import {useSyncExternalStore, type ReactNode} from "react";
import {Navigate, useLocation} from "react-router-dom";
import {getSession, subscribeAuth} from "./CognitoAuth";

export function AuthGuard({children}: {children: ReactNode}) {
  const location = useLocation();
  const session = useSyncExternalStore(subscribeAuth, getSession, getSession);
  if (import.meta.env.VITE_CRQ_DATA_MODE !== "api") return children;
  return session ? children : <Navigate to="/login" replace state={{from: location.pathname + location.search}} />;
}
