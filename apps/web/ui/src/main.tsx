import { createRoot } from "react-dom/client";
import { setBaseUrl } from "@/api";
import App from "./App";
import "./index.css";

const savedBaseUrl = localStorage.getItem("mapping-api-base-url");
const envBaseUrl = import.meta.env.VITE_API_BASE_URL;
const baseUrl = savedBaseUrl || envBaseUrl || "";

if (baseUrl) {
  setBaseUrl(baseUrl);
}

if (!localStorage.getItem("mapping-user-id")) {
  localStorage.setItem("mapping-user-id", "dev-user");
}
if (!localStorage.getItem("mapping-user-role")) {
  localStorage.setItem("mapping-user-role", "analyst");
}

createRoot(document.getElementById("root")!).render(<App />);
