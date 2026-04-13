import { BrowserRouter, Routes, Route } from "react-router-dom";
import { LandingScreen } from "@/screens/LandingScreen";
import { ProfileScreen } from "@/screens/ProfileScreen";
import { PlaceholderScreen } from "@/screens/PlaceholderScreen";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingScreen />} />
        <Route path="/profile" element={<ProfileScreen />} />
        <Route
          path="/school"
          element={
            <PlaceholderScreen label="School + Major — coming soon" />
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
