import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in
    const storedSession = localStorage.getItem('supabase_session');
    if (storedSession) {
      try {
        const parsedSession = JSON.parse(storedSession);
        setSession(parsedSession);
        // Verify session is still valid
        verifySession(parsedSession.access_token);
      } catch (e) {
        localStorage.removeItem('supabase_session');
        setLoading(false);
      }
    } else {
      setLoading(false);
    }
  }, []);

  const verifySession = async (accessToken) => {
    try {
      const response = await axios.get(`${API}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });
      setUser(response.data.user);
      setLoading(false);
    } catch (error) {
      console.error('Session verification failed:', error);
      localStorage.removeItem('supabase_session');
      setSession(null);
      setUser(null);
      setLoading(false);
    }
  };

  const signUp = async (email, password, fullName = '', companyName = '') => {
    try {
      const response = await axios.post(`${API}/auth/signup`, {
        email,
        password,
        full_name: fullName,
        company_name: companyName
      });

      if (response.data.session) {
        const sessionData = response.data.session;
        setSession(sessionData);
        setUser(response.data.user);
        localStorage.setItem('supabase_session', JSON.stringify(sessionData));
      }

      return { success: true, data: response.data };
    } catch (error) {
      console.error('Sign up error:', error);
      return {
        success: false,
        error: error.response?.data?.detail || 'Sign up failed'
      };
    }
  };

  const signIn = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/signin`, {
        email,
        password
      });

      const sessionData = response.data.session;
      setSession(sessionData);
      setUser(response.data.user);
      localStorage.setItem('supabase_session', JSON.stringify(sessionData));

      return { success: true, data: response.data };
    } catch (error) {
      console.error('Sign in error:', error);
      return {
        success: false,
        error: error.response?.data?.detail || 'Invalid email or password'
      };
    }
  };

  const signOut = async () => {
    try {
      if (session?.access_token) {
        await axios.post(`${API}/auth/signout`, {}, {
          headers: {
            'Authorization': `Bearer ${session.access_token}`
          }
        });
      }
    } catch (error) {
      console.error('Sign out error:', error);
    } finally {
      setSession(null);
      setUser(null);
      localStorage.removeItem('supabase_session');
    }
  };

  const getAuthHeaders = () => {
    if (session?.access_token) {
      return {
        'Authorization': `Bearer ${session.access_token}`
      };
    }
    return {};
  };

  const value = {
    user,
    session,
    loading,
    signUp,
    signIn,
    signOut,
    getAuthHeaders,
    isAuthenticated: !!user
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
