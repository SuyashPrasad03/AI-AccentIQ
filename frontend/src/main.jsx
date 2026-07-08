import { createRoot } from "react-dom/client";
import { Provider } from "react-redux";
import { store } from "./store/store.js";
import { ToastProvider } from "./components/Toast.jsx";
import App from "./App.jsx";
import "./index.css";

createRoot(document.getElementById("root")).render(
  <Provider store={store}>
    <ToastProvider>
      <App />
    </ToastProvider>
  </Provider>
);
