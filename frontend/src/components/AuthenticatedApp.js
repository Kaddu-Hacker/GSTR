import React, { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Login } from './Login';
import { Signup } from './Signup';
import { Loader2 } from 'lucide-react';

export const AuthenticatedApp = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const [showLogin, setShowLogin] = useState(true);

  // Show loading spinner while checking auth status
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-gray-950 via-gray-900 to-black">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Show login/signup if not authenticated
  if (!isAuthenticated) {
    return showLogin 
      ? <Login onSwitchToSignup={() => setShowLogin(false)} />
      : <Signup onSwitchToLogin={() => setShowLogin(true)} />;
  }

  // Show main app if authenticated
  return <>{children}</>;
};
