/**
 * Redux slice for anonymous/user quota state.
 *
 * State shape:
 *   used          – number of analyses used
 *   limit         – maximum allowed
 *   remaining     – limit - used
 *   requires_auth – true when the anon user has hit the free limit
 *   status        – "idle" | "loading" | "succeeded" | "failed"
 */

import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { getQuotaStatus } from "../api/quota.js";

export const fetchQuota = createAsyncThunk(
  "quota/fetch",
  async (_, { rejectWithValue }) => {
    try {
      return await getQuotaStatus();
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

const quotaSlice = createSlice({
  name: "quota",
  initialState: {
    used: 0,
    limit: 3,
    remaining: 3,
    requires_auth: false,
    status: "idle",
  },
  reducers: {
    // Optimistic local increment — corrected by the next fetchQuota call
    incrementLocal(state) {
      state.used = Math.min(state.used + 1, state.limit);
      state.remaining = Math.max(state.remaining - 1, 0);
      state.requires_auth = state.used >= state.limit;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchQuota.pending, (state) => {
        state.status = "loading";
      })
      .addCase(fetchQuota.fulfilled, (state, action) => {
        state.used = action.payload.used;
        state.limit = action.payload.limit;
        state.remaining = action.payload.remaining;
        state.requires_auth = action.payload.requires_auth;
        state.status = "succeeded";
      })
      .addCase(fetchQuota.rejected, (state) => {
        state.status = "failed";
        // Keep defaults showing (3/3) rather than hiding the pill
        if (state.used === 0 && state.limit === 0) {
          state.limit = 3;
          state.remaining = 3;
        }
      });
  },
});

export const { incrementLocal } = quotaSlice.actions;
export default quotaSlice.reducer;

// ── Selectors ───────────────────────────────────────────────────────────────
export const selectQuota = (state) => state.quota;
export const selectRequiresAuth = (state) => state.quota.requires_auth;
