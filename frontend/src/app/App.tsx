import {Navigate, Route, Routes, useLocation} from "react-router-dom";
import {AppFrame} from "../components/AppFrame";
import {AssessmentSectionPage} from "../pages/AssessmentSectionPage";
import {CreateAssessmentPage} from "../pages/CreateAssessmentPage";
import {DashboardPage} from "../pages/DashboardPage";
import {LoginPage} from "../pages/LoginPage";
import {ResultsPage} from "../pages/ResultsPage";
import {ReviewRunPage} from "../pages/ReviewRunPage";
import {RunPage} from "../pages/RunPage";
import {AuthCallbackPage} from "../pages/AuthCallbackPage";
import {AuthGuard} from "../auth/AuthGuard";

export function App() {
  const location = useLocation();
  if (location.pathname === "/login") return <LoginPage />;
  if (location.pathname === "/auth/callback") return <AuthCallbackPage />;
  return <AuthGuard><AppFrame><Routes>
    <Route path="/" element={<Navigate to="/assessments" replace />} />
    <Route path="/assessments" element={<DashboardPage />} />
    <Route path="/assessments/new" element={<CreateAssessmentPage />} />
    <Route path="/assessments/:assessmentId/review-run" element={<ReviewRunPage />} />
    <Route path="/assessments/:assessmentId/:section" element={<AssessmentSectionPage />} />
    <Route path="/runs/:runId" element={<RunPage />} />
    <Route path="/results/:runId/:page" element={<ResultsPage />} />
    <Route path="*" element={<Navigate to="/assessments" replace />} />
  </Routes></AppFrame></AuthGuard>;
}
