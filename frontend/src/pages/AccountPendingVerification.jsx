import { useLocation } from "react-router-dom";

import client from "../api/client";
import { useAuth } from "../context/AuthContext";
import { extractErrorMessage } from "../constants";
import { useState } from "react";

export default function AccountPendingVerification() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const email = user?.email || location.state?.email || "";
  const [message, setMessage] = useState("");

  const handleResend = async () => {
    setMessage("");
    try {
      const { data } = await client.post("/resend-verification/", { email });
      setMessage(data.detail);
    } catch (err) {
      setMessage(extractErrorMessage(err));
    }
  };

  return (
    <div className="page page-narrow">
      <h1>Verify your email</h1>
      <p>
        We sent a verification link to <strong>{email}</strong>. Please check your inbox (and spam
        folder) and click the link to activate your account.
      </p>
      <button type="button" className="button" onClick={handleResend}>
        Resend verification email
      </button>
      {message && <p className="form-hint">{message}</p>}
      {user && (
        <button type="button" className="button button-secondary" onClick={logout}>
          Logout
        </button>
      )}
    </div>
  );
}
