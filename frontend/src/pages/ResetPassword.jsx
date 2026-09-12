import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import client from "../api/client";
import { extractErrorMessage } from "../constants";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") || "";
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");
    setSubmitting(true);
    try {
      const { data } = await client.post("/password/reset/confirm/", {
        token,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setMessage(data.detail);
      setTimeout(() => navigate("/login"), 2000);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (!token) {
    return (
      <div className="page page-narrow">
        <h1>Reset password</h1>
        <p className="form-error">Missing reset token. Please use the link from your email.</p>
        <Link to="/forgot-password">Request a new link</Link>
      </div>
    );
  }

  return (
    <div className="page page-narrow">
      <h1>Reset your password</h1>
      <form className="form" onSubmit={handleSubmit}>
        <label>
          New password
          <input
            type="password"
            required
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
          />
        </label>
        <label>
          Confirm new password
          <input
            type="password"
            required
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
          />
        </label>

        {message && <p className="form-success">{message}</p>}
        {error && <p className="form-error">{error}</p>}

        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Resetting..." : "Reset password"}
        </button>
      </form>
    </div>
  );
}
