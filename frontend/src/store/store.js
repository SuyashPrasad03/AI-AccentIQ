import { configureStore } from "@reduxjs/toolkit";
import authReducer from "./authSlice.js";
import quotaReducer from "./quotaSlice.js";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    quota: quotaReducer,
  },
});
