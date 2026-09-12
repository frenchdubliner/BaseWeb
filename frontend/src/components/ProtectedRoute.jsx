import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children, requireVerified = false }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="page-loading">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requireVerified && !user.is_active) {
    return <Navigate to="/account-pending" replace />;
  }

  return children;
}
