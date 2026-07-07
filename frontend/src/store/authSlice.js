/**
 * Redux slice for authentication state.
 *
 * State shape:
 *   user          – { id, email, email_verified_at, created_at } | null
 *   accessToken   – JWT string kept in memory (never localStorage) | null
 *   isLoading     – true while the silent-refresh boot check is in flight
 *   error         – last auth error message | null
 */

import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { loginUser, verifyOtp, refreshToken, logoutUser } from "../api/auth.js";

// ── Async thunks ────────────────────────────────────────────────────────────

/** Silent boot-time refresh — called once in App on mount. */
export const initAuth = createAsyncThunk("auth/init", async (_, { rejectWithValue }) => {
  try {
    const data = await refreshToken();
    return data; // { access_token, user }
  } catch {
    return rejectWithValue(null); // not logged in — not an error
  }
});

export const login = createAsyncThunk(
  "auth/login",
  async ({ email, password }, { rejectWithValue }) => {
    try {
      return await loginUser(email, password);
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

export const verifyOtpAndRegister = createAsyncThunk(
  "auth/verifyOtp",
  async ({ email, otp, password }, { rejectWithValue }) => {
    try {
      return await verifyOtp(email, otp, password);
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

export const logout = createAsyncThunk("auth/logout", async (_, { rejectWithValue }) => {
  try {
    await logoutUser();
  } catch (err) {
    return rejectWithValue(err.message);
  }
});

export const silentRefresh = createAsyncThunk(
  "auth/silentRefresh",
  async (_, { rejectWithValue }) => {
    try {
      return await refreshToken();
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

// ── Slice ───────────────────────────────────────────────────────────────────

const authSlice = createSlice({
  name: "auth",
  initialState: {
    user: null,
    accessToken: null,
    isLoading: true,   // true until initAuth settles
    error: null,
  },
  reducers: {
    setAccessToken(state, action) {
      state.accessToken = action.payload;
    },
    clearError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // ── initAuth ─────────────────────────────────────────────
    builder
      .addCase(initAuth.fulfilled, (state, action) => {
        state.user = action.payload.user;
        state.accessToken = action.payload.access_token;
        state.isLoading = false;
      })
      .addCase(initAuth.rejected, (state) => {
        state.user = null;
        state.accessToken = null;
        state.isLoading = false;
      });

    // ── login ────────────────────────────────────────────────
    builder
      .addCase(login.pending, (state) => {
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.user = action.payload.user;
        state.accessToken = action.payload.access_token;
        state.error = null;
      })
      .addCase(login.rejected, (state, action) => {
        state.error = action.payload;
      });

    // ── verifyOtpAndRegister ─────────────────────────────────
    builder
      .addCase(verifyOtpAndRegister.pending, (state) => {
        state.error = null;
      })
      .addCase(verifyOtpAndRegister.fulfilled, (state, action) => {
        state.user = action.payload.user;
        state.accessToken = action.payload.access_token;
        state.error = null;
      })
      .addCase(verifyOtpAndRegister.rejected, (state, action) => {
        state.error = action.payload;
      });

    // ── logout ───────────────────────────────────────────────
    builder
      .addCase(logout.fulfilled, (state) => {
        state.user = null;
        state.accessToken = null;
        state.error = null;
      });

    // ── silentRefresh ────────────────────────────────────────
    builder
      .addCase(silentRefresh.fulfilled, (state, action) => {
        state.user = action.payload.user;
        state.accessToken = action.payload.access_token;
      })
      .addCase(silentRefresh.rejected, (state) => {
        state.user = null;
        state.accessToken = null;
      });
  },
});

export const { setAccessToken, clearError } = authSlice.actions;
export default authSlice.reducer;

// ── Selectors ───────────────────────────────────────────────────────────────
export const selectUser = (state) => state.auth.user;
export const selectAccessToken = (state) => state.auth.accessToken;
export const selectIsAuthenticated = (state) => !!state.auth.user;
export const selectAuthLoading = (state) => state.auth.isLoading;
export const selectAuthError = (state) => state.auth.error;
