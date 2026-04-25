import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export function LandingScreen() {
  const navigate = useNavigate();

  useEffect(() => {
    navigate("/set-your-course", { replace: true });
  }, [navigate]);

  return null;
}
