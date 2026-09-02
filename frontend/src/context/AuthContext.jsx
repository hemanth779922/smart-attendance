import React, { createContext, useContext, useState, useEffect } from "react";
import { api, getAuthToken, getStoredUser, setTokens, clearTokens } from "../api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(getStoredUser());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const token = getAuthToken();
      if (token) {
        try {
          const profile = await api.getMe();
          setUser(profile);
          localStorage.setItem("user", JSON.stringify(profile));
        } catch (err) {
          console.error("Session verification failed:", err);
          clearTokens();
          setUser(null);
        }
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  const login = async (email, password) => {
    const res = await api.login(email, password);
    const userInfo = {
      id: res.user_id,
      email: res.email,
      full_name: res.full_name,
      role: res.role,
    };
    setTokens(res.access_token, res.refresh_token, userInfo);
    setUser(userInfo);
    return userInfo;
  };

  const logout = () => {
    clearTokens();
    setUser(null);
  };

  const isAdmin = user?.role === "ADMIN";
  const isFaculty = user?.role === "FACULTY" || user?.role === "ADMIN";
  const isStudent = user?.role === "STUDENT";

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        isAdmin,
        isFaculty,
        isStudent,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
