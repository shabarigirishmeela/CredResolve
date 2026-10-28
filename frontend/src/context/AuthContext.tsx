import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, DemoUser } from '../types';
import { apiClient } from '../api/client';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  demoLogin: (demoUser: DemoUser) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('credresolve_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('credresolve_token');
      const storedUser = localStorage.getItem('credresolve_user');
      if (storedToken && storedUser) {
        try {
          setUser(JSON.parse(storedUser));
          setToken(storedToken);
        } catch {
          localStorage.removeItem('credresolve_token');
          localStorage.removeItem('credresolve_user');
        }
      }
      setIsLoading(false);
    };
    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const data = await apiClient.login({ email, password });
      setToken(data.access_token);
      setUser(data.user);
      localStorage.setItem('credresolve_token', data.access_token);
      localStorage.setItem('credresolve_user', JSON.stringify(data.user));
    } finally {
      setIsLoading(false);
    }
  };

  const demoLogin = async (demoUser: DemoUser) => {
    await login(demoUser.email, demoUser.password);
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('credresolve_token');
    localStorage.removeItem('credresolve_user');
  };

  return (
    <AuthContext.Provider value={{
      user,
      token,
      isAuthenticated: !!token && !!user,
      isLoading,
      login,
      demoLogin,
      logout
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
