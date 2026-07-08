import { createRoot } from "react-dom/client";
import { Provider } from "react-redux";
import { store } from "./store/store.js";
import App from "./App.jsx";
import "./index.css";

// Note: No StrictMode — it causes double API calls in development.
// StrictMode is a dev-only check that fires effects twice to find bugs.
// Re-enable for debugging if needed: wrap <App /> in <StrictMode>.
createRoot(document.getElementById("root")).render(
  <Provider store={store}>
    <App />
  </Provider>
);
