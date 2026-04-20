import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Landing } from "@/pages/Landing";
import { LandingScreen } from "@/screens/LandingScreen";
import { ProfileScreen } from "@/screens/ProfileScreen";
import { SchoolMajorScreen } from "@/screens/SchoolMajorScreen";
import { SetYourCourseScreen } from "@/screens/SetYourCourseScreen";
import { CareerPickScreen } from "@/screens/CareerPickScreen";
import { RevealScreen } from "@/screens/RevealScreen";
import { GauntletScreen } from "@/screens/GauntletScreen";
import { BranchTreeScreen } from "@/screens/BranchTreeScreen";
import { SaveWrappedScreen } from "@/screens/SaveWrappedScreen";
import { MenuScreen } from "@/screens/MenuScreen";
import { MockupsShowcase } from "@/screens/MockupsShowcase";
import { PlaceholderScreen } from "@/screens/PlaceholderScreen";
import { AppHeader } from "@/components/ui/AppHeader";
import { GlobalChrome } from "@/components/ui/GlobalChrome";

export function AppRoutes() {
  return (
    <>
      <GlobalChrome />
      <AppHeader />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/app" element={<LandingScreen />} />
        <Route path="/profile" element={<ProfileScreen />} />
        <Route path="/school" element={<SchoolMajorScreen />} />
        <Route path="/set-your-course" element={<SetYourCourseScreen />} />
        <Route path="/career-pick" element={<CareerPickScreen />} />
        <Route path="/reveal" element={<RevealScreen />} />
        <Route path="/gauntlet" element={<GauntletScreen />} />
        <Route path="/branches" element={<BranchTreeScreen />} />
        <Route path="/save" element={<SaveWrappedScreen />} />
        <Route path="/menu" element={<MenuScreen />} />
        <Route path="/mockups/horizon" element={<MockupsShowcase />} />
        <Route
          path="/build"
          element={
            <PlaceholderScreen label="Career reveal — coming in F3" />
          }
        />
      </Routes>
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}

export default App;
