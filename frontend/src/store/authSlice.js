/**
 * Redux slice for authentication state.
 *
 * State shape:
 *   user          – { id, email, email_verified_at, created_at } | null
 *   accessToken   – JWT string | null
 *   isLoading     – true while the silent-refresh boot check is in flight
 *   error         – last auth error message | null
 *
 * Persistence: access token + user are stored in localStorage for cross-domain
 * deployments where httpOnly cookies don't work.
 */

import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { loginUser, verifyOtp, refreshToken, logoutUser, clearStoredRefreshToken } from "../api/auth.js";

const AUTH_STORAGE_KEY = "accentiq_auth";

function persistAuth(user, accessToken) {
  if (user && accessToken) {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({ user, accessToken }));
  } else {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  }
}

function loadPersistedAuth() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    const { user, accessToken } = JSON.parse(raw);
    if (user && accessToken) return { user, accessToken };
  } catch { /* corrupted */ }
  return null;
}

// ── Async thunks ────────────────────────────────────────────────────────────

/** Silent boot-time refresh — called once in App on mount. */
export const initAuth = createAsyncThunk("auth/init", async (_, { rejectWithValue }) => {
  // Use persisted auth immediately (instant — no network wait)
  const persisted = loadPersistedAuth();

  // Try to refresh the token in background (gets a fresh access token)
  try {
    const data = await refreshToken();
    return data; // { access_token, user, refresh_token }
  } catch {
    // If refresh fails but we have persisted state, use it
    if (persisted) return { access_token: persisted.accessToken, user: persisted.user };
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

export const logout = createAsyncThunk("auth/logout", async () => {
  try {
    await logoutUser();
  } catch { /* ignore */ }
  clearStoredRefreshToken();
  persistAuth(null, null);
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
    user: loadPersistedAuth()?.user || null,
    accessToken: loadPersistedAuth()?.accessToken || null,
    isLoading: false,  // never block rendering — use persisted state instantly
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
        persistAuth(action.payload.user, action.payload.access_token);
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
        persistAuth(action.payload.user, action.payload.access_token);
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
        persistAuth(action.payload.user, action.payload.access_token);
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
        persistAuth(action.payload.user, action.payload.access_token);
      })
      .addCase(silentRefresh.rejected, (state) => {
        state.user = null;
        state.accessToken = null;
        persistAuth(null, null);
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
