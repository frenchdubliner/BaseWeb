import { useEffect, useState } from "react";

import client from "../api/client";
import { useAuth } from "../context/AuthContext";
import { DROPOFF_LOCATIONS, PAYMENT_PREFERENCES, extractErrorMessage } from "../constants";

export default function Profile() {
  const { user, setUser } = useAuth();
  const [form, setForm] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [resendMessage, setResendMessage] = useState("");
  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [passwordMessage, setPasswordMessage] = useState("");
  const [passwordError, setPasswordError] = useState("");

  useEffect(() => {
    if (user) {
      setForm({
        first_name: user.first_name,
        last_name: user.last_name,
        phone_number: user.phone_number,
        dropoff_location: user.dropoff_location,
        payment_preference: user.payment_preference,
      });
    }
  }, [user]);

  if (!user || !form) return <div className="page-loading">Loading...</div>;

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage("");
    setError("");
    try {
      const { data } = await client.patch("/profile/", form);
      setUser(data);
      setMessage("Profile updated successfully.");
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  };

  const handleResend = async () => {
    setResendMessage("");
    try {
      const { data } = await client.post("/resend-verification/", { email: user.email });
      setResendMessage(data.detail);
    } catch (err) {
      setResendMessage(extractErrorMessage(err));
    }
  };

  const handlePasswordChange = async (event) => {
    event.preventDefault();
    setPasswordMessage("");
    setPasswordError("");
    try {
      const { data } = await client.post("/password/change/", passwordForm);
      setPasswordMessage(data.detail);
      setPasswordForm({ current_password: "", new_password: "", confirm_password: "" });
    } catch (err) {
      setPasswordError(extractErrorMessage(err));
    }
  };

  return (
    <div className="page page-narrow">
      <h1>Your profile</h1>

      {!user.is_active && (
        <div className="card notice">
          <p>Your email address is not verified yet. Some features are limited until you verify.</p>
          <button type="button" className="button" onClick={handleResend}>
            Resend verification email
          </button>
          {resendMessage && <p className="form-hint">{resendMessage}</p>}
        </div>
      )}

      <form className="form" onSubmit={handleSubmit}>
        <label>
          Email
          <input type="email" value={user.email} disabled />
        </label>
        <label>
          First name
          <input type="text" name="first_name" value={form.first_name} onChange={handleChange} />
        </label>
        <label>
          Last name
          <input type="text" name="last_name" value={form.last_name} onChange={handleChange} />
        </label>
        <label>
          Phone number
          <input type="tel" name="phone_number" value={form.phone_number} onChange={handleChange} />
        </label>
        <label>
          Dropoff location
          <select name="dropoff_location" value={form.dropoff_location} onChange={handleChange}>
            {DROPOFF_LOCATIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Payment preference
          <select name="payment_preference" value={form.payment_preference} onChange={handleChange}>
            {PAYMENT_PREFERENCES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        {message && <p className="form-success">{message}</p>}
        {error && <p className="form-error">{error}</p>}

        <button type="submit" className="button">
          Save changes
        </button>
      </form>

      {user.is_active && (
        <>
          <h2>Change password</h2>
          <form className="form" onSubmit={handlePasswordChange}>
            <label>
              Current password
              <input
                type="password"
                required
                value={passwordForm.current_password}
                onChange={(event) =>
                  setPasswordForm((prev) => ({ ...prev, current_password: event.target.value }))
                }
              />
            </label>
            <label>
              New password
              <input
                type="password"
                required
                value={passwordForm.new_password}
                onChange={(event) =>
                  setPasswordForm((prev) => ({ ...prev, new_password: event.target.value }))
                }
              />
            </label>
            <label>
              Confirm new password
              <input
                type="password"
                required
                value={passwordForm.confirm_password}
                onChange={(event) =>
                  setPasswordForm((prev) => ({ ...prev, confirm_password: event.target.value }))
                }
              />
            </label>

            {passwordMessage && <p className="form-success">{passwordMessage}</p>}
            {passwordError && <p className="form-error">{passwordError}</p>}

            <button type="submit" className="button">
              Change password
            </button>
          </form>
        </>
      )}
    </div>
  );
}
