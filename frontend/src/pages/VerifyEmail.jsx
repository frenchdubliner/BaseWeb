import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import client from "../api/client";
import { extractErrorMessage } from "../constants";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState("verifying");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Missing verification token.");
      return;
    }

    client
      .post("/verify-email/", { token })
      .then((response) => {
        setStatus("success");
        setMessage(response.data.detail);
      })
      .catch((error) => {
        setStatus("error");
        setMessage(extractErrorMessage(error));
      });
  }, [token]);

  return (
    <div className="page page-narrow">
      <h1>Email verification</h1>
      {status === "verifying" && <p>Verifying your email...</p>}
      {status !== "verifying" && <p className={status === "error" ? "form-error" : ""}>{message}</p>}
      <Link className="button" to="/login">
        Go to login
      </Link>
    </div>
  );
}
