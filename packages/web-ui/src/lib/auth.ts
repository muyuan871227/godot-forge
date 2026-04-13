"use client";

import api, { authApi } from "./api";

const DEMO_USER = {
  email: "demo@godotforge.dev",
  username: "demo",
  password: "demo123456",
};

let authInitialized = false;
let authPromise: Promise<void> | null = null;

export async function ensureAuth(): Promise<void> {
  if (authInitialized) return;
  if (authPromise) return authPromise;

  authPromise = _doAuth();
  try {
    await authPromise;
    authInitialized = true;
  } catch {
    authPromise = null;
  }
}

async function _doAuth(): Promise<void> {
  // Try existing token
  const existingToken = api.getAuthToken();
  if (existingToken) {
    try {
      await authApi.me();
      return;
    } catch {
      // Token expired
    }
  }

  // Register first (idempotent — if user exists, will fail and we login)
  try {
    const result = await authApi.register(DEMO_USER);
    if (result.access_token) {
      api.setAuthToken(result.access_token);
      return;
    }
  } catch {
    // User already exists, try login
  }

  // Login
  const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";
  const formData = new URLSearchParams();
  formData.set("username", DEMO_USER.username);
  formData.set("password", DEMO_USER.password);

  const resp = await fetch(`${BASE_URL}/api/v1/users/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formData,
  });

  if (!resp.ok) {
    throw new Error(`Login failed: ${resp.status}`);
  }

  const data = await resp.json();
  if (data.access_token) {
    api.setAuthToken(data.access_token);
  } else {
    throw new Error("No token in login response");
  }
}
