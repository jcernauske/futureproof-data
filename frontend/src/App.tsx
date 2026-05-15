import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ProfileScreen } from "@/screens/ProfileScreen";
import { SetYourCourseScreen } from "@/screens/SetYourCourseScreen";
import { FutureScreen } from "@/screens/FutureScreen";
import { MenuScreen } from "@/screens/MenuScreen";
import { MockupsShowcase } from "@/screens/MockupsShowcase";
import { ArchetypesShowcase } from "@/screens/ArchetypesShowcase";
import { BuildResultsScreen } from "@/screens/BuildResultsScreen";
import { AboutScreen } from "@/screens/AboutScreen";
import { AppHeader } from "@/components/ui/AppHeader";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { GlobalChrome } from "@/components/ui/GlobalChrome";
import { useDocumentLocale } from "@/i18n/useDocumentLocale";

export function AppRoutes() {
  useDocumentLocale();
  return (
    <>
      <GlobalChrome />
      <AppHeader />
      <Routes>
        <Route path="/" element={<Navigate to="/set-your-course" replace />} />
        <Route path="/profile" element={<ProfileScreen />} />
        <Route path="/set-your-course" element={<SetYourCourseScreen />} />
        <Route path="/my-build" element={<BuildResultsScreen />} />
        {/* /future is the canonical career-tree route. "Branches"
            doesn't read to students; "future" is the framing the
            product actually owns. The old lane-style BranchHorizonMap
            was deprecated 2026-05-01; /branches stays as a redirect
            for any in-flight bookmarks. */}
        <Route path="/future" element={<FutureScreen />} />
        <Route path="/branches" element={<Navigate to="/future" replace />} />
        <Route path="/menu" element={<Navigate to="/builds" replace />} />
        <Route path="/builds" element={<MenuScreen />} />
        <Route path="/about" element={<AboutScreen />} />
        {/* /help is the in-app "read the shape" page — twelve pentagons:
            nine real-build archetypes plus three illustrative missing-data
            shapes. /mockups/archetypes stays at the original nine so
            scripts/_archetype_screenshot.py (Kaggle writeup) keeps working. */}
        <Route path="/help" element={<ArchetypesShowcase />} />
        <Route path="/mockups/horizon" element={<MockupsShowcase />} />
        <Route
          path="/mockups/archetypes"
          element={<ArchetypesShowcase showMissingData={false} />}
        />
      </Routes>
    </>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
