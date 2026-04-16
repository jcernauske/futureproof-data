import { BrowserRouter, Routes, Route } from "react-router-dom";
import { LandingScreen } from "@/screens/LandingScreen";
import { ProfileScreen } from "@/screens/ProfileScreen";
import { SchoolMajorScreen } from "@/screens/SchoolMajorScreen";
import { CareerPickScreen } from "@/screens/CareerPickScreen";
import { RevealScreen } from "@/screens/RevealScreen";
import { GauntletScreen } from "@/screens/GauntletScreen";
import { BranchTreeScreen } from "@/screens/BranchTreeScreen";
import { PlaceholderScreen } from "@/screens/PlaceholderScreen";
import { AppHeader } from "@/components/ui/AppHeader";

function App() {
  return (
    <BrowserRouter>
      <AppHeader />
      <Routes>
        <Route path="/" element={<LandingScreen />} />
        <Route path="/profile" element={<ProfileScreen />} />
        <Route path="/school" element={<SchoolMajorScreen />} />
        <Route path="/career-pick" element={<CareerPickScreen />} />
        <Route path="/reveal" element={<RevealScreen />} />
        <Route path="/gauntlet" element={<GauntletScreen />} />
        <Route path="/branches" element={<BranchTreeScreen />} />
        <Route
          path="/build"
          element={
            <PlaceholderScreen label="Career reveal — coming in F3" />
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
