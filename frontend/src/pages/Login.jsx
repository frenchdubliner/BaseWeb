import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import CaptchaWidget from "../components/CaptchaWidget";
import { useAuth } from "../context/AuthContext";
import { extractErrorMessage } from "../constants";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [captcha, setCaptcha] = useState({ token: "", provider: "turnstile" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const from = location.state?.from?.pathname || "/profile";

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const user = await login({
        email,
        password,
        captcha_token: captcha.token,
        captcha_provider: captcha.provider,
      });
      navigate(user.is_active ? from : "/account-pending", { replace: true });
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page page-narrow">
      <h1>Log in</h1>
      <form className="form" onSubmit={handleSubmit}>
        <label>
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>

        <CaptchaWidget onVerify={(token, provider) => setCaptcha({ token, provider })} />

        {error && <p className="form-error">{error}</p>}

        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Logging in..." : "Log in"}
        </button>
      </form>
      <p>
        <Link to="/forgot-password">Forgot your password?</Link>
      </p>
      <p>
        Don&apos;t have an account? <Link to="/register">Register</Link>
      </p>
    </div>
  );
}
