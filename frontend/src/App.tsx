import { BrowserRouter, Routes, Route } from "react-router-dom";
import { LandingScreen } from "@/screens/LandingScreen";
import { ProfileScreen } from "@/screens/ProfileScreen";
import { SchoolMajorScreen } from "@/screens/SchoolMajorScreen";
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
