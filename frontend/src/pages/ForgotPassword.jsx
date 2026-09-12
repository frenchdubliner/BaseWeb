import { useState } from "react";
import { Link } from "react-router-dom";

import CaptchaWidget from "../components/CaptchaWidget";
import client from "../api/client";
import { extractErrorMessage } from "../constants";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [captcha, setCaptcha] = useState({ token: "", provider: "turnstile" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");
    setSubmitting(true);
    try {
      const { data } = await client.post("/password/reset/", {
        email,
        captcha_token: captcha.token,
        captcha_provider: captcha.provider,
      });
      setMessage(data.detail);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page page-narrow">
      <h1>Forgot your password?</h1>
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

        <CaptchaWidget onVerify={(token, provider) => setCaptcha({ token, provider })} />

        {message && <p className="form-success">{message}</p>}
        {error && <p className="form-error">{error}</p>}

        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Sending..." : "Send reset link"}
        </button>
      </form>
      <p>
        <Link to="/login">Back to login</Link>
      </p>
    </div>
  );
}
